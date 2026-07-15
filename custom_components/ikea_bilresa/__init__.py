"""The IKEA BILRESA (smooth scroll) integration.

A passive Matter Server listener that turns the BILRESA scroll wheel's real-time
``multi_press_ongoing`` events (which the core Matter integration drops) into
clean, per-gesture actions — exposed as ``event`` entities, a bus event, and
(via config subentries) turnkey light bindings.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_URL, DEFAULT_MATTER_URL
from .coordinator import BilresaCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.EVENT]

type BilresaConfigEntry = ConfigEntry[BilresaCoordinator]


def _matter_server_url(hass: HomeAssistant) -> str:
    """Best-effort discovery of the Matter Server WebSocket URL."""
    for entry in hass.config_entries.async_entries("matter"):
        if url := entry.data.get("url"):
            return url
    return DEFAULT_MATTER_URL


async def async_setup_entry(hass: HomeAssistant, entry: BilresaConfigEntry) -> bool:
    """Set up IKEA BILRESA from a config entry."""
    url = entry.data.get(CONF_URL) or _matter_server_url(hass)
    coordinator = BilresaCoordinator(hass, url)
    entry.runtime_data = coordinator

    _LOGGER.info("Connecting IKEA BILRESA listener to Matter Server at %s", url)
    await coordinator.async_start()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_setup_bindings(entry)

    # Re-sync bindings in place when a subentry changes — no reload / reconnect.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: BilresaConfigEntry
) -> None:
    entry.runtime_data.async_setup_bindings(entry)


async def async_unload_entry(hass: HomeAssistant, entry: BilresaConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded
