"""Tests for the rotation trace: the buffer, and what a binding records in it."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.ikea_bilresa.const import (
    ACTION_ROTATE,
    CONF_ACCELERATION,
    CONF_STEP,
    CONF_TRANSITION,
    DIRECTION_DOWN,
    ROLE_SCROLL_DOWN,
)
from custom_components.ikea_bilresa.engine import WheelAction
from custom_components.ikea_bilresa.trace import RotationTrace

from .test_binding import _binding


def test_recording_is_off_until_it_is_armed() -> None:
    """A diagnostic that runs unasked is a cost every user pays for nothing."""
    trace = RotationTrace()

    trace.record("rotate", notches=1)

    assert trace.dump() == []
    assert trace.enabled is False


def test_arming_starts_from_a_clean_buffer() -> None:
    """A capture must begin at a known point, not blend into older rows."""
    trace = RotationTrace()
    trace.set_enabled(True)
    trace.record("rotate", notches=1)
    trace.set_enabled(False)

    trace.set_enabled(True)

    assert trace.dump() == []


def test_rows_are_numbered_and_bounded() -> None:
    trace = RotationTrace(limit=3)
    trace.set_enabled(True)

    for index in range(5):
        trace.record("rotate", notches=index)

    rows = trace.dump()
    assert [row["seq"] for row in rows] == [3, 4, 5]
    assert [row["notches"] for row in rows] == [2, 3, 4]


def _traced(monkeypatch, **overrides):
    trace = RotationTrace()
    trace.set_enabled(True)
    binding, _interval, _watchdog = _binding(
        monkeypatch,
        **{CONF_TRANSITION: 0.0, CONF_STEP: 3, CONF_ACCELERATION: 0, **overrides},
    )
    binding._trace = trace
    del binding._rotate_by  # the shared helper mocks it; tracing wraps the real one
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )
    return binding, trace


def test_a_step_records_where_its_starting_value_came_from(monkeypatch) -> None:
    """`from_source` is the field that decides whether a scroll lost steps."""
    binding, trace = _traced(monkeypatch)
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )

    binding._rotate_by(1, False)
    now[0] = 0.2
    binding._rotate_by(2, False)

    rows = [row for row in trace.dump() if row["kind"] == "rotate"]
    assert [row["from_source"] for row in rows] == ["state", "tracked"]
    assert rows[0]["from_value"] == 255
    assert rows[0]["notches"] == 1
    assert rows[1]["from_value"] == rows[0]["target"]
    assert all(row["dispatched"] for row in rows)


def test_discarding_the_target_records_why_and_what_caused_it(monkeypatch) -> None:
    """Steps go missing here, so the reason and the trigger must both be kept."""
    binding, trace = _traced(monkeypatch)
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_by(1, False)

    now[0] = 0.3
    external = SimpleNamespace(state="on", attributes={"brightness": 12})
    binding._handle_target_state_change(SimpleNamespace(data={"new_state": external}))

    forget = [row for row in trace.dump() if row["kind"] == "forget"]
    assert len(forget) == 1
    assert forget[0]["reason"] == "unrecognized_value_during_scroll"
    assert forget[0]["reported"] == 12
    assert forget[0]["had_tracked"] == 247.35
    assert forget[0]["recent_commands"] == [247.35]


def test_a_recognized_echo_is_recorded_as_kept(monkeypatch) -> None:
    """Seeing which reports were accepted is as diagnostic as seeing rejects."""
    binding, trace = _traced(monkeypatch)
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_by(1, False)

    now[0] = 0.3
    echo = SimpleNamespace(state="on", attributes={"brightness": 247})
    binding._handle_target_state_change(SimpleNamespace(data={"new_state": echo}))

    kept = [row for row in trace.dump() if row["kind"] == "echo_ignored"]
    assert len(kept) == 1
    assert kept[0]["reported"] == 247
    assert binding._tracked == 247.35


def test_an_arriving_action_is_recorded_before_any_filter(monkeypatch) -> None:
    """A notch dropped on the way in must still appear in the capture.

    Recording only applied steps hides exactly the losses worth finding: the
    capture would show a shorter gesture rather than a dropped action.
    """
    binding, trace = _traced(monkeypatch)
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: 0.0
    )
    # Arm the post-button suppression window the same way a real press does.
    binding._suppress_scroll_through = binding._scroll_gesture
    binding._suppress_scroll_until = 5.0

    binding._rotate(
        WheelAction(
            node_id=101,
            wheel_name="",
            channel=1,
            endpoint_id=2,
            type=ACTION_ROTATE,
            direction=DIRECTION_DOWN,
            notches=4,
        )
    )

    actions = [row for row in trace.dump() if row["kind"] == "action"]
    assert [(row["notches"], row["suppressed"]) for row in actions] == [(4, True)]
    assert not [row for row in trace.dump() if row["kind"] == "rotate"]


def test_a_binding_without_tracing_records_nothing(monkeypatch) -> None:
    """The default binding must not pay for a diagnostic nobody switched on."""
    binding, _interval, _watchdog = _binding(monkeypatch, **{CONF_STEP: 3})
    del binding._rotate_by
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )

    binding._rotate_by(3, False)

    assert binding._trace.dump() == []
