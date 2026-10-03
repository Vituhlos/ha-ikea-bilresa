"""Place BILRESA entities on Home Assistant's core Matter device.

Since Home Assistant 2026.8 a device belongs to exactly one config entry. This
integration therefore never co-owns the core Matter device: its entities are
attached to it by reference (`Entity.device_entry`), and a wheel that cannot be
matched to a Matter device gets a standalone device of its own instead.

The link is also this integration's only read-only source of truth for whether
one physical wheel is reachable; see `wheel_availability`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any, Literal, Protocol

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .model import BilresaWheel

_LOGGER = logging.getLogger(__name__)

_MATTER_DOMAIN = "matter"
_MATTER_DEVICE_ID_PREFIX = "deviceid"
_MATTER_SERIAL_PREFIX = "serial"
_MATTER_NODE_POSTFIX = "MatterNodeDevice"

type DeviceIdentifier = tuple[str, str]

type WheelAvailability = Literal["connected", "unavailable", "unknown"]


@dataclass(frozen=True, slots=True)
class MatterDeviceLink:
    """The core Matter device a wheel resolved to, or None when it stands alone."""

    device: dr.DeviceEntry | None


def node_identifier(node_id: int) -> DeviceIdentifier:
    """Identifier of the standalone device this integration owns for a node."""
    return (DOMAIN, str(node_id))


def _normalized_url(value: Any) -> str | None:
    """Normalize a configured Matter Server URL for exact matching."""
    return value.rstrip("/") if isinstance(value, str) else None


@callback
def _matching_matter_entry_ids(hass: HomeAssistant, url: str) -> set[str]:
    """Return core Matter config entries that use the same server URL."""
    configured_url = _normalized_url(url)
    return {
        entry.entry_id
        for entry in hass.config_entries.async_entries(_MATTER_DOMAIN)
        if _normalized_url(entry.data.get("url")) == configured_url
    }


def matter_node_identifier(
    server_info: dict[str, Any] | None, node_id: int
) -> DeviceIdentifier | None:
    """Build the canonical core-Matter identifier for an unbridged node.

    Home Assistant identifies a Matter node from its operational instance name:
    compressed fabric ID plus node ID, both as 16-character uppercase hex.
    BILRESA is an unbridged node, so the root-device postfix is fixed.
    """
    if not server_info:
        return None
    compressed_fabric_id = server_info.get("compressed_fabric_id")
    if (
        isinstance(compressed_fabric_id, bool)
        or not isinstance(compressed_fabric_id, int)
        or isinstance(node_id, bool)
        or not isinstance(node_id, int)
    ):
        return None
    value = (
        f"{_MATTER_DEVICE_ID_PREFIX}_{compressed_fabric_id:016X}-"
        f"{node_id:016X}-{_MATTER_NODE_POSTFIX}"
    )
    return (_MATTER_DOMAIN, value)


def _candidate_identifiers(
    server_info: dict[str, Any] | None, wheel: BilresaWheel
) -> list[DeviceIdentifier]:
    """Core Matter identifiers that may name this wheel's registry device."""
    candidates: list[DeviceIdentifier] = []
    if wheel.serial:
        candidates.append((_MATTER_DOMAIN, f"{_MATTER_SERIAL_PREFIX}_{wheel.serial}"))
    if operational_identifier := matter_node_identifier(server_info, wheel.node_id):
        candidates.append(operational_identifier)
    return candidates


