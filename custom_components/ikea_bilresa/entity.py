"""Shared base for the stateful per-channel entities (dials and switches).

`event.py` deliberately keeps its own copy of this logic: its entities predate
these, are covered by their own tests, and rewriting them to inherit here would
mix a refactor into a feature. This base exists so the two new platforms do not
duplicate device-registry reconciliation and availability between themselves.
"""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    SIGNAL_CONNECTION,
    SIGNAL_SETTINGS_UPDATED,
    SIGNAL_WHEELS_UPDATED,
    signal_channel,
)
from .coordinator import BilresaCoordinator
from .device_link import reconcile_wheel_device
from .engine import WheelAction
from .model import BilresaWheel


class BilresaChannelEntity(Entity):
    """One wheel channel, carrying the wheel's reconciled device identity."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BilresaCoordinator,
        wheel: BilresaWheel,
        channel: int,
        identifiers: set[tuple[str, str]],
        *,
        linked_to_matter: bool,
    ) -> None:
        self._coordinator = coordinator
        self._wheel = wheel
        self._channel = channel
        self._set_device_info(identifiers, linked_to_matter)

    @callback
    def update_wheel(
        self,
        wheel: BilresaWheel,
        identifiers: set[tuple[str, str]],
        *,
        linked_to_matter: bool,
    ) -> None:
        """Refresh metadata after a Matter node or firmware update."""
        self._wheel = wheel
        self._set_device_info(identifiers, linked_to_matter)

    @callback
    def _set_device_info(
        self, identifiers: set[tuple[str, str]], linked_to_matter: bool
    ) -> None:
        """Set registry metadata using identifiers already reconciled safely."""
        if linked_to_matter:
            # Keep core Matter's name and hardware metadata authoritative.
            self._attr_device_info = DeviceInfo(identifiers=identifiers)
            return
        self._attr_device_info = DeviceInfo(
            identifiers=identifiers,
            manufacturer="IKEA of Sweden",
            model="BILRESA scroll wheel",
            name=self._wheel.name,
        )

    @property
    def available(self) -> bool:
        """Unavailable while disconnected, and while the channel is disabled.

        A disabled channel never receives an action — the coordinator drops it
        — so leaving these entities showing a stale value as though they were
        live would misrepresent them.
        """
        return self._coordinator.connected and self._coordinator.channel_enabled(
            self._wheel.node_id, self._channel
        )

    async def async_added_to_hass(self) -> None:
        """Listen for this channel's actions, plus connection and settings."""
        await super().async_added_to_hass()
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
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_SETTINGS_UPDATED, self._handle_settings_updated
            )
        )

    @callback
    def _handle_settings_updated(self) -> None:
        """React to edited wheel settings.

        Availability always has to be repainted; a subclass that caches
        anything derived from the settings overrides this to rebuild it first.
        """
        self.async_write_ha_state()

    @callback
    def _handle_action(self, action: WheelAction) -> None:
        """Handle one decoded action for this channel."""
        raise NotImplementedError


@callback
def async_setup_channel_platform(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
    factory: Callable[
        [BilresaCoordinator, BilresaWheel, int, set[tuple[str, str]], bool],
        BilresaChannelEntity,
    ],
) -> None:
    """Create one entity per wheel channel, reconciling on hot add / remove.

    Dual buttons are skipped: they have endpoints rather than channels, so a
    dial or a per-channel toggle has nothing to address on them.
    """
    coordinator: BilresaCoordinator = entry.runtime_data
    entities: dict[tuple[int, int], BilresaChannelEntity] = {}

    @callback
    def _sync() -> None:
        desired: set[tuple[int, int]] = set()
        pending: list[BilresaChannelEntity] = []
        for wheel in coordinator.wheels.values():
            if wheel.is_dual_button:
                continue
            link = reconcile_wheel_device(
                hass,
                config_entry_id=entry.entry_id,
                matter_url=coordinator.url,
                server_info=coordinator.matter_server_info,
                wheel=wheel,
            )
            identifiers = set(link.identifiers)
            linked = link.device is not None
            channels = sorted(
                {e.channel for e in wheel.endpoints.values() if e.channel is not None}
            )
            for channel in channels:
                key = (wheel.node_id, channel)
                desired.add(key)
                existing = entities.get(key)
                if existing is None:
                    entity = factory(coordinator, wheel, channel, identifiers, linked)
                    entities[key] = entity
                    pending.append(entity)
                else:
                    existing.update_wheel(wheel, identifiers, linked_to_matter=linked)
        for key in list(entities):
            if key not in desired:
                entity = entities.pop(key)
                hass.async_create_task(entity.async_remove(force_remove=True))
        if pending:
            async_add_entities(pending)

    _sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_WHEELS_UPDATED, _sync))
