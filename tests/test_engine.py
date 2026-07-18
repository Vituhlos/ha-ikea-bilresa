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


def test_press_variants_ignored_for_rotate(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    assert engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press")) is None
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


def test_released_current_position_clears_scroll_baseline(
    wheel: BilresaWheel,
) -> None:
    engine = GestureEngine()
    engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 8))
    engine.observe_position(NODE, 1, 0)

    action = engine.process(
        wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_ongoing", 3)
    )

    assert action is not None
    assert action.notches == 3
