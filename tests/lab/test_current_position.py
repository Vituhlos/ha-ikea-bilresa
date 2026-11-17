"""Switch.CurrentPosition through the real ``attribute_updated`` path.

The attribute ids below are written as literals from the authoritative source,
not from ``const.py`` (which may be the thing that is wrong). Matter Switch
cluster 0x003B (59):

* ``0x0000`` NumberOfPositions (default 2),
* ``0x0001`` CurrentPosition (0 .. NumberOfPositions - 1),
* ``0x0002`` MultiPressMax.

Sources, both read on 2026-11-17: project-chip/connectedhomeip
``data_model/1.3`` and ``1.4`` ``clusters/Switch.xml``, and the matter.js model
``packages/model/src/standard/elements/switch.element.ts``.

What a position means to the engine: ``GestureEngine.observe_position`` is told
the button went back to 0, which ends the host-observed press time. So a
CurrentPosition of 0 reported during a hold makes the release carry no duration.

The mismatch with the specification is shown here. That it changes anything on
real hardware is **not** proven; the expected failures say so.
"""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.ikea_bilresa import const
from custom_components.ikea_bilresa.matter_core import CoreMatterEventSource

from .fake_matter import E2490_ENDPOINTS, Wire, e2490_node
from .known_issues import SUSPECTED_CURRENT_POSITION

NODE = 14
BTN1 = E2490_ENDPOINTS[1]["button"]

SPEC_NUMBER_OF_POSITIONS = 0x0000
SPEC_CURRENT_POSITION = 0x0001
SPEC_MULTI_PRESS_MAX = 0x0002


def _release_duration(lab, attribute: int | None, value: Any = 0) -> int | None:
    """Hold for 1.4 s; optionally report an attribute at 0.9 s; read the release."""
    wire = Wire(NODE)
    lab.load(e2490_node(NODE))
    lab.play(
        [
            (0.0, wire.event(BTN1, "initial_press")),
            (0.72, wire.event(BTN1, "long_press")),
        ]
    )
    if attribute is not None:
        lab.at(0.9)
        lab.attribute_updated(NODE, f"{BTN1}/59/{attribute}", value)
    lab.play([(1.4, wire.event(BTN1, "long_release"))])
    released = [a for a in lab.actions() if a["type"] == "release"]
    assert len(released) == 1
    return released[0]["observed_duration_ms"]


# -- the specification, as an executable expectation -------------------------


def test_without_a_position_report_the_hold_is_timed_to_the_release(lab) -> None:
    """The control: no attribute report, the press lasted 1.4 s."""
    assert _release_duration(lab, None) == 1400


@SUSPECTED_CURRENT_POSITION
def test_a_current_position_of_zero_ends_the_observed_press(lab) -> None:
    """CurrentPosition (0x0001) back at 0 during a hold: the release has no time."""
    assert _release_duration(lab, SPEC_CURRENT_POSITION, 0) is None


@SUSPECTED_CURRENT_POSITION
def test_number_of_positions_is_never_a_button_position(lab) -> None:
    """Attribute 0x0000 is NumberOfPositions: reporting it must not touch the press."""
    assert _release_duration(lab, SPEC_NUMBER_OF_POSITIONS, 0) == 1400


@SUSPECTED_CURRENT_POSITION
def test_number_of_positions_is_classified_as_irrelevant_not_invalid(lab) -> None:
    """A valid NumberOfPositions (2) is not a position and is not malformed."""
    lab.load(e2490_node(NODE))
    lab.attribute_updated(NODE, f"{BTN1}/59/{SPEC_NUMBER_OF_POSITIONS}", 2)

    assert lab.record()["ignored"] == {"irrelevant_attribute_update": 1}


@SUSPECTED_CURRENT_POSITION
@pytest.mark.parametrize("value", [2, 5, -1, True, "0", None])
def test_an_invalid_current_position_is_rejected_as_invalid(lab, value) -> None:
    """CurrentPosition must be 0 or 1 here; anything else is refused and counted."""
    lab.load(e2490_node(NODE))
    lab.attribute_updated(NODE, f"{BTN1}/59/{SPEC_CURRENT_POSITION}", value)

    assert lab.record()["ignored"] == {"invalid_switch_position": 1}
    assert lab.actions() == []


@SUSPECTED_CURRENT_POSITION
def test_the_core_source_follows_the_specification_path() -> None:
    """The core Matter source watches endpoint/59/1, not endpoint/59/0."""
    follows = CoreMatterEventSource._is_switch_position_path
    assert follows(f"{BTN1}/59/{SPEC_CURRENT_POSITION}") is True
    assert follows(f"{BTN1}/59/{SPEC_NUMBER_OF_POSITIONS}") is False


# -- what this branch does today, pinned -------------------------------------
#
# These pass now and fail once the constant follows the specification. They show
# that the expected failures above fail for the declared reason. Delete them with
# the SUSPECTED_CURRENT_POSITION markers.


def test_observed_today_attribute_zero_is_taken_as_the_position(lab) -> None:
    assert const.ATTR_SWITCH_CURRENT_POSITION == 0
    assert _release_duration(lab, SPEC_NUMBER_OF_POSITIONS, 0) is None
    follows = CoreMatterEventSource._is_switch_position_path
    assert follows(f"{BTN1}/59/0") is True
    assert follows(f"{BTN1}/59/1") is False


def test_observed_today_the_specification_attribute_is_ignored(lab) -> None:
    assert _release_duration(lab, SPEC_CURRENT_POSITION, 0) == 1400
    assert lab.record()["ignored"]["irrelevant_attribute_update"] == 1


# -- controlled rejection that does not depend on the constant ---------------


@pytest.mark.parametrize(
    ("payload", "counter"),
    [
        ("not a list", "malformed_attribute_update"),
        ([NODE, f"{BTN1}/59"], "malformed_attribute_update"),
        (["14", f"{BTN1}/59/1", 0], "malformed_attribute_update"),
        ([777, f"{BTN1}/59/1", 0], "unknown_attribute_node"),
        ([NODE, f"{BTN1}/59", 0], "malformed_attribute_path"),
        ([NODE, f"{BTN1}/59/x", 0], "malformed_attribute_path"),
        ([NODE, f"{BTN1}/6/0", 0], "irrelevant_attribute_update"),
        ([NODE, f"99/59/{SPEC_MULTI_PRESS_MAX}", 18], "irrelevant_attribute_update"),
        ([NODE, f"{BTN1}/59/{SPEC_MULTI_PRESS_MAX}", 3], "irrelevant_attribute_update"),
    ],
)
def test_a_bad_attribute_update_is_counted_once_and_changes_nothing(
    lab, payload, counter: str
) -> None:
    lab.load(e2490_node(NODE))
    lab.coordinator._on_event("attribute_updated", payload)
    lab.settle()

    assert lab.record()["ignored"] == {counter: 1}
    assert lab.actions() == []
    assert lab.safety.kinds() == []
