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
from .device_link import resolve_matter_device, wheel_availability

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

    wheels = []
    for node_id, wheel in coordinator.wheels.items():
        # `matter_event_source` and `telemetry` below describe the server
        # connection and say nothing about one wheel. Resolving the linked core
        # Matter device is the only read-only way to tell a flat battery apart
        # from a dead server. `linked_to_matter` is included because it is the
        # reason availability can be "unknown".
        link = resolve_matter_device(
            hass,
            matter_url=coordinator.url,
            server_info=coordinator.matter_server_info,
            wheel=wheel,
        )
        wheels.append(
            {
                "node_id": node_id,
                "name": wheel.name,
                "serial": wheel.serial,
                "variant": wheel.variant,
                "linked_to_matter": link.device is not None,
                "availability": wheel_availability(hass, link.device),
                "endpoints": {
                    ep: {
                        "channel": e.channel,
                        "role": e.role,
                        "multi_press_max": e.multi_press_max,
                    }
                    for ep, e in wheel.endpoints.items()
                },
            }
        )

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
