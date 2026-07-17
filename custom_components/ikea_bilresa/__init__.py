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
from homeassistant.helpers.device_registry import (
    DeviceEntryType,
)
from homeassistant.helpers.device_registry import (
    async_get as async_get_device_registry,
)
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import CONF_URL, DEFAULT_MATTER_URL, DOMAIN, SUBENTRY_BINDING
from .coordinator import BilresaCoordinator
from .panel import async_remove_panel, async_setup_panel
from .panel_api import async_register_commands
from .presentation import migrate_generated_binding_title

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.EVENT]

type BilresaConfigEntry = ConfigEntry[BilresaCoordinator]


async def async_migrate_entry(hass: HomeAssistant, entry: BilresaConfigEntry) -> bool:
    """Remove the retired service device and normalize generated binding titles."""
    _LOGGER.debug(
        "Migrating IKEA BILRESA config entry from version %s.%s",
        entry.version,
        entry.minor_version,
    )

    if entry.version != 1:
        return False

    if entry.minor_version < 2:
        entity_registry = async_get_entity_registry(hass)
        if entity_id := entity_registry.async_get_entity_id(
            Platform.BINARY_SENSOR,
            DOMAIN,
            f"{entry.entry_id}_connection",
        ):
            entity_registry.async_remove(entity_id)

        device_registry = async_get_device_registry(hass)
        service_device = device_registry.async_get_device(
            identifiers={(DOMAIN, entry.entry_id)}
        )
        if (
            service_device is not None
            and service_device.entry_type is DeviceEntryType.SERVICE
        ):
            device_registry.async_remove_device(service_device.id)

        for subentry in entry.subentries.values():
            if subentry.subentry_type != SUBENTRY_BINDING:
                continue
            title = migrate_generated_binding_title(subentry.title)
            if title != subentry.title:
                hass.config_entries.async_update_subentry(entry, subentry, title=title)

        hass.config_entries.async_update_entry(entry, minor_version=2)

    _LOGGER.info("IKEA BILRESA config entry migration completed")
    return True


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

    # Panel last, and never fatal: a panel that cannot be served must degrade to
    # "no panel", not to a failed setup. Wheels, bindings and events do not
    # depend on it. See panel.py — this is still the Phase 0 spike.
    async_register_commands(hass)
    await async_setup_panel(hass)

    # Re-sync bindings in place when a subentry changes — no reload / reconnect.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: BilresaConfigEntry
) -> None:
    configured_url = entry.data.get(CONF_URL) or _matter_server_url(hass)
    if configured_url != entry.runtime_data.url:
        await hass.config_entries.async_reload(entry.entry_id)
        return
    entry.runtime_data.async_setup_bindings(entry)


async def async_unload_entry(hass: HomeAssistant, entry: BilresaConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        # Before stopping the coordinator: a sidebar entry pointing at an
        # unloaded integration is worse than no sidebar entry.
        async_remove_panel(hass)
        await entry.runtime_data.async_stop()
    return unloaded
