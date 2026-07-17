"""Failure-state tests for System Health."""

from __future__ import annotations

from types import SimpleNamespace

from homeassistant.config_entries import ConfigEntryState
import pytest

from custom_components.ikea_bilresa.system_health import _async_system_health_info


@pytest.mark.asyncio
async def test_system_health_without_config_entry() -> None:
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda _domain: [])
    )

    assert await _async_system_health_info(hass) == {"configured": False}


@pytest.mark.asyncio
async def test_system_health_reports_setup_failure_without_runtime_data() -> None:
    entry = SimpleNamespace(
        state=ConfigEntryState.SETUP_ERROR,
        subentries={},
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda _domain: [entry])
    )

    result = await _async_system_health_info(hass)

    assert result["configured"] is True
    assert result["config_entry_state"] == ConfigEntryState.SETUP_ERROR.value
    assert result["matter_server_connected"] is False
    assert result["matter_event_source"] == "unavailable"
