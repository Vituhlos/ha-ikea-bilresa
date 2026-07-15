"""Tests for integration setup metadata and config-entry migration."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from homeassistant.const import Platform
from homeassistant.helpers.device_registry import DeviceEntryType
import pytest

import custom_components.ikea_bilresa as integration
from custom_components.ikea_bilresa import PLATFORMS, async_migrate_entry
from custom_components.ikea_bilresa.const import SUBENTRY_BINDING


def test_only_physical_device_platform_is_forwarded() -> None:
    """The integration overview must not gain an integration service device."""
    assert PLATFORMS == [Platform.EVENT]


@pytest.mark.asyncio
async def test_migration_removes_connection_service_device(monkeypatch) -> None:
    """Version 1.2 removes the retired connection entity and service device."""
    entity_registry = MagicMock()
    entity_registry.async_get_entity_id.return_value = (
        "binary_sensor.ikea_bilresa_connection"
    )
    service_device = SimpleNamespace(
        id="service-device-id", entry_type=DeviceEntryType.SERVICE
    )
    device_registry = MagicMock()
    device_registry.async_get_device.return_value = service_device
    monkeypatch.setattr(
        integration, "async_get_entity_registry", lambda hass: entity_registry
    )
    monkeypatch.setattr(
        integration, "async_get_device_registry", lambda hass: device_registry
    )

    generated_subentry = SimpleNamespace(
        subentry_type=SUBENTRY_BINDING,
        title="Kitchen wheel · channel 1",
    )
    custom_subentry = SimpleNamespace(
        subentry_type=SUBENTRY_BINDING,
        title="My evening scenes",
    )
    entry = SimpleNamespace(
        entry_id="entry-id",
        version=1,
        minor_version=1,
        subentries={
            "generated": generated_subentry,
            "custom": custom_subentry,
        },
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_update_entry=MagicMock(),
            async_update_subentry=MagicMock(),
        )
    )

    assert await async_migrate_entry(hass, entry) is True

    entity_registry.async_get_entity_id.assert_called_once_with(
        Platform.BINARY_SENSOR,
        "ikea_bilresa",
        "entry-id_connection",
    )
    entity_registry.async_remove.assert_called_once_with(
        "binary_sensor.ikea_bilresa_connection"
    )
    device_registry.async_remove_device.assert_called_once_with("service-device-id")
    hass.config_entries.async_update_subentry.assert_called_once_with(
        entry,
        generated_subentry,
        title="Kitchen wheel · CH 1",
    )
    hass.config_entries.async_update_entry.assert_called_once_with(
        entry, minor_version=2
    )


@pytest.mark.asyncio
async def test_migration_rejects_unknown_major_version() -> None:
    """A future config-entry format must not be modified by older code."""
    entry = SimpleNamespace(version=2, minor_version=1)

    assert await async_migrate_entry(SimpleNamespace(), entry) is False
