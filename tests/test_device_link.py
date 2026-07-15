"""Tests for safe cross-integration Matter device linking."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.ikea_bilresa.const import DOMAIN
from custom_components.ikea_bilresa.device_link import (
    matter_node_identifier,
    reconcile_wheel_device,
    resolve_matter_device,
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
