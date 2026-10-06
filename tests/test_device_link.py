"""Tests for safe cross-integration Matter device linking."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.ikea_bilresa.const import DOMAIN
from custom_components.ikea_bilresa.device_link import (
    matter_node_identifier,
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
