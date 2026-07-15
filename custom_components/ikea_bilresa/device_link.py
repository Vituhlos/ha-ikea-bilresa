"""Safely link BILRESA entities to Home Assistant's core Matter device.

The link is also this integration's only read-only source of truth for whether
one physical wheel is reachable; see `wheel_availability`.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Literal

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, callback
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
    """A resolved core Matter device and the identifiers safe to advertise."""

    device: dr.DeviceEntry | None
    identifiers: frozenset[DeviceIdentifier]


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


@callback
def resolve_matter_device(
    hass: HomeAssistant,
    *,
    matter_url: str,
    server_info: dict[str, Any] | None,
    wheel: BilresaWheel,
) -> MatterDeviceLink:
    """Resolve one wheel to exactly one core Matter registry device.

    Resolution is restricted to the core Matter config entry for the same
    server. Serial and operational identifiers must not disagree. If the match
    is absent or ambiguous, the integration keeps its standalone device.
    """
    custom_identifier = (DOMAIN, str(wheel.node_id))
    matter_entry_ids = _matching_matter_entry_ids(hass, matter_url)
    if not matter_entry_ids:
        return MatterDeviceLink(None, frozenset({custom_identifier}))

    candidates: list[DeviceIdentifier] = []
    if wheel.serial:
        candidates.append((_MATTER_DOMAIN, f"{_MATTER_SERIAL_PREFIX}_{wheel.serial}"))
    if operational_identifier := matter_node_identifier(server_info, wheel.node_id):
        candidates.append(operational_identifier)

    registry = dr.async_get(hass)
    matches: dict[str, tuple[dr.DeviceEntry, set[DeviceIdentifier]]] = {}
    for identifier in candidates:
        device = registry.async_get_device(identifiers={identifier})
        if device is None or not device.config_entries.intersection(matter_entry_ids):
            continue
        match = matches.setdefault(device.id, (device, set()))
        match[1].add(identifier)

    if len(matches) != 1:
        if len(matches) > 1:
            _LOGGER.warning(
                "BILRESA serial and operational Matter identifiers resolve to "
                "different devices; keeping the custom device separate"
            )
        return MatterDeviceLink(None, frozenset({custom_identifier}))

    device, identifiers = next(iter(matches.values()))
    return MatterDeviceLink(
        device,
        frozenset({custom_identifier, *identifiers}),
    )


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
    """Attach a wheel to its core Matter device and retire a legacy duplicate."""
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
    custom_identifier = (DOMAIN, str(wheel.node_id))
    target = link.device
    legacy = device_registry.async_get_device(identifiers={custom_identifier})

    # Associate the custom config entry before moving any entities. This call
    # does not touch identifiers and is safe even while a legacy device owns
    # our node identifier.
    device_registry.async_update_device(
        target.id,
        add_config_entry_id=config_entry_id,
    )

    if legacy is None or legacy.id == target.id:
        if legacy is None:
            device_registry.async_update_device(
                target.id, merge_identifiers={custom_identifier}
            )
        return link

    for entity in er.async_entries_for_device(
        entity_registry, legacy.id, include_disabled_entities=True
    ):
        if entity.config_entry_id == config_entry_id and entity.platform == DOMAIN:
            entity_registry.async_update_entity(entity.entity_id, device_id=target.id)

    remaining_entities = er.async_entries_for_device(
        entity_registry, legacy.id, include_disabled_entities=True
    )
    if remaining_entities or not legacy.config_entries <= {config_entry_id}:
        _LOGGER.warning(
            "A legacy BILRESA device has unrelated registry references; "
            "leaving its identifier untouched"
        )
        return MatterDeviceLink(
            target, link.identifiers - frozenset({custom_identifier})
        )

    # Home Assistant does not allow an active device with no identifiers. Move
    # entities first, remove the now-empty legacy device, then transfer our
    # identifier to the canonical Matter device.
    device_registry.async_remove_device(legacy.id)
    device_registry.async_update_device(
        target.id, merge_identifiers={custom_identifier}
    )
    _LOGGER.info("Merged a legacy standalone BILRESA device into core Matter")

    return link
