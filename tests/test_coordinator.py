"""Tests for event-source fallback and privacy-safe telemetry."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.ikea_bilresa.coordinator import BilresaCoordinator
from custom_components.ikea_bilresa.matter_core import CoreMatterUnavailable
from custom_components.ikea_bilresa.model import BilresaWheel


class FailingCoreSource:
    source = "core_matter_client"
    server_info = None

    def __init__(self, *_args) -> None:
        self.stop = AsyncMock()

    async def start(self) -> None:
        raise CoreMatterUnavailable("unsupported test client")


class FakeWebSocketSource:
    source = "dedicated_websocket"
    server_info = {"sdk_version": "test"}

    def __init__(self, *_args) -> None:
        self.start = AsyncMock()
        self.stop = AsyncMock()


@pytest.mark.asyncio
async def test_initial_core_failure_falls_back_and_records_reason(monkeypatch) -> None:
    hass = SimpleNamespace()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
        FailingCoreSource,
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.MatterWSClient",
        FakeWebSocketSource,
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.async_get_clientsession",
        lambda _hass: Mock(),
    )

    coordinator = BilresaCoordinator(hass, "ws://matter/ws")
    await coordinator.async_start()

    assert coordinator.event_source == "dedicated_websocket"
    assert coordinator.telemetry["fallback_count"] == 1
    assert coordinator.telemetry["last_fallback_reason"] == "unsupported test client"
    coordinator._client.start.assert_awaited_once()


def test_recent_telemetry_is_bounded_and_excludes_node_id(monkeypatch) -> None:
    hass = SimpleNamespace()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
        lambda *_args: SimpleNamespace(source="core", server_info=None),
    )
    coordinator = BilresaCoordinator(hass, "ws://matter/ws")

    for event_number in range(25):
        coordinator._on_event(
            "node_event",
            {
                "node_id": 123456,
                "endpoint_id": 1,
                "cluster_id": 59,
                "event_id": 5,
                "event_number": event_number,
            },
        )

    recent = coordinator.telemetry["recent_events"]
    assert len(recent) == 20
    assert recent[0]["event_number"] == 5
    assert all("node_id" not in event for event in recent)


def test_existing_wheel_metadata_is_refreshed(monkeypatch) -> None:
    """A firmware update may add serial metadata to an already known node."""
    hass = SimpleNamespace()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
        lambda *_args: SimpleNamespace(source="core", server_info=None),
    )
    coordinator = BilresaCoordinator(hass, "ws://matter/ws")
    original = BilresaWheel(
        node_id=12,
        name="BILRESA scroll wheel",
        product_name="BILRESA scroll wheel",
        serial=None,
        endpoints={},
    )
    updated = BilresaWheel(
        node_id=12,
        name="BILRESA scroll wheel",
        product_name="BILRESA scroll wheel",
        serial="new-serial",
        endpoints={},
    )
    wheels = iter([original, updated, updated])
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.parse_node",
        lambda _node: next(wheels),
    )

    assert coordinator._register_wheel({}) is True
    assert coordinator._register_wheel({}) is True
    assert coordinator.wheels[12].serial == "new-serial"
    assert coordinator._register_wheel({}) is False
