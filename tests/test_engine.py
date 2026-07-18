"""Unit tests for the gesture engine (pure logic, no Home Assistant runtime)."""

from __future__ import annotations

import pytest

from custom_components.ikea_bilresa.const import (
    ACTION_HOLD,
    ACTION_PRESS,
    ACTION_RELEASE,
    ACTION_ROTATE,
    DIRECTION_DOWN,
    DIRECTION_UP,
    ROLE_BUTTON,
    ROLE_SCROLL_DOWN,
    ROLE_SCROLL_UP,
)
from custom_components.ikea_bilresa.engine import GestureEngine
from custom_components.ikea_bilresa.model import BilresaWheel, SwitchEndpoint

NODE = 12


@pytest.fixture
def wheel() -> BilresaWheel:
    return BilresaWheel(
        node_id=NODE,
        name="Test wheel",
        product_name="BILRESA scroll wheel",
        serial="SER123",
        endpoints={
            1: SwitchEndpoint(1, 1, ROLE_SCROLL_UP),
            2: SwitchEndpoint(2, 1, ROLE_SCROLL_DOWN),
            3: SwitchEndpoint(3, 1, ROLE_BUTTON),
        },
    )


def _decoded(endpoint_id: int, role: str, event_type: str, count=None) -> dict:
    return {
        "node_id": NODE,
        "wheel_name": "Test wheel",
        "endpoint_id": endpoint_id,
        "channel": 1,
        "role": role,
        "event_type": event_type,
        "count": count,
        "raw": {},
    }


def test_single_notch(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    action = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 1)
    )
    assert action is not None
    assert action.type == ACTION_ROTATE
    assert action.direction == DIRECTION_UP
    assert action.notches == 1


def test_cumulative_ongoing_yields_deltas(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    a1 = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 6))
    a2 = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 12))
    a3 = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 18))
    assert [a1.notches, a2.notches, a3.notches] == [6, 6, 6]


def test_new_gesture_resets_after_complete(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 4))
    action = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 5)
    )
    assert action.notches == 5


def test_ongoing_counter_wrap_resets(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 8))
    # A lower count than last means a new gesture began.
    action = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 3)
    )
    assert action.notches == 3


def test_scroll_down_direction(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    action = engine.process(
        wheel, _decoded(2, ROLE_SCROLL_DOWN, "multi_press_complete", 2)
    )
    assert action.direction == DIRECTION_DOWN
    assert action.notches == 2


def test_scroll_initial_press_dispatches_first_notch_immediately(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    action = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))

    assert action is not None
    assert action.type == ACTION_ROTATE
    assert action.direction == DIRECTION_UP
    assert action.notches == 1


def test_scroll_initial_notch_is_not_counted_again_on_complete(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    first = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    complete = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 1)
    )

    assert first is not None
    assert first.notches == 1
    assert complete is None


def test_scroll_initial_notch_is_subtracted_from_first_cumulative_batch(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    first = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    ongoing = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 6)
    )
    complete = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 6)
    )

    assert first is not None
    assert ongoing is not None
    assert [first.notches, ongoing.notches] == [1, 5]
    assert complete is None


def test_eager_first_notch_preserves_exact_eighteen_count_total(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    actions = [
        engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press")),
        engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 6)),
        engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 12)),
        engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 18)),
        engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 18)),
    ]

    assert [action.notches for action in actions if action is not None] == [1, 5, 6, 6]
    assert sum(action.notches for action in actions if action is not None) == 18


def test_sanitized_bilresa_fast_trace_preserves_both_cumulative_sequences(
    wheel: BilresaWheel,
) -> None:
    """Replay the count jumps observed on Matter Server 9.1.0."""
    engine = GestureEngine()
    events = [
        ("initial_press", None),
        ("initial_press", None),
        ("multi_press_ongoing", 5),
        ("initial_press", None),
        ("multi_press_ongoing", 10),
        ("initial_press", None),
        ("multi_press_ongoing", 13),
        ("initial_press", None),
        ("multi_press_ongoing", 16),
        ("initial_press", None),
        ("multi_press_ongoing", 18),
        ("multi_press_complete", 18),
        ("initial_press", None),
        ("initial_press", None),
        ("multi_press_ongoing", 3),
        ("initial_press", None),
        ("multi_press_ongoing", 7),
        ("initial_press", None),
        ("multi_press_ongoing", 11),
        ("initial_press", None),
        ("multi_press_ongoing", 14),
        ("multi_press_complete", 14),
    ]
    actions = [
        engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, event_type, count))
        for event_type, count in events
    ]
    first_sequence = [action.notches for action in actions[:12] if action is not None]
    second_sequence = [action.notches for action in actions[12:] if action is not None]

    assert first_sequence == [1, 1, 3, 1, 4, 1, 2, 1, 2, 1, 1]
    assert sum(first_sequence) == 18
    assert second_sequence == [1, 1, 1, 1, 3, 1, 3, 1, 2]
    assert sum(second_sequence) == 14


def test_every_spec_ordered_sequence_from_one_to_eighteen_is_exact(
    wheel: BilresaWheel,
) -> None:
    for final_count in range(1, 19):
        engine = GestureEngine()
        actions = [engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))]
        for count in range(2, final_count + 1):
            actions.append(
                engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
            )
            actions.append(
                engine.process(
                    wheel,
                    _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", count),
                )
            )
        actions.append(
            engine.process(
                wheel,
                _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", final_count),
            )
        )

        assert sum(action.notches for action in actions if action is not None) == (
            final_count
        )


