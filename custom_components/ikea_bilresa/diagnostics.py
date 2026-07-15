"""Diagnostics support for the IKEA BILRESA integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import BilresaConfigEntry
from .const import (
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_HOLD_TARGET,
    CONF_NODE_ID,
    CONF_TARGET,
    CONF_TRIPLE_TARGET,
    CONF_URL,
)

TO_REDACT = {
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_HOLD_TARGET,
    CONF_NODE_ID,
    CONF_TARGET,
    CONF_TRIPLE_TARGET,
    CONF_URL,
    "compressed_fabric_id",
    "name",
    "serial",
    "title",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BilresaConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    wheels = [
        {
            "node_id": node_id,
            "name": wheel.name,
            "serial": wheel.serial,
            "endpoints": {
                ep: {"channel": e.channel, "role": e.role}
                for ep, e in wheel.endpoints.items()
            },
        }
        for node_id, wheel in coordinator.wheels.items()
    ]

    bindings = [
        {"title": subentry.title, **dict(subentry.data)}
        for subentry in entry.subentries.values()
    ]

    return async_redact_data(
        {
            "url": entry.data.get(CONF_URL),
            "matter_server_info": coordinator.matter_server_info,
            "matter_event_source": coordinator.event_source,
            "wheel_count": len(wheels),
            "wheels": wheels,
            "bindings": bindings,
            "telemetry": coordinator.telemetry,
        },
        TO_REDACT,
    )
