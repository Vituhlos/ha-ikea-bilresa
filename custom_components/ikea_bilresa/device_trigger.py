"""Device triggers for IKEA BILRESA scroll wheels.

Lets users build automations from the device page ("When … Channel 1 scrolled
up") without touching YAML. Each trigger is a thin wrapper around the
``ikea_bilresa_event`` bus event, filtered to this wheel and channel.
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
)

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

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
        vol.Required(CONF_SUBTYPE): vol.In(CHANNELS),
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


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for a BILRESA wheel."""
    base = {CONF_PLATFORM: "device", CONF_DOMAIN: DOMAIN, CONF_DEVICE_ID: device_id}
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
    channel = int(config[CONF_SUBTYPE].split("_")[1])
    event_data = {
        "node_id": _node_id_for_device(hass, config[CONF_DEVICE_ID]),
        "channel": channel,
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
