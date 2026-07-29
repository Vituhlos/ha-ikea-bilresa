"""The capture/replay harness, and a capture of the defect it exists to find.

A capture recorded on the physical wheel becomes a permanent test here. The
value is that a defect stops depending on somebody being in the room with a
BILRESA in hand, and that two candidate fixes can be compared on identical
input rather than on two different turns of a wheel.
"""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.ikea_bilresa.trace import CAPTURE_VERSION

from .replay import replay, simulate_target

CAPTURES = Path(__file__).parent / "fixtures" / "captures"

NOTCH_UNITS = 3 / 100 * 255  # a 3 % step of the 0-255 brightness range


def _capture(name: str) -> dict:
    return json.loads((CAPTURES / name).read_text(encoding="utf-8"))


def _rows(*entries) -> list[dict]:
    return [{"seq": index + 1, **entry} for index, entry in enumerate(entries)]


def test_a_replay_reproduces_exact_single_shot_arithmetic(monkeypatch) -> None:
    """The baseline: undisturbed steps must land on the one-shot result."""
    capture = {
        "capture_version": CAPTURE_VERSION,
        "bindings": {"14:channel:1": {"step": 3, "transition": 0.0}},
        "rows": _rows(
            {
                "t": 0.0,
                "kind": "raw",
                "binding": "14:channel:1",
                "role": "scroll_down",
                "event_type": "initial_press",
                "endpoint": 2,
            },
            {
                "t": 0.0,
                "kind": "rotate",
                "binding": "14:channel:1",
                "notches": 1,
                "direction": "down",
            },
            {
                "t": 0.5,
                "kind": "rotate",
                "binding": "14:channel:1",
                "notches": 4,
                "direction": "down",
            },
            {
                "t": 1.0,
                "kind": "rotate",
                "binding": "14:channel:1",
                "notches": 5,
                "direction": "down",
            },
        ),
    }

    result = replay(capture, monkeypatch, initial_value=255)

    assert result.notches == 10
    assert result.sent[-1] == round(255 - 10 * NOTCH_UNITS)
    assert not result.forgets


def test_a_lagging_report_mid_gesture_is_reproduced_offline(monkeypatch) -> None:
    """A stale report inside the gesture must not rebase the next step.

    This is the shape of the rc.5 anomaly: the target acknowledges an older
    absolute value while later notches are still arriving.
    """
    capture = {
        "capture_version": CAPTURE_VERSION,
        "bindings": {"14:channel:1": {"step": 3, "transition": 0.0}},
        "rows": _rows(
            {
                "t": 0.0,
                "kind": "raw",
                "binding": "14:channel:1",
                "role": "scroll_down",
                "event_type": "initial_press",
                "endpoint": 2,
            },
            {
                "t": 0.0,
                "kind": "rotate",
                "binding": "14:channel:1",
                "notches": 1,
                "direction": "down",
            },
            {
                "t": 0.2,
                "kind": "rotate",
                "binding": "14:channel:1",
                "notches": 2,
                "direction": "down",
            },
            # the target reports the value from before the last batch
            {
                "t": 0.45,
                "kind": "state",
                "binding": "14:channel:1",
                "state": "on",
                "value": 247,
            },
            {
                "t": 0.6,
                "kind": "rotate",
                "binding": "14:channel:1",
                "notches": 1,
                "direction": "down",
            },
        ),
    }

    result = replay(capture, monkeypatch, initial_value=255)

    assert result.sent[-1] == round(255 - 4 * NOTCH_UNITS)


def test_replay_is_deterministic(monkeypatch) -> None:
    """Same capture, same result — otherwise it cannot settle an argument."""
    capture = {
        "capture_version": CAPTURE_VERSION,
        "bindings": {"14:channel:1": {"step": 3, "transition": 0.0}},
        "rows": _rows(
            {
                "t": 0.0,
                "kind": "raw",
                "binding": "14:channel:1",
                "role": "scroll_down",
                "event_type": "initial_press",
                "endpoint": 2,
            },
            {
                "t": 0.1,
                "kind": "rotate",
                "binding": "14:channel:1",
                "notches": 3,
                "direction": "down",
            },
            {
                "t": 0.4,
                "kind": "state",
                "binding": "14:channel:1",
                "state": "on",
                "value": 232,
            },
            {
                "t": 0.7,
                "kind": "rotate",
                "binding": "14:channel:1",
                "notches": 2,
                "direction": "down",
            },
        ),
    }

    first = replay(capture, monkeypatch, initial_value=255)
    second = replay(capture, monkeypatch, initial_value=255)

    assert first.sent == second.sent
    assert [row["from_source"] for row in first.rotations] == [
        row["from_source"] for row in second.rotations
    ]


