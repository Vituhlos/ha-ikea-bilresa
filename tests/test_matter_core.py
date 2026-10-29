"""Tests for reuse of Home Assistant's core Matter client."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from custom_components.ikea_bilresa.matter_core import (
    _UNAVAILABLE_CHECKS_BEFORE_FALLBACK,
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
        self._nodes = [SimpleNamespace(node_data=FakeNodeData(node_id, {"1/59/0": 0}))]
        self.callback = None
        self.unsubscribe = Mock()

    def subscribe_events(self, *, callback):
        self.callback = callback
        return self.unsubscribe

    def get_nodes(self):
        return self._nodes

    def set_position(self, endpoint_id: int, value: int) -> None:
        self._nodes[0].node_data.attributes[f"{endpoint_id}/59/0"] = value


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
async def test_restores_attribute_path_context_from_core_node_cache(
    monkeypatch,
) -> None:
    client = FakeMatterClient()
    hass = SimpleNamespace(config_entries=FakeConfigEntries(client))
    events: list[tuple[str, Any]] = []
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.matter_core.async_track_time_interval",
        lambda *_args: Mock(),
    )
    source = CoreMatterEventSource(
        hass, "ws://matter/ws", lambda event, data: events.append((event, data))
    )
    await source.start()

    client.set_position(1, 1)
    client.callback(FakeEventType("attribute_updated"), 1)

    assert events[-1] == ("attribute_updated", [12, "1/59/0", 1])


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
async def test_transient_core_matter_restart_reattaches_without_fallback(
    monkeypatch,
) -> None:
    first = FakeMatterClient(12)
    second = FakeMatterClient(13)
    config_entries = FakeConfigEntries(first)
    hass = SimpleNamespace(config_entries=config_entries)
    events: list[tuple[str, Any]] = []
    unavailable = Mock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.matter_core.async_track_time_interval",
        lambda *_args: Mock(),
    )
    source = CoreMatterEventSource(
        hass,
        "ws://matter/ws",
        lambda event, data: events.append((event, data)),
        on_unavailable=unavailable,
    )
    await source.start()

    config_entries.client = None
    for _ in range(5):
        source._check_client(None)

    unavailable.assert_not_called()
    first.unsubscribe.assert_called_once()
    assert events[-1] == ("__disconnected__", None)

    config_entries.client = second
    source._check_client(None)

    unavailable.assert_not_called()
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
    for _ in range(_UNAVAILABLE_CHECKS_BEFORE_FALLBACK - 1):
        source._check_client(None)
        unavailable.assert_not_called()
    source._check_client(None)
    unavailable.assert_called_once()


# -- the cost of an attribute update ----------------------------------------


class CountingAttributes(dict):
    """A node's attribute table that counts how often it is walked."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.walks = 0

    def items(self):
        self.walks += 1
        return super().items()

    def __iter__(self):
        self.walks += 1
        return super().__iter__()


class BusyMatterClient(FakeMatterClient):
    """Many nodes with large tables: a house full of Matter lights."""

    def __init__(self, nodes: int = 40, attributes: int = 300) -> None:
        super().__init__(12)
        self.tables: dict[int, CountingAttributes] = {}
        self._nodes = []
        for node_id in range(1, nodes + 1):
            table = CountingAttributes(
                {
                    f"1/{cluster}/{attribute}": 0
                    for cluster in range(60, 60 + attributes // 10)
                    for attribute in range(10)
                }
            )
            if node_id == 12:
                table["1/59/0"] = 0
            self.tables[node_id] = table
            self._nodes.append(SimpleNamespace(node_data=FakeNodeData(node_id, table)))

    def walks(self) -> int:
        return sum(table.walks for table in self.tables.values())


async def _started(monkeypatch, client) -> tuple[CoreMatterEventSource, list]:
    hass = SimpleNamespace(config_entries=FakeConfigEntries(client))
    events: list[tuple[str, Any]] = []
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.matter_core.async_track_time_interval",
        lambda *_args: Mock(),
    )
    source = CoreMatterEventSource(
        hass, "ws://matter/ws", lambda event, data: events.append((event, data))
    )
    await source.start()
    return source, events


@pytest.mark.asyncio
async def test_updates_from_other_devices_do_not_walk_every_node(monkeypatch) -> None:
    """The Core event loop froze for minutes: every update walked every node.

    An update carries only its new value, so every node's CurrentPosition has
    to be read, but the paths to read are found once, not on every update.
    """
    client = BusyMatterClient()
    source, _events = await _started(monkeypatch, client)

    client.callback(FakeEventType("attribute_updated"), 1)
    after_the_first = client.walks()
    for _ in range(50):
        client.callback(FakeEventType("attribute_updated"), 1)

    assert client.walks() == after_the_first


