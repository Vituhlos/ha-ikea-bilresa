"""Switch entities: a toggle per wheel channel, flipped by the button."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import ACTION_PRESS
from .coordinator import BilresaCoordinator
from .engine import WheelAction
from .entity import BilresaChannelEntity, async_setup_channel_platform
from .model import BilresaWheel

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up one button toggle per wheel channel."""
    async_setup_channel_platform(
        hass,
        entry,
        async_add_entities,
        lambda coordinator, wheel, channel, identifiers, linked: (
            BilresaChannelButtonSwitch(
                coordinator, wheel, channel, identifiers, linked_to_matter=linked
            )
        ),
    )


class BilresaChannelButtonSwitch(BilresaChannelEntity, SwitchEntity, RestoreEntity):
    """A toggle flipped by each single press of a channel's centre button.

    Nothing is commanded on the device itself — the wheel is a stateless remote
    and this integration stays passive over Matter. The entity only remembers
    on/off so automations, dashboards and templates can hang off it.
    """

    _attr_icon = "mdi:gesture-tap-button"

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
        self._attr_unique_id = f"{wheel.node_id}_ch{channel}_button"
        self._attr_name = f"Button {channel}"
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            self._attr_is_on = last.state == STATE_ON

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set the toggle on from the UI or a service call."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Set the toggle off from the UI or a service call."""
        self._attr_is_on = False
        self.async_write_ha_state()

    @callback
    def _handle_action(self, action: WheelAction) -> None:
        # Single press only. Double, triple and hold keep their own events, so
        # binding one of them to something else stays possible.
        if action.type != ACTION_PRESS or action.presses != 1:
            return
        self._attr_is_on = not self._attr_is_on
        self.async_write_ha_state()
