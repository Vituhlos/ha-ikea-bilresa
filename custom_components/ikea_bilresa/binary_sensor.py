"""Binary sensor exposing the Matter Server connection state."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_CONNECTION
from .coordinator import BilresaCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the connection binary sensor."""
    async_add_entities([BilresaConnectionSensor(entry.entry_id, entry.runtime_data)])


class BilresaConnectionSensor(BinarySensorEntity):
    """Reports whether the listener is connected to the Matter Server."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = None
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "matter_server"

    def __init__(self, entry_id: str, coordinator: BilresaCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry_id}_connection"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="IKEA BILRESA",
            manufacturer="Vituhlos",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def is_on(self) -> bool:
        return self._coordinator.connected

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_CONNECTION, self.async_write_ha_state
            )
        )
