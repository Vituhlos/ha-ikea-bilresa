"""Issue #21: the Core event loop froze on Matter attribute updates.

On an install with many Matter nodes, every attribute update of *any* device
converted every node to a mapping and walked every attribute of every node: a
minute or two of the Home Assistant event loop on 63 nodes. The fix finds each
node's Switch.CurrentPosition paths once and reads only those afterwards.

This is the same property, end to end and counted instead of timed: the real
``CoreMatterEventSource`` feeds the real ``BilresaCoordinator`` from a client
with 64 nodes of 300 attributes each, and the lab counts how often an attribute
table is walked, how often it is read, and how many nodes are converted. Counting
operations is deterministic; wall-clock time would not be. The source's clock is
the lab clock (the name ``time`` inside ``matter_core`` is rebound for the test,
the process clock is not touched).

The connection lifecycle (``__connected__``) goes through Home Assistant's real
issue registry and is not part of this scenario, so it is filtered out.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from custom_components.ikea_bilresa import const
from custom_components.ikea_bilresa import matter_core as matter_core_module
from custom_components.ikea_bilresa.matter_core import CoreMatterEventSource

from .fake_clock import fake_time_module
from .fake_matter import E2490_ENDPOINTS, Wire, e2490_node
from .harness import LabHarness

WHEEL = 99  # an id none of the 63 other nodes has
UP1 = E2490_ENDPOINTS[1]["up"]
BTN1 = E2490_ENDPOINTS[1]["button"]
NODES = 64  # 63 other devices and one BILRESA wheel
URL = "ws://matter.lab.invalid/ws"
# The path the integration watches; taken from the constant so this scenario is
# about the cost of an update, not about which attribute id that constant has.
POSITION = f"{BTN1}/59/{const.ATTR_SWITCH_CURRENT_POSITION}"


class CountingTable(dict):
    """An attribute table that counts being walked and being read."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.walks = 0
        self.reads = 0

    def items(self):  # type: ignore[no-untyped-def]
        self.walks += 1
        return super().items()

    def __iter__(self):  # type: ignore[no-untyped-def]
        self.walks += 1
        return super().__iter__()

    def __getitem__(self, key):  # type: ignore[no-untyped-def]
        self.reads += 1
        return super().__getitem__(key)

    def __contains__(self, key):  # type: ignore[no-untyped-def]
        self.reads += 1
        return super().__contains__(key)


@dataclass
class _NodeData:
    node_id: int
    attributes: dict[str, Any]


class _EventType:
    def __init__(self, value: str) -> None:
        self.value = value


class BusyClient:
    """Many nodes with large tables, and the one wheel among them."""

    def __init__(self) -> None:
        self.server_info = SimpleNamespace(sdk_version="lab")
        self.callback: Any = None
        self.tables: dict[int, CountingTable] = {}
        self._nodes: list[Any] = []
        for node_id in range(1, NODES):  # 1..63
            table = CountingTable(
                {
                    f"1/{cluster}/{attribute}": 0
                    for cluster in range(60, 90)
                    for attribute in range(10)
                }
            )
            self._add(node_id, table)
        wheel = CountingTable(e2490_node(WHEEL)["attributes"])
        wheel[POSITION] = 0
        self._add(WHEEL, wheel)

    def _add(self, node_id: int, table: CountingTable) -> None:
        self.tables[node_id] = table
        self._nodes.append(SimpleNamespace(node_data=_NodeData(node_id, table)))

    def subscribe_events(self, *, callback: Any):
        self.callback = callback
        return lambda: None

    def get_nodes(self) -> list[Any]:
        return self._nodes

    def update(self) -> None:
        """An attribute update from some device: it carries only its new value."""
        self.callback(_EventType("attribute_updated"), 1)

    def walks(self) -> int:
        return sum(table.walks for table in self.tables.values())

    def reads(self) -> int:
        return sum(table.reads for table in self.tables.values())


class _World:
    def __init__(self, lab: LabHarness, monkeypatch: pytest.MonkeyPatch) -> None:
        self.lab = lab
        self.client = BusyClient()
        self.forwarded: list[tuple[str, Any]] = []
        self.converted = 0
        monkeypatch.setattr(matter_core_module, "time", fake_time_module(lab.clock))
        monkeypatch.setattr(
            matter_core_module,
            "async_track_time_interval",
            lambda _hass, action, interval: lab.scheduler.every(
                interval, action, "core_client_check"
            ),
        )
        real = CoreMatterEventSource._node_to_mapping

        def counted(node: Any) -> dict[str, Any]:
            self.converted += 1
            return real(node)

        monkeypatch.setattr(
            CoreMatterEventSource, "_node_to_mapping", staticmethod(counted)
        )
        entry = SimpleNamespace(
            data={"url": URL},
            runtime_data=SimpleNamespace(
                adapter=SimpleNamespace(matter_client=self.client)
            ),
        )
        hass = SimpleNamespace(
            config_entries=SimpleNamespace(async_loaded_entries=lambda _d: [entry])
        )
        self.source = CoreMatterEventSource(
            hass,  # type: ignore[arg-type]
            URL,
            self._forward,
        )

    def _forward(self, event: str, data: Any) -> None:
        if event.startswith("__") and event != "__nodes__":
            return  # connection lifecycle: real registries, not this scenario
        if event == "attribute_updated":
            self.forwarded.append((event, data))
        self.lab.coordinator._on_event(event, data)

    def start(self) -> None:
        self.lab.tasks.run_now(self.source.start())
        self.lab.settle()

    def stop(self) -> None:
        self.lab.tasks.run_now(self.source.stop())


