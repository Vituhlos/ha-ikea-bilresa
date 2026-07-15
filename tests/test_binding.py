"""Tests for binding timer safety and convenience behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from custom_components.ikea_bilresa.binding import LightBinding
from custom_components.ikea_bilresa.const import (
    ACTION_PRESS,
    ACTION_RELEASE,
    BUTTON_RESPONSE_FAST,
    BUTTON_RESPONSE_MULTI_PRESS,
    CONF_ACCELERATION,
    CONF_BUTTON_RESPONSE,
    CONF_CHANNEL,
    CONF_DOUBLE_TARGET,
    CONF_HOLD_ACTION,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_TARGET,
    DIRECTION_DOWN,
    DIRECTION_UP,
    HOLD_RAMP,
    MODE_VOLUME,
)
from custom_components.ikea_bilresa.engine import WheelAction


def _binding(monkeypatch, **overrides) -> tuple[LightBinding, Mock, Mock]:
    state = SimpleNamespace(state="on", attributes={"brightness": 128})
    hass = SimpleNamespace(
        states=SimpleNamespace(get=Mock(return_value=state)),
        services=SimpleNamespace(async_call=Mock(return_value=object())),
        async_create_task=Mock(),
    )
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
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_track_state_change_event",
        lambda *_args: Mock(),
    )
    data = {
        CONF_NODE_ID: 101,
        CONF_CHANNEL: 1,
        CONF_TARGET: "light.test",
        CONF_HOLD_ACTION: HOLD_RAMP,
        **overrides,
    }
    binding = LightBinding(hass, data)
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


@pytest.mark.parametrize("presses", [1, 2, 3])
def test_fast_single_press_runs_once_and_suppresses_completion(
    monkeypatch, presses: int
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST}
    )
    binding._single_press = Mock()

    binding._handle_raw_button("short_release")
    binding._handle_raw_button("short_release")
    binding._handle_action(_action(ACTION_PRESS, presses=presses))

    binding._single_press.assert_called_once()

    binding._handle_raw_button("short_release")
    assert binding._single_press.call_count == 2


def test_explicit_multi_press_response_waits_for_completion(
    monkeypatch,
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch,
        **{
            CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_MULTI_PRESS,
            CONF_DOUBLE_TARGET: "switch.double",
        },
    )
    binding._single_press = Mock()
    binding._toggle = Mock()

    binding._handle_raw_button("short_release")
    binding._handle_action(_action(ACTION_PRESS, presses=2))

    binding._single_press.assert_not_called()
    binding._toggle.assert_called_once_with("switch.double")


def test_missing_response_policy_preserves_completion_aware_behavior(
    monkeypatch,
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    binding._single_press = Mock()

    binding._handle_raw_button("short_release")
    binding._handle_action(_action(ACTION_PRESS, presses=1))

    binding._single_press.assert_called_once()


def test_connection_change_clears_fast_press_guard(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST}
    )
    binding._single_press = Mock()

    binding._handle_raw_button("short_release")
    binding._handle_connection_change()
    binding._handle_raw_button("short_release")

    assert binding._single_press.call_count == 2


def test_lost_completion_guard_recovers_on_later_gesture(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST}
    )
    binding._single_press = Mock()
    times = iter([1.0, 1.0, 4.0, 4.1, 4.1])
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: next(times)
    )

    binding._handle_raw_button("short_release")
    binding._handle_raw_button("initial_press")
    binding._handle_raw_button("short_release")

    assert binding._single_press.call_count == 2


def test_hold_sequence_never_runs_fast_single_press(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST}
    )
    binding._single_press = Mock()

    binding._handle_raw_button("initial_press")
    binding._handle_raw_button("long_press")
    binding._handle_raw_button("long_release")

    binding._single_press.assert_not_called()


def test_unload_clears_guard_and_unsubscribes_raw_signal(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST}
    )
    unsubscribers = [Mock(), Mock(), Mock()]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_dispatcher_connect",
        Mock(side_effect=unsubscribers),
    )

    unsubscribe = binding.async_attach()
    binding._handle_raw_button("short_release")
    unsubscribe()

    assert binding._fast_press_started is None
    for signal_unsubscribe in unsubscribers:
        signal_unsubscribe.assert_called_once()


@pytest.mark.parametrize(
    "method_name",
    [
        "_rotate_brightness",
        "_rotate_color_temp",
        "_rotate_color",
        "_rotate_volume",
        "_rotate_cover",
        "_rotate_temperature",
        "_rotate_fan",
        "_rotate_number",
    ],
)
@pytest.mark.parametrize("unavailable_state", [None, "unknown", "unavailable"])
def test_rotation_modes_do_not_call_services_for_unavailable_target(
    monkeypatch, method_name: str, unavailable_state: str | None
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    state = (
        None
        if unavailable_state is None
        else SimpleNamespace(state=unavailable_state, attributes={})
    )
    binding.hass.states.get.return_value = state

    getattr(binding, method_name)(1, True)

    binding.hass.async_create_task.assert_not_called()


def test_unavailable_ramp_stops_without_recurring_commands(monkeypatch) -> None:
    binding, interval_unsub, watchdog_unsub = _binding(monkeypatch)
    binding._rotate_by = LightBinding._rotate_by.__get__(binding)
    binding._start_ramp()
    assert binding._ramp_unsub is not None

    binding.hass.states.get.return_value = SimpleNamespace(
        state="unavailable", attributes={}
    )
    binding._ramp_tick(None)

    interval_unsub.assert_called_once()
    watchdog_unsub.assert_called_once()
    binding.hass.async_create_task.reset_mock()
    binding._ramp_tick(None)
    binding.hass.async_create_task.assert_not_called()


def test_recovery_resynchronizes_from_real_target_state(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    unavailable = SimpleNamespace(state="unavailable", attributes={})
    recovered = SimpleNamespace(state="on", attributes={"brightness": 51})
    binding.hass.states.get.side_effect = [unavailable, recovered]
    binding._tracked = 220

    assert binding._available_state("light.test") is None
    assert binding._available_state("light.test") is recovered
    assert binding._tracked is None


def test_button_action_skips_unavailable_target_and_recovers(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    binding.hass.states.get.return_value = SimpleNamespace(
        state="unknown", attributes={}
    )

    binding._single_press()
    binding._single_press()
    binding.hass.async_create_task.assert_not_called()

    binding.hass.states.get.return_value = SimpleNamespace(state="on", attributes={})
    binding._single_press()
    binding.hass.async_create_task.assert_called_once()


def test_legacy_incompatible_mode_target_fails_closed(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_MODE: MODE_VOLUME}
    )
    binding._rotate_by = LightBinding._rotate_by.__get__(binding)

    binding._rotate_by(1, True)
    binding._start_ramp()

    binding.hass.async_create_task.assert_not_called()
    assert binding._ramp_unsub is None


def test_trailing_rotation_from_pre_button_gesture_is_suppressed(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    binding._handle_raw_input("scroll_up", "initial_press")
    binding._handle_raw_input("button", "initial_press")
    binding._hold_off_rotation()

    binding._rotate(_action("rotate"))

    binding._rotate_by.assert_not_called()


def test_deliberate_new_rotation_after_button_is_not_suppressed(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    binding._handle_raw_input("scroll_up", "initial_press")
    binding._handle_raw_input("button", "initial_press")
    binding._hold_off_rotation()
    binding._handle_raw_input("scroll_up", "initial_press")

    binding._rotate(_action("rotate"))

    binding._rotate_by.assert_called_once()


def test_missing_gesture_boundary_expires(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    times = iter([1.0, 4.0])
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: next(times)
    )
    binding._handle_raw_input("button", "initial_press")
    binding._hold_off_rotation()

    binding._rotate(_action("rotate"))

    binding._rotate_by.assert_called_once()


def test_velocity_acceleration_uses_elapsed_time_not_first_batch_size(
    monkeypatch,
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_ACCELERATION: 100}
    )
    times = iter([0.0, 1.0])
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: next(times)
    )

    assert binding._accelerate(20, DIRECTION_UP) == 20
    assert binding._accelerate(6, DIRECTION_UP) == 12


def test_velocity_acceleration_resets_after_idle_and_direction_change(
    monkeypatch,
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_ACCELERATION: 100}
    )
    times = iter([0.0, 1.0, 3.0, 3.5])
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: next(times)
    )

    assert binding._accelerate(6, DIRECTION_UP) == 6
    assert binding._accelerate(6, DIRECTION_UP) == 12
    assert binding._accelerate(6, DIRECTION_UP) == 6
    assert binding._accelerate(6, DIRECTION_DOWN) == 6


def test_disabled_acceleration_preserves_every_delta(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_ACCELERATION: 0}
    )

    assert [binding._accelerate(n, DIRECTION_UP) for n in (1, 3, 8)] == [1, 3, 8]


def test_velocity_resets_on_gesture_completion_and_reconnect(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_ACCELERATION: 100}
    )
    binding._velocity_samples.extend([(1.0, 2), (2.0, 4)])
    binding._velocity_direction = DIRECTION_UP

    binding._handle_raw_input("scroll_up", "multi_press_complete")
    assert binding._reset_velocity_after_rotate is True
    binding._handle_connection_change()

    assert not binding._velocity_samples
    assert binding._velocity_direction is None


def test_rotate_up_from_off_uses_predictable_configured_floor(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    binding._rotate_by = LightBinding._rotate_by.__get__(binding)
    binding.hass.states.get.return_value = SimpleNamespace(state="off", attributes={})

    binding._rotate_brightness(1, True)

    payload = binding.hass.services.async_call.call_args.args[2]
    assert payload["brightness"] == 8


def test_external_state_change_invalidates_tracked_target(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    binding._tracked = 220
    binding._command_authoritative_until = 1.0
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: 2.0
    )
    event = SimpleNamespace(
        data={"new_state": SimpleNamespace(state="on", attributes={"brightness": 40})}
    )

    binding._handle_target_state_change(event)

    assert binding._tracked is None


def test_own_transition_echo_does_not_rebase_tracking(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    binding._tracked = 220
    binding._command_authoritative_until = 3.0
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: 2.0
    )
    event = SimpleNamespace(
        data={"new_state": SimpleNamespace(state="on", attributes={"brightness": 100})}
    )

    binding._handle_target_state_change(event)

    assert binding._tracked == 220


def test_unavailable_state_event_stops_ramp_and_clears_tracking(monkeypatch) -> None:
    binding, interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    binding._start_ramp()
    binding._tracked = 120
    event = SimpleNamespace(
        data={"new_state": SimpleNamespace(state="unavailable", attributes={})}
    )

    binding._handle_target_state_change(event)

    interval_unsub.assert_called_once()
    assert binding._tracked is None
