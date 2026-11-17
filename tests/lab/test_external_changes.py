"""Outside changes, delayed echoes and the device itself: three different things.

* a *command* from the binding changes the device (``_applied``) at once;
* an *echo* only moves what Home Assistant sees (``_reported``), later;
* an *outside change* (an app, an automation, another remote) moves both.

A report that was already in flight when an outside change happened is, by
default, superseded and dropped: the device reports in order and its newest
state supersedes older reports. ``stale_echoes="deliver"`` models the opposite, a
reordered stale report that arrives after the change. Both are tested, and an
echo that was delivered before the change is simply history.

Each scenario is a plain function of the harness and the target class, so the
mutation tests at the end can run it against a deliberately wrong target and
prove it fails.
"""

from __future__ import annotations

from typing import Any

import pytest

from .fake_matter import E2490_ENDPOINTS, Wire, e2490_node
from .harness import LabHarness
from .targets import (
    ClimateTarget,
    LightTarget,
    MediaPlayerTarget,
    NumberTarget,
)

NODE = 14
UP1 = E2490_ENDPOINTS[1]["up"]
BTN1 = E2490_ENDPOINTS[1]["button"]
LIGHT = "light.lab"


def _rotation_binding(target: str, mode: str, step: int) -> dict[str, Any]:
    return {
        "node_id": NODE,
        "channel": 1,
        "target": target,
        "mode": mode,
        "step": step,
        "step_curve": "linear",
        "transition": 0.0,
    }


def _notch(lab: LabHarness, when: float) -> None:
    wire = Wire(NODE)
    lab.play([(when, event) for event in wire.scroll(UP1, complete=1)])


# -- scenario: toggle after an outside change ---------------------------------


def toggle_after_outside_change(
    lab: LabHarness, light_class: type[LightTarget], *, start_on: bool
) -> None:
    """On -> outside off -> toggle -> on, and the mirror image."""
    lab.add_target(light_class(LIGHT, on=start_on, brightness=120))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(
        {
            "node_id": NODE,
            "channel": 1,
            "target": LIGHT,
            "mode": "brightness",
            "click_action": "toggle",
            "click_target": LIGHT,
        }
    )
    lab.at(1.0)
    lab.registry.external_change(LIGHT, (not start_on, 120))
    lab.settle()
    target = lab.registry.target(LIGHT)
    assert target.requested()["state"] == ("off" if start_on else "on")
    seen = lab.registry.get(LIGHT)
    assert seen is not None and seen.state == ("off" if start_on else "on")

    wire = Wire(NODE)
    lab.play([(2.0, event) for event in wire.click(BTN1, 1)])

    assert [(i["service"], i["status"]) for i in lab.spy.intents] == [
        ("toggle", "accepted")
    ]
    # The toggle must act on what the device really is, not on a stale copy.
    assert target.requested()["state"] == ("on" if start_on else "off")


@pytest.mark.parametrize("start_on", [True, False])
def test_toggle_acts_on_the_state_after_an_outside_change(
    lab: LabHarness, start_on: bool
) -> None:
    toggle_after_outside_change(lab, LightTarget, start_on=start_on)


# -- scenarios: the next rotation starts from what the outside set ------------


def test_an_outside_brightness_change_is_what_the_next_turn_starts_from(lab) -> None:
    """100 -> outside 40 -> one notch up: 40 + 7.65 = 47.65, sent as 48."""
    lab.add_target(LightTarget(LIGHT, brightness=100))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_rotation_binding(LIGHT, "brightness", 3))
    lab.at(10.0)
    lab.registry.external_change(LIGHT, (True, 40))
    lab.settle()
    assert lab.registry.target(LIGHT).requested() == {"state": "on", "brightness": 40}
    assert lab.registry.target(LIGHT).value() == 40

    _notch(lab, 11.0)

    assert [i["data"]["brightness"] for i in lab.spy.intents] == [48]
    assert lab.registry.target(LIGHT).requested()["brightness"] == 48


