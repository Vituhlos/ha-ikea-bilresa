"""Number entities: a 1-100 dial per wheel channel, moved by scrolling.

This is the channel's own value, independent of any binding. A channel can
drive a light through a binding, carry a dial for automations to read, or both.
"""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .channel_controls import ScrollAccelerator, apply_rotation
from .const import (
    ACTION_ROTATE,
    DIAL_DEFAULT,
    DIAL_MAX,
    DIAL_MIN,
    DIRECTION_UP,
)
from .coordinator import BilresaCoordinator
from .engine import WheelAction
from .entity import BilresaChannelEntity, async_setup_channel_platform
from .model import BilresaWheel

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up one dial per wheel channel."""
    async_setup_channel_platform(
        hass,
        entry,
        async_add_entities,
        lambda coordinator, wheel, channel, identifiers, linked: BilresaChannelDial(
            coordinator, wheel, channel, identifiers, linked_to_matter=linked
        ),
    )


class BilresaChannelDial(BilresaChannelEntity, RestoreNumber):
    """A 1-100 value per wheel channel, adjusted by scrolling."""

    _attr_icon = "mdi:knob"
    _attr_native_min_value = DIAL_MIN
    _attr_native_max_value = DIAL_MAX
    _attr_native_step = 1.0
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: BilresaCoordinator,
        wheel: BilresaWheel,
        channel: int,
        identifiers: set[tuple[str, str]],
        *,
        linked_to_matter: bool,
    ) -> None:
        super().__init__(
            coordinator, wheel, channel, identifiers, linked_to_matter=linked_to_matter
        )
        self._attr_unique_id = f"{wheel.node_id}_ch{channel}_dial"
        self._attr_name = f"Dial {channel}"
        self._attr_native_value = DIAL_DEFAULT
        self._accelerator = self._new_accelerator()

    def _new_accelerator(self) -> ScrollAccelerator:
        """One accelerator per dial, so each channel measures its own scroll."""
        return ScrollAccelerator(
            self._coordinator.settings_for(self._wheel.node_id).acceleration
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            # Clamp on restore: the stored range is not guaranteed to match if
            # the bounds ever change.
            self._attr_native_value = min(
                DIAL_MAX, max(DIAL_MIN, float(last.native_value))
            )

    @callback
    def _handle_settings_updated(self) -> None:
        # Acceleration is read once at construction, so an edited setting has
        # to rebuild the accelerator, not just repaint the state.
        self._accelerator = self._new_accelerator()
        super()._handle_settings_updated()

    async def async_set_native_value(self, value: float) -> None:
        """Set the dial from the UI or a service call."""
        self._attr_native_value = value
        self.async_write_ha_state()

    @callback
    def _handle_action(self, action: WheelAction) -> None:
        if action.type != ACTION_ROTATE or action.notches <= 0:
            return
        settings = self._coordinator.settings_for(self._wheel.node_id)
        notches = self._accelerator.accelerate(action.notches, action.direction)
        current = self._attr_native_value
        self._attr_native_value = apply_rotation(
            current if current is not None else DIAL_DEFAULT,
            notches,
            action.direction == DIRECTION_UP,
            settings.step,
        )
        self.async_write_ha_state()
