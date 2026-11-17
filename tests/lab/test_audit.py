"""Guards on the lab itself: that it uses production code, and stays sealed.

* the production decoder, engine, coordinator and binding really run (and the
  lab contains no second copy of them);
* the lab never asks for a fixture that could reach a real Home Assistant, a
  real socket or real time;
* simulated time does not leak into real time or into the event loop;
* the extra doubles refuse what they do not model.
"""

from __future__ import annotations

import asyncio
from collections import Counter
import functools
import os
from pathlib import Path
import re
import socket
import sys
import time
from typing import Any

import pytest

from custom_components.ikea_bilresa import coordinator as coordinator_module
from custom_components.ikea_bilresa import model
from custom_components.ikea_bilresa.binding import LightBinding
from custom_components.ikea_bilresa.coordinator import BilresaCoordinator
from custom_components.ikea_bilresa.engine import GestureEngine

from .conftest import _REAL_MONOTONIC
from .fake_matter import E2490_ENDPOINTS, Wire, e2490_node
from .service_spy import LabSafetyViolation
from .targets import LightTarget, MediaPlayerTarget

LAB = Path(__file__).parent
SOURCES = sorted(p for p in LAB.glob("*.py") if p.name != "test_audit.py")
UP1 = E2490_ENDPOINTS[1]["up"]


# -- production code really runs, and is not copied ---------------------------


def test_the_lab_uses_the_production_objects(lab) -> None:
    assert type(lab.coordinator) is BilresaCoordinator
    assert coordinator_module.parse_node is model.parse_node
    assert coordinator_module.decode_event is model.decode_event
    assert type(lab.coordinator._engine) is GestureEngine


def test_a_scroll_runs_every_production_stage(lab, monkeypatch) -> None:
    """Count the real calls: parse_node, decode_event, the engine, the binding."""
    calls: Counter[str] = Counter()

    def count(owner: Any, name: str, label: str) -> None:
        original = getattr(owner, name)

        @functools.wraps(original)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            calls[label] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(owner, name, wrapper)

    count(coordinator_module, "parse_node", "parse_node")
    count(coordinator_module, "decode_event", "decode_event")
    count(GestureEngine, "process", "GestureEngine.process")
    count(LightBinding, "_handle_action", "LightBinding._handle_action")
    count(LightBinding, "_dispatch_call", "LightBinding._dispatch_call")

    lab.add_target(LightTarget("light.lab", brightness=100))
    lab.load(e2490_node(14))
    lab.setup_bindings(
        {
            "node_id": 14,
            "channel": 1,
            "target": "light.lab",
            "mode": "brightness",
            "step": 3,
            "transition": 0.0,
        }
    )
    wire = Wire(14)
    lab.play([(0.0, event) for event in wire.scroll(UP1, complete=1)])

    assert calls["parse_node"] == 1
    assert calls["decode_event"] == 3
    assert calls["GestureEngine.process"] == 3
    assert calls["LightBinding._handle_action"] == 1
    assert calls["LightBinding._dispatch_call"] == 1
    assert len(lab.spy.intents) == 1


def test_the_lab_holds_no_second_copy_of_production_logic() -> None:
    """No lab module defines a decoder, an engine or a binding of its own."""
    forbidden = re.compile(
        r"^\s*(?:async\s+)?(?:def|class)\s+"
        r"(parse_node|decode_event|parse_taglist|GestureEngine|LightBinding|"
        r"_rotate_(?:brightness|volume|number|temperature|color_temp|color|cover|fan|mode|by)"
        r"|_brightness_step|_resync|_delta)\b",
        re.MULTILINE,
    )
    offenders = [
        f"{path.name}: {match.group(1)}"
        for path in SOURCES
        for match in forbidden.finditer(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


# -- the lab never asks for anything that could be real -----------------------


def test_the_lab_requests_no_real_home_assistant_socket_or_clock_fixture() -> None:
    """Static check of every lab source (this file is the one exempt, it names them)."""
    forbidden = [
        # fixtures that give a real hass, a real server or open sockets
        "socket_enabled",
        "enable_socket",
        "hass_client",
        "hass_ws_client",
        "aiohttp_client",
        "aiohttp_server",
        "MockConfigEntry",
        "async_setup_component",
        "requests_mock",
        "respx",
        "freezer",
        # real waiting
        "time.sleep(",
        "threading",
        "subprocess",
    ]
    hits = [
        f"{path.name}: {token}"
        for path in SOURCES
        for token in forbidden
        if token in path.read_text(encoding="utf-8")
    ]
    assert hits == []


def test_the_lab_never_waits_for_real_time() -> None:
    """``asyncio.sleep`` appears only as the zero-length probe of the task guard."""
    pattern = re.compile(r"asyncio\.sleep\((?!0\))")
    assert [p.name for p in SOURCES if pattern.search(p.read_text("utf-8"))] == []


@pytest.mark.skipif(
    not os.environ.get("CI") or sys.platform == "win32",
    reason=(
        "SKIP outside Linux CI: the Home Assistant test plugin's socket guard is the"
        " canonical outer layer only there (CI=true); a local Windows run uses a"
        " stand-in that switches it off"
    ),
)
def test_the_ha_plugin_socket_guard_is_on_in_ci() -> None:
    """Outer layer, independent of the lab's own tripwire."""
    assert socket.socket.__name__ == "GuardedSocket"


# -- time -------------------------------------------------------------------


async def test_the_event_loop_keeps_real_time_while_the_lab_runs(lab) -> None:
    """pytest-asyncio's loop and ``time.monotonic`` are untouched by the fake clock."""
    loop = asyncio.get_running_loop()
    started = loop.time()
    fake_before = lab.clock.now

    await asyncio.sleep(0.02)

    assert time.monotonic is _REAL_MONOTONIC
    assert loop.time() - started >= 0.015
    assert lab.clock.now == fake_before, "the real sleep did not move the fake clock"
    lab.advance(5.0)
    assert loop.time() - started < 4.0, "the fake clock did not move the real one"


def test_the_lab_clock_only_moves_when_the_scheduler_moves_it(lab) -> None:
    before = lab.clock.now
    time.sleep(0)  # a real call, zero length
    assert lab.clock.now == before
    lab.advance(2.5)
    assert lab.clock.now == before + 2.5


# -- the doubles refuse what they do not model ------------------------------


def test_the_services_and_states_doubles_refuse_unknown_attributes(lab) -> None:
    with pytest.raises(LabSafetyViolation):
        lab.hass.services.async_register("evil", "run", lambda call: None)
    with pytest.raises(LabSafetyViolation):
        lab.hass.states.async_set("light.lab", "on")

    assert [e["kind"] for e in lab.safety.acknowledge()] == [
        "services_attribute_blocked",
        "states_attribute_blocked",
    ]


def test_a_service_of_another_kind_of_entity_is_refused(lab) -> None:
    """``light.turn_on`` aimed at a lab media player is not a thing the lab models."""
    lab.add_target(MediaPlayerTarget("media_player.lab", volume=0.5))
    with pytest.raises(LabSafetyViolation):
        lab.tasks.run_now(
            lab.hass.services.async_call(
                "light", "turn_on", {"entity_id": "media_player.lab"}
            )
        )

    assert lab.spy.intents[-1]["status"] == "rejected:service_not_allowed_for_entity"
    assert lab.registry.target("media_player.lab").value() == 0.5
    lab.safety.acknowledge()
