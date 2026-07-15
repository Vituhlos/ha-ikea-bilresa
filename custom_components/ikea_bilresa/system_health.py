"""Provide System Health information for IKEA BILRESA."""

from __future__ import annotations

from typing import Any

from homeassistant.components import system_health
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, SUBENTRY_BINDING


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register IKEA BILRESA System Health callbacks."""
    register.async_register_info(_async_system_health_info)


async def _async_system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Return connection, discovery and binding information."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return {"configured": False}

    entry = entries[0]
    result: dict[str, Any] = {
        "configured": True,
        "config_entry_state": entry.state.value,
    }
    if entry.state is not ConfigEntryState.LOADED or not hasattr(entry, "runtime_data"):
        result.update(
            {
                "matter_server_connected": False,
                "matter_event_source": "unavailable",
                "discovered_wheels": 0,
                "configured_bindings": sum(
                    subentry.subentry_type == SUBENTRY_BINDING
                    for subentry in entry.subentries.values()
                ),
            }
        )
        return result

    coordinator = entry.runtime_data
    server_info = coordinator.matter_server_info or {}
    telemetry = coordinator.telemetry
    result.update(
        {
            "matter_server_connected": coordinator.connected,
            "matter_server_version": server_info.get("sdk_version", "unknown"),
            "matter_event_source": coordinator.event_source,
            "last_matter_event": telemetry["last_event_at"] or "never",
            "fallback_reason": telemetry["last_fallback_reason"] or "none",
            "discovered_wheels": len(coordinator.wheels),
            "configured_bindings": sum(
                subentry.subentry_type == SUBENTRY_BINDING
                for subentry in entry.subentries.values()
            ),
        }
    )
    return result
