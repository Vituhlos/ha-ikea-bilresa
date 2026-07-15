"""Event entities: one per wheel channel, exposing clean scroll/press actions."""

from __future__ import annotations

import logging

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ACTION_HOLD,
    ACTION_PRESS,
    ACTION_RELEASE,
    ACTION_ROTATE,
    DIRECTION_UP,
    DOMAIN,
    ET_HOLD,
    ET_RELEASE,
    ET_ROTATE_DOWN,
    ET_ROTATE_UP,
    PRESS_EVENT_TYPES,
    SIGNAL_CONNECTION,
    SIGNAL_WHEELS_UPDATED,
    WHEEL_EVENT_TYPES,
    signal_channel,
)
from .coordinator import BilresaCoordinator
from .engine import WheelAction
from .model import BilresaWheel

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up event entities, reconciling as wheels are added or removed."""
    coordinator: BilresaCoordinator = entry.runtime_data
    entities: dict[tuple[int, int], BilresaChannelEvent] = {}

    @callback
    def _sync() -> None:
        desired: set[tuple[int, int]] = set()
        new: list[BilresaChannelEvent] = []
        for node_id, wheel in coordinator.wheels.items():
            channels = sorted(
                {e.channel for e in wheel.endpoints.values() if e.channel is not None}
            )
            for channel in channels:
                key = (node_id, channel)
                desired.add(key)
                if key not in entities:
                    entity = BilresaChannelEvent(coordinator, wheel, channel)
                    entities[key] = entity
                    new.append(entity)
        for key in list(entities):
            if key not in desired:
                entity = entities.pop(key)
                hass.async_create_task(entity.async_remove(force_remove=True))
        if new:
            async_add_entities(new)

    _sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_WHEELS_UPDATED, _sync))


class BilresaChannelEvent(EventEntity):
    """A single wheel channel as an event entity."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_icon = "mdi:knob"
    _attr_event_types = WHEEL_EVENT_TYPES

    def __init__(
        self, coordinator: BilresaCoordinator, wheel: BilresaWheel, channel: int
    ) -> None:
        self._coordinator = coordinator
        self._wheel = wheel
        self._channel = channel
        self._attr_unique_id = f"{wheel.node_id}_ch{channel}"
        self._attr_name = f"Channel {channel}"
        # Always carry our own identifier (used by device triggers); when the
        # wheel reports a serial, also merge onto the core-Matter device.
        identifiers = {(DOMAIN, str(wheel.node_id))}
        if wheel.serial:
            identifiers.add(("matter", f"serial_{wheel.serial}"))
        self._attr_device_info = DeviceInfo(
            identifiers=identifiers,
            manufacturer="IKEA of Sweden",
            model="BILRESA scroll wheel",
            name=wheel.name,
        )

    @property
    def available(self) -> bool:
        return self._coordinator.connected

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                signal_channel(self._wheel.node_id, self._channel),
                self._handle_action,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_CONNECTION, self.async_write_ha_state
            )
        )

    @callback
    def _handle_action(self, action: WheelAction) -> None:
        if action.type == ACTION_ROTATE:
            event_type = (
                ET_ROTATE_UP if action.direction == DIRECTION_UP else ET_ROTATE_DOWN
            )
            self._trigger_event(event_type, {"notches": action.notches})
        elif action.type == ACTION_PRESS:
            event_type = PRESS_EVENT_TYPES.get(action.presses, PRESS_EVENT_TYPES[1])
            self._trigger_event(event_type, {"presses": action.presses})
        elif action.type == ACTION_HOLD:
            self._trigger_event(ET_HOLD)
        elif action.type == ACTION_RELEASE:
            self._trigger_event(ET_RELEASE)
        else:
            return
        self.async_write_ha_state()