def test_a_capture_reports_which_steps_restarted_from_the_entity(
    monkeypatch,
) -> None:
    """`from_source` is what a capture is read for: it names the cause."""
    capture = {
        "capture_version": CAPTURE_VERSION,
        "bindings": {"14:channel:1": {"step": 3, "transition": 0.0}},
        "rows": _rows(
            {
                "t": 0.0,
                "kind": "raw",
                "binding": "14:channel:1",
                "role": "scroll_down",
                "event_type": "initial_press",
                "endpoint": 2,
            },
            {
                "t": 0.0,
                "kind": "rotate",
                "binding": "14:channel:1",
                "notches": 1,
                "direction": "down",
            },
            # a value nobody sent: a genuine third-party change
            {
                "t": 0.3,
                "kind": "state",
                "binding": "14:channel:1",
                "state": "on",
                "value": 100,
            },
            {
                "t": 0.5,
                "kind": "rotate",
                "binding": "14:channel:1",
                "notches": 1,
                "direction": "down",
            },
        ),
    }

    result = replay(capture, monkeypatch, initial_value=255)

    assert [row["from_source"] for row in result.rotations] == ["state", "state"]
    assert [row["reason"] for row in result.forgets] == [
        "unrecognized_value_during_scroll"
    ]


def test_recorded_hardware_captures_still_hold(monkeypatch) -> None:
    """Every capture committed under fixtures/captures replays to its target.

    Each file carries an `expect` block, so adding a capture from the wheel
    adds a regression test without writing any code.
    """
    if not CAPTURES.is_dir():
        return
    for path in sorted(CAPTURES.glob("*.json")):
        capture = _capture(path.name)
        expect = capture.get("expect")
        if not expect:
            continue
        result = replay(
            capture, monkeypatch, initial_value=expect.get("initial_value", 255)
        )
        assert result.sent[-1] == expect["final_sent"], path.name
        if "notches" in expect:
            assert result.notches == expect["notches"], path.name
        if "max_forgets" in expect:
            # A capture can end on the right value by saturating, so the number
            # of discarded targets is asserted separately: that is what the
            # defect actually looked like.
            assert len(result.forgets) <= expect["max_forgets"], (
                f"{path.name}: {[row['reported'] for row in result.forgets]}"
            )


def test_the_same_gesture_survives_every_kind_of_target(monkeypatch) -> None:
    """The integration claims to drive more than one Shelly dimmer.

    A target that fades reports values that were never commanded, and a cover
    motor is still travelling long after the gesture ended. Matching reports
    against commanded values cannot recognize either, so the real hardware
    capture is replayed against each profile: none of them may lose steps.
    """
    base = _capture("hardware-2026-07-29-round1-decode-only.json")
    # The recorded decode log carries one InitialPress; the device emits one
    # per notch, which is what keeps the authority window refreshed.
    rows = list(base["rows"])
    rows += [
        {
            **row,
            "kind": "raw",
            "role": "scroll_down",
            "event_type": "initial_press",
            "endpoint": 2,
            "t": max(0.0, round(row["t"] - 0.001, 3)),
        }
        for row in rows
        if row["kind"] == "rotate"
    ]
    base = {**base, "rows": sorted(rows, key=lambda r: r["t"])}

    profiles = {
        "instant": {"profile": "instant", "delay": 0.25},
        "instant-quantized": {"profile": "instant", "delay": 0.25, "quantum": 2.55},
        "fade": {"profile": "fade", "delay": 0.25, "travel": 120.0},
        "slow-fade": {"profile": "fade", "delay": 0.25, "travel": 40.0},
        "cover-speed": {"profile": "slow", "delay": 0.5, "travel": 8.0},
    }

    for name, options in profiles.items():
        capture = simulate_target(base, initial_value=255, **options)
        result = replay(capture, monkeypatch, initial_value=255)
        rebases = [row for row in result.rotations if row["from_source"] == "state"][
            1:
        ]  # the first step legitimately reads the entity
        assert not rebases, f"{name} rebased mid-gesture: {rebases}"
        assert result.sent[-1] == 3, f"{name} ended at {result.sent[-1]}"


def test_a_genuine_outside_change_is_still_honoured(monkeypatch) -> None:
    """The trajectory test must not become "ignore everything"."""
    capture = {
        "capture_version": CAPTURE_VERSION,
        "bindings": {"14:channel:1": {"step": 3, "transition": 0.0}},
        "rows": _rows(
            {
                "t": 0.0,
                "kind": "raw",
                "binding": "14:channel:1",
                "role": "scroll_down",
                "event_type": "initial_press",
                "endpoint": 2,
            },
            {
                "t": 0.0,
                "kind": "rotate",
                "binding": "14:channel:1",
                "notches": 2,
                "direction": "down",
            },
            # far below anything on the path from 255 towards 239
            {
                "t": 0.3,
                "kind": "state",
                "binding": "14:channel:1",
                "state": "on",
                "value": 40,
            },
            {
                "t": 0.5,
                "kind": "rotate",
                "binding": "14:channel:1",
                "notches": 1,
                "direction": "down",
            },
        ),
    }

    result = replay(capture, monkeypatch, initial_value=255)

    assert [row["reason"] for row in result.forgets] == [
        "unrecognized_value_during_scroll"
    ]
    assert result.rotations[-1]["from_source"] == "state"
