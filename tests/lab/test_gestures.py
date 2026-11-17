"""A: the decoder and the gesture engine, fed synthetic Matter events.

Every expected value below is worked out by hand from the Matter Switch
contract and docs/DEVICE_REFERENCE.md, not by calling the code under test.
Inputs enter as ``node_event`` messages, so ``parse_node``, ``decode_event`` and
``GestureEngine`` all run for real.
"""

from __future__ import annotations

import pytest

from .fake_matter import E2490_ENDPOINTS, Wire, e2489_node, e2490_node

NODE = 14
UP1 = E2490_ENDPOINTS[1]["up"]
DOWN1 = E2490_ENDPOINTS[1]["down"]
BTN1 = E2490_ENDPOINTS[1]["button"]
UP2 = E2490_ENDPOINTS[2]["up"]
BTN2 = E2490_ENDPOINTS[2]["button"]


def _at(time_s: float, events: list[dict]) -> list[tuple[float, dict]]:
    return [(time_s, event) for event in events]


def _types(lab) -> list[str]:
    return [action["type"] for action in lab.actions()]


# -- A01 .. A04: scrolling ------------------------------------------------


def test_a01_one_notch_up_and_down(lab) -> None:
    """A01: one notch is exactly one action, in the right direction."""
    wire = Wire(NODE)
    lab.load(e2490_node(NODE))
    # The documented single-notch stream: InitialPress, ShortRelease and a
    # MultiPressComplete of 1, which the InitialPress has already paid for.
    lab.play(
        _at(0.0, wire.scroll(UP1, complete=1))
        + _at(1.0, wire.scroll(DOWN1, complete=1))
    )

    assert lab.rotations() == [(1, "up", 1), (1, "down", 1)]


def test_a02_cumulative_batches_add_up_without_duplicates(lab) -> None:
    """A02: the documented fast gesture, counts 6, 12, 16, 18, totals 18.

    InitialPress pays for the first notch; each cumulative report then adds
    only the difference to the previous one, less the notch already paid:
    1, 6-1, 12-6, 16-12, 18-16 = 1, 5, 6, 4, 2. Complete(18) adds nothing.
    """
    wire = Wire(NODE)
    lab.load(e2490_node(NODE))
    gesture = wire.scroll(UP1, ongoing=(6, 12, 16, 18), complete=18)
    lab.play(
        [(0.0, gesture[0])]
        + [(0.5 + 0.5 * i, e) for i, e in enumerate(gesture[1:], start=0)]
    )

    assert lab.rotations() == [
        (1, "up", 1),
        (1, "up", 5),
        (1, "up", 6),
        (1, "up", 4),
        (1, "up", 2),
    ]
    assert sum(notches for _, _, notches in lab.rotations()) == 18


def test_a03_a_first_notch_reported_only_in_complete_is_not_lost(lab) -> None:
    """A03: no InitialPress seen, only Complete(1): that notch still counts once."""
    wire = Wire(NODE)
    lab.load(e2490_node(NODE))
    lab.play(_at(0.0, wire.scroll(UP1, complete=1, initial=False)))

    assert lab.rotations() == [(1, "up", 1)]


def test_a04_a_repeated_count_adds_nothing(lab) -> None:
    """A04: the same cumulative count twice is delta 0, then Complete adds none."""
    wire = Wire(NODE)
    lab.load(e2490_node(NODE))
    lab.play(_at(0.0, wire.scroll(UP1, ongoing=(6, 6), complete=6)))

    assert lab.rotations() == [(1, "up", 1), (1, "up", 5)]


def test_a04_a_new_gesture_starts_from_zero(lab) -> None:
    """After Complete the next gesture does not inherit the old count."""
    wire = Wire(NODE)
    lab.load(e2490_node(NODE))
    lab.play(
        _at(0.0, wire.scroll(UP1, ongoing=(6,), complete=6))
        + _at(2.0, wire.scroll(UP1, ongoing=(3,), complete=3))
    )

    assert lab.rotations() == [
        (1, "up", 1),
        (1, "up", 5),
        (1, "up", 1),
        (1, "up", 2),
    ]


# -- channels and wheels --------------------------------------------------


def test_channels_keep_their_own_counts(lab) -> None:
    """Channel 1 and channel 2 scrolled in turn: no count crosses over."""
    wire = Wire(NODE)
    lab.load(e2490_node(NODE))
    lab.play(
        [
            (0.0, wire.event(UP1, "initial_press")),
            (0.1, wire.event(UP2, "initial_press")),
            (0.5, wire.event(UP1, "multi_press_ongoing", count=6)),
            (0.6, wire.event(UP2, "multi_press_ongoing", count=6)),
            (1.0, wire.event(UP1, "multi_press_complete", count=6)),
            (1.1, wire.event(UP2, "multi_press_complete", count=6)),
        ]
    )

    assert lab.rotations() == [
        (1, "up", 1),
        (2, "up", 1),
        (1, "up", 5),
        (2, "up", 5),
    ]


def test_two_wheels_at_once_stay_apart(lab) -> None:
    """Two wheels scrolled together: every action carries its own node id."""
    first, second = Wire(14), Wire(15)
    lab.load(e2490_node(14), e2490_node(15))
    lab.play(
        [
            (0.0, first.event(UP1, "initial_press")),
            (0.1, second.event(UP1, "initial_press")),
            (0.5, first.event(UP1, "multi_press_ongoing", count=4)),
            (0.6, second.event(UP1, "multi_press_ongoing", count=7)),
        ]
    )

    assert [(a["node_id"], a["notches"]) for a in lab.actions()] == [
        (14, 1),
        (15, 1),
        (14, 3),
        (15, 6),
    ]


