"""Tests for safe cross-integration Matter device linking."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.ikea_bilresa.const import DOMAIN
from custom_components.ikea_bilresa.device_link import (
    matter_node_identifier,
    reconcile_wheel_device,
    resolve_matter_device,
    wheel_availability,
)
from custom_components.ikea_bilresa.model import BilresaWheel

MATTER_URL = "ws://matter/ws"
MATTER_ENTRY_ID = "matter-entry"
CUSTOM_ENTRY_ID = "bilresa-entry"
NODE_ID = 42
OPERATIONAL_IDENTIFIER = (
    "matter",
    "deviceid_0000000000000002-000000000000002A-MatterNodeDevice",
)
CUSTOM_IDENTIFIER = (DOMAIN, str(NODE_ID))


def _wheel(serial: str | None = None) -> BilresaWheel:
    return BilresaWheel(
        node_id=NODE_ID,
        name="BILRESA scroll wheel",
        product_name="BILRESA scroll wheel",
        serial=serial,
        endpoints={},
    )


def _hass() -> SimpleNamespace:
    matter_entry = SimpleNamespace(
        entry_id=MATTER_ENTRY_ID,
        data={"url": MATTER_URL},
    )
    return SimpleNamespace(
        config_entries=SimpleNamespace(
            async_entries=lambda domain: [matter_entry] if domain == "matter" else []
        )
    )


def test_builds_home_assistant_operational_identifier() -> None:
    assert matter_node_identifier({"compressed_fabric_id": 2}, NODE_ID) == (
        OPERATIONAL_IDENTIFIER
    )
    assert matter_node_identifier({}, NODE_ID) is None
    assert matter_node_identifier({"compressed_fabric_id": True}, NODE_ID) is None


def test_resolves_missing_serial_by_operational_identifier(monkeypatch) -> None:
    target = SimpleNamespace(id="matter-device", config_entries={MATTER_ENTRY_ID})
    device_registry = MagicMock()
    device_registry.async_get_device.side_effect = lambda *, identifiers: (
        target if identifiers == {OPERATIONAL_IDENTIFIER} else None
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.device_link.dr.async_get",
        lambda _hass: device_registry,
    )

    link = resolve_matter_device(
        _hass(),
        matter_url=MATTER_URL,
        server_info={"compressed_fabric_id": 2},
        wheel=_wheel(),
    )

    assert link.device is target
    assert link.identifiers == frozenset({CUSTOM_IDENTIFIER, OPERATIONAL_IDENTIFIER})


def test_does_not_link_to_a_different_matter_server(monkeypatch) -> None:
    device_registry = MagicMock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.device_link.dr.async_get",
        lambda _hass: device_registry,
    )

    link = resolve_matter_device(
        _hass(),
        matter_url="ws://other-matter/ws",
        server_info={"compressed_fabric_id": 2},
        wheel=_wheel(),
    )

    assert link.device is None
    assert link.identifiers == frozenset({CUSTOM_IDENTIFIER})
    device_registry.async_get_device.assert_not_called()


def test_conflicting_serial_and_operational_matches_stay_separate(
    monkeypatch,
) -> None:
    serial_identifier = ("matter", "serial_example")
    serial_device = SimpleNamespace(
        id="serial-device", config_entries={MATTER_ENTRY_ID}
    )
    node_device = SimpleNamespace(id="node-device", config_entries={MATTER_ENTRY_ID})
    device_registry = MagicMock()

    def _get_device(*, identifiers):
        if identifiers == {serial_identifier}:
            return serial_device
        if identifiers == {OPERATIONAL_IDENTIFIER}:
            return node_device
        return None

    device_registry.async_get_device.side_effect = _get_device
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.device_link.dr.async_get",
        lambda _hass: device_registry,
    )

    link = resolve_matter_device(
        _hass(),
        matter_url=MATTER_URL,
        server_info={"compressed_fabric_id": 2},
        wheel=_wheel("example"),
    )

    assert link.device is None
    assert link.identifiers == frozenset({CUSTOM_IDENTIFIER})


def test_reconciles_existing_standalone_device(monkeypatch) -> None:
    target = SimpleNamespace(
        id="matter-device",
        config_entries={MATTER_ENTRY_ID},
        identifiers={OPERATIONAL_IDENTIFIER},
    )
    legacy = SimpleNamespace(
        id="legacy-device",
        config_entries={CUSTOM_ENTRY_ID},
        identifiers={CUSTOM_IDENTIFIER},
        connections=set(),
    )
    entity = SimpleNamespace(
        entity_id="event.bilresa_channel_1",
        config_entry_id=CUSTOM_ENTRY_ID,
        platform=DOMAIN,
    )
    device_registry = MagicMock()

    def _get_device(*, identifiers):
        if identifiers == {OPERATIONAL_IDENTIFIER}:
            return target
        if identifiers == {CUSTOM_IDENTIFIER}:
            return legacy
        return None

    device_registry.async_get_device.side_effect = _get_device
    entity_registry = MagicMock()
    entries_for_device = MagicMock(side_effect=[[entity], []])
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.device_link.dr.async_get",
        lambda _hass: device_registry,
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.device_link.er.async_get",
        lambda _hass: entity_registry,
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.device_link.er.async_entries_for_device",
        entries_for_device,
    )

    link = reconcile_wheel_device(
        _hass(),
        config_entry_id=CUSTOM_ENTRY_ID,
        matter_url=MATTER_URL,
        server_info={"compressed_fabric_id": 2},
        wheel=_wheel(),
    )

    assert link.device is target
    assert device_registry.async_update_device.call_args_list == [
        ((target.id,), {"add_config_entry_id": CUSTOM_ENTRY_ID}),
        (
            (target.id,),
            {"merge_identifiers": {CUSTOM_IDENTIFIER}},
        ),
    ]
    entity_registry.async_update_entity.assert_called_once_with(
        entity.entity_id, device_id=target.id
    )
    device_registry.async_remove_device.assert_called_once_with(legacy.id)


# -- per-wheel availability -----------------------------------------------


def _availability_hass(entries, states) -> SimpleNamespace:
    """A hass whose linked device exposes `entries` with the given states."""
    return SimpleNamespace(
        states=SimpleNamespace(get=lambda entity_id: states.get(entity_id)),
        _entries=entries,
    )


def _patch_entity_registry(monkeypatch, hass) -> None:
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.device_link.er.async_get",
        lambda _hass: MagicMock(),
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.device_link.er.async_entries_for_device",
        lambda _registry, _device_id: hass._entries,
    )


def _entry(entity_id: str, platform: str) -> SimpleNamespace:
    return SimpleNamespace(entity_id=entity_id, platform=platform)


def _state(value: str) -> SimpleNamespace:
    return SimpleNamespace(state=value)


def test_unlinked_wheel_availability_is_unknown() -> None:
    assert wheel_availability(SimpleNamespace(), None) == "unknown"


def test_wheel_is_unavailable_when_every_matter_entity_is(monkeypatch) -> None:
    hass = _availability_hass(
        [_entry("sensor.wheel_battery", "matter"), _entry("event.wheel_sw", "matter")],
        {
            "sensor.wheel_battery": _state("unavailable"),
            "event.wheel_sw": _state("unavailable"),
        },
    )
    _patch_entity_registry(monkeypatch, hass)

    assert (
        wheel_availability(hass, SimpleNamespace(id="matter-device")) == "unavailable"
    )


def test_one_live_matter_entity_proves_the_wheel_answered(monkeypatch) -> None:
    hass = _availability_hass(
        [_entry("sensor.wheel_battery", "matter"), _entry("event.wheel_sw", "matter")],
        {
            "sensor.wheel_battery": _state("87"),
            "event.wheel_sw": _state("unavailable"),
        },
    )
    _patch_entity_registry(monkeypatch, hass)

    assert wheel_availability(hass, SimpleNamespace(id="matter-device")) == "connected"


def test_unknown_state_is_not_unavailable(monkeypatch) -> None:
    """A reachable node with no value yet must not be reported as dead."""
    hass = _availability_hass(
        [_entry("event.wheel_sw", "matter")],
        {"event.wheel_sw": _state("unknown")},
    )
    _patch_entity_registry(monkeypatch, hass)

    assert wheel_availability(hass, SimpleNamespace(id="matter-device")) == "connected"


def test_own_entities_are_ignored(monkeypatch) -> None:
    """Reading our own entities would return the server-wide state in a circle.

    They live on the same device after linking, and their `available` is
    coordinator.connected -- which is exactly what this function must not use.
    """
    hass = _availability_hass(
        [_entry("event.bilresa_channel_1", DOMAIN)],
        {"event.bilresa_channel_1": _state("2026-07-15T18:00:00+00:00")},
    )
    _patch_entity_registry(monkeypatch, hass)

    assert wheel_availability(hass, SimpleNamespace(id="matter-device")) == "unknown"


def test_device_without_states_is_unknown(monkeypatch) -> None:
    hass = _availability_hass([_entry("sensor.wheel_battery", "matter")], {})
    _patch_entity_registry(monkeypatch, hass)

    assert wheel_availability(hass, SimpleNamespace(id="matter-device")) == "unknown"