def test_an_outside_number_change_is_what_the_next_turn_starts_from(lab) -> None:
    """0-100, now 50 -> outside 20 -> 10 % per notch: 30."""
    entity = "input_number.lab_level"
    lab.add_target(NumberTarget(entity, minimum=0, maximum=100, step=1, value=50))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_rotation_binding(entity, "number", 10))
    lab.at(10.0)
    lab.registry.external_change(entity, 20)
    lab.settle()
    assert lab.registry.target(entity).requested() == {"value": 20.0}

    _notch(lab, 11.0)

    assert [i["data"]["value"] for i in lab.spy.intents] == [30.0]


def test_an_outside_climate_change_is_what_the_next_turn_starts_from(lab) -> None:
    """7-35, now 20 -> outside 25 -> one notch is 2.8: 27.8, rounded to 28.0."""
    lab.add_target(
        ClimateTarget(
            "climate.lab",
            min_temp=7,
            max_temp=35,
            temperature=20.0,
            target_temp_step=0.5,
        )
    )
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_rotation_binding("climate.lab", "temperature", 10))
    lab.at(10.0)
    lab.registry.external_change("climate.lab", 25.0)
    lab.settle()
    assert lab.registry.target("climate.lab").requested() == {"temperature": 25.0}

    _notch(lab, 11.0)

    assert [i["data"]["temperature"] for i in lab.spy.intents] == [28.0]


def test_an_outside_volume_change_is_what_the_next_turn_starts_from(lab) -> None:
    """Now 0.30 -> outside 0.60 -> 10 % per notch: 0.70."""
    speaker = "media_player.lab_speaker"
    lab.add_target(MediaPlayerTarget(speaker, volume=0.3))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_rotation_binding(speaker, "volume", 10))
    lab.at(10.0)
    lab.registry.external_change(speaker, 0.6)
    lab.settle()
    assert lab.registry.target(speaker).requested() == {"volume_level": 0.6}

    _notch(lab, 11.0)

    assert [i["data"]["volume_level"] for i in lab.spy.intents] == [0.7]


# -- scenarios: an echo versus an outside change ------------------------------


def _delayed_echo_world(lab: LabHarness, light_class: type[LightTarget]) -> None:
    """Light 100, reports 0.4 s late; one notch at 0 s asks for 108."""
    lab.add_target(light_class(LIGHT, brightness=100, echo_delay=0.4))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_rotation_binding(LIGHT, "brightness", 3))
    _notch(lab, 0.0)


def echo_never_changes_the_device(
    lab: LabHarness, light_class: type[LightTarget]
) -> None:
    """A reordered stale echo moves only the reported value, never the device."""
    _delayed_echo_world(lab, light_class)
    target = lab.registry.target(LIGHT)
    assert target.requested()["brightness"] == 108, "the command is applied at once"
    assert target.value() == 100, "but still reported old"

    lab.at(0.1)
    lab.registry.external_change(LIGHT, (True, 40), stale_echoes="deliver")
    lab.at(0.5)

    assert target.value() == 108, "the stale echo was delivered after the change"
    assert target.requested() == {"state": "on", "brightness": 40}, "device untouched"
    delivered = [h for h in lab.registry.history if h.get("stale")]
    assert [h["value"] for h in delivered] == [108]


def test_an_echo_only_moves_what_is_reported(lab) -> None:
    echo_never_changes_the_device(lab, LightTarget)


def test_an_echo_in_flight_is_superseded_by_an_outside_change(lab) -> None:
    """Default: the change at 0.1 s drops the 108 echo due at 0.4 s."""
    _delayed_echo_world(lab, LightTarget)
    lab.at(0.1)
    lab.registry.external_change(LIGHT, (True, 40))
    lab.at(0.5)
    target = lab.registry.target(LIGHT)

    assert target.value() == 40 and target.requested()["brightness"] == 40
    kinds = [h["event"] for h in lab.registry.history]
    assert kinds == ["requested", "external", "stale_echo_dropped"]