def test_a_direction_change_is_not_mixed(lab) -> None:
    """Up then down on one channel: eager credit is per endpoint, never shared."""
    wire = Wire(NODE)
    lab.load(e2490_node(NODE))
    lab.play(
        _at(0.0, wire.scroll(UP1, ongoing=(2,), complete=2))
        + _at(1.0, wire.scroll(DOWN1, ongoing=(3,), complete=3))
    )

    assert lab.rotations() == [
        (1, "up", 1),
        (1, "up", 1),
        (1, "down", 1),
        (1, "down", 2),
    ]


# -- A10: presses and holds -----------------------------------------------


@pytest.mark.parametrize("presses", [1, 2, 3])
def test_a10_e2490_button_counts_presses(lab, presses: int) -> None:
    """A10: a wheel button reports single, double and triple presses."""
    wire = Wire(NODE)
    lab.load(e2490_node(NODE))
    lab.play(_at(0.0, wire.click(BTN1, presses)))

    pressed = [a for a in lab.actions() if a["type"] == "press"]
    assert [(a["channel"], a["presses"]) for a in pressed] == [(1, presses)]
    # One short_release per physical tap, ahead of the completed press.
    assert _types(lab).count("short_release") == presses


def test_a10_e2490_hold_and_release_report_host_observed_time(lab) -> None:
    """InitialPress at 0 s, LongPress at 0.72 s, LongRelease at 1.4 s."""
    wire = Wire(NODE)
    lab.load(e2490_node(NODE))
    lab.play(
        [
            (0.0, wire.event(BTN1, "initial_press")),
            (0.72, wire.event(BTN1, "long_press")),
            (1.4, wire.event(BTN1, "long_release")),
        ]
    )

    held = [a for a in lab.actions() if a["type"] in ("hold", "release")]
    assert [(a["type"], a["observed_duration_ms"]) for a in held] == [
        ("hold", 720),
        ("release", 1400),
    ]


@pytest.mark.parametrize("endpoint", [1, 2])
def test_a10_e2489_single_and_double_press(lab, endpoint: int) -> None:
    """A10: the two-button remote reports single and double press on each button."""
    wire = Wire(9001)
    lab.load(e2489_node(9001))
    lab.play(_at(0.0, wire.click(endpoint, 1)) + _at(2.0, wire.click(endpoint, 2)))

    pressed = [a for a in lab.actions() if a["type"] == "press"]
    assert [(a["endpoint_id"], a["channel"], a["presses"]) for a in pressed] == [
        (endpoint, None, 1),
        (endpoint, None, 2),
    ]


def test_a10_e2489_has_no_triple_press(lab) -> None:
    """A count above MultiPressMax (2) never becomes a press."""
    wire = Wire(9001)
    lab.load(e2489_node(9001))
    lab.play(_at(0.0, wire.click(1, 3)))

    assert [a for a in lab.actions() if a["type"] == "press"] == []


def test_a11_e2489_overflow_completes_with_zero_and_clicks_nothing(lab) -> None:
    """Three rapid taps: the recorded stream ends in Complete(0), no press.

    docs/DEVICE_REFERENCE_BUTTON.md, Matter Server 9.1.0: two reported
    press/release phases with MultiPressOngoing(2), then MultiPressComplete(0).
    """
    wire = Wire(9001)
    lab.load(e2489_node(9001))
    lab.play(
        _at(
            0.0,
            [
                wire.event(1, "initial_press"),
                wire.event(1, "short_release"),
                wire.event(1, "initial_press"),
                wire.event(1, "multi_press_ongoing", count=2),
                wire.event(1, "short_release"),
                wire.event(1, "multi_press_complete", count=0),
            ],
        )
    )

    assert _types(lab) == ["short_release", "short_release"]


def test_a10_e2489_hold_and_release(lab) -> None:
    wire = Wire(9001)
    lab.load(e2489_node(9001))
    lab.play(
        [
            (0.0, wire.event(2, "initial_press")),
            (0.72, wire.event(2, "long_press")),
            (1.63, wire.event(2, "long_release")),
        ]
    )

    held = [a for a in lab.actions() if a["type"] in ("hold", "release")]
    assert [(a["type"], a["observed_duration_ms"]) for a in held] == [
        ("hold", 720),
        ("release", 1630),
    ]


# -- malformed input ------------------------------------------------------


def test_malformed_events_end_in_a_controlled_rejection(lab) -> None:
    """Bad counts, bad clusters and unknown nodes produce no action and are counted."""
    wire = Wire(NODE)
    lab.load(e2490_node(NODE))
    bad = [
        wire.event(UP1, "multi_press_ongoing"),  # count missing
        wire.event(UP1, "multi_press_ongoing", count=-1),
        wire.event(UP1, "multi_press_ongoing", count=19),  # above MultiPressMax 18
        wire.event(UP1, "multi_press_ongoing", count=0),
        wire.event(UP1, "multi_press_ongoing", count=True),  # a bool is not a count
        wire.raw(UP1, 5, {"currentNumberOfPressesCounted": 3}, cluster_id=6),
        wire.raw(99, 5, {"currentNumberOfPressesCounted": 3}),  # unknown endpoint
        wire.raw(UP1, None, {"currentNumberOfPressesCounted": 3}),  # no event id
        wire.raw(UP1, 5, {"currentNumberOfPressesCounted": 3}, node_id=777),
    ]
    lab.play([(0.0, event) for event in bad])

    assert lab.actions() == []
    ignored = lab.record()["ignored"]
    assert sum(ignored.values()) == len(bad)
    assert lab.safety.kinds() == []

    # The same endpoint still works afterwards: nothing was left half-counted.
    lab.play(_at(1.0, wire.scroll(UP1, complete=1)))
    assert lab.rotations() == [(1, "up", 1)]