@pytest.fixture
def world(lab: LabHarness, monkeypatch: pytest.MonkeyPatch):
    built = _World(lab, monkeypatch)
    built.start()
    yield built
    built.stop()


def test_the_wheel_is_found_among_sixty_four_nodes(world) -> None:
    assert list(world.lab.coordinator.wheels) == [WHEEL]
    assert world.converted == NODES, "every node is converted once, when attaching"


def flood_does_no_further_work(world) -> None:
    """200 updates: no table walked again, no node converted again."""
    world.client.update()
    walks, converted = world.client.walks(), world.converted
    for _ in range(200):
        world.client.update()

    assert world.client.walks() == walks
    assert world.converted == converted


def test_a_flood_of_updates_from_other_devices_does_no_further_walking(world) -> None:
    flood_does_no_further_work(world)


def test_the_work_per_update_is_bounded_by_the_watched_paths(world) -> None:
    """Only the wheel has a CurrentPosition path (one); the other 63 nodes are not
    read at all after the first lookup. Per update: one membership test and one
    read of that one path, so 500 updates read at most 2 x 500 attributes.
    """
    world.client.update()
    reads_before = world.client.reads()
    for _ in range(500):
        world.client.update()

    assert world.client.reads() - reads_before <= 2 * 500
    assert all(
        table.reads == 0
        for node_id, table in world.client.tables.items()
        if node_id != WHEEL
    )


def test_a_changed_position_is_forwarded_exactly_once(world) -> None:
    world.client.update()
    world.forwarded.clear()

    world.client.tables[WHEEL][POSITION] = 1
    for _ in range(5):
        world.client.update()

    assert world.forwarded == [("attribute_updated", [WHEEL, POSITION, 1])]
    assert world.lab.record()["ignored"].get("invalid_switch_position", 0) == 0


def lookup_is_refreshed_once_per_node(world) -> None:
    world.client.update()
    walks = world.client.walks()

    world.lab.advance(29.0)
    for _ in range(100):
        world.client.update()
    assert world.client.walks() == walks

    # 70 s in, every node is past its own limit (30 s plus up to 29 s of jitter):
    # exactly one walk each, no more, and none missed.
    world.lab.advance(41.0)
    world.client.update()
    refreshed = world.client.walks()
    assert refreshed - walks == NODES
    for _ in range(100):
        world.client.update()
    assert world.client.walks() == refreshed


def test_the_lookup_is_repeated_only_after_its_age_limit_and_once_per_node(
    world,
) -> None:
    """Paths are looked up again every 30-60 s so a table changed in place is
    found: after 29 s nothing; past the limit exactly one walk per node, then
    nothing again.
    """
    lookup_is_refreshed_once_per_node(world)


def test_a_wheel_still_scrolls_correctly_during_the_flood(world) -> None:
    """Gestures and attribute updates interleave; every notch is still counted once."""
    lab = world.lab
    wire = Wire(WHEEL)
    gesture = wire.scroll(UP1, ongoing=(6,), complete=6)
    for index, event in enumerate(gesture):
        for _ in range(50):
            world.client.update()
        lab.at(0.2 * index)
        lab.emit(event)

    assert lab.rotations() == [(1, "up", 1), (1, "up", 5)]


# -- mutations: the old behaviour must fail the scenario ----------------------


def test_mutation_looking_the_paths_up_on_every_update_is_caught(
    world, monkeypatch
) -> None:
    """The cache is made to expire at once: every update walks the tables again,
    which is the shape of the Core freeze. Patched for this test only.
    """
    monkeypatch.setattr(matter_core_module, "_POSITION_PATH_MAX_AGE", -1000.0)
    with pytest.raises(AssertionError):
        flood_does_no_further_work(world)


def test_mutation_converting_every_node_on_every_update_is_caught(
    world, monkeypatch
) -> None:
    """The other half of the old bug: every update converted every node."""
    real = CoreMatterEventSource._forward_switch_position_updates

    def converting(self: CoreMatterEventSource) -> None:
        for node in self._matter_client.get_nodes():
            self._node_to_mapping(node)
        real(self)

    monkeypatch.setattr(
        CoreMatterEventSource, "_forward_switch_position_updates", converting
    )
    with pytest.raises(AssertionError):
        flood_does_no_further_work(world)


def test_mutation_a_cache_that_never_expires_is_caught(world, monkeypatch) -> None:
    """With expiry removed no node is ever refreshed: zero walks, not ``NODES``."""
    monkeypatch.setattr(matter_core_module, "_POSITION_PATH_MAX_AGE", float("inf"))
    with pytest.raises(AssertionError):
        lookup_is_refreshed_once_per_node(world)
