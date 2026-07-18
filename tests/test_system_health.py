"""Failure-state tests for System Health."""

from __future__ import annotations

from types import SimpleNamespace

from homeassistant.config_entries import ConfigEntryState
import pytest

from custom_components.ikea_bilresa.const import ROLE_BUTTON, ROLE_SCROLL_UP
from custom_components.ikea_bilresa.model import BilresaWheel, SwitchEndpoint
from custom_components.ikea_bilresa.system_health import _async_system_health_info


def _wheel(node_id: int) -> BilresaWheel:
    return BilresaWheel(
        node_id=node_id,
        name="Wheel",
        product_name="BILRESA scroll wheel",
        serial=None,
        endpoints={1: SwitchEndpoint(1, 1, ROLE_SCROLL_UP)},
    )


def _dual_button(node_id: int) -> BilresaWheel:
    return BilresaWheel(
        node_id=node_id,
        name="Buttons",
        product_name="BILRESA dual button",
        serial=None,
        endpoints={
            1: SwitchEndpoint(1, None, ROLE_BUTTON),
            2: SwitchEndpoint(2, None, ROLE_BUTTON),
        },
    )


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
    assert result["discovered_wheels"] == 0
    assert result["discovered_buttons"] == 0


@pytest.mark.asyncio
async def test_system_health_counts_wheels_and_buttons_separately() -> None:
    coordinator = SimpleNamespace(
        matter_server_info={
            "sdk_version": "matter-server/1.2.6",
            "schema_version": 12,
        },
        telemetry={"last_event_at": None, "last_fallback_reason": None},
        connected=True,
        event_source="core_matter_client",
        wheels={1: _wheel(1), 2: _wheel(2), 15: _dual_button(15)},
    )
    entry = SimpleNamespace(
        state=ConfigEntryState.LOADED,
        subentries={},
        runtime_data=coordinator,
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda _domain: [entry])
    )

    result = await _async_system_health_info(hass)

    # A dual button must not inflate the wheel count.
    assert result["discovered_wheels"] == 2
    assert result["discovered_buttons"] == 1
    assert result["matter_server_schema"] == 12
    assert result["matter_client_compatibility_schema"] == 11