@callback
def resolve_matter_device(
    hass: HomeAssistant,
    *,
    matter_url: str,
    server_info: dict[str, Any] | None,
    wheel: BilresaWheel,
) -> MatterDeviceLink:
    """Resolve one wheel to exactly one core Matter registry device, read-only.

    Resolution is restricted to the core Matter config entry for the same
    server, and every lookup is scoped to that config entry: identifiers are
    only unique within one. Serial and operational identifiers must not
    disagree. If the match is absent or ambiguous, the wheel stands alone.
    """
    matter_entry_ids = _matching_matter_entry_ids(hass, matter_url)
    if not matter_entry_ids:
        return MatterDeviceLink(None)

    registry = dr.async_get(hass)
    matches: dict[str, dr.DeviceEntry] = {}
    for identifier in _candidate_identifiers(server_info, wheel):
        for entry_id in sorted(matter_entry_ids):
            device = registry.async_get_device_by_identifier(identifier, entry_id)
            if device is not None:
                matches[device.id] = device

    if len(matches) != 1:
        if len(matches) > 1:
            _LOGGER.warning(
                "BILRESA serial and operational Matter identifiers resolve to "
                "different devices; keeping the custom device separate"
            )
        return MatterDeviceLink(None)

    return MatterDeviceLink(next(iter(matches.values())))


@callback
def wheel_availability(
    hass: HomeAssistant, device: dr.DeviceEntry | None
) -> WheelAvailability:
    """Report whether one physical wheel is reachable, read-only.

    This integration cannot answer that on its own. `BilresaCoordinator.connected`
    describes the Matter Server connection, not a node, and
    `BilresaChannelEvent.available` returns it verbatim — so a wheel with a flat
    battery reports available for as long as the server is up. Core Matter does
    track per-node reachability and marks its own entities unavailable, so the
    linked device is the only source that distinguishes one dead wheel from a
    dead server.

    Only core Matter's entities are consulted. This integration's own entities
    live on the same device after linking, and reading those would just return
    the server-wide state back through a longer path.

    Returns `unknown` rather than guessing when the wheel never linked, when the
    device exposes no core Matter entities, or when none of them have a state
    yet. `unknown` means "no evidence", not "fine".
    """
    if device is None:
        return "unknown"

    entity_registry = er.async_get(hass)
    states = [
        state
        for entry in er.async_entries_for_device(entity_registry, device.id)
        if entry.platform == _MATTER_DOMAIN
        and (state := hass.states.get(entry.entity_id)) is not None
    ]
    if not states:
        return "unknown"
    # Core Matter drops every entity of an unreachable node at once. A single
    # live state is therefore enough to prove the wheel answered. STATE_UNKNOWN
    # is not unavailable: the node is reachable, it just has no value yet.
    if all(state.state == STATE_UNAVAILABLE for state in states):
        return "unavailable"
    return "connected"


@callback
def reconcile_wheel_device(
    hass: HomeAssistant,
    *,
    config_entry_id: str,
    matter_url: str,
    server_info: dict[str, Any] | None,
    wheel: BilresaWheel,
) -> MatterDeviceLink:
    """Move a wheel's entities onto its core Matter device; retire our own.

    Idempotent, and safe to run on every sync. It also performs the one-time
    migration from two older layouts: the standalone device of 0.5.0, and the
    duplicate that Home Assistant 2026.8 forked for every wheel once a device
    could no longer be shared between config entries.

    The order matters. Removing a device also removes the entities of its own
    config entry that still sit on it, so entities are moved first and a device
    is removed only once nothing is left on it.
    """
    link = resolve_matter_device(
        hass,
        matter_url=matter_url,
        server_info=server_info,
        wheel=wheel,
    )
    if link.device is None:
        return link

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    target = link.device
    custom_identifier = node_identifier(wheel.node_id)

    unique_id_prefix = f"{wheel.node_id}_"
    for entity in er.async_entries_for_config_entry(entity_registry, config_entry_id):
        if (
            entity.platform == DOMAIN
            and entity.unique_id.startswith(unique_id_prefix)
            and entity.device_id != target.id
        ):
            entity_registry.async_update_entity(entity.entity_id, device_id=target.id)

    # Our own devices for this node: the standalone one carries our node
    # identifier, the forked duplicate may carry only the Matter ones.
    own_devices = device_registry.async_get_devices(
        identifiers={
            custom_identifier,
            *(i for i in target.identifiers if i[0] == _MATTER_DOMAIN),
        },
        config_entry_id=config_entry_id,
    )
    for device in own_devices:
        if er.async_entries_for_device(
            entity_registry, device.id, include_disabled_entities=True
        ):
            _LOGGER.warning(
                "A retired BILRESA device still has entities attached; "
                "leaving it in place"
            )
            continue
        device_registry.async_remove_device(device.id)
        _LOGGER.info("Retired a duplicate BILRESA device in favour of core Matter")

    # Earlier releases wrote our node identifier onto the Matter device so the
    # legacy device triggers could find it. Nothing reads it any more, and a
    # device we do not own should not carry it.
    if custom_identifier in target.identifiers:
        device_registry.async_update_device(
            target.id, new_identifiers=target.identifiers - {custom_identifier}
        )
        return MatterDeviceLink(device_registry.async_get(target.id) or target)

    return link


