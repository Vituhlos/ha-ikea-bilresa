"""B10: number, input_number and climate targets, and the PR #71 defect.

A ``number`` target is rotated by a percentage of its own range, so the range
is the whole question. The expected values are worked out from the range by
hand: a 10 % step of a span of 10 is 1, of a span of 30 is 3, and so on.

PR #71 (a valid bound of ``0`` read as missing) is fixed on this branch: the
three scenarios below that reproduced it are ordinary tests now, with the inputs
and expected values they always had.
"""

from __future__ import annotations

from typing import Any

import pytest

from .catalog import covers
from .fake_matter import E2490_ENDPOINTS, Wire, e2490_node
from .targets import ClimateTarget, NumberTarget

NODE = 14
UP1 = E2490_ENDPOINTS[1]["up"]
DOWN1 = E2490_ENDPOINTS[1]["down"]


def _binding(target: str, mode: str, step: int) -> dict[str, Any]:
    return {
        "node_id": NODE,
        "channel": 1,
        "target": target,
        "mode": mode,
        "step": step,
        "transition": 0.0,
    }


def _rotate_once(lab, endpoint: int) -> None:
    wire = Wire(NODE)
    lab.play([(0.0, event) for event in wire.scroll(endpoint, complete=1)])


def _sent(lab) -> list[tuple[str, str, dict[str, Any], str]]:
    return [
        (i["domain"], i["service"], i["data"], i["status"]) for i in lab.spy.intents
    ]


def _number(lab, **kwargs: Any) -> str:
    entity = "input_number.lab_level"
    lab.add_target(NumberTarget(entity, **kwargs))
    return entity


# -- number / input_number: what works today ---------------------------------


@pytest.mark.parametrize(
    ("minimum", "maximum", "step", "value", "binding_step", "up", "expected"),
    [
        # 10 % of a span of 100 is 10.
        (0, 100, 1, 50, 10, True, 60.0),
        # A decimal step: 10 % of 10 is 1.0, already a multiple of 0.5.
        (0, 10, 0.5, 2.0, 10, True, 3.0),
        # A negative minimum with a positive maximum: span 20, 10 % is 2.
        (-10, 10, 1, 0, 10, True, 2.0),
        # Clamped at the top: 98 + 10 = 108, the range ends at 100.
        (0, 100, 1, 98, 10, True, 100.0),
        # Clamped at a negative floor: -9 - 2 = -11, the range starts at -10.
        (-10, 10, 1, -9, 10, False, -10.0),
        # Quantized to the entity's step: 50 + 3 = 53, the nearest multiple of 5.
        (0, 100, 5, 50, 3, True, 55.0),
    ],
)
@covers("mode:number")
def test_number_targets_follow_their_own_range(
    lab, minimum, maximum, step, value, binding_step, up, expected
) -> None:
    entity = _number(lab, minimum=minimum, maximum=maximum, step=step, value=value)
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_binding(entity, "number", binding_step))
    _rotate_once(lab, UP1 if up else DOWN1)

    assert _sent(lab) == [
        ("input_number", "set_value", {"value": expected}, "accepted")
    ]
    assert lab.registry.target(entity).value() == expected


def test_a_number_target_never_receives_a_value_outside_its_range(lab) -> None:
    """Whatever the binding sends, the simulated entity would have accepted it."""
    entity = _number(lab, minimum=0, maximum=100, step=1, value=50)
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_binding(entity, "number", 10))
    _rotate_once(lab, UP1)

    assert [i["status"] for i in lab.spy.intents] == ["accepted"]


# -- climate: what works today -----------------------------------------------


@pytest.mark.parametrize(
    ("minimum", "maximum", "temperature", "step", "up", "expected"),
    [
        # span 28, 10 % is 2.8: 20 + 2.8 = 22.8, rounded to the 0.5 step.
        (7, 35, 20.0, 0.5, True, 23.0),
        # No target_temp_step reported: the binding falls back to 0.5.
        (7, 35, 20.0, None, True, 23.0),
        # 34 + 2.8 = 36.8, the thermostat stops at 35.
        (7, 35, 34.0, 0.5, True, 35.0),
        # A negative range with non-zero bounds: span 15, 10 % is 1.5.
        (-20, -5, -10.0, 0.5, True, -8.5),
    ],
)
@covers("mode:temperature")
def test_climate_targets_follow_their_own_range(
    lab, minimum, maximum, temperature, step, up, expected
) -> None:
    lab.add_target(
        ClimateTarget(
            "climate.lab",
            min_temp=minimum,
            max_temp=maximum,
            temperature=temperature,
            target_temp_step=step,
        )
    )
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_binding("climate.lab", "temperature", 10))
    _rotate_once(lab, UP1 if up else DOWN1)

    assert _sent(lab) == [
        ("climate", "set_temperature", {"temperature": expected}, "accepted")
    ]


# -- PR #71: a bound of zero is a real bound ---------------------------------


def test_number_with_a_maximum_of_zero_stops_at_zero(lab) -> None:
    """The reproduction from PR #71.

    input_number, minimum -10, maximum 0, step 1, now -1; Value binding, 10 %
    per step; one notch up. The span is 10, so one notch is 1: -1 + 1 = 0.

    The maximum 0 is a real limit. Before the fix (PR #71) it was read as missing
    and replaced by 100: the span became 110, one notch 11, and the binding asked
    for 10, which the entity refuses.
    """
    entity = _number(lab, minimum=-10, maximum=0, step=1, value=-1)
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_binding(entity, "number", 10))
    _rotate_once(lab, UP1)

    assert _sent(lab) == [("input_number", "set_value", {"value": 0.0}, "accepted")]


def test_climate_with_a_minimum_of_zero_does_not_go_up_when_turned_down(lab) -> None:
    """min_temp 0, max_temp 30, now 1.0, 10 % per step (span 30, a step is 3).

    One notch down: 1.0 - 3 = -2, the floor is 0, so the setpoint goes to 0.0.
    The minimum 0 is a real limit. Before the fix it was read as missing and
    replaced by 7, so the same notch down raised the setpoint from 1.0 to 7.0.
    """
    lab.add_target(
        ClimateTarget(
            "climate.lab",
            min_temp=0,
            max_temp=30,
            temperature=1.0,
            target_temp_step=0.5,
        )
    )
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_binding("climate.lab", "temperature", 10))
    _rotate_once(lab, DOWN1)

    assert _sent(lab) == [
        ("climate", "set_temperature", {"temperature": 0.0}, "accepted")
    ]


def test_climate_with_a_maximum_of_zero_stops_at_zero(lab) -> None:
    """min_temp -20, max_temp 0, now -5, 10 % per step (span 20, a step is 2).

    One notch up: -5 + 2 = -3, inside the range. Before the fix the maximum 0 was
    read as missing and replaced by 35: the span became 55 and the setpoint was
    asked to move to 0.5, above the thermostat's maximum.
    """
    lab.add_target(
        ClimateTarget(
            "climate.lab",
            min_temp=-20,
            max_temp=0,
            temperature=-5.0,
            target_temp_step=0.5,
        )
    )
    lab.load(e2490_node(NODE))
    lab.setup_bindings(_binding("climate.lab", "temperature", 10))
    _rotate_once(lab, UP1)

    assert _sent(lab) == [
        ("climate", "set_temperature", {"temperature": -3.0}, "accepted")
    ]