def test_duplicate_cumulative_count_does_not_repeat_a_batch(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    first = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 6))
    duplicate = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 6)
    )

    assert first is not None
    assert first.notches == 6
    assert duplicate is None


def test_stale_equal_count_keeps_new_eager_credit_for_next_increment(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 6))
    eager = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    stale = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 6))
    next_count = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 7)
    )

    assert eager is not None
    assert eager.notches == 1
    assert stale is None
    assert next_count is None


@pytest.mark.parametrize("invalid_count", [None, True, -1, "2", 19])
def test_invalid_scroll_completion_clears_eager_accounting(
    wheel: BilresaWheel,
    invalid_count,
) -> None:
    wheel.endpoints[1].multi_press_max = 18
    engine = GestureEngine()
    eager = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    invalid = engine.process(
        wheel,
        _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", invalid_count),
    )
    next_complete = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 1)
    )

    assert eager is not None
    assert eager.notches == 1
    assert invalid is None
    assert next_complete is not None
    assert next_complete.notches == 1


def test_scroll_zero_completion_ends_sequence_without_duplicate(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    eager = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    overflow = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 0)
    )
    next_eager = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    next_complete = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 1)
    )

    assert eager is not None
    assert eager.notches == 1
    assert overflow is None
    assert next_eager is not None
    assert next_eager.notches == 1
    assert next_complete is None


def test_multiple_initial_credits_preserve_exact_cumulative_total(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    first = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    second = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    ongoing = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 2)
    )

    assert first is not None
    assert second is not None
    assert [first.notches, second.notches] == [1, 1]
    assert ongoing is None


def test_eager_credits_are_isolated_by_direction_endpoint(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    up = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    down = engine.process(wheel, _decoded(2, ROLE_SCROLL_DOWN, "initial_press"))
    up_complete = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 1)
    )
    down_complete = engine.process(
        wheel, _decoded(2, ROLE_SCROLL_DOWN, "multi_press_complete", 1)
    )

    assert up is not None
    assert down is not None
    assert up.direction == DIRECTION_UP
    assert down.direction == DIRECTION_DOWN
    assert up_complete is None
    assert down_complete is None


def test_scroll_release_events_add_no_delta(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    assert engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "short_release")) is None


@pytest.mark.parametrize(("count", "presses"), [(1, 1), (2, 2), (3, 3)])
def test_button_click_counts(wheel: BilresaWheel, count: int, presses: int) -> None:
    engine = GestureEngine()
    action = engine.process(
        wheel, _decoded(3, ROLE_BUTTON, "multi_press_complete", count)
    )
    assert action.type == ACTION_PRESS
    assert action.presses == presses


def test_button_hold_and_release(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    hold = engine.process(wheel, _decoded(3, ROLE_BUTTON, "long_press"))
    release = engine.process(wheel, _decoded(3, ROLE_BUTTON, "long_release"))
    assert hold.type == ACTION_HOLD
    assert release.type == ACTION_RELEASE


def test_hold_duration_uses_one_uninterrupted_monotonic_press(
    wheel: BilresaWheel,
) -> None:
    times = iter((10.0, 10.6, 12.25))
    engine = GestureEngine(clock=lambda: next(times))

    engine.process(wheel, _decoded(3, ROLE_BUTTON, "initial_press"))
    hold = engine.process(wheel, _decoded(3, ROLE_BUTTON, "long_press"))
    release = engine.process(wheel, _decoded(3, ROLE_BUTTON, "long_release"))

    assert hold is not None
    assert hold.observed_duration_ms == 600
    assert release is not None
    assert release.observed_duration_ms == 2250


def test_current_position_release_invalidates_observed_duration(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine(clock=lambda: 10.0)
    engine.process(wheel, _decoded(3, ROLE_BUTTON, "initial_press"))
    engine.observe_position(NODE, 3, 0)

    release = engine.process(wheel, _decoded(3, ROLE_BUTTON, "long_release"))

    assert release is not None
    assert release.observed_duration_ms is None


def test_zero_press_completion_is_not_reinterpreted_as_single(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    assert (
        engine.process(wheel, _decoded(3, ROLE_BUTTON, "multi_press_complete", 0))
        is None
    )


def test_button_count_above_reported_multi_press_max_is_ignored(
    wheel: BilresaWheel,
) -> None:
    wheel.endpoints[3].multi_press_max = 2
    engine = GestureEngine()
    assert (
        engine.process(wheel, _decoded(3, ROLE_BUTTON, "multi_press_complete", 3))
        is None
    )


def test_released_current_position_preserves_active_scroll_sequence(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 8))
    engine.observe_position(NODE, 1, 0)

    action = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 10)
    )

    assert action is not None
    assert action.notches == 2


def test_position_release_does_not_duplicate_eager_single_notch(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    first = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    engine.observe_position(NODE, 1, 0)
    complete = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 1)
    )

    assert first is not None
    assert first.notches == 1
    assert complete is None


def test_lower_counter_after_incomplete_gesture_uses_eager_credit_once(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 8))
    first = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    complete = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 1)
    )

    assert first is not None
    assert first.notches == 1
    assert complete is None


def test_reset_drops_eager_scroll_credit(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    engine.reset()

    complete = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 1)
    )

    assert complete is not None
    assert complete.notches == 1
