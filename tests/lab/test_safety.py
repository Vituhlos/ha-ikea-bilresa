"""The lab's safety boundary: it fails closed, and says so.

Nothing here weakens production rules; it proves that the sandbox the other
tests stand on holds. Each refusal is recorded in ``lab.safety`` and the test
acknowledges it explicitly, so a refusal nobody expected fails the test that
caused it (see ``conftest.lab``).
"""

from __future__ import annotations

import asyncio
import socket
import time
from typing import Any

import pytest

from custom_components.ikea_bilresa import binding as binding_module

from .fake_matter import E2490_ENDPOINTS, Wire, e2490_node
from .harness import LabHarness
from .service_spy import LabSafetyViolation
from .targets import LightTarget, Target

NODE = 14
BTN1 = E2490_ENDPOINTS[1]["button"]


class _Inert(Target):
    """A lab-owned entity whose domain the lab has no model for.

    ``apply`` must never run: reaching it would mean a service call got past
    the allow-list.
    """

    reached = False

    def apply(self, service: str, data: dict[str, Any]):
        type(self).reached = True
        raise AssertionError("an unmodelled service must never be applied")

    def publish(self, snapshot: Any) -> None: ...

    def reported_state(self) -> tuple[str, dict[str, Any]]:
        return "off", {}

    def requested(self) -> dict[str, Any]:
        return {}

    def value(self) -> Any:
        return None


def _call(lab, *args: Any, **kwargs: Any) -> None:
    """Run one direct service call through the spy, as the binding would."""
    coro = lab.hass.services.async_call(*args, **kwargs)
    lab.tasks.run_now(coro)


# -- the hass double ----------------------------------------------------------


def test_hass_has_only_what_the_binding_needs(lab) -> None:
    for attribute in ("config", "config_entries", "data", "loop", "async_add_job"):
        with pytest.raises(LabSafetyViolation):
            getattr(lab.hass, attribute)
    with pytest.raises(LabSafetyViolation):
        lab.hass.bus.async_listen("anything", lambda event: None)

    kinds = [e["kind"] for e in lab.safety.acknowledge()]
    assert kinds.count("hass_attribute_blocked") == 5
    assert kinds.count("bus_attribute_blocked") == 1


# -- direct service calls -----------------------------------------------------


@pytest.mark.parametrize(
    ("domain", "service", "data", "kind"),
    [
        ("script", "turn_on", {"entity_id": "script.evil"}, "service_not_allowed"),
        (
            "automation",
            "trigger",
            {"entity_id": "automation.evil"},
            "service_not_allowed",
        ),
        ("homeassistant", "restart", {}, "service_not_allowed"),
        ("light", "turn_on", {"entity_id": "light.kitchen"}, "entity_not_lab_owned"),
        # A name that only looks like ours is not ours: ownership is a lookup,
        # never a prefix.
        ("light", "turn_on", {"entity_id": "light.lab_spoof"}, "entity_not_lab_owned"),
        ("light", "turn_on", {}, "no_entity_id"),
    ],
)
def test_a_service_outside_the_lab_is_refused_and_recorded(
    lab, domain: str, service: str, data: dict[str, Any], kind: str
) -> None:
    lab.add_target(LightTarget("light.lab", brightness=100))

    with pytest.raises(LabSafetyViolation):
        _call(lab, domain, service, data)

    assert lab.spy.intents[-1]["status"] == f"rejected:{kind}"
    assert [e["kind"] for e in lab.safety.acknowledge()] == [kind]
    assert lab.registry.target("light.lab").value() == 100, "a refusal changes nothing"


def test_a_service_target_parameter_is_refused(lab) -> None:
    """Area, device and label targets are never resolved in the lab."""
    lab.add_target(LightTarget("light.lab", brightness=100))

    with pytest.raises(LabSafetyViolation):
        _call(
            lab,
            "light",
            "turn_on",
            {"entity_id": "light.lab"},
            target={"area_id": "kitchen"},
        )

    assert [e["kind"] for e in lab.safety.acknowledge()] == [
        "target_parameter_not_allowed"
    ]


# -- what the production binding generates ------------------------------------


@pytest.mark.parametrize(
    ("entity", "action"),
    [("script.evil", "on"), ("automation.evil", "trigger")],
)
def test_a_press_aimed_at_a_script_or_automation_cannot_reach_it(
    lab, entity: str, action: str
) -> None:
    """The binding builds script.turn_on / automation.trigger; the spy stops it."""
    _Inert.reached = False
    lab.add_target(_Inert(entity))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(
        {
            "node_id": NODE,
            "channel": 1,
            "target": "light.lab",
            "mode": "brightness",
            "click_action": action,
            "click_target": entity,
        }
    )
    lab.add_target(LightTarget("light.lab"))
    wire = Wire(NODE)
    lab.play([(0.0, event) for event in wire.click(BTN1, 1)])

    domain = entity.split(".")[0]
    assert [(i["domain"], i["status"]) for i in lab.spy.intents] == [
        (domain, "rejected:service_not_allowed")
    ]
    assert _Inert.reached is False
    assert [e["kind"] for e in lab.safety.acknowledge()] == ["service_not_allowed"]