def test_an_echo_already_delivered_is_just_history(lab) -> None:
    """The change at 0.6 s comes after the 0.4 s echo: both stand, in order."""
    _delayed_echo_world(lab, LightTarget)
    lab.at(0.6)
    lab.registry.external_change(LIGHT, (True, 40))
    target = lab.registry.target(LIGHT)

    assert target.value() == 40 and target.requested()["brightness"] == 40
    assert [(h["event"], h.get("value")) for h in lab.registry.history] == [
        ("requested", None),
        ("reported", 108),
        ("external", 40),
    ]


def test_a_change_at_the_very_instant_of_the_echo_comes_after_it(lab) -> None:
    """Defined tie-break: ``at(0.4)`` runs the echo due at 0.4 s first."""
    _delayed_echo_world(lab, LightTarget)
    lab.at(0.4)
    lab.registry.external_change(LIGHT, (True, 40))

    assert [(h["event"], h.get("value")) for h in lab.registry.history] == [
        ("requested", None),
        ("reported", 108),
        ("external", 40),
    ]


def test_a_reordered_stale_echo_leaves_reported_and_device_apart(lab) -> None:
    """``deliver``: the old 108 arrives after the change; reported 108, device 40."""
    _delayed_echo_world(lab, LightTarget)
    lab.at(0.1)
    lab.registry.external_change(LIGHT, (True, 40), stale_echoes="deliver")
    lab.at(0.5)
    target = lab.registry.target(LIGHT)

    assert (target.value(), target.requested()["brightness"]) == (108, 40)
    assert [(h["event"], h.get("stale")) for h in lab.registry.history] == [
        ("requested", None),
        ("external", None),
        ("reported", True),
    ]


def test_an_unknown_stale_policy_is_refused(lab) -> None:
    lab.add_target(LightTarget(LIGHT, brightness=100))
    with pytest.raises(ValueError):
        lab.registry.external_change(LIGHT, (True, 40), stale_echoes="sometimes")


# -- determinism -------------------------------------------------------------------


def _digest_of(variant: str) -> str:
    with pytest.MonkeyPatch.context() as patch:
        lab = LabHarness(patch)
        _delayed_echo_world(lab, LightTarget)
        if variant == "drop":
            lab.at(0.1)
            lab.registry.external_change(LIGHT, (True, 40))
        elif variant == "deliver":
            lab.at(0.1)
            lab.registry.external_change(LIGHT, (True, 40), stale_echoes="deliver")
        elif variant == "after":
            lab.at(0.6)
            lab.registry.external_change(LIGHT, (True, 40))
        lab.at(1.0)
        digest = lab.digest()
        lab.close()
    return digest


@pytest.mark.parametrize("variant", ["drop", "deliver", "after"])
def test_the_same_echo_conflict_repeats_exactly(variant: str) -> None:
    assert _digest_of(variant) == _digest_of(variant)


def test_the_three_conflict_orders_really_differ() -> None:
    assert len({_digest_of(v) for v in ("drop", "deliver", "after")}) == 3


# -- mutations: a wrong target must make the scenarios fail -------------------------


class _OnlyReportsTheChange(LightTarget):
    """Wrong: an outside change updates what is reported, not the device."""

    def set_device(self, snapshot: Any) -> None:
        self._reported = snapshot


class _EchoChangesTheDevice(LightTarget):
    """Wrong: a delayed echo also overwrites the device's real state."""

    def publish(self, snapshot: Any) -> None:
        self._applied = snapshot
        self._reported = snapshot


@pytest.mark.parametrize("start_on", [True, False])
def test_mutation_a_device_that_ignores_the_change_fails_the_toggle_scenario(
    lab: LabHarness, start_on: bool
) -> None:
    with pytest.raises(AssertionError):
        toggle_after_outside_change(lab, _OnlyReportsTheChange, start_on=start_on)


def test_mutation_an_echo_that_changes_the_device_fails_the_echo_scenario(
    lab: LabHarness,
) -> None:
    with pytest.raises(AssertionError):
        echo_never_changes_the_device(lab, _EchoChangesTheDevice)
