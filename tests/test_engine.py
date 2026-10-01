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


def test_short_release_ignored_for_rotate(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    assert engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "short_release")) is None


def test_initial_press_moves_first_notch_early(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    action = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    assert action.type == ACTION_ROTATE
    assert action.direction == DIRECTION_UP
    assert action.notches == 1


def test_single_notch_after_initial_press_not_doubled(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    first = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "short_release"))
    done = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 1))
    assert first.notches == 1
    assert done is None


def test_gesture_total_kept_with_early_first_notch(wheel: BilresaWheel) -> None:
    # Real stream: initial_press per batch, cumulative ongoing counts, final complete.
    engine = GestureEngine()
    stream = [
        ("initial_press", None),
        ("multi_press_ongoing", 6),
        ("short_release", None),
        ("initial_press", None),  # mid-gesture: must not add a notch
        ("multi_press_ongoing", 12),
        ("short_release", None),
        ("multi_press_complete", 12),
    ]
    actions = [
        engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, e, c)) for e, c in stream
    ]
    assert sum(a.notches for a in actions if a) == 12


def test_next_gesture_gets_early_notch_again(wheel: BilresaWheel) -> None:
    engine = GestureEngine()
    engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "multi_press_complete", 3))
    action = engine.process(wheel, _decoded(1, ROLE_SCROLL_UP, "initial_press"))
    assert action.notches == 1


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