@pytest.mark.parametrize("gesture", ["click", "hold"])
def test_user_actions_are_never_built_or_run(lab, gesture: str) -> None:
    """A "run actions" gesture is stopped before any script exists."""
    sequence = [{"action": "script.turn_on", "target": {"entity_id": "script.evil"}}]
    config: dict[str, Any] = {
        "node_id": NODE,
        "channel": 1,
        "target": "light.lab",
        "mode": "brightness",
    }
    if gesture == "click":
        config.update({"click_action": "run", "click_sequence": sequence})
    else:
        config.update({"hold_action": "run", "hold_sequence": sequence})
    lab.add_target(LightTarget("light.lab"))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(config)
    wire = Wire(NODE)
    if gesture == "click":
        lab.play([(0.0, event) for event in wire.click(BTN1, 1)])
    else:
        lab.play(
            [
                (0.0, wire.event(BTN1, "initial_press")),
                (0.72, wire.event(BTN1, "long_press")),
                (1.2, wire.event(BTN1, "long_release")),
            ]
        )

    assert lab.spy.intents == [], "no service call was made"
    assert [(e["kind"], e["where"]) for e in lab.safety.acknowledge()] == [
        ("script_blocked", "validate")
    ]
    failed = [a for a in lab.dispatcher.activity if a["status"] == "failed"]
    assert [a["reason"] for a in failed] == ["invalid_actions"]


def test_building_a_script_directly_is_refused(lab) -> None:
    with pytest.raises(LabSafetyViolation):
        binding_module.Script(lab.hass, [], "evil", "ikea_bilresa")
    assert [e["kind"] for e in lab.safety.acknowledge()] == ["script_blocked"]


def test_reading_the_real_registries_is_refused(lab) -> None:
    with pytest.raises(LabSafetyViolation):
        binding_module.async_extract_referenced_entity_ids(lab.hass, {})  # type: ignore[arg-type]
    assert [e["kind"] for e in lab.safety.acknowledge()] == ["registry_access_blocked"]


# -- tasks, network, clock ----------------------------------------------------


def test_a_task_that_would_wait_for_something_real_is_refused(lab) -> None:
    with pytest.raises(LabSafetyViolation):
        lab.tasks.run_now(asyncio.sleep(0))
    assert [e["kind"] for e in lab.safety.acknowledge()] == ["task_suspended"]


def test_the_network_tripwire_blocks_everything_but_loopback(
    lab, network_attempts: list[str]
) -> None:
    """A connection or a lookup toward a Matter server never leaves the process.

    No socket is created: the tripwire's ``connect`` is called directly with a
    stand-in object (it raises before it would use it), so this also holds on
    Linux CI, where the Home Assistant test plugin refuses to create sockets at
    all. The address is a documentation range and the name does not exist.
    """
    with pytest.raises(LabSafetyViolation):
        socket.socket.connect(object(), ("192.0.2.1", 5580))  # type: ignore[arg-type]
    with pytest.raises(LabSafetyViolation):
        socket.getaddrinfo("matter-server.invalid", 5580)

    assert network_attempts == ["192.0.2.1", "matter-server.invalid"]
    network_attempts.clear()


def test_the_process_clock_is_not_patched() -> None:
    """Only the name ``time`` inside the binding module is rebound, and restored."""
    real = time.monotonic
    with pytest.MonkeyPatch.context() as patch:
        harness = LabHarness(patch)
        assert time.monotonic is real
        assert binding_module.time is not time
        harness.close()
    assert binding_module.time is time
    assert time.monotonic is real


# -- timers -------------------------------------------------------------------


def _ramp_setup(lab) -> Wire:
    lab.add_target(LightTarget("light.lab", brightness=100))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(
        {
            "node_id": NODE,
            "channel": 1,
            "target": "light.lab",
            "mode": "brightness",
            "step": 3,
            "transition": 0.0,
            "hold_action": "ramp",
            "hold_target": "light.lab",
        }
    )
    return Wire(NODE)


def test_a_hold_ramp_starts_and_a_release_leaves_no_timer(lab) -> None:
    wire = _ramp_setup(lab)
    lab.play(
        [
            (0.0, wire.event(BTN1, "initial_press")),
            (0.72, wire.event(BTN1, "long_press")),
        ]
    )
    lab.at(1.5)
    running = [t for t in lab.scheduler.pending() if not t.startswith("echo:")]
    ramping_intents = len(lab.spy.intents)
    assert running, "a ramp is running while the button is held"
    assert ramping_intents >= 1

    lab.play([(1.6, wire.event(BTN1, "long_release"))])
    assert [t for t in lab.scheduler.pending() if not t.startswith("echo:")] == []


def test_a_lost_release_is_stopped_by_the_watchdog(lab) -> None:
    """No LongRelease ever arrives: the 30 s watchdog ends the ramp by itself."""
    wire = _ramp_setup(lab)
    lab.play(
        [
            (0.0, wire.event(BTN1, "initial_press")),
            (0.72, wire.event(BTN1, "long_press")),
        ]
    )
    lab.at(40.0)

    assert [t for t in lab.scheduler.pending() if not t.startswith("echo:")] == []
    sent_by_30s = [i for i in lab.spy.intents if i["t"] <= 31.0]
    assert sent_by_30s, "the ramp did run before it was stopped"
    assert all(i["t"] <= 31.0 for i in lab.spy.intents), "nothing after the watchdog"


def test_shutdown_during_a_hold_cancels_the_ramp(lab) -> None:
    """The fixture's teardown asserts it: no timer survives ``async_stop``."""
    wire = _ramp_setup(lab)
    lab.play(
        [
            (0.0, wire.event(BTN1, "initial_press")),
            (0.72, wire.event(BTN1, "long_press")),
        ]
    )
    assert [t for t in lab.scheduler.pending() if not t.startswith("echo:")]
