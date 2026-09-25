"""Unit tests for the config flow's Matter device lookup."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from custom_components.ikea_bilresa import config_flow

IDENTIFIER = ("matter", "serial_ABC")


def _hass(*matter_entry_ids: str) -> Mock:
    hass = Mock()
    hass.config_entries.async_entries.return_value = [
        SimpleNamespace(entry_id=entry_id) for entry_id in matter_entry_ids
    ]
    return hass


def _device(name: str, name_by_user: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(name=name, name_by_user=name_by_user)


def test_matter_device_name_uses_matter_config_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = Mock(spec=["async_get_device", "async_get_device_by_identifier"])
    registry.async_get_device_by_identifier.side_effect = lambda identifier, entry: (
        _device("BILRESA scroll wheel", "Office wheel") if entry == "matter" else None
    )
    monkeypatch.setattr(config_flow, "async_get_device_registry", lambda hass: registry)

    hass = _hass("other", "matter")
    assert config_flow._matter_device_name(hass, "ABC") == "Office wheel"
    hass.config_entries.async_entries.assert_called_once_with("matter")
    registry.async_get_device_by_identifier.assert_called_with(IDENTIFIER, "matter")
    registry.async_get_device.assert_not_called()


def test_matter_device_name_missing_device(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = Mock(spec=["async_get_device", "async_get_device_by_identifier"])
    registry.async_get_device_by_identifier.return_value = None
    monkeypatch.setattr(config_flow, "async_get_device_registry", lambda hass: registry)

    assert config_flow._matter_device_name(_hass("matter"), "ABC") is None


def test_matter_device_name_legacy_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = Mock(spec=["async_get_device"])
    registry.async_get_device.return_value = _device("BILRESA scroll wheel")
    monkeypatch.setattr(config_flow, "async_get_device_registry", lambda hass: registry)

    assert config_flow._matter_device_name(_hass(), "ABC") == "BILRESA scroll wheel"
    registry.async_get_device.assert_called_once_with(identifiers={IDENTIFIER})
