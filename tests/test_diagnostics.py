"""Privacy contract tests for downloadable diagnostics."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.ikea_bilresa.const import (
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_HOLD_TARGET,
    CONF_NODE_ID,
    CONF_TARGET,
    CONF_TRIPLE_TARGET,
    CONF_URL,
)
from custom_components.ikea_bilresa.device_link import MatterDeviceLink
from custom_components.ikea_bilresa.diagnostics import (
    TO_REDACT,
    async_get_config_entry_diagnostics,
)
from custom_components.ikea_bilresa.model import BilresaWheel, SwitchEndpoint

REDACTED = "**REDACTED**"


def test_household_identifiers_are_redacted() -> None:
    assert {
        CONF_URL,
        CONF_NODE_ID,
        CONF_TARGET,
        CONF_CLICK_TARGET,
        CONF_DOUBLE_TARGET,
        CONF_TRIPLE_TARGET,
        CONF_HOLD_TARGET,
        "serial",
        "compressed_fabric_id",
        "name",
        "title",
    } <= TO_REDACT


def _wheel(node_id: int, serial: str | None) -> BilresaWheel:
    return BilresaWheel(
        node_id=node_id,
        name="BILRESA scroll wheel",
        product_name="BILRESA scroll wheel",
        serial=serial,
        endpoints={
            1: SwitchEndpoint(
                endpoint_id=1,
                channel=1,
                role="button",
                multi_press_max=3,
            )
        },
    )


def _entry(wheels: dict[int, BilresaWheel]) -> SimpleNamespace:
    coordinator = SimpleNamespace(
        url="ws://matter/ws",
        wheels=wheels,
        matter_server_info={"compressed_fabric_id": 2, "schema_version": 11},
        event_source="core_matter_client",
        telemetry={"actions_dispatched": 3, "recent_events": []},
    )
    return SimpleNamespace(
        data={CONF_URL: "ws://matter/ws"},
        subentries={},
        runtime_data=coordinator,
    )


async def test_reports_availability_per_wheel(monkeypatch) -> None:
    """A flat battery must be distinguishable from a dead server."""
    linked = SimpleNamespace(id="matter-device")
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.diagnostics.resolve_matter_device",
        lambda _hass, **_kw: MatterDeviceLink(linked, frozenset()),
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.diagnostics.wheel_availability",
        lambda _hass, device: "unavailable" if device is linked else "unknown",
    )

    result = await async_get_config_entry_diagnostics(
        SimpleNamespace(), _entry({7: _wheel(7, "abc")})
    )

    assert result["wheels"][0]["availability"] == "unavailable"
    assert result["wheels"][0]["linked_to_matter"] is True
    assert result["wheels"][0]["variant"] == "wheel"
    assert result["wheels"][0]["endpoints"][1]["multi_press_max"] == 3
    # the server connection is reported separately and stays untouched
    assert result["matter_event_source"] == "core_matter_client"


async def test_unlinked_wheel_reports_unknown_not_connected(monkeypatch) -> None:
    """Without a link there is no evidence, and no evidence is not health."""
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.diagnostics.resolve_matter_device",
        lambda _hass, **_kw: MatterDeviceLink(None, frozenset()),
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.diagnostics.wheel_availability",
        lambda _hass, _device: "unknown",
    )

    result = await async_get_config_entry_diagnostics(
        SimpleNamespace(), _entry({7: _wheel(7, None)})
    )

    assert result["wheels"][0]["availability"] == "unknown"
    assert result["wheels"][0]["linked_to_matter"] is False


async def test_availability_does_not_leak_identifiers(monkeypatch) -> None:
    """The new fields must not reopen what the redaction policy closed."""
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.diagnostics.resolve_matter_device",
        lambda _hass, **_kw: MatterDeviceLink(
            SimpleNamespace(id="matter-device"), frozenset()
        ),
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.diagnostics.wheel_availability",
        lambda _hass, _device: "connected",
    )

    result = await async_get_config_entry_diagnostics(
        SimpleNamespace(), _entry({7: _wheel(7, "household-serial")})
    )

    wheel = result["wheels"][0]
    assert wheel["node_id"] == REDACTED
    assert wheel["name"] == REDACTED
    assert wheel["serial"] == REDACTED
    assert result["url"] == REDACTED
    assert "household-serial" not in str(result)
    assert "matter-device" not in str(result)
