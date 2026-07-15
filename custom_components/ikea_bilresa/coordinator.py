"""Runtime coordinator: Matter Server listener + wheel/action dispatch."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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
    SIGNAL_CONNECTION,
    SIGNAL_WHEELS_UPDATED,
    SUBENTRY_BINDING,
    signal_channel,
)
from .engine import GestureEngine, WheelAction
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
        self._client = MatterWSClient(
            url, async_get_clientsession(hass), self._on_event
        )
        self._binding_unsubs: list[Callable[[], None]] = []
        self._disconnect_timer: Callable[[], None] | None = None

    @property
    def matter_server_info(self) -> dict | None:
        """Server info reported by the Matter Server (schema, sdk version)."""
        return self._client.server_info

    async def async_start(self) -> None:
        await self._client.start()

    async def async_stop(self) -> None:
        self._detach_bindings()
        if self._disconnect_timer is not None:
            self._disconnect_timer()
            self._disconnect_timer = None
        await self._client.stop()

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
        if self._binding_unsubs:
            _LOGGER.debug("Attached %s light binding(s)", len(self._binding_unsubs))

    @callback
    def _detach_bindings(self) -> None:
        for unsub in self._binding_unsubs:
            unsub()
        self._binding_unsubs.clear()

    # -- event handling ---------------------------------------------------

    @callback
    def _on_event(self, event_type: str, data) -> None:
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
            self._handle_node_event(data)

    @callback
    def _handle_node_event(self, data: dict) -> None:
        if data.get("cluster_id") != CLUSTER_SWITCH:
            return
        wheel = self.wheels.get(data.get("node_id"))
        if wheel is None:
            return
        decoded = decode_event(wheel, data)
        if decoded is None:
            return
        action = self._engine.process(wheel, decoded)
        if action is not None:
            self._dispatch(action)

    @callback
    def _dispatch(self, action: WheelAction) -> None:
        _LOGGER.debug(
            "action: node=%s ch=%s %s dir=%s notches=%s presses=%s",
            action.node_id,
            action.channel,
            action.type,
            action.direction,
            action.notches,
            action.presses,
        )
        self.hass.bus.async_fire(EVENT_BILRESA, asdict(action))
        async_dispatcher_send(
            self.hass, signal_channel(action.node_id, action.channel), action
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
        if wheel is None or wheel.node_id in self.wheels:
            return False
        self.wheels[wheel.node_id] = wheel
        _LOGGER.info(
            "Discovered BILRESA wheel: node %s '%s' -> %s",
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