@pytest.mark.asyncio
async def test_updates_convert_no_node_to_a_mapping(monkeypatch) -> None:
    client = BusyMatterClient()
    source, _events = await _started(monkeypatch, client)
    converted = []
    real = source._node_to_mapping
    monkeypatch.setattr(
        CoreMatterEventSource,
        "_node_to_mapping",
        staticmethod(lambda node: converted.append(node) or real(node)),
    )

    for _ in range(20):
        client.callback(FakeEventType("attribute_updated"), 1)

    assert converted == []


@pytest.mark.asyncio
async def test_a_changed_position_is_forwarded_once_among_many_nodes(
    monkeypatch,
) -> None:
    client = BusyMatterClient()
    source, events = await _started(monkeypatch, client)
    client.callback(FakeEventType("attribute_updated"), 1)
    events.clear()

    client.tables[12]["1/59/0"] = 1
    client.callback(FakeEventType("attribute_updated"), 1)
    client.callback(FakeEventType("attribute_updated"), 1)

    assert events == [("attribute_updated", [12, "1/59/0", 1])]


@pytest.mark.asyncio
async def test_a_position_path_that_appears_later_is_found(monkeypatch) -> None:
    client = BusyMatterClient()
    source, events = await _started(monkeypatch, client)
    client.callback(FakeEventType("attribute_updated"), 1)
    events.clear()

    # The table grows in place: a new endpoint with its own position.
    client.tables[12]["2/59/0"] = 1
    client.callback(FakeEventType("attribute_updated"), 1)

    assert ("attribute_updated", [12, "2/59/0", 1]) in events


@pytest.mark.asyncio
async def test_a_replaced_attribute_table_is_scanned_again(monkeypatch) -> None:
    client = BusyMatterClient()
    source, events = await _started(monkeypatch, client)
    client.callback(FakeEventType("attribute_updated"), 1)
    events.clear()

    # A node update swaps in a new table, with a position at a new path and
    # the same number of attributes as before.
    old = client.tables[12]
    replacement = CountingAttributes({k: v for k, v in old.items() if k != "1/59/0"})
    replacement["3/59/0"] = 1
    client._nodes[11].node_data.attributes = replacement
    client.callback(FakeEventType("attribute_updated"), 1)

    assert ("attribute_updated", [12, "3/59/0", 1]) in events


@pytest.mark.asyncio
async def test_a_removed_node_leaves_nothing_behind(monkeypatch) -> None:
    client = BusyMatterClient(nodes=5, attributes=20)
    source, _events = await _started(monkeypatch, client)
    client.callback(FakeEventType("attribute_updated"), 1)
    assert len(source._position_paths) == 5

    client._nodes = client._nodes[:2]
    client.callback(FakeEventType("attribute_updated"), 1)

    assert set(source._position_paths) == {1, 2}


@pytest.mark.asyncio
async def test_a_table_changed_in_place_without_changing_size_is_found_in_time(
    monkeypatch,
) -> None:
    """The one change the cache cannot see on its own is noticed after a while."""
    clock = {"now": 1000.0}
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.matter_core.time.monotonic",
        lambda: clock["now"],
    )
    client = BusyMatterClient()
    source, events = await _started(monkeypatch, client)
    client.callback(FakeEventType("attribute_updated"), 1)
    events.clear()

    # One position path is swapped for another; the number of attributes is the
    # same and the table is the same object.
    table = client.tables[12]
    del table["1/59/0"]
    table["3/59/0"] = 1
    client.callback(FakeEventType("attribute_updated"), 1)
    assert not any(e[1][1] == "3/59/0" for e in events if e[0] == "attribute_updated")

    # Within a minute (30 seconds plus at most 30 more per node) it is looked up
    # again, and the new path is forwarded.
    clock["now"] += 61.0
    client.callback(FakeEventType("attribute_updated"), 1)
    assert ("attribute_updated", [12, "3/59/0", 1]) in events


@pytest.mark.asyncio
async def test_the_lookup_is_not_repeated_within_the_age_limit(monkeypatch) -> None:
    clock = {"now": 1000.0}
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.matter_core.time.monotonic",
        lambda: clock["now"],
    )
    client = BusyMatterClient()
    source, _events = await _started(monkeypatch, client)
    client.callback(FakeEventType("attribute_updated"), 1)
    after_the_first = client.walks()

    clock["now"] += 29.0
    for _ in range(20):
        client.callback(FakeEventType("attribute_updated"), 1)

    assert client.walks() == after_the_first

    # Past the limit each node is looked up once, not on every update after that.
    clock["now"] += 40.0
    client.callback(FakeEventType("attribute_updated"), 1)
    once_more = client.walks()
    for _ in range(20):
        client.callback(FakeEventType("attribute_updated"), 1)
    assert client.walks() == once_more
