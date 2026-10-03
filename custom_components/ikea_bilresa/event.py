"""Event entities: one per wheel channel, exposing clean scroll/press actions."""

from __future__ import annotations

import logging

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ACTION_HOLD,
    ACTION_PRESS,
    ACTION_RELEASE,
    ACTION_ROTATE,
    DIRECTION_UP,
    ET_HOLD,
    ET_RELEASE,
    ET_ROTATE_DOWN,
    ET_ROTATE_UP,
    PRESS_EVENT_TYPES,
    ROLE_BUTTON,
    SIGNAL_CONNECTION,
    SIGNAL_WHEELS_UPDATED,
    WHEEL_EVENT_TYPES,
    button_event_types,
    signal_channel,
)
from .coordinator import BilresaCoordinator
from .device_link import MatterDeviceLink
from .engine import WheelAction
from .entity import attach_to_device
from .model import BilresaWheel

_LOGGER = logging.getLogger(__name__)


def _duration_attributes(action: WheelAction) -> dict[str, int] | None:
    """Expose a duration only when one uninterrupted host observation exists."""
    if action.observed_duration_ms is None:
        return None
    return {"observed_duration_ms": action.observed_duration_ms}


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up event entities, reconciling as wheels are added or removed."""
    coordinator: BilresaCoordinator = entry.runtime_data
    # Keyed by (node_id, sub_id): sub_id is the channel for a wheel and the
    # endpoint id for a dual button. One node is only ever one variant, so the
    # two key spaces never collide within a node.
    entities: dict[tuple[int, int], EventEntity] = {}
    # Shared with the per-variant helpers below; cleared at the start of each
    # _sync so those helpers can append to them through the closure.
    desired: set[tuple[int, int]] = set()
    pending: list[EventEntity] = []

    @callback
    def _sync() -> None:
        desired.clear()
        pending.clear()
        for _node_id, wheel in coordinator.wheels.items():
            # Reconcile before constructing: existing registry entries are
            # moved first, so a new entity never lands beside a stale one.
            link = coordinator.device_links.link_for(wheel)
            if wheel.is_dual_button:
                _sync_buttons(wheel, link)
            else:
                _sync_channels(wheel, link)
        for key in list(entities):
            if key not in desired:
                entity = entities.pop(key)
                hass.async_create_task(entity.async_remove(force_remove=True))
        if pending:
            async_add_entities(list(pending))

    @callback
    def _sync_channels(wheel: BilresaWheel, link: MatterDeviceLink) -> None:
        channels = sorted(
            {e.channel for e in wheel.endpoints.values() if e.channel is not None}
        )
        for channel in channels:
            key = (wheel.node_id, channel)
            desired.add(key)
            existing = entities.get(key)
            if existing is None:
                entity = BilresaChannelEvent(coordinator, wheel, channel, link)
                entities[key] = entity
                pending.append(entity)
            elif isinstance(existing, BilresaChannelEvent):
                existing.update_wheel(wheel)

    @callback
    def _sync_buttons(wheel: BilresaWheel, link: MatterDeviceLink) -> None:
        # One entity per physical button, numbered 1..N in endpoint order.
        button_eps = sorted(
            ep for ep, e in wheel.endpoints.items() if e.role == ROLE_BUTTON
        )
        for index, endpoint_id in enumerate(button_eps, start=1):
            key = (wheel.node_id, endpoint_id)
            desired.add(key)
            existing = entities.get(key)
            if existing is None:
                entity = BilresaButtonEvent(
                    coordinator,
                    wheel,
                    endpoint_id,
                    index,
                    wheel.endpoints[endpoint_id].multi_press_max,
                    link,
                )
                entities[key] = entity
                pending.append(entity)
            elif isinstance(existing, BilresaButtonEvent):
                existing.update_wheel(wheel)

    _sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_WHEELS_UPDATED, _sync))


class BilresaChannelEvent(EventEntity):
    """A single wheel channel as an event entity."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_icon = "mdi:knob"
    _attr_event_types = WHEEL_EVENT_TYPES

    def __init__(
        self,
        coordinator: BilresaCoordinator,
        wheel: BilresaWheel,
        channel: int,
        link: MatterDeviceLink,
    ) -> None:
        self._coordinator = coordinator
        self._wheel = wheel
        self._channel = channel
        self._attr_unique_id = f"{wheel.node_id}_ch{channel}"
        self._attr_name = f"Channel {channel}"
        attach_to_device(self, wheel, link, model="BILRESA scroll wheel")

    @callback
    def update_wheel(self, wheel: BilresaWheel) -> None:
        """Refresh metadata after a Matter node or firmware update."""
        self._wheel = wheel

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
            if attributes := _duration_attributes(action):
                self._trigger_event(ET_HOLD, attributes)
            else:
                self._trigger_event(ET_HOLD)
        elif action.type == ACTION_RELEASE:
            if attributes := _duration_attributes(action):
                self._trigger_event(ET_RELEASE, attributes)
            else:
                self._trigger_event(ET_RELEASE)
        else:
            return
        self.async_write_ha_state()


class BilresaButtonEvent(EventEntity):
    """A single physical button of the dual button (E2489) as an event entity.

    Unlike a wheel channel, a button carries no channel: both endpoints report
    `channel = None`, so they share the same per-channel dispatcher signal and
    are told apart by endpoint id. The advertised event types omit rotation and
    are capped by the endpoint's MultiPressMax, so a device that cannot triple
    press never offers a triple-press trigger.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_icon = "bilresa:dual-button"

    def __init__(
        self,
        coordinator: BilresaCoordinator,
        wheel: BilresaWheel,
        endpoint_id: int,
        button_index: int,
        multi_press_max: int | None,
        link: MatterDeviceLink,
    ) -> None:
        self._coordinator = coordinator
        self._wheel = wheel
        self._endpoint_id = endpoint_id
        self._attr_unique_id = f"{wheel.node_id}_ep{endpoint_id}"
        self._attr_name = f"Button {button_index}"
        self._attr_event_types = button_event_types(multi_press_max)
        attach_to_device(self, wheel, link, model="BILRESA dual button")

    @callback
    def update_wheel(self, wheel: BilresaWheel) -> None:
        """Refresh metadata after a Matter node or firmware update."""
        self._wheel = wheel

    @property
    def available(self) -> bool:
        return self._coordinator.connected

    async def async_added_to_hass(self) -> None:
        # Both buttons share the channel=None signal; `_handle_action` filters
        # by endpoint so each entity keeps only its own button's gestures.
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                signal_channel(self._wheel.node_id, None),
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
        if action.endpoint_id != self._endpoint_id:
            return
        if action.type == ACTION_PRESS:
            event_type = PRESS_EVENT_TYPES.get(action.presses, PRESS_EVENT_TYPES[1])
            # A press count above this button's MultiPressMax is not advertised;
            # drop it rather than raise on an unknown event type.
            if event_type not in self.event_types:
                return
            self._trigger_event(event_type, {"presses": action.presses})
        elif action.type == ACTION_HOLD:
            if attributes := _duration_attributes(action):
                self._trigger_event(ET_HOLD, attributes)
            else:
                self._trigger_event(ET_HOLD)
        elif action.type == ACTION_RELEASE:
            if attributes := _duration_attributes(action):
                self._trigger_event(ET_RELEASE, attributes)
            else:
                self._trigger_event(ET_RELEASE)
        else:
            return
        self.async_write_ha_state()
