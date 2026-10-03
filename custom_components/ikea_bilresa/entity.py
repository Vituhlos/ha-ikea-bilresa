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
from .device_link import MatterDeviceLink, node_identifier
from .engine import WheelAction
from .model import BilresaWheel


def attach_to_device(
    entity: Entity, wheel: BilresaWheel, link: MatterDeviceLink, *, model: str
) -> None:
    """Point a not-yet-registered entity at the device it belongs on.

    Linked: reference the core Matter device without describing it. A
    `device_info` naming another config entry's device would make Home
    Assistant fork a duplicate owned by this integration, and core Matter's
    name and hardware metadata stay authoritative.

    Standalone: describe a device of our own, identified by our node id only.
    """
    if link.device is not None:
        entity.device_entry = link.device
        entity._attr_device_info = None  # noqa: SLF001
        return
    entity._attr_device_info = DeviceInfo(  # noqa: SLF001
        identifiers={node_identifier(wheel.node_id)},
        manufacturer="IKEA of Sweden",
        model=model,
        name=wheel.name,
    )


class BilresaChannelEntity(Entity):
    """One wheel channel, carrying the wheel's reconciled device identity."""

    _attr_should_poll = False
    _attr_has_entity_name = True

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
        attach_to_device(self, wheel, link, model="BILRESA scroll wheel")

    @callback
    def update_wheel(self, wheel: BilresaWheel) -> None:
        """Refresh metadata after a Matter node or firmware update.

        The device is not touched here: once the entity is registered, the
        entity registry is what moves it, and Home Assistant refreshes
        `device_entry` from there.
        """
        self._wheel = wheel

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
        [BilresaCoordinator, BilresaWheel, int, MatterDeviceLink],
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
            # Reconcile before constructing: existing registry entries are
            # moved first, so a new entity never lands beside a stale one.
            link = coordinator.device_links.link_for(wheel)
            channels = sorted(
                {e.channel for e in wheel.endpoints.values() if e.channel is not None}
            )
            for channel in channels:
                key = (wheel.node_id, channel)
                desired.add(key)
                existing = entities.get(key)
                if existing is None:
                    entity = factory(coordinator, wheel, channel, link)
                    entities[key] = entity
                    pending.append(entity)
                else:
                    existing.update_wheel(wheel)
        for key in list(entities):
            if key not in desired:
                entity = entities.pop(key)
                hass.async_create_task(entity.async_remove(force_remove=True))
        if pending:
            async_add_entities(pending)

    _sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_WHEELS_UPDATED, _sync))
