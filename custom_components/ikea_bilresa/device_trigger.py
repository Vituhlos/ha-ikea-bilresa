"""Device triggers for IKEA BILRESA remotes.

Lets users build automations from the device page — "When … Channel 1 scrolled
up" for a scroll wheel, or "When … Button 1 double-pressed" for the dual button —
without touching YAML. Each trigger is a thin wrapper around the
``ikea_bilresa_event`` bus event, filtered to this device: by channel for a
wheel, by endpoint for a dual button (whose buttons carry no channel).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import (
    ACTION_HOLD,
    ACTION_PRESS,
    ACTION_RELEASE,
    ACTION_ROTATE,
    DIRECTION_DOWN,
    DIRECTION_UP,
    DOMAIN,
    ET_DOUBLE_PRESS,
    ET_HOLD,
    ET_PRESS,
    ET_RELEASE,
    ET_ROTATE_DOWN,
    ET_ROTATE_UP,
    ET_TRIPLE_PRESS,
    EVENT_BILRESA,
    ROLE_BUTTON,
    button_event_types,
)
from .model import BilresaWheel

CONF_SUBTYPE = "subtype"

TRIGGER_TYPES = {
    ET_ROTATE_UP,
    ET_ROTATE_DOWN,
    ET_PRESS,
    ET_DOUBLE_PRESS,
    ET_TRIPLE_PRESS,
    ET_HOLD,
    ET_RELEASE,
}
CHANNELS = ("channel_1", "channel_2", "channel_3")
# The dual button (E2489) has buttons, not channels. Two is the real device;
# the schema allows a couple of extras so a hypothetical wider device still
# validates rather than being rejected.
BUTTONS = ("button_1", "button_2", "button_3", "button_4")

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
        vol.Required(CONF_SUBTYPE): vol.In((*CHANNELS, *BUTTONS)),
    }
)

# device-trigger type -> the event_data that identifies it on EVENT_BILRESA
_EVENT_DATA: dict[str, dict[str, Any]] = {
    ET_ROTATE_UP: {"type": ACTION_ROTATE, "direction": DIRECTION_UP},
    ET_ROTATE_DOWN: {"type": ACTION_ROTATE, "direction": DIRECTION_DOWN},
    ET_PRESS: {"type": ACTION_PRESS, "presses": 1},
    ET_DOUBLE_PRESS: {"type": ACTION_PRESS, "presses": 2},
    ET_TRIPLE_PRESS: {"type": ACTION_PRESS, "presses": 3},
    ET_HOLD: {"type": ACTION_HOLD},
    ET_RELEASE: {"type": ACTION_RELEASE},
}


def _node_id_for_device(hass: HomeAssistant, device_id: str) -> int | None:
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    for domain, identifier in device.identifiers:
        if domain == DOMAIN:
            try:
                return int(identifier)
            except ValueError:
                return None
    return None


def _wheel_for_device(hass: HomeAssistant, device_id: str) -> BilresaWheel | None:
    """Return the discovered BILRESA behind a device, or None if unknown.

    Used to tell a wheel from a dual button so the right triggers are offered.
    Read duck-typed from the loaded coordinator to avoid an import cycle.
    """
    node_id = _node_id_for_device(hass, device_id)
    if node_id is None:
        return None
    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        wheels = getattr(coordinator, "wheels", None)
        if wheels and node_id in wheels:
            return wheels[node_id]
    return None


def _button_endpoints(wheel: BilresaWheel) -> list[int]:
    """Button endpoint ids in the 1..N order used for `button_N` subtypes."""
    return sorted(ep for ep, e in wheel.endpoints.items() if e.role == ROLE_BUTTON)


def _button_endpoint(wheel: BilresaWheel | None, button_index: int) -> int | None:
    """Resolve a 1-based `button_N` subtype to its Matter endpoint id."""
    if wheel is None:
        return None
    endpoints = _button_endpoints(wheel)
    if 1 <= button_index <= len(endpoints):
        return endpoints[button_index - 1]
    return None


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for a BILRESA wheel or dual button."""
    base = {CONF_PLATFORM: "device", CONF_DOMAIN: DOMAIN, CONF_DEVICE_ID: device_id}
    wheel = _wheel_for_device(hass, device_id)
    if wheel is not None and wheel.is_dual_button:
        # Buttons, not channels: one subtype per physical button, and no rotation
        # or triple press — only the gestures the endpoint's MultiPressMax allows.
        return [
            {**base, CONF_TYPE: trigger_type, CONF_SUBTYPE: f"button_{index}"}
            for index, endpoint_id in enumerate(_button_endpoints(wheel), start=1)
            for trigger_type in button_event_types(
                wheel.endpoints[endpoint_id].multi_press_max
            )
        ]
    return [
        {**base, CONF_TYPE: trigger_type, CONF_SUBTYPE: channel}
        for channel in CHANNELS
        for trigger_type in TRIGGER_TYPES
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a device trigger by wrapping the ikea_bilresa_event."""
    subtype = config[CONF_SUBTYPE]
    node_id = _node_id_for_device(hass, config[CONF_DEVICE_ID])
    index = int(subtype.split("_")[1])
    if subtype.startswith("button_"):
        # A dual button has channel=None; its gestures are addressed by endpoint.
        event_data = {
            "node_id": node_id,
            "endpoint_id": _button_endpoint(
                _wheel_for_device(hass, config[CONF_DEVICE_ID]), index
            ),
            **_EVENT_DATA[config[CONF_TYPE]],
        }
    else:
        event_data = {
            "node_id": node_id,
            "channel": index,
            **_EVENT_DATA[config[CONF_TYPE]],
        }
    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_BILRESA,
            event_trigger.CONF_EVENT_DATA: event_data,
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
