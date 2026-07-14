"""Runtime coordinator: Matter Server listener + wheel/action dispatch."""

from __future__ import annotations

from dataclasses import asdict
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CLUSTER_SWITCH,
    EVENT_BILRESA,
    SIGNAL_WHEELS_UPDATED,
    signal_channel,
)
from .engine import GestureEngine, WheelAction
from .matter_ws import MatterWSClient
from .model import BilresaWheel, decode_event, parse_node

_LOGGER = logging.getLogger(__name__)


class BilresaCoordinator:
    """Owns the Matter Server connection and turns events into actions.

    Discovery and per-gesture state are keyed by node/endpoint, so any number
    of wheels are handled without configuration.
    """

    def __init__(self, hass: HomeAssistant, url: str) -> None:
        self.hass = hass
        self.url = url
        self.wheels: dict[int, BilresaWheel] = {}
        self._engine = GestureEngine()
        self._client = MatterWSClient(
            url, async_get_clientsession(hass), self._on_event
        )

    async def async_start(self) -> None:
        await self._client.start()

    async def async_stop(self) -> None:
        await self._client.stop()

    @callback
    def _on_event(self, event_type: str, data) -> None:
        if event_type == "__nodes__":
            self._handle_nodes(data)
            return
        if event_type != "node_event" or not isinstance(data, dict):
            return
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
        # Advanced surface: raw bus event (usable directly in automations).
        self.hass.bus.async_fire(EVENT_BILRESA, asdict(action))
        # Primary surface: per-channel dispatcher for entities and bindings.
        async_dispatcher_send(
            self.hass, signal_channel(action.node_id, action.channel), action
        )

    @callback
    def _handle_nodes(self, nodes) -> None:
        if not nodes:
            return
        added = False
        for node in nodes:
            wheel = parse_node(node)
            if wheel is None or wheel.node_id in self.wheels:
                continue
            self.wheels[wheel.node_id] = wheel
            added = True
            _LOGGER.info(
                "Discovered BILRESA wheel: node %s '%s' -> %s",
                wheel.node_id,
                wheel.name,
                {ep: (e.channel, e.role) for ep, e in wheel.endpoints.items()},
            )
        if added:
            self._engine.reset()
            async_dispatcher_send(self.hass, SIGNAL_WHEELS_UPDATED)
