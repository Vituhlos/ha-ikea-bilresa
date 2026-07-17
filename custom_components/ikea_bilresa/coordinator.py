"""Runtime coordinator: Matter Server listener + wheel/action dispatch."""

from __future__ import annotations

import asyncio
from collections import Counter, deque
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later

from .binding import LightBinding
from .const import (
    CLUSTER_SWITCH,
    DISCONNECT_GRACE_SECONDS,
    DOMAIN,
    EVENT_BILRESA,
    ISSUE_CANNOT_CONNECT,
    SIGNAL_BINDING_ACTIVITY,
    SIGNAL_CONNECTION,
    SIGNAL_WHEELS_UPDATED,
    SUBENTRY_BINDING,
    signal_channel,
    signal_raw_button,
)
from .engine import GestureEngine, WheelAction
from .matter_core import CoreMatterEventSource, CoreMatterUnavailable
from .matter_ws import MatterWSClient
from .model import BilresaWheel, decode_event, parse_node

_LOGGER = logging.getLogger(__name__)


class BilresaCoordinator:
    """Owns the Matter Server connection and turns events into actions.

    Discovery and per-gesture state are keyed by node/endpoint, so any number
    of wheels are handled without configuration, including wheels commissioned
    or removed while Home Assistant is running.
    """

    def __init__(self, hass: HomeAssistant, url: str) -> None:
        self.hass = hass
        self.url = url
        self.connected = False
        self.wheels: dict[int, BilresaWheel] = {}
        self._engine = GestureEngine()
        self._client: CoreMatterEventSource | MatterWSClient = CoreMatterEventSource(
            hass, url, self._on_event, self._core_matter_unavailable
        )
        self._source_switch_lock = asyncio.Lock()
        self._stopping = False
        self._binding_unsubs: list[Callable[[], None]] = []
        self._binding_keys: set[tuple[int, int]] = set()
        self._bindings: dict[tuple[int, int], LightBinding] = {}
        self._disconnect_timer: Callable[[], None] | None = None
        self._event_counts: Counter[str] = Counter()
        self._ignored_counts: Counter[str] = Counter()
        self._recent_events: deque[dict[str, Any]] = deque(maxlen=20)
        self._actions_dispatched = 0
        self._connection_count = 0
        self._fallback_count = 0
        self._last_event_at: datetime | None = None
        self._last_fallback_reason: str | None = None

    @property
    def matter_server_info(self) -> dict | None:
        """Server info reported by the Matter Server (schema, sdk version)."""
        return self._client.server_info

    @property
    def event_source(self) -> str:
        """Return which Matter event stream is currently in use."""
        return self._client.source

    @property
    def telemetry(self) -> dict[str, Any]:
        """Return bounded, privacy-safe runtime counters for diagnostics."""
        return {
            "event_counts": dict(self._event_counts),
            "ignored_counts": dict(self._ignored_counts),
            "actions_dispatched": self._actions_dispatched,
            "connection_count": self._connection_count,
            "fallback_count": self._fallback_count,
            "last_fallback_reason": self._last_fallback_reason,
            "last_event_at": (
                self._last_event_at.isoformat() if self._last_event_at else None
            ),
            "recent_events": list(self._recent_events),
        }

    async def async_start(self) -> None:
        self._stopping = False
        try:
            await self._client.start()
        except CoreMatterUnavailable as err:
            _LOGGER.warning(
                "Cannot reuse Home Assistant's Matter client (%s); falling back "
                "to a dedicated read-only WebSocket",
                err,
            )
            self._fallback_count += 1
            self._last_fallback_reason = str(err)
            self._client = MatterWSClient(
                self.url, async_get_clientsession(self.hass), self._on_event
            )
            await self._client.start()

    async def async_stop(self) -> None:
        self._stopping = True
        self._detach_bindings()
        if self._disconnect_timer is not None:
            self._disconnect_timer()
            self._disconnect_timer = None
        await self._client.stop()

    @callback
    def _core_matter_unavailable(self, reason: str) -> None:
        """Schedule a one-way runtime fallback without blocking HA callbacks."""
        if self._stopping or not isinstance(self._client, CoreMatterEventSource):
            return
        self.hass.async_create_task(self._async_fallback_to_websocket(reason))

    async def _async_fallback_to_websocket(self, reason: str) -> None:
        async with self._source_switch_lock:
            if self._stopping or not isinstance(self._client, CoreMatterEventSource):
                return
            _LOGGER.warning(
                "Core Matter event source became unavailable (%s); switching "
                "to the dedicated passive WebSocket",
                reason,
            )
            self._fallback_count += 1
            self._last_fallback_reason = reason
            await self._client.stop()
            self._client = MatterWSClient(
                self.url, async_get_clientsession(self.hass), self._on_event
            )
            await self._client.start()

    # -- bindings ---------------------------------------------------------

    @callback
    def async_setup_bindings(self, entry: ConfigEntry) -> None:
        """(Re)attach light bindings from the entry's subentries, in place.

        Called on setup and whenever a binding subentry changes, so adding or
        editing a binding never needs a full reload / reconnect.
        """
        self._detach_bindings()
        for subentry in entry.subentries.values():
            if subentry.subentry_type != SUBENTRY_BINDING:
                continue
            binding = LightBinding(self.hass, dict(subentry.data))
            self._binding_unsubs.append(binding.async_attach())
            key = (binding.node_id, binding.channel)
            self._binding_keys.add(key)
            self._bindings[key] = binding
        if self._binding_unsubs:
            _LOGGER.debug("Attached %s light binding(s)", len(self._binding_unsubs))

    @callback
    def _detach_bindings(self) -> None:
        for unsub in self._binding_unsubs:
            unsub()
        self._binding_unsubs.clear()
        self._binding_keys.clear()
        self._bindings.clear()

    @callback
    def test_binding_action(self, action: WheelAction) -> bool:
        """Execute a synthetic panel test through one configured binding."""
        binding = self._bindings.get((action.node_id, action.channel or 0))
        if binding is None:
            return False
        binding.test_action(action)
        return True

    # -- event handling ---------------------------------------------------

    @callback
    def _on_event(self, event_type: str, data) -> None:
        self._event_counts[event_type] += 1
        if event_type == "__connected__":
            self._set_connected(True)
        elif event_type == "__disconnected__":
            self._set_connected(False)
        elif event_type == "__nodes__":
            self._handle_nodes(data)
        elif event_type == "node_added":
            self._add_node(data)
        elif event_type == "node_removed":
            self._remove_node(data)
        elif event_type == "node_event" and isinstance(data, dict):
            self._last_event_at = datetime.now(UTC)
            self._recent_events.append(
                {
                    "endpoint_id": data.get("endpoint_id"),
                    "cluster_id": data.get("cluster_id"),
                    "event_id": data.get("event_id"),
                    "event_number": data.get("event_number"),
                }
            )
            self._handle_node_event(data)
        else:
            self._ignored_counts["unsupported_event"] += 1

    @callback
    def _handle_node_event(self, data: dict) -> None:
        if data.get("cluster_id") != CLUSTER_SWITCH:
            self._ignored_counts["non_switch_cluster"] += 1
            return
        node_id = data.get("node_id")
        wheel = self.wheels.get(node_id) if node_id is not None else None
        if wheel is None:
            self._ignored_counts["unknown_wheel"] += 1
            return
        decoded = decode_event(wheel, data)
        if decoded is None:
            self._ignored_counts["undecodable_switch_event"] += 1
            return
        # Internal gesture metadata lets bindings distinguish trailing updates
        # from a deliberate new rotation and lets fast button bindings react to
        # ShortRelease. It never reaches the public HA event bus.
        async_dispatcher_send(
            self.hass,
            signal_raw_button(wheel.node_id, decoded["channel"]),
            decoded["role"],
            decoded["event_type"],
        )
        action = self._engine.process(wheel, decoded)
        if action is not None:
            self._dispatch(action)
        else:
            self._ignored_counts["non_actionable_switch_event"] += 1

    @callback
    def _dispatch(self, action: WheelAction) -> None:
        self._actions_dispatched += 1
        _LOGGER.debug(
            "action: node=%s ch=%s %s dir=%s notches=%s presses=%s",
            action.node_id,
            action.channel,
            action.type,
            action.direction,
            action.notches,
            action.presses,
        )
        event_data = asdict(action)
        device = dr.async_get(self.hass).async_get_device(
            identifiers={(DOMAIN, str(action.node_id))}
        )
        if device is not None:
            event_data["device_id"] = device.id
        self.hass.bus.async_fire(EVENT_BILRESA, event_data)
        async_dispatcher_send(
            self.hass, signal_channel(action.node_id, action.channel), action
        )
        if (action.node_id, action.channel) not in self._binding_keys:
            async_dispatcher_send(
                self.hass,
                SIGNAL_BINDING_ACTIVITY,
                {
                    **event_data,
                    "dispatch_status": "not_configured",
                    "dispatched": False,
                    "result": None,
                    "reason": "binding_not_configured",
                },
            )

    # -- discovery (initial dump + hot add/remove) ------------------------

    @callback
    def _handle_nodes(self, nodes) -> None:
        if not nodes:
            return
        added = False
        for node in nodes:
            if self._register_wheel(node):
                added = True
        if added:
            self._engine.reset()
            async_dispatcher_send(self.hass, SIGNAL_WHEELS_UPDATED)

    @callback
    def _add_node(self, node) -> None:
        if self._register_wheel(node):
            async_dispatcher_send(self.hass, SIGNAL_WHEELS_UPDATED)

    @callback
    def _register_wheel(self, node) -> bool:
        wheel = parse_node(node)
        if wheel is None:
            return False
        existing = self.wheels.get(wheel.node_id)
        if existing == wheel:
            return False
        self.wheels[wheel.node_id] = wheel
        if existing is not None:
            _LOGGER.info("Updated BILRESA wheel metadata for node %s", wheel.node_id)
            return True
        _LOGGER.info(
            "Discovered BILRESA %s: node %s '%s' -> %s",
            wheel.variant,
            wheel.node_id,
            wheel.name,
            {ep: (e.channel, e.role) for ep, e in wheel.endpoints.items()},
        )
        return True

    @callback
    def _remove_node(self, data) -> None:
        node_id = data if isinstance(data, int) else (data or {}).get("node_id")
        if node_id in self.wheels:
            wheel = self.wheels.pop(node_id)
            _LOGGER.info("BILRESA wheel removed: node %s '%s'", node_id, wheel.name)
            async_dispatcher_send(self.hass, SIGNAL_WHEELS_UPDATED)

    # -- connection state + repair issue ----------------------------------

    @callback
    def _set_connected(self, connected: bool) -> None:
        if connected and not self.connected:
            self._connection_count += 1
        self.connected = connected
        if connected:
            if self._disconnect_timer is not None:
                self._disconnect_timer()
                self._disconnect_timer = None
            ir.async_delete_issue(self.hass, DOMAIN, ISSUE_CANNOT_CONNECT)
        elif self._disconnect_timer is None:
            self._disconnect_timer = async_call_later(
                self.hass, DISCONNECT_GRACE_SECONDS, self._raise_connect_issue
            )
        async_dispatcher_send(self.hass, SIGNAL_CONNECTION)

    @callback
    def _raise_connect_issue(self, _now) -> None:
        self._disconnect_timer = None
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            ISSUE_CANNOT_CONNECT,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=ISSUE_CANNOT_CONNECT,
            translation_placeholders={"url": self.url},
        )