class _WheelSource(Protocol):
    """What the manager reads from the coordinator."""

    url: str
    wheels: dict[int, BilresaWheel]

    @property
    def matter_server_info(self) -> dict[str, Any] | None:
        """Server info reported by the Matter Server."""


class DeviceLinkManager:
    """Keep every wheel's entities on the right device while running.

    Platforms ask it for a wheel's link when they sync. It also follows the
    device registry: a wheel commissioned while Home Assistant runs can reach
    this integration before core Matter has created its device, and that
    device has to be picked up when it appears.
    """

    def __init__(
        self, hass: HomeAssistant, config_entry_id: str, source: _WheelSource
    ) -> None:
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._source = source
        self._device_ids: dict[int, str] = {}
        self._reconciling = False

    @callback
    def async_start(self) -> Callable[[], None]:
        """Follow the device registry; returns the unsubscribe callback."""
        return self._hass.bus.async_listen(
            dr.EVENT_DEVICE_REGISTRY_UPDATED, self._handle_device_registry_updated
        )

    @callback
    def link_for(self, wheel: BilresaWheel) -> MatterDeviceLink:
        """Reconcile one wheel and return where its entities belong."""
        self._reconciling = True
        try:
            link = reconcile_wheel_device(
                self._hass,
                config_entry_id=self._config_entry_id,
                matter_url=self._source.url,
                server_info=self._source.matter_server_info,
                wheel=wheel,
            )
        finally:
            self._reconciling = False
        if link.device is not None:
            self._device_ids[wheel.node_id] = link.device.id
        else:
            self._device_ids.pop(wheel.node_id, None)
        return link

    @callback
    def device_id(self, node_id: int) -> str | None:
        """Registry device that carries a node's entities, if there is one.

        Cached, because the coordinator asks on every notch.
        """
        if (device_id := self._device_ids.get(node_id)) is not None:
            return device_id
        device = dr.async_get(self._hass).async_get_device_by_identifier(
            node_identifier(node_id), self._config_entry_id
        )
        if device is None:
            return None
        self._device_ids[node_id] = device.id
        return device.id

    @callback
    def forget(self, node_id: int) -> None:
        """Drop a node that is no longer discovered."""
        self._device_ids.pop(node_id, None)

    @callback
    def _handle_device_registry_updated(
        self, event: Event[dr.EventDeviceRegistryUpdatedData]
    ) -> None:
        device_id = event.data["device_id"]
        if event.data["action"] == "remove":
            for node_id, cached in list(self._device_ids.items()):
                if cached == device_id:
                    del self._device_ids[node_id]
            return
        if self._reconciling:
            return
        device = dr.async_get(self._hass).async_get(device_id)
        if device is None:
            return
        server_info = self._source.matter_server_info
        for wheel in list(self._source.wheels.values()):
            if self._device_ids.get(wheel.node_id) == device.id:
                continue
            if device.identifiers.isdisjoint(
                _candidate_identifiers(server_info, wheel)
            ):
                continue
            self.link_for(wheel)
