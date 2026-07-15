"""Tests for binding timer safety and convenience behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from custom_components.ikea_bilresa.binding import LightBinding
from custom_components.ikea_bilresa.const import (
    ACTION_PRESS,
    ACTION_RELEASE,
    CONF_CHANNEL,
    CONF_HOLD_ACTION,
    CONF_NODE_ID,
    CONF_TARGET,
    HOLD_RAMP,
)
from custom_components.ikea_bilresa.engine import WheelAction


def _binding(monkeypatch) -> tuple[LightBinding, Mock, Mock]:
    hass = SimpleNamespace()
    interval_unsub = Mock()
    watchdog_unsub = Mock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_track_time_interval",
        lambda *_args: interval_unsub,
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_call_later",
        lambda *_args: watchdog_unsub,
    )
    binding = LightBinding(
        hass,
        {
            CONF_NODE_ID: 101,
            CONF_CHANNEL: 1,
            CONF_TARGET: "light.test",
            CONF_HOLD_ACTION: HOLD_RAMP,
        },
    )
    binding._rotate_by = Mock()
    return binding, interval_unsub, watchdog_unsub


def _action(action_type: str, *, presses: int = 0) -> WheelAction:
    return WheelAction(
        node_id=101,
        wheel_name="Test wheel",
        channel=1,
        endpoint_id=3,
        type=action_type,
        presses=presses,
    )


def test_release_stops_ramp_and_changes_next_direction(monkeypatch) -> None:
    binding, interval_unsub, watchdog_unsub = _binding(monkeypatch)
    binding._start_ramp()
    binding._handle_action(_action(ACTION_RELEASE))
    interval_unsub.assert_called_once()
    watchdog_unsub.assert_called_once()
    assert binding._ramp_up is False


def test_watchdog_stops_ramp_without_changing_direction(monkeypatch) -> None:
    binding, interval_unsub, watchdog_unsub = _binding(monkeypatch)
    binding._start_ramp()
    binding._ramp_watchdog(None)
    interval_unsub.assert_called_once()
    watchdog_unsub.assert_not_called()
    assert binding._ramp_up is True


def test_new_gesture_and_connection_change_stop_ramp(monkeypatch) -> None:
    binding, interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    binding._start_ramp()
    binding._handle_action(_action(ACTION_PRESS, presses=2))
    interval_unsub.assert_called_once()

    binding._start_ramp()
    binding._handle_connection_change()
    assert interval_unsub.call_count == 2
