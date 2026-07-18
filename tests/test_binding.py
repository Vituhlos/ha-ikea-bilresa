"""Tests for binding timer safety and convenience behavior."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from custom_components.ikea_bilresa.binding import LightBinding
from custom_components.ikea_bilresa.const import (
    ACTION_HOLD,
    ACTION_PRESS,
    ACTION_RELEASE,
    ACTION_ROTATE,
    BUTTON_RESPONSE_FAST,
    BUTTON_RESPONSE_INSTANT,
    BUTTON_RESPONSE_MULTI_PRESS,
    CONF_ACCELERATION,
    CONF_BUTTON_RESPONSE,
    CONF_CHANNEL,
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_ENDPOINT,
    CONF_HOLD_ACTION,
    CONF_HOLD_TARGET,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_RAMP_DIRECTION,
    CONF_TARGET,
    CONF_TRANSITION,
    DIRECTION_DOWN,
    DIRECTION_UP,
    HOLD_NONE,
    HOLD_RAMP,
    MODE_VOLUME,
    RAMP_DIRECTION_DOWN,
    RAMP_DIRECTION_UP,
)
from custom_components.ikea_bilresa.engine import WheelAction


def _monotonic_values(*values: float):
    """Return deterministic test time without failing during fixture cleanup."""
    iterator = iter(values)
    last = values[-1]
    return lambda: next(iterator, last)


def _binding(monkeypatch, **overrides) -> tuple[LightBinding, Mock, Mock]:
    state = SimpleNamespace(state="on", attributes={"brightness": 128})

    def _close_task(coro):
        coro.close()
        return Mock()

    hass = SimpleNamespace(
        states=SimpleNamespace(get=Mock(return_value=state)),
        services=SimpleNamespace(async_call=Mock(return_value=object())),
        async_create_task=Mock(side_effect=_close_task),
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
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_dispatcher_send", Mock()
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


def _button_binding(
    monkeypatch, *, node_id: int, endpoint_id: int, target: str, **overrides
) -> tuple[LightBinding, Mock, Mock]:
    binding, interval_unsub, watchdog_unsub = _binding(
        monkeypatch,
        **{
            CONF_NODE_ID: node_id,
            CONF_ENDPOINT: endpoint_id,
            CONF_CHANNEL: None,
            CONF_TARGET: None,
            CONF_HOLD_ACTION: HOLD_NONE,
            CONF_CLICK_TARGET: target,
            **overrides,
        },
    )
    return binding, interval_unsub, watchdog_unsub


def _button_action(
    node_id: int, endpoint_id: int, action_type: str, *, presses: int = 0
) -> WheelAction:
    return WheelAction(
        node_id=node_id,
        wheel_name="Test dual button",
        channel=None,
        endpoint_id=endpoint_id,
        type=action_type,
        presses=presses,
    )


def test_button_bindings_keep_endpoints_devices_and_targets_independent(
    monkeypatch,
) -> None:
    first, _interval, _watchdog = _button_binding(
        monkeypatch, node_id=101, endpoint_id=1, target="light.first"
    )
    second, _interval, _watchdog = _button_binding(
        monkeypatch, node_id=101, endpoint_id=2, target="light.second"
    )

    first._handle_dispatched_action(_button_action(101, 2, ACTION_PRESS, presses=1))
    first._handle_dispatched_action(_button_action(202, 1, ACTION_PRESS, presses=1))
    first.hass.services.async_call.assert_not_called()

    first._handle_dispatched_action(_button_action(101, 1, ACTION_PRESS, presses=1))
    second._handle_dispatched_action(_button_action(101, 2, ACTION_PRESS, presses=1))

    assert (
        first.hass.services.async_call.call_args.args[2]["entity_id"] == "light.first"
    )
    assert (
        second.hass.services.async_call.call_args.args[2]["entity_id"] == "light.second"
    )


def test_button_fast_response_filters_shared_raw_signal_by_endpoint(
    monkeypatch,
) -> None:
    binding, _interval, _watchdog = _button_binding(
        monkeypatch,
        node_id=101,
        endpoint_id=1,
        target="light.first",
        **{CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST},
    )
    binding._single_press = Mock()

    binding._handle_raw_input("button", "short_release", 2)
    binding._handle_raw_input("button", "short_release", 1)

    binding._single_press.assert_called_once()


def test_button_fixed_down_ramp_reuses_release_and_watchdog_safety(
    monkeypatch,
) -> None:
    binding, interval_unsub, watchdog_unsub = _button_binding(
        monkeypatch,
        node_id=101,
        endpoint_id=2,
        target="light.second",
        **{
            CONF_HOLD_ACTION: HOLD_RAMP,
            CONF_HOLD_TARGET: "light.second",
            CONF_RAMP_DIRECTION: RAMP_DIRECTION_DOWN,
        },
    )

    binding._handle_dispatched_action(_button_action(101, 2, ACTION_HOLD))
    binding._rotate_by.assert_called_once_with(1, False)
    binding._handle_dispatched_action(_button_action(101, 2, ACTION_RELEASE))
    interval_unsub.assert_called_once()
    watchdog_unsub.assert_called_once()
    assert binding._ramp_up is False

    binding._handle_dispatched_action(_button_action(101, 2, ACTION_HOLD))
    binding._ramp_watchdog(None)
    assert interval_unsub.call_count == 2
    assert binding._ramp_up is False


def test_two_button_hold_pair_ramps_shared_light_in_opposite_directions(
    monkeypatch,
) -> None:
    up, _interval, _watchdog = _button_binding(
        monkeypatch,
        node_id=101,
        endpoint_id=1,
        target="light.shared",
        **{
            CONF_HOLD_ACTION: HOLD_RAMP,
            CONF_HOLD_TARGET: "light.shared",
            CONF_RAMP_DIRECTION: RAMP_DIRECTION_UP,
        },
    )
    down, _interval, _watchdog = _button_binding(
        monkeypatch,
        node_id=101,
        endpoint_id=2,
        target="light.shared",
        **{
            CONF_HOLD_ACTION: HOLD_RAMP,
            CONF_HOLD_TARGET: "light.shared",
            CONF_RAMP_DIRECTION: RAMP_DIRECTION_DOWN,
        },
    )

    up._handle_dispatched_action(_button_action(101, 1, ACTION_HOLD))
    down._handle_dispatched_action(_button_action(101, 2, ACTION_HOLD))

    up._rotate_by.assert_called_once_with(1, True)
    down._rotate_by.assert_called_once_with(1, False)


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


def test_ramp_already_at_limit_waits_only_for_release_safety(monkeypatch) -> None:
    binding, interval_unsub, watchdog_unsub = _binding(monkeypatch)
    binding._rotate_by = LightBinding._rotate_by.__get__(binding)
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on",
        attributes={"brightness": 255},
    )

    binding._handle_action(_action(ACTION_HOLD))

    assert binding._ramp_unsub is None
    assert binding._ramp_action is not None
    interval_unsub.assert_not_called()
    watchdog_unsub.assert_not_called()

    binding._handle_action(_action(ACTION_RELEASE))

    watchdog_unsub.assert_called_once()
    assert binding._ramp_action is None
    assert binding._ramp_up is False


def test_ramp_pauses_recurring_ticks_when_it_reaches_limit(monkeypatch) -> None:
    binding, interval_unsub, watchdog_unsub = _binding(monkeypatch)
    binding._rotate_by = LightBinding._rotate_by.__get__(binding)
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on",
        attributes={"brightness": 250},
    )

    binding._handle_action(_action(ACTION_HOLD))
    assert binding._ramp_unsub is not None

    binding._ramp_tick(None)

    interval_unsub.assert_called_once()
    assert binding._ramp_unsub is None
    assert binding._ramp_action is not None

    binding._handle_action(_action(ACTION_RELEASE))

    watchdog_unsub.assert_called_once()
    assert binding._ramp_action is None
    assert binding._ramp_up is False


def test_new_gesture_and_connection_change_stop_ramp(monkeypatch) -> None:
    binding, interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    binding._start_ramp()
    binding._handle_action(_action(ACTION_PRESS, presses=2))
    interval_unsub.assert_called_once()

    binding._start_ramp()
    binding._handle_connection_change()
    assert interval_unsub.call_count == 2


def test_fast_press_stops_ramp_paused_at_limit(monkeypatch) -> None:
    binding, interval_unsub, watchdog_unsub = _binding(
        monkeypatch, **{CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST}
    )
    binding._single_press = Mock()
    binding._start_ramp()
    binding._pause_ramp_at_limit()

    assert binding._ramp_active is True
    assert binding._ramp_unsub is None

    binding._handle_raw_button("short_release")

    interval_unsub.assert_called_once()
    watchdog_unsub.assert_called_once()
    binding._single_press.assert_called_once()
    assert binding._ramp_active is False
    assert binding._ramp_action is None


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


def test_instant_single_press_runs_on_initial_press_exactly_once(
    monkeypatch,
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch,
        **{
            CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_INSTANT,
            CONF_HOLD_ACTION: HOLD_NONE,
        },
    )
    binding._single_press = Mock()

    binding._handle_raw_button("initial_press")
    binding._handle_raw_button("short_release")
    binding._handle_action(_action(ACTION_PRESS, presses=1))

    binding._single_press.assert_called_once()


def test_instant_press_guard_recovers_on_later_gesture(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch,
        **{
            CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_INSTANT,
            CONF_HOLD_ACTION: HOLD_NONE,
        },
    )
    binding._single_press = Mock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic",
        _monotonic_values(1.0, 1.0, 4.0, 4.0),
    )

    binding._handle_raw_button("initial_press")
    binding._handle_raw_button("initial_press")

    assert binding._single_press.call_count == 2


def test_ambiguous_stored_instant_policy_falls_back_to_completion(
    monkeypatch,
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch,
        **{
            CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_INSTANT,
            CONF_HOLD_ACTION: HOLD_RAMP,
        },
    )
    binding._single_press = Mock()

    binding._handle_raw_button("initial_press")
    binding._handle_action(_action(ACTION_PRESS, presses=1))

    binding._single_press.assert_called_once()


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
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic",
        _monotonic_values(1.0, 1.0, 4.0, 4.1, 4.1),
    )

    binding._handle_raw_button("short_release")
    binding._handle_raw_button("initial_press")
    binding._handle_raw_button("short_release")

    assert binding._single_press.call_count == 2


def test_fast_press_debug_trace_records_latency_without_identifiers(
    monkeypatch, caplog
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST}
    )
    now = [10.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    caplog.set_level(logging.DEBUG, logger="custom_components.ikea_bilresa.binding")

    binding._handle_raw_button("short_release")
    now[0] = 10.08
    binding._handle_target_state_change(
        SimpleNamespace(data={"new_state": SimpleNamespace(state="on")})
    )
    now[0] = 10.25
    binding._handle_action(_action(ACTION_PRESS, presses=1))

    messages = [record.getMessage() for record in caplog.records]
    assert any("stage=short_release elapsed_ms=0.0" in msg for msg in messages)
    assert any("stage=service_dispatch elapsed_ms=0.0" in msg for msg in messages)
    assert any("stage=target_state_change elapsed_ms=80.0" in msg for msg in messages)
    assert any(
        "stage=multi_press_complete elapsed_ms=250.0 presses=1" in msg
        for msg in messages
    )
    assert all("light.test" not in msg and "101" not in msg for msg in messages)


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


@pytest.mark.parametrize(
    ("method_name", "up", "state_name", "attributes"),
    [
        ("_rotate_brightness", True, "on", {"brightness": 255}),
        ("_rotate_brightness", False, "on", {"brightness": 3}),
        (
            "_rotate_color_temp",
            True,
            "on",
            {
                "color_temp_kelvin": 6500,
                "min_color_temp_kelvin": 2700,
                "max_color_temp_kelvin": 6500,
            },
        ),
        (
            "_rotate_color_temp",
            False,
            "on",
            {
                "color_temp_kelvin": 2700,
                "min_color_temp_kelvin": 2700,
                "max_color_temp_kelvin": 6500,
            },
        ),
        ("_rotate_volume", True, "on", {"volume_level": 1.0}),
        ("_rotate_volume", False, "on", {"volume_level": 0.0}),
        ("_rotate_cover", True, "open", {"current_position": 100}),
        ("_rotate_cover", False, "closed", {"current_position": 0}),
        (
            "_rotate_temperature",
            True,
            "heat",
            {
                "temperature": 35.0,
                "min_temp": 7.0,
                "max_temp": 35.0,
                "target_temp_step": 0.5,
            },
        ),
        (
            "_rotate_temperature",
            False,
            "heat",
            {
                "temperature": 7.0,
                "min_temp": 7.0,
                "max_temp": 35.0,
                "target_temp_step": 0.5,
            },
        ),
        ("_rotate_fan", True, "on", {"percentage": 100}),
        ("_rotate_fan", False, "off", {"percentage": 0}),
        (
            "_rotate_number",
            True,
            "100",
            {"min": 0.0, "max": 100.0, "step": 1.0},
        ),
        (
            "_rotate_number",
            False,
            "0",
            {"min": 0.0, "max": 100.0, "step": 1.0},
        ),
    ],
)
def test_bounded_rotation_does_not_repeat_service_at_limit(
    monkeypatch,
    method_name: str,
    up: bool,
    state_name: str,
    attributes: dict,
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    updates = []
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_dispatcher_send",
        lambda _hass, _signal, payload: updates.append(payload),
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state=state_name,
        attributes=attributes,
    )
    binding._active_action = _action(ACTION_ROTATE)

    getattr(binding, method_name)(1, up)

    binding.hass.services.async_call.assert_not_called()
    binding.hass.async_create_task.assert_not_called()
    assert updates[-1]["dispatch_status"] == "completed"
    assert updates[-1]["reason"] == "target_unchanged"
    assert updates[-1]["result"]["before"] == updates[-1]["result"]["after"]


def test_color_rotation_still_wraps_instead_of_stopping_at_hue_boundary(
    monkeypatch,
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on",
        attributes={"hs_color": (359.0, 80.0)},
    )

    binding._rotate_color(1, True)

    payload = binding.hass.services.async_call.call_args.args[2]
    assert payload["hs_color"] == [9.8, 80.0]


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
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic",
        _monotonic_values(1.0, 4.0),
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
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic",
        _monotonic_values(0.0, 1.0),
    )

    assert binding._accelerate(20, DIRECTION_UP) == 20
    assert binding._accelerate(6, DIRECTION_UP) == 12


def test_velocity_acceleration_resets_after_idle_and_direction_change(
    monkeypatch,
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_ACCELERATION: 100}
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic",
        _monotonic_values(0.0, 1.0, 3.0, 3.5),
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


def test_brightness_reports_calculated_result_before_dispatch(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    updates = []
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_dispatcher_send",
        lambda _hass, _signal, payload: updates.append(payload),
    )
    action = _action(ACTION_ROTATE)
    action.direction = DIRECTION_UP
    action.notches = 1
    binding._active_action = action

    binding._rotate_brightness(1, True)

    pending = updates[-1]
    assert pending["action_id"] == action.action_id
    assert pending["dispatch_status"] == "pending"
    assert pending["result"] == {
        "kind": "brightness",
        "before": 50,
        "after": 53,
        "unit": "%",
    }


@pytest.mark.asyncio
async def test_service_dispatch_reports_acceptance_for_exact_action(
    monkeypatch,
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    updates = []
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_dispatcher_send",
        lambda _hass, _signal, payload: updates.append(payload),
    )
    action = _action(ACTION_PRESS, presses=1)

    async def accepted():
        return None

    await binding._async_dispatch_service(
        "homeassistant",
        "toggle",
        accepted(),
        result={"kind": "entity_action"},
        action=action,
    )

    assert updates[-1]["action_id"] == action.action_id
    assert updates[-1]["dispatch_status"] == "accepted"
    assert updates[-1]["dispatched"] is True


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


def test_delayed_zero_transition_echo_does_not_drop_active_gesture_steps(
    monkeypatch,
) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_TRANSITION: 0.0}
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )
    binding._handle_raw_input("scroll_down", "initial_press", 2)

    binding._rotate_brightness(1, False)
    now[0] = 0.2
    binding._rotate_brightness(2, False)

    # Shelly may acknowledge an older absolute target after the fixed
    # zero-transition echo margin while the Matter gesture is still active.
    now[0] = 0.6
    stale_echo = SimpleNamespace(state="on", attributes={"brightness": 247})
    binding.hass.states.get.return_value = stale_echo
    binding._handle_target_state_change(SimpleNamespace(data={"new_state": stale_echo}))

    now[0] = 0.7
    binding._rotate_brightness(1, False)

    assert binding.hass.services.async_call.call_args.args[2]["brightness"] == 224


def test_scroll_tracking_survives_overlapping_direction_boundaries(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._tracked = 180
    binding._command_authoritative_until = 0.25

    binding._handle_raw_input("scroll_up", "initial_press", 1)
    now[0] = 0.4
    binding._handle_raw_input("scroll_down", "initial_press", 2)
    binding._handle_raw_input("scroll_up", "multi_press_complete", 1)
    binding._handle_target_state_change(
        SimpleNamespace(
            data={
                "new_state": SimpleNamespace(state="on", attributes={"brightness": 80})
            }
        )
    )

    assert binding._tracked == 180

    now[0] = 0.8
    binding._handle_raw_input("scroll_down", "multi_press_complete", 2)
    binding._handle_target_state_change(
        SimpleNamespace(
            data={
                "new_state": SimpleNamespace(state="on", attributes={"brightness": 80})
            }
        )
    )

    assert binding._tracked is None


def test_missing_scroll_completion_expires_target_authority(monkeypatch) -> None:
    binding, _interval_unsub, _watchdog_unsub = _binding(monkeypatch)
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._tracked = 180
    binding._command_authoritative_until = 0.25
    binding._handle_raw_input("scroll_up", "initial_press", 1)

    now[0] = 2.1
    binding._handle_target_state_change(
        SimpleNamespace(
            data={
                "new_state": SimpleNamespace(state="on", attributes={"brightness": 80})
            }
        )
    )

    assert binding._tracked is None
    assert binding._active_scrolls == {}


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
