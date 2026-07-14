"""The IKEA BILRESA (smooth scroll) integration.

Phase 1: connect to the Matter Server, discover BILRESA wheels, and for every
switch event (including the real-time ``multi_press_ongoing`` events the core
Matter integration currently drops) log it and fire an ``ikea_bilresa_event``
on the Home Assistant event bus. This is already usable as an automation
trigger; ``event`` entities and a smooth-dimming blueprint follow in phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CLUSTER_SWITCH,
    CONF_URL,
    DEFAULT_MATTER_URL,
    DOMAIN,
    EVENT_BILRESA,
)
from .matter_ws import MatterWSClient
from .model import BilresaWheel, decode_event, parse_node

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = []  # event entities arrive in phase 2

type BilresaConfigEntry = ConfigEntry["BilresaRuntime"]

SIGNAL_WHEELS_UPDATED = f"{DOMAIN}_wheels_updated"


def signal_action(node_id: int, endpoint_id: int) -> str:
    """Dispatcher signal for a single endpoint's decoded actions."""
    return f"{DOMAIN}_action_{node_id}_{endpoint_id}"


@dataclass
class BilresaRuntime:
    """Runtime data for a config entry."""

    client: MatterWSClient | None = None
    wheels: dict[int, BilresaWheel] = field(default_factory=dict)


def _matter_server_url(hass: HomeAssistant) -> str:
    """Best-effort discovery of the Matter Server WebSocket URL."""
    for entry in hass.config_entries.async_entries("matter"):
        if url := entry.data.get("url"):
            return url
    return DEFAULT_MATTER_URL


async def async_setup_entry(hass: HomeAssistant, entry: BilresaConfigEntry) -> bool:
    """Set up IKEA BILRESA from a config entry."""
    session = async_get_clientsession(hass)
    url = entry.data.get(CONF_URL) or _matter_server_url(hass)
    runtime = BilresaRuntime()

    @callback
    def _on_event(event_type: str, data) -> None:
        if event_type == "__nodes__":
            _handle_nodes(hass, runtime, data)
            return
        if event_type != "node_event" or not isinstance(data, dict):
            return
        if data.get("cluster_id") != CLUSTER_SWITCH:
            return
        wheel = runtime.wheels.get(data.get("node_id"))
        if wheel is None:
            return
        action = decode_event(wheel, data)
        if action is None:
            return

        _LOGGER.info(
            "BILRESA '%s' ch%s %s -> %s (count=%s) raw=%s",
            action["wheel_name"],
            action["channel"],
            action["role"],
            action["event_type"],
            action["count"],
            action["raw"],
        )
        hass.bus.async_fire(EVENT_BILRESA, action)
        async_dispatcher_send(
            hass, signal_action(action["node_id"], action["endpoint_id"]), action
        )

    client = MatterWSClient(url, session, _on_event)
    runtime.client = client
    entry.runtime_data = runtime

    _LOGGER.info("Connecting IKEA BILRESA listener to Matter Server at %s", url)
    await client.start()

    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


@callback
def _handle_nodes(hass: HomeAssistant, runtime: BilresaRuntime, nodes) -> None:
    """Parse the initial node dump and register any BILRESA wheels."""
    if not nodes:
        return
    found = 0
    for node in nodes:
        wheel = parse_node(node)
        if wheel is None:
            continue
        runtime.wheels[wheel.node_id] = wheel
        found += 1
        _LOGGER.info(
            "Discovered BILRESA wheel: node %s '%s' -> %s",
            wheel.node_id,
            wheel.name,
            {ep: (e.channel, e.role) for ep, e in wheel.endpoints.items()},
        )
    if found:
        async_dispatcher_send(hass, SIGNAL_WHEELS_UPDATED)
    else:
        _LOGGER.warning(
            "IKEA BILRESA connected to the Matter Server but found no BILRESA "
            "wheels among the commissioned nodes"
        )


async def async_unload_entry(hass: HomeAssistant, entry: BilresaConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = True
    if PLATFORMS:
        unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and entry.runtime_data.client:
        await entry.runtime_data.client.stop()
    return unloaded
