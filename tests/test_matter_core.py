"""Tests for reuse of Home Assistant's core Matter client."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from custom_components.ikea_bilresa.matter_core import (
    CoreMatterEventSource,
    CoreMatterUnavailable,
)


@dataclass
class FakeNodeData:
    node_id: int
    attributes: dict[str, Any]


@dataclass
class FakeNodeEvent:
    node_id: int
    endpoint_id: int
    cluster_id: int
    event_id: int
    data: dict[str, Any]


class FakeEventType:
    def __init__(self, value: str) -> None:
        self.value = value


class FakeMatterClient:
    def __init__(self, node_id: int = 12) -> None:
        self.server_info = SimpleNamespace(sdk_version="test-sdk")
        self._nodes = [SimpleNamespace(node_data=FakeNodeData(node_id, {}))]
        self.callback = None
        self.unsubscribe = Mock()

    def subscribe_events(self, *, callback):
        self.callback = callback
        return self.unsubscribe

    def get_nodes(self):
        return self._nodes


class FakeConfigEntries:
    def __init__(self, client: Any | None, url: str = "ws://matter/ws") -> None:
        self.client = client
        self.url = url

    def async_loaded_entries(self, domain: str):
        assert domain == "matter"
        if self.client is None:
            return []
        runtime_data = SimpleNamespace(
            adapter=SimpleNamespace(matter_client=self.client)
        )
        return [SimpleNamespace(data={"url": self.url}, runtime_data=runtime_data)]


@pytest.mark.asyncio
async def test_reuses_nodes_and_node_events(monkeypatch) -> None:
    client = FakeMatterClient()
    config_entries = FakeConfigEntries(client)
    hass = SimpleNamespace(config_entries=config_entries)
    events: list[tuple[str, Any]] = []
    monitor_unsubscribe = Mock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.matter_core.async_track_time_interval",
        lambda *_args: monitor_unsubscribe,
    )

    source = CoreMatterEventSource(
        hass,
        "ws://matter/ws",
        lambda event, data: events.append((event, data)),
    )
    await source.start()

    assert events[0] == ("__connected__", None)
    assert events[1][0] == "__nodes__"
    assert events[1][1][0]["node_id"] == 12
    assert source.server_info == {"sdk_version": "test-sdk"}

    node_event = FakeNodeEvent(12, 1, 0x003B, 0x05, {"count": 4})
    client.callback(FakeEventType("node_event"), node_event)
    assert events[-1] == (
        "node_event",
        {
            "node_id": 12,
            "endpoint_id": 1,
            "cluster_id": 0x003B,
            "event_id": 0x05,
            "data": {"count": 4},
        },
    )

    await source.stop()
    client.unsubscribe.assert_called_once()
    monitor_unsubscribe.assert_called_once()
    assert events[-1] == ("__disconnected__", None)


@pytest.mark.asyncio
async def test_reattaches_after_core_matter_reload(monkeypatch) -> None:
    first = FakeMatterClient(12)
    second = FakeMatterClient(13)
    config_entries = FakeConfigEntries(first)
    hass = SimpleNamespace(config_entries=config_entries)
    events: list[tuple[str, Any]] = []
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.matter_core.async_track_time_interval",
        lambda *_args: Mock(),
    )
    source = CoreMatterEventSource(
        hass,
        "ws://matter/ws",
        lambda event, data: events.append((event, data)),
    )
    await source.start()

    config_entries.client = second
    source._check_client(None)

    first.unsubscribe.assert_called_once()
    assert events[-2] == ("__connected__", None)
    assert events[-1][0] == "__nodes__"
    assert events[-1][1][0]["node_id"] == 13


@pytest.mark.asyncio
async def test_unavailable_without_loaded_matter_entry(monkeypatch) -> None:
    hass = SimpleNamespace(config_entries=FakeConfigEntries(None))
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.matter_core.async_track_time_interval",
        lambda *_args: Mock(),
    )
    source = CoreMatterEventSource(hass, "ws://matter/ws", Mock())

    with pytest.raises(CoreMatterUnavailable):
        await source.start()


@pytest.mark.asyncio
async def test_rejects_core_client_for_different_server_url(monkeypatch) -> None:
    hass = SimpleNamespace(
        config_entries=FakeConfigEntries(
            FakeMatterClient(), url="ws://different-matter/ws"
        )
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.matter_core.async_track_time_interval",
        lambda *_args: Mock(),
    )
    source = CoreMatterEventSource(hass, "ws://configured-matter/ws", Mock())

    with pytest.raises(CoreMatterUnavailable):
        await source.start()


@pytest.mark.asyncio
async def test_runtime_incompatibility_requests_fallback(monkeypatch) -> None:
    client = FakeMatterClient()
    config_entries = FakeConfigEntries(client)
    hass = SimpleNamespace(config_entries=config_entries)
    unavailable = Mock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.matter_core.async_track_time_interval",
        lambda *_args: Mock(),
    )
    source = CoreMatterEventSource(
        hass, "ws://matter/ws", Mock(), on_unavailable=unavailable
    )
    await source.start()

    config_entries.url = "ws://different-matter/ws"
    source._check_client(None)
    unavailable.assert_not_called()
    source._check_client(None)
    unavailable.assert_called_once()
