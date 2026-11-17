"""Issue #9: a Zigbee2MQTT light group reports wandering levels mid-scroll.

The reporter's setup: a group of 3-4 bulbs, wheel step 3, transition 0.8. Z2M does
not report an average for a group; it passes up whichever member reported last,
so during a fade the group's reported brightness wanders, "usually much brighter
than the levels just before and after". The binding must not rebase its next
step onto such a report while the scroll is under way.

``GroupLightTarget`` models exactly that: for every command the group first
reports the old level, then a level 60 units brighter, and only then the new one.

Expected values are plain arithmetic: starting at 100, notch k of a 3 % linear
step (7.65 units) lands on ``round(100 + 7.65 k)``: 108, 115, 123, 131, 138, 146.
(The reporter used the perceptual curve; the linear one keeps the arithmetic
checkable by hand.) The first notch of a scroll is sent without a fade and every
later one with the whole configured 0.8 s, as ``_smoothing_transition`` documents.
"""

from __future__ import annotations

from typing import Any

import pytest

from .fake_matter import E2490_ENDPOINTS, Wire, e2490_node
from .harness import LabHarness
from .targets import GroupLightTarget, LightTarget

NODE = 14
UP1 = E2490_ENDPOINTS[1]["up"]
GROUP = "light.group"
START = 100
EXPECTED = [round(START + 7.65 * k) for k in range(1, 7)]


def _binding(target: Any, **extra: Any) -> dict[str, Any]:
    return {
        "node_id": NODE,
        "channel": 1,
        "target": target,
        "mode": "brightness",
        "step": 3,
        "step_curve": "linear",
        "transition": 0.8,
        **extra,
    }


def _notches(lab: LabHarness, count: int, *, start: float = 0.0) -> None:
    """``count`` single notches, half a second apart (a slow scroll)."""
    wire = Wire(NODE)
    for index in range(count):
        lab.play([(start + 0.5 * index, e) for e in wire.scroll(UP1, complete=1)])


def _sent(lab: LabHarness) -> list[tuple[Any, Any]]:
    return [
        (i["data"].get("brightness"), i["data"].get("transition"))
        for i in lab.spy.intents
    ]


def wandering_group_scenario(lab: LabHarness) -> None:
    lab.add_target(GroupLightTarget(GROUP, brightness=START))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_binding(GROUP))
    _notches(lab, 6)
    lab.advance(3.0)

    assert _sent(lab) == [
        (level, 0.0 if index == 0 else 0.8) for index, level in enumerate(EXPECTED)
    ]
    # The group really did wander: three reports per command, two of them wrong.
    reported = [h["value"] for h in lab.registry.history if h["event"] == "reported"]
    assert any(value > 150 for value in reported[:6]), "the bright member reported"
    # ...and the wheel ended where six notches put it, not on a stale level.
    assert lab.registry.target(GROUP).requested()["brightness"] == EXPECTED[-1]
    assert lab.registry.target(GROUP).value() == EXPECTED[-1]


def test_wandering_group_reports_do_not_move_the_scroll(lab) -> None:
    wandering_group_scenario(lab)


def test_every_notch_after_the_first_is_faded_for_the_whole_transition(lab) -> None:
    """The reporter's second point, and the documented answer: the first notch of
    a scroll is eager (0.0), the following ones carry the configured 0.8 s.
    """
    lab.add_target(GroupLightTarget(GROUP, brightness=START))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_binding(GROUP))
    _notches(lab, 4)

    assert [t for _, t in _sent(lab)] == [0.0, 0.8, 0.8, 0.8]


def test_a_genuine_outside_change_after_the_scroll_is_honoured(lab) -> None:
    """The window is bounded: once the scroll has been quiet, an outside change to
    40 is what the next notch starts from: 40 + 7.65 = 47.65, sent as 48.
    """
    lab.add_target(GroupLightTarget(GROUP, brightness=START))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_binding(GROUP))
    _notches(lab, 1)
    lab.at(10.0)
    lab.registry.external_change(GROUP, (True, 40))
    lab.settle()
    _notches(lab, 1, start=11.0)

    assert [level for level, _ in _sent(lab)] == [108, 48]


# -- one binding, several lights ----------------------------------------------


def multi_light_scenario(lab: LabHarness) -> None:
    members = ["light.a", "light.b", "light.c"]
    for member, delay in zip(members, (0.1, 0.3, 0.6), strict=True):
        lab.add_target(LightTarget(member, brightness=START, echo_delay=delay))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_binding(members))
    _notches(lab, 6)
    lab.advance(3.0)

    # Bulbs acknowledge at different times; the binding still sends one value to
    # all three each time, from its own tracked level.
    assert [i["entity_id"] for i in lab.spy.intents] == [members] * 6
    assert [level for level, _ in _sent(lab)] == EXPECTED
    for member in members:
        assert lab.registry.target(member).value() == EXPECTED[-1]


def test_lights_that_acknowledge_at_different_times_stay_in_step(lab) -> None:
    multi_light_scenario(lab)


# -- mutation: a binding that rebases onto every report is caught -------------


def test_mutation_rebasing_onto_wandering_reports_fails_the_scenario(
    lab, monkeypatch
) -> None:
    """Treat the scroll as never authoritative, so every report is believed: the
    exact failure of issue #9. Patches the production class inside this test only.
    """
    from custom_components.ikea_bilresa.binding import LightBinding

    monkeypatch.setattr(LightBinding, "_scroll_authoritative", lambda self, now: False)
    with pytest.raises(AssertionError):
        wandering_group_scenario(lab)


def _digest(scenario: Any) -> str:
    with pytest.MonkeyPatch.context() as patch:
        lab = LabHarness(patch)
        scenario(lab)
        digest = lab.digest()
        lab.close()
    return digest


@pytest.mark.parametrize("scenario", [wandering_group_scenario, multi_light_scenario])
def test_the_scenarios_repeat_exactly(scenario: Any) -> None:
    assert _digest(scenario) == _digest(scenario)
