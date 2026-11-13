"""Tests for binding timer safety and convenience behavior."""

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from custom_components.ikea_bilresa.binding import (
    _ACTIVE_SCROLL_TIMEOUT,
    _RAMP_NOTCHES,
    _SCROLL_AUTHORITY_GRACE,
    _SMOOTHING_FULL_BATCH,
    LightBinding,
)
from custom_components.ikea_bilresa.channel_controls import to_perceptual
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
    CONF_MAX_VOLUME,
    CONF_MIN_BRIGHTNESS,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_RAMP_DIRECTION,
    CONF_STEP,
    CONF_STEP_CURVE,
    CONF_TARGET,
    CONF_TRANSITION,
    CONF_TRIPLE_TARGET,
    DIRECTION_DOWN,
    DIRECTION_UP,
    HOLD_NONE,
    HOLD_RAMP,
    HOLD_TOGGLE,
    MODE_BRIGHTNESS,
    MODE_COLOR,
    MODE_COLOR_TEMP,
    MODE_COVER,
    MODE_VOLUME,
    RAMP_DIRECTION_DOWN,
    RAMP_DIRECTION_UP,
    ROLE_SCROLL_DOWN,
)
from custom_components.ikea_bilresa.engine import GestureEngine, WheelAction
from custom_components.ikea_bilresa.model import BilresaWheel, SwitchEndpoint


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
    binding._press_target = Mock()

    binding._handle_raw_button("short_release")
    binding._handle_action(_action(ACTION_PRESS, presses=2))

    binding._single_press.assert_not_called()
    binding._press_target.assert_called_once_with(
        "double_press", "switch.double", "toggle"
    )


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
    unsubscribers = [Mock(), Mock(), Mock(), Mock()]
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
    accelerator = binding._accelerator
    accelerator._samples.extend([(1.0, 2), (2.0, 4)])
    accelerator._direction = DIRECTION_UP

    binding._handle_raw_input("scroll_up", "multi_press_complete")
    assert binding._reset_velocity_after_rotate is True
    binding._handle_connection_change()

    assert not accelerator._samples
    assert accelerator._direction is None


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

    # A completion ends one Matter gesture, not necessarily the physical
    # rotation, so the grace window still owns the calculated target.
    assert binding._tracked == 180

    now[0] = 2.0
    binding._handle_target_state_change(
        SimpleNamespace(
            data={
                "new_state": SimpleNamespace(state="on", attributes={"brightness": 80})
            }
        )
    )

    assert binding._tracked is None


def _smoothing_binding(monkeypatch, **overrides):
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch,
        **{CONF_TRANSITION: 0.4, CONF_STEP: 3, CONF_ACCELERATION: 0, **overrides},
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 128}
    )
    return binding


def _dispatched_transition(binding) -> float:
    return binding.hass.services.async_call.call_args.args[2]["transition"]


def test_a_single_notch_is_never_smoothed(monkeypatch) -> None:
    """The eager first notch must stay immediate at any configured value."""
    binding = _smoothing_binding(monkeypatch)

    binding._rotate_brightness(1, up=True)

    assert _dispatched_transition(binding) == 0.0


def test_a_full_size_batch_receives_the_configured_transition(monkeypatch) -> None:
    binding = _smoothing_binding(monkeypatch)

    binding._rotate_brightness(_SMOOTHING_FULL_BATCH, up=True)

    assert _dispatched_transition(binding) == 0.4


def test_batch_smoothing_scales_with_batch_size(monkeypatch) -> None:
    """Half a full batch travels half as far, so it is spread half as long."""
    binding = _smoothing_binding(monkeypatch)

    binding._rotate_brightness(_SMOOTHING_FULL_BATCH // 2, up=True)

    assert _dispatched_transition(binding) == pytest.approx(0.2)


def test_a_batch_beyond_the_observed_maximum_stays_at_the_ceiling(monkeypatch) -> None:
    binding = _smoothing_binding(monkeypatch)

    binding._rotate_brightness(_SMOOTHING_FULL_BATCH * 3, up=True)

    assert _dispatched_transition(binding) == 0.4


def test_zero_configured_transition_disables_smoothing(monkeypatch) -> None:
    """The historic instant behavior stays reachable from the existing field."""
    binding = _smoothing_binding(monkeypatch, **{CONF_TRANSITION: 0.0})

    binding._rotate_brightness(_SMOOTHING_FULL_BATCH, up=True)

    assert _dispatched_transition(binding) == 0.0


def test_hold_to_ramp_steps_are_never_smoothed(monkeypatch) -> None:
    """Ramp ticks are one notch each, so the ramp keeps its own cadence."""
    binding = _smoothing_binding(monkeypatch)
    del binding._rotate_by  # the shared helper mocks it; this test needs the real one

    binding._start_ramp()

    assert _RAMP_NOTCHES == 1
    assert _dispatched_transition(binding) == 0.0


def test_follow_up_batches_in_one_scroll_get_the_full_transition(
    monkeypatch,
) -> None:
    """After the eager first batch, small batches fade instead of stepping.

    Issue #9: a slow scroll arrives as one-to-three notch batches. Scaling
    the transition by batch size shrank each of them to a fraction of the
    configured value, so every step landed as a visible jump. Everything
    after the first dispatched batch of a continuous scroll travels the
    whole configured transition instead.
    """
    binding = _smoothing_binding(monkeypatch)
    binding._min_command_interval = 0.0  # every batch dispatches at once
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)

    binding._rotate_brightness(1, up=False)
    assert _dispatched_transition(binding) == 0.0

    binding._rotate_brightness(1, up=False)
    assert _dispatched_transition(binding) == 0.4

    binding._rotate_brightness(3, up=False)
    assert _dispatched_transition(binding) == 0.4


def test_a_later_matter_gesture_in_the_same_scroll_stays_smoothed(
    monkeypatch,
) -> None:
    """The firmware splits one physical rotation into several gestures.

    A gesture completed only a fraction of a second ago is still inside the
    same scroll, so its first batch is not a fresh eager notch — smoothing
    applies the moment the scroll has already taken a command.
    """
    binding = _smoothing_binding(monkeypatch)
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._min_command_interval = 0.0  # every batch dispatches at once
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)
    assert _dispatched_transition(binding) == 0.0

    binding._handle_raw_input(ROLE_SCROLL_DOWN, "multi_press_complete", 2)
    now[0] = 0.5
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)

    assert _dispatched_transition(binding) == 0.4


def test_a_fresh_scroll_after_quiet_gets_its_eager_first_batch_back(
    monkeypatch,
) -> None:
    """Once the scroll has been quiet, the next rotation is a new gesture."""
    binding = _smoothing_binding(monkeypatch)
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "multi_press_complete", 2)

    now[0] = _ACTIVE_SCROLL_TIMEOUT + _SCROLL_AUTHORITY_GRACE + 0.1
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)

    assert _dispatched_transition(binding) == 0.0


def test_a_ramp_started_right_after_a_scroll_stays_immediate(monkeypatch) -> None:
    """Ramp ticks keep their own cadence even when a scroll already commanded."""
    binding = _smoothing_binding(monkeypatch)
    del binding._rotate_by  # the shared helper mocks it; this needs the real one
    binding._min_command_interval = 0.0  # every batch dispatches at once
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)

    binding._handle_action(_action(ACTION_HOLD))
    assert _dispatched_transition(binding) == 0.0

    binding._ramp_tick(None)
    assert _dispatched_transition(binding) == 0.0


def test_color_temperature_batches_are_smoothed_too(monkeypatch) -> None:
    binding = _smoothing_binding(monkeypatch, **{CONF_MODE: MODE_COLOR_TEMP})

    binding._rotate_color_temp(_SMOOTHING_FULL_BATCH, up=True)

    assert _dispatched_transition(binding) == 0.4


def test_turning_off_at_the_minimum_is_smoothed_like_its_batch(monkeypatch) -> None:
    binding = _smoothing_binding(monkeypatch, **{CONF_MIN_BRIGHTNESS: 0})
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 10}
    )

    binding._rotate_brightness(_SMOOTHING_FULL_BATCH, up=False)

    assert binding.hass.services.async_call.call_args.args[1] == "turn_off"
    assert _dispatched_transition(binding) == 0.4


def _replay_recorded_fast_scroll(binding, now, *, step_seconds: float = 0.05):
    """Drive the exact recorded capture through the real decoder and binding.

    The raw sequence is the sanitized Matter Server 9.1.0 trace already
    replayed by ``test_sanitized_bilresa_fast_trace_preserves_both_cumulative_
    sequences``: one continuous physical rotation the firmware splits into two
    gestures of 18 and 14 notches.
    """
    engine = GestureEngine()
    wheel = BilresaWheel(
        node_id=101,
        name="Test wheel",
        product_name="BILRESA scroll wheel",
        serial="SER123",
        endpoints={2: SwitchEndpoint(2, 1, ROLE_SCROLL_DOWN)},
    )
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

    def _pump(event_type, count):
        # Exactly the coordinator's order: raw hint first, then the decoded
        # action, both inside one synchronous block.
        binding._handle_raw_input(ROLE_SCROLL_DOWN, event_type, 2)
        action = engine.process(
            wheel,
            {
                "node_id": 101,
                "wheel_name": "Test wheel",
                "endpoint_id": 2,
                "channel": 1,
                "role": ROLE_SCROLL_DOWN,
                "event_type": event_type,
                "count": count,
                "raw": {},
            },
        )
        if action is not None:
            binding._rotate_brightness(action.notches, up=False)

    for index, (event_type, count) in enumerate(events):
        now[0] = index * step_seconds
        _pump(event_type, count)
        if event_type == "multi_press_complete" and count == 18:
            yield now[0]


def test_recorded_fast_scroll_applies_every_notch_exactly(monkeypatch) -> None:
    """Both gestures of one rotation must land on the single-shot arithmetic."""
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_TRANSITION: 0.0, CONF_STEP: 3, CONF_ACCELERATION: 0}
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )

    for _gap in _replay_recorded_fast_scroll(binding, now):
        pass

    # 32 notches of 3 % from 255: 255 - 32 * 7.65 = 10.2
    assert binding.hass.services.async_call.call_args.args[2]["brightness"] == 10


def test_stale_echo_between_two_gestures_of_one_scroll_keeps_accounting(
    monkeypatch,
) -> None:
    """The gap after MultiPressComplete must not rebase the next gesture.

    A Shelly Plus 0-10V dimmer acknowledges an older absolute brightness after
    the 250 ms zero-transition margin has already expired. Landing between two
    gestures of one physical rotation, that echo used to erase confirmed
    notches — the RC.5 accounting anomaly (18 notches moved the light by 15).
    """
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_TRANSITION: 0.0, CONF_STEP: 3, CONF_ACCELERATION: 0}
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )

    for gap in _replay_recorded_fast_scroll(binding, now):
        # Two batches behind: the value dispatched before the last one.
        stale = SimpleNamespace(state="on", attributes={"brightness": 133})
        binding.hass.states.get.return_value = stale
        now[0] = gap + 0.3
        binding._handle_target_state_change(SimpleNamespace(data={"new_state": stale}))

    assert binding.hass.services.async_call.call_args.args[2]["brightness"] == 10


def test_quantized_echo_of_our_own_value_is_recognized(monkeypatch) -> None:
    """A dimmer storing whole percent returns 155 for a dispatched 156."""
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_TRANSITION: 0.0, CONF_STEP: 3}
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 156}
    )
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)
    dispatched = binding._tracked

    now[0] = 0.4
    quantized = SimpleNamespace(state="on", attributes={"brightness": 147})
    binding._handle_target_state_change(SimpleNamespace(data={"new_state": quantized}))

    assert binding._tracked == dispatched


def test_off_path_report_mid_scroll_cannot_rebase_the_tracked_target(
    monkeypatch,
) -> None:
    """Issue #9: a wandering mid-scroll report is ignored, not trusted.

    A Zigbee2MQTT group republishes whichever member bulb answered last, so
    during a fade the entity's brightness wanders to values nobody sent.
    Each of those reports used to drop the tracked target, and the next
    notch restarted from a stale member level — the jumps to an unrelated
    brightness reported while scrolling. The scroll now finishes on its own
    arithmetic.
    """
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_TRANSITION: 0.0, CONF_STEP: 3}
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)

    now[0] = 0.4
    stray = SimpleNamespace(state="on", attributes={"brightness": 12})
    binding._handle_target_state_change(SimpleNamespace(data={"new_state": stray}))

    assert binding._tracked == pytest.approx(255 - 7.65)

    now[0] = 0.6
    binding._handle_target_state_change(SimpleNamespace(data={"new_state": stray}))

    assert binding._tracked == pytest.approx(255 - 7.65)


def test_the_first_report_after_a_scroll_ends_still_rebases(monkeypatch) -> None:
    """The mid-scroll window is bounded: a real external change lands after it."""
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_TRANSITION: 0.0, CONF_STEP: 3}
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)

    now[0] = 0.4
    external = SimpleNamespace(state="on", attributes={"brightness": 12})
    binding._handle_target_state_change(SimpleNamespace(data={"new_state": external}))
    assert binding._tracked is not None

    # Once the scroll has been quiet, the same value is a real external
    # change: the next rotation resyncs onto it.
    now[0] = _ACTIVE_SCROLL_TIMEOUT + _SCROLL_AUTHORITY_GRACE + 0.1
    binding._handle_target_state_change(SimpleNamespace(data={"new_state": external}))
    binding.hass.states.get.return_value = external
    binding._rotate_brightness(1, up=False)

    assert binding._tracked == pytest.approx(12 - 7.65)


def test_wandering_group_reports_do_not_move_a_scroll_in_progress(
    monkeypatch,
) -> None:
    """Regression test for the stale-level jumps reported in issue #9.

    Modelled on the report: a Zigbee2MQTT group republishes whichever member
    bulb answered last, so its brightness wanders off the commanded path
    while a fade is running. Member reports below and above the path must
    all be ignored mid-gesture, and the scroll's arithmetic must land
    exactly where the notches put it.
    """
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_TRANSITION: 0.0, CONF_STEP: 3, CONF_ACCELERATION: 0}
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )

    def _member_reported(value: int) -> None:
        binding._handle_target_state_change(
            SimpleNamespace(
                data={
                    "new_state": SimpleNamespace(
                        state="on", attributes={"brightness": value}
                    )
                }
            )
        )

    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)
    now[0] = 0.2
    binding._rotate_brightness(2, up=False)

    # One member still sits near the top, another is deep into its fade:
    # both levels lie off the path between the last report and our commands.
    now[0] = 0.3
    _member_reported(190)
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 190}
    )
    now[0] = 0.5
    _member_reported(254)

    binding._handle_raw_input(ROLE_SCROLL_DOWN, "multi_press_complete", 2)
    now[0] = 0.6
    binding._rotate_brightness(1, up=False)

    # Four notches of 3 % from 255: the group chatter must not have moved it.
    assert binding._tracked == pytest.approx(255 - 4 * 7.65)
    assert binding.hass.services.async_call.call_args.args[2]["brightness"] == round(
        255 - 4 * 7.65
    )


def test_a_lingering_off_path_group_state_does_not_reset_the_next_scroll(
    monkeypatch,
) -> None:
    """A stale member level must not rebase even the scroll after next.

    A Zigbee2MQTT group's entity state is whichever member bulb reported
    last; when that report is a stray member level it lingers after the
    scroll ends. The next scroll must continue from the tracked target it
    calculated — rebasing onto the lingering state would recreate the
    stale-level jump one gesture later.
    """
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_TRANSITION: 0.0, CONF_STEP: 3, CONF_ACCELERATION: 0}
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )

    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)
    binding._rotate_brightness(1, up=False)

    # One member reports 190 mid-scroll — off the commanded path, ignored.
    # It stays as the group's entity state: no further reports arrive.
    now[0] = 0.3
    binding._handle_target_state_change(
        SimpleNamespace(
            data={
                "new_state": SimpleNamespace(state="on", attributes={"brightness": 190})
            }
        )
    )
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "multi_press_complete", 2)
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 190}
    )

    # The authority window has expired (1.6 > 0.3 + grace) while _resync's
    # freshness window has not (1.6 < 0 + 3): the tracked target — two
    # notches from 255 — must still win over the lingering member level.
    now[0] = 1.6
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)

    assert binding._tracked == pytest.approx(255 - 3 * 7.65)
    assert binding.hass.services.async_call.call_args.args[2]["brightness"] == round(
        255 - 3 * 7.65
    )


def test_a_mid_scroll_echo_does_not_force_a_later_resync(monkeypatch) -> None:
    """Own echoes ignored mid-scroll must not disturb the next scroll.

    The cumulative accounting the authority window protects has to carry
    straight into a quick successive scroll.
    """
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_TRANSITION: 0.0, CONF_STEP: 3, CONF_ACCELERATION: 0}
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )

    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)

    # A report travelling along the commanded path is an own echo: ignored
    # without parking anything for reconciliation.
    now[0] = 0.3
    binding._handle_target_state_change(
        SimpleNamespace(
            data={
                "new_state": SimpleNamespace(state="on", attributes={"brightness": 253})
            }
        )
    )
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "multi_press_complete", 2)
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 253}
    )

    now[0] = 1.6
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_brightness(1, up=False)

    # Nothing external was seen, so the tracked target carries straight on.
    assert binding._tracked == pytest.approx(255 - 2 * 7.65)


def test_an_off_path_report_mid_scroll_is_ignored_for_a_color_temp_light(
    monkeypatch,
) -> None:
    """The light-group distrust covers every mode that targets a light.

    A group bound in color-temperature mode produces the same last-member-
    wins state wanderings as a brightness group, so its off-path reports
    must be ignored mid-scroll too.
    """
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch,
        **{
            CONF_MODE: MODE_COLOR_TEMP,
            CONF_TARGET: "light.kelvin_group",
            CONF_TRANSITION: 0.0,
            CONF_STEP: 3,
            CONF_ACCELERATION: 0,
        },
    )
    binding._min_command_interval = 0.0
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on",
        attributes={
            "color_temp_kelvin": 4000,
            "min_color_temp_kelvin": 2000,
            "max_color_temp_kelvin": 6535,
        },
    )

    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_color_temp(1, up=False)

    # 3 % of the 4535 K span per notch, one notch down: tracked lands at
    # 4000 - 136.05. A member report far outside the commanded path must
    # not move it.
    now[0] = 0.3
    binding._handle_target_state_change(
        SimpleNamespace(
            data={
                "new_state": SimpleNamespace(
                    state="on", attributes={"color_temp_kelvin": 6000}
                )
            }
        )
    )

    now[0] = 0.5
    binding._rotate_color_temp(1, up=False)

    notch = 0.03 * 4535
    assert binding._tracked == pytest.approx(4000 - 2 * notch)
    assert binding.hass.services.async_call.call_args.args[2][
        "color_temp_kelvin"
    ] == round(4000 - 2 * notch)


def test_a_non_light_target_still_rebases_on_a_mid_scroll_external_change(
    monkeypatch,
) -> None:
    """Outside the light modes the established rebase stays.

    A cover, climate, media or number target has no aggregated state to
    distrust, so an off-path report mid-scroll is a real external change
    and must keep winning immediately, exactly as before this fix.
    """
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch,
        **{
            CONF_MODE: MODE_COVER,
            CONF_TARGET: "cover.test",
            CONF_TRANSITION: 0.0,
            CONF_STEP: 3,
            CONF_ACCELERATION: 0,
        },
    )
    binding._min_command_interval = 0.0
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="open", attributes={"current_position": 80}
    )

    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_cover(1, up=False)
    assert binding._tracked == 77

    # A wall switch or another controller moves the cover mid-scroll: the
    # off-path report forgets the tracked target and the next notch
    # resyncs from the real position instead of fighting the change.
    now[0] = 0.3
    binding._handle_target_state_change(
        SimpleNamespace(
            data={
                "new_state": SimpleNamespace(
                    state="open", attributes={"current_position": 30}
                )
            }
        )
    )
    assert binding._tracked is None

    binding.hass.states.get.return_value = SimpleNamespace(
        state="open", attributes={"current_position": 30}
    )
    now[0] = 0.5
    binding._rotate_cover(1, up=False)

    assert binding._tracked == 27
    assert binding.hass.services.async_call.call_args.args[2]["position"] == 27


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


def test_a_burst_of_targets_reaches_the_device_as_one_command(monkeypatch) -> None:
    """Absolute values make intermediate commands redundant.

    Captured on hardware: fourteen calls in 4.3 seconds left the dimmer 68
    units from the value it was last sent. Only the newest value matters, so a
    burst inside the interval must collapse to a single send.
    """
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_TRANSITION: 0.0, CONF_STEP: 3}
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    scheduled = []
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_call_later",
        lambda _hass, delay, cb: scheduled.append((delay, cb)) or Mock(),
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )

    binding._rotate_brightness(1, up=False)  # leading edge: sent at once
    now[0] = 0.05
    binding._rotate_brightness(1, up=False)
    now[0] = 0.10
    binding._rotate_brightness(1, up=False)

    assert binding.hass.services.async_call.call_count == 1
    assert len(scheduled) == 1

    now[0] = 0.18
    scheduled[0][1](None)

    # One deferred call carrying the newest target, not the ones in between.
    assert binding.hass.services.async_call.call_count == 2
    assert binding.hass.services.async_call.call_args.args[2]["brightness"] == round(
        255 - 3 * 7.65
    )


def test_the_first_command_of_a_gesture_is_never_delayed(monkeypatch) -> None:
    """The eager response is the point of this integration; it must not queue."""
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_TRANSITION: 0.0, CONF_STEP: 3}
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: 100.0
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )

    binding._rotate_brightness(1, up=False)

    assert binding.hass.services.async_call.call_count == 1


def test_a_queued_command_is_dropped_when_the_target_goes_away(monkeypatch) -> None:
    """A deferred send must not arrive after the target became unavailable."""
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, **{CONF_TRANSITION: 0.0, CONF_STEP: 3}
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    cancel = Mock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_call_later",
        lambda *_a: cancel,
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 255}
    )
    binding._rotate_brightness(1, up=False)
    now[0] = 0.05
    binding._rotate_brightness(1, up=False)

    binding._handle_target_state_change(
        SimpleNamespace(
            data={"new_state": SimpleNamespace(state="unavailable", attributes={})}
        )
    )

    cancel.assert_called_once()
    assert binding._pending_command is None


# -- step curve ------------------------------------------------------------


def test_a_binding_without_a_step_curve_keeps_the_historic_arithmetic(
    monkeypatch,
) -> None:
    """The default must not move. Every stored binding predates this field.

    3 % of the 0-255 range is 7.65 units a notch, applied linearly. These are
    the numbers the integration has produced since the step setting existed.
    """
    binding, _i, _w = _binding(monkeypatch)

    assert binding._brightness_step(255, 1, False) == 255 - 7.65
    assert binding._brightness_step(255, 12, False) == 255 - 12 * 7.65
    assert binding._brightness_step(128, 4, True) == 128 + 4 * 7.65
    # Zero notches is a real case (a batch fully consumed by eager credits).
    assert binding._brightness_step(128, 0, True) == 128


def test_an_explicit_linear_curve_matches_the_absent_one(monkeypatch) -> None:
    absent, _i, _w = _binding(monkeypatch)
    explicit, _i2, _w2 = _binding(monkeypatch, **{CONF_STEP_CURVE: "linear"})

    for notches in (1, 3, 12):
        assert absent._brightness_step(
            200, notches, False
        ) == explicit._brightness_step(200, notches, False)


def test_the_perceptual_curve_makes_a_notch_a_constant_apparent_size(
    monkeypatch,
) -> None:
    """The point of the setting, stated as the property it must have.

    Measured on hardware 2026-08-02, a linear 3 % notch covers 1.2 L* at the top
    of the range and 2.1 L* near the bottom. On the perceptual curve both are
    the configured share of the perceptual range, wherever the lamp happens to
    be.
    """
    binding, _i, _w = _binding(monkeypatch, **{CONF_STEP_CURVE: "perceptual"})

    high = to_perceptual(255) - to_perceptual(binding._brightness_step(255, 1, False))
    low = to_perceptual(60) - to_perceptual(binding._brightness_step(60, 1, False))

    assert round(high, 2) == round(low, 2) == 3.0


def test_the_perceptual_curve_cannot_leave_the_brightness_range(monkeypatch) -> None:
    binding, _i, _w = _binding(monkeypatch, **{CONF_STEP_CURVE: "perceptual"})

    assert binding._brightness_step(255, 80, True) <= 255
    assert binding._brightness_step(4, 80, False) >= 0


# -- scenes and scripts as gesture targets ----------------------------------


def _service_calls(binding) -> list[tuple[str, str, dict]]:
    """The (domain, service, data) of every service call the binding started."""
    return [
        (call.args[0], call.args[1], call.args[2])
        for call in binding.hass.services.async_call.call_args_list
    ]


@pytest.mark.parametrize(
    ("domain", "service"), [("script", "toggle"), ("scene", "turn_on")]
)
@pytest.mark.parametrize(
    ("gesture", "overrides"),
    [
        ("short", {CONF_CLICK_TARGET: "{entity}"}),
        ("double", {CONF_DOUBLE_TARGET: "{entity}"}),
        ("hold", {CONF_HOLD_ACTION: HOLD_TOGGLE, CONF_HOLD_TARGET: "{entity}"}),
    ],
)
def test_a_scene_is_run_and_a_script_is_toggled(
    monkeypatch, domain: str, service: str, gesture: str, overrides: dict
) -> None:
    """A scene has no ``toggle``; a script is toggled, so a second press stops it."""
    entity = f"{domain}.evening"
    binding, _i, _w = _binding(
        monkeypatch,
        **{key: value.format(entity=entity) for key, value in overrides.items()},
    )
    binding.hass.states.get.return_value = SimpleNamespace(state="off", attributes={})
    action = {
        "short": _action(ACTION_PRESS, presses=1),
        "double": _action(ACTION_PRESS, presses=2),
        "hold": _action(ACTION_HOLD),
    }[gesture]

    binding._handle_action(action)

    assert _service_calls(binding) == [(domain, service, {"entity_id": entity})]


@pytest.mark.parametrize(
    ("click", "service"),
    [("toggle", "toggle"), ("on", "turn_on"), ("off", "turn_off")],
)
def test_a_script_short_press_follows_the_stored_click_action(
    monkeypatch, click: str, service: str
) -> None:
    binding, _i, _w = _binding(
        monkeypatch, click_action=click, **{CONF_CLICK_TARGET: "script.go"}
    )

    binding._handle_action(_action(ACTION_PRESS, presses=1))

    [(domain, called, data)] = _service_calls(binding)
    assert (domain, called) == ("script", service)
    assert data["entity_id"] == "script.go"
    # Only "run" can tell the script what started it; toggle and stop cannot.
    assert ("variables" in data) is (service == "turn_on")


@pytest.mark.parametrize("click", ["toggle", "on"])
def test_a_scene_short_press_is_always_run(monkeypatch, click: str) -> None:
    binding, _i, _w = _binding(
        monkeypatch, click_action=click, **{CONF_CLICK_TARGET: "scene.go"}
    )

    binding._handle_action(_action(ACTION_PRESS, presses=1))

    assert _service_calls(binding) == [("scene", "turn_on", {"entity_id": "scene.go"})]


def test_a_light_target_still_goes_through_homeassistant(monkeypatch) -> None:
    binding, _i, _w = _binding(monkeypatch, **{CONF_DOUBLE_TARGET: "light.other"})

    binding._handle_action(_action(ACTION_PRESS, presses=2))

    assert _service_calls(binding) == [
        ("homeassistant", "toggle", {"entity_id": "light.other"})
    ]


def test_a_scene_never_activated_still_runs(monkeypatch) -> None:
    """A fresh scene reports ``unknown``; that is no reason to skip it."""
    binding, _i, _w = _binding(monkeypatch, **{CONF_DOUBLE_TARGET: "scene.fresh"})
    binding.hass.states.get.return_value = SimpleNamespace(
        state="unknown", attributes={}
    )

    binding._handle_action(_action(ACTION_PRESS, presses=2))

    assert _service_calls(binding) == [
        ("scene", "turn_on", {"entity_id": "scene.fresh"})
    ]


def test_an_unavailable_scene_or_missing_script_is_skipped(monkeypatch) -> None:
    binding, _i, _w = _binding(monkeypatch, **{CONF_DOUBLE_TARGET: "scene.gone"})
    binding.hass.states.get.return_value = SimpleNamespace(
        state="unavailable", attributes={}
    )
    binding._handle_action(_action(ACTION_PRESS, presses=2))

    binding.hass.states.get.return_value = None
    binding._handle_action(_action(ACTION_PRESS, presses=2))

    assert _service_calls(binding) == []


def test_scene_cycling_runs_a_scene_that_was_never_activated(monkeypatch) -> None:
    binding, _i, _w = _binding(
        monkeypatch, scenes=["scene.a", "scene.b"], click_action="toggle"
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="unknown", attributes={}
    )

    binding._handle_action(_action(ACTION_PRESS, presses=1))
    binding._handle_action(_action(ACTION_PRESS, presses=1))

    assert [call[2]["entity_id"] for call in _service_calls(binding)] == [
        "scene.a",
        "scene.b",
    ]


@pytest.mark.parametrize(
    ("entity", "named"),
    [("scene.go", "run"), ("script.go", "toggle"), ("light.other", "toggle")],
)
def test_the_live_activity_names_what_a_press_did(
    monkeypatch, entity: str, named: str
) -> None:
    """A scene is shown as run, not as "turned on"."""
    binding, _i, _w = _binding(monkeypatch, **{CONF_DOUBLE_TARGET: entity})
    binding._report_activity = Mock()

    binding._handle_action(_action(ACTION_PRESS, presses=2))

    pending = [
        call
        for call in binding._report_activity.call_args_list
        if call.args[0] == "pending"
    ]
    assert pending[0].kwargs["result"] == {
        "kind": "entity_action",
        "action": named,
        "target": entity,
    }


# -- one action per gesture --------------------------------------------------

_PRESS_GESTURES = {
    "double_press": (CONF_DOUBLE_TARGET, "double_press_action", 2),
    "triple_press": (CONF_TRIPLE_TARGET, "triple_press_action", 3),
}


def _press(binding, gesture: str) -> None:
    if gesture == "hold":
        binding._handle_action(_action(ACTION_HOLD))
    else:
        presses = {"short_press": 1, "double_press": 2, "triple_press": 3}[gesture]
        binding._handle_action(_action(ACTION_PRESS, presses=presses))


def _gesture_binding(monkeypatch, gesture: str, target: str, action: str | None):
    """A binding whose one gesture acts on ``target`` with ``action``."""
    if gesture == "short_press":
        overrides = {CONF_CLICK_TARGET: target, "click_action": action or "toggle"}
    elif gesture == "hold":
        overrides = {
            CONF_HOLD_ACTION: HOLD_TOGGLE,
            CONF_HOLD_TARGET: target,
            **({"hold_target_action": action} if action else {}),
        }
    else:
        target_key, action_key, _presses = _PRESS_GESTURES[gesture]
        overrides = {target_key: target, **({action_key: action} if action else {})}
    binding, _i, _w = _binding(monkeypatch, **overrides)
    binding.hass.states.get.return_value = SimpleNamespace(state="off", attributes={})
    return binding


@pytest.mark.parametrize(
    "gesture", ["short_press", "double_press", "triple_press", "hold"]
)
@pytest.mark.parametrize(
    ("action", "domain", "service"),
    [
        ("toggle", "homeassistant", "toggle"),
        ("on", "homeassistant", "turn_on"),
        ("off", "homeassistant", "turn_off"),
    ],
)
def test_every_gesture_can_toggle_turn_on_or_turn_off_a_light(
    monkeypatch, gesture: str, action: str, domain: str, service: str
) -> None:
    binding = _gesture_binding(monkeypatch, gesture, "switch.fan", action)

    _press(binding, gesture)

    assert _service_calls(binding) == [(domain, service, {"entity_id": "switch.fan"})]


@pytest.mark.parametrize(
    "gesture", ["short_press", "double_press", "triple_press", "hold"]
)
@pytest.mark.parametrize(
    ("action", "service"),
    [("toggle", "toggle"), ("on", "turn_on"), ("off", "turn_off")],
)
def test_every_gesture_can_run_stop_or_toggle_a_script(
    monkeypatch, gesture: str, action: str, service: str
) -> None:
    binding = _gesture_binding(monkeypatch, gesture, "script.go", action)

    _press(binding, gesture)

    [(domain, called, data)] = _service_calls(binding)
    assert (domain, called) == ("script", service)
    assert data["entity_id"] == "script.go"
    assert ("variables" in data) is (action == "on")


@pytest.mark.parametrize("gesture", ["double_press", "triple_press", "hold"])
def test_a_gesture_stored_without_an_action_still_toggles(
    monkeypatch, gesture: str
) -> None:
    """Bindings saved before the choice existed toggled their target."""
    binding = _gesture_binding(monkeypatch, gesture, "script.go", None)

    _press(binding, gesture)

    assert _service_calls(binding) == [("script", "toggle", {"entity_id": "script.go"})]


@pytest.mark.parametrize(
    "gesture", ["short_press", "double_press", "triple_press", "hold"]
)
def test_a_scene_is_run_whether_the_action_is_toggle_or_on(
    monkeypatch, gesture: str
) -> None:
    for action in ("toggle", "on"):
        binding = _gesture_binding(monkeypatch, gesture, "scene.evening", action)
        _press(binding, gesture)
        assert _service_calls(binding) == [
            ("scene", "turn_on", {"entity_id": "scene.evening"})
        ]


@pytest.mark.parametrize(
    "gesture", ["short_press", "double_press", "triple_press", "hold"]
)
def test_a_scene_cannot_be_turned_off_and_nothing_is_sent(
    monkeypatch, gesture: str
) -> None:
    """Data that predates the check is skipped, not sent to a missing service."""
    binding = _gesture_binding(monkeypatch, gesture, "scene.evening", "off")
    binding._report_activity = Mock()

    _press(binding, gesture)

    assert _service_calls(binding) == []
    assert binding._report_activity.call_args.args[0] == "skipped"
    assert binding._report_activity.call_args.kwargs["reason"] == "action_not_supported"


@pytest.mark.parametrize(
    ("gesture", "presses"),
    [("short_press", 1), ("double_press", 2), ("triple_press", 3), ("hold", 0)],
)
def test_a_script_is_told_which_gesture_started_it(
    monkeypatch, gesture: str, presses: int
) -> None:
    binding = _gesture_binding(monkeypatch, gesture, "script.go", "on")

    _press(binding, gesture)

    [(_domain, _service, data)] = _service_calls(binding)
    assert data["variables"] == {
        "gesture": gesture,
        "presses": presses,
        "channel": 1,
        "endpoint": None,
        "device": "Test wheel",
    }


@pytest.mark.parametrize(
    ("action", "named"),
    [("on", "run"), ("off", "stop"), ("toggle", "toggle")],
)
def test_the_live_activity_names_a_script_press(
    monkeypatch, action: str, named: str
) -> None:
    binding = _gesture_binding(monkeypatch, "double_press", "script.go", action)
    binding._report_activity = Mock()

    _press(binding, "double_press")

    pending = [
        call
        for call in binding._report_activity.call_args_list
        if call.args[0] == "pending"
    ]
    assert pending[0].kwargs["result"]["action"] == named


@pytest.mark.parametrize(
    ("response", "raw_events"),
    [
        (BUTTON_RESPONSE_FAST, ["short_release"]),
        (BUTTON_RESPONSE_INSTANT, ["initial_press"]),
    ],
)
def test_a_script_started_by_an_early_press_is_told_the_device_name(
    monkeypatch, response: str, raw_events: list[str]
) -> None:
    """Fast and Instant run before the engine has named the wheel."""
    binding, _i, _w = _binding(
        monkeypatch,
        **{
            CONF_BUTTON_RESPONSE: response,
            CONF_CLICK_TARGET: "script.go",
            "click_action": "on",
            CONF_HOLD_ACTION: HOLD_NONE,
        },
    )
    binding._device_name = lambda: "Living room wheel"
    binding.hass.states.get.return_value = SimpleNamespace(state="off", attributes={})

    for event in raw_events:
        binding._handle_raw_button(event)

    [(_domain, _service, data)] = _service_calls(binding)
    assert data["variables"]["device"] == "Living room wheel"
    assert data["variables"]["gesture"] == "short_press"
    assert data["variables"]["presses"] == 1


def test_a_completed_press_names_the_device_from_its_own_action(monkeypatch) -> None:
    binding, _i, _w = _binding(
        monkeypatch, **{CONF_DOUBLE_TARGET: "script.go", "double_press_action": "on"}
    )
    binding._device_name = lambda: "Another name"
    binding.hass.states.get.return_value = SimpleNamespace(state="off", attributes={})

    binding._handle_action(_action(ACTION_PRESS, presses=2))

    [(_domain, _service, data)] = _service_calls(binding)
    assert data["variables"]["device"] == "Test wheel"


# -- verbs by kind of target -------------------------------------------------

_STATELESS_VERBS = [
    ("media_player.sonos", "play_pause", "media_player", "media_play_pause"),
    ("media_player.sonos", "play", "media_player", "media_play"),
    ("media_player.sonos", "pause", "media_player", "media_pause"),
    ("media_player.sonos", "stop", "media_player", "media_stop"),
    ("media_player.sonos", "next", "media_player", "media_next_track"),
    ("media_player.sonos", "previous", "media_player", "media_previous_track"),
    ("media_player.sonos", "volume_up", "media_player", "volume_up"),
    ("media_player.sonos", "volume_down", "media_player", "volume_down"),
    ("media_player.sonos", "toggle", "homeassistant", "toggle"),
    ("cover.blind", "toggle", "cover", "toggle"),
    ("cover.blind", "open", "cover", "open_cover"),
    ("cover.blind", "close", "cover", "close_cover"),
    ("cover.blind", "stop", "cover", "stop_cover"),
    ("lock.door", "lock", "lock", "lock"),
    ("vacuum.robot", "start", "vacuum", "start"),
    ("vacuum.robot", "pause", "vacuum", "pause"),
    ("vacuum.robot", "stop", "vacuum", "stop"),
    ("vacuum.robot", "return_home", "vacuum", "return_to_base"),
    ("vacuum.robot", "locate", "vacuum", "locate"),
    ("valve.water", "close", "valve", "close_valve"),
    ("valve.water", "stop", "valve", "stop_valve"),
    ("siren.alarm", "off", "siren", "turn_off"),
    ("button.doorbell", "press", "button", "press"),
    ("input_button.go", "press", "input_button", "press"),
    ("automation.night", "trigger", "automation", "trigger"),
    ("fan.bedroom", "speed_up", "fan", "increase_speed"),
    ("fan.bedroom", "speed_down", "fan", "decrease_speed"),
    ("input_select.mode", "next_option", "input_select", "select_next"),
    ("input_select.mode", "previous_option", "input_select", "select_previous"),
    ("input_select.mode", "first_option", "input_select", "select_first"),
    ("input_select.mode", "last_option", "input_select", "select_last"),
    ("select.mode", "next_option", "select", "select_next"),
    ("input_number.level", "step_up", "input_number", "increment"),
    ("input_number.level", "step_down", "input_number", "decrement"),
]


@pytest.mark.parametrize(
    "gesture", ["short_press", "double_press", "triple_press", "hold"]
)
@pytest.mark.parametrize(
    ("entity", "verb", "domain", "service"),
    _STATELESS_VERBS,
    ids=[f"{e}-{v}" for e, v, _d, _s in _STATELESS_VERBS],
)
def test_every_gesture_can_carry_out_a_verb_of_its_kind_of_target(
    monkeypatch, gesture: str, entity: str, verb: str, domain: str, service: str
) -> None:
    binding = _gesture_binding(monkeypatch, gesture, entity, verb)

    _press(binding, gesture)

    assert _service_calls(binding) == [(domain, service, {"entity_id": entity})]


@pytest.mark.parametrize(("muted", "asked"), [(False, True), (True, False)])
def test_mute_asks_for_the_opposite_of_what_the_player_is_now(
    monkeypatch, muted: bool, asked: bool
) -> None:
    binding = _gesture_binding(
        monkeypatch, "double_press", "media_player.tv", "mute_toggle"
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="playing", attributes={"is_volume_muted": muted}
    )

    _press(binding, "double_press")

    assert _service_calls(binding) == [
        (
            "media_player",
            "volume_mute",
            {"entity_id": "media_player.tv", "is_volume_muted": asked},
        )
    ]


@pytest.mark.parametrize(
    "attributes", [{}, {"is_volume_muted": None}, {"is_volume_muted": "no"}]
)
def test_mute_is_skipped_when_the_player_does_not_say_whether_it_is_muted(
    monkeypatch, attributes: dict
) -> None:
    """A mute toggled the wrong way is worse than a press that did nothing."""
    binding = _gesture_binding(
        monkeypatch, "double_press", "media_player.tv", "mute_toggle"
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="off", attributes=attributes
    )
    binding._report_activity = Mock()

    _press(binding, "double_press")

    assert _service_calls(binding) == []
    assert binding._report_activity.call_args_list[-1].kwargs["reason"] == (
        "state_not_readable"
    )


def test_a_verb_the_target_does_not_have_is_skipped(monkeypatch) -> None:
    """Stored data can predate a check; the runtime must not guess a service."""
    binding = _gesture_binding(monkeypatch, "double_press", "lock.door", "play_pause")
    binding._report_activity = Mock()

    _press(binding, "double_press")

    assert _service_calls(binding) == []
    assert binding._report_activity.call_args_list[-1].kwargs["reason"] == (
        "action_not_supported"
    )


@pytest.mark.parametrize(
    ("entity", "verb"),
    [("lock.door", "toggle"), ("lock.door", "off"), ("siren.alarm", "on")],
)
def test_nothing_unlocks_or_sounds_through_the_switchable_words(
    monkeypatch, entity: str, verb: str
) -> None:
    """One stray press must not open a door or sound a siren."""
    binding = _gesture_binding(monkeypatch, "short_press", entity, verb)

    _press(binding, "short_press")

    assert _service_calls(binding) == []


def test_a_button_that_was_never_pressed_still_acts_though_its_state_is_unknown(
    monkeypatch,
) -> None:
    binding = _gesture_binding(monkeypatch, "double_press", "button.doorbell", "press")
    binding.hass.states.get.return_value = SimpleNamespace(
        state="unknown", attributes={}
    )

    _press(binding, "double_press")

    assert _service_calls(binding) == [
        ("button", "press", {"entity_id": "button.doorbell"})
    ]


def test_an_unavailable_target_is_skipped_whatever_the_verb(monkeypatch) -> None:
    binding = _gesture_binding(
        monkeypatch, "double_press", "media_player.tv", "play_pause"
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="unavailable", attributes={}
    )

    _press(binding, "double_press")

    assert _service_calls(binding) == []


@pytest.mark.parametrize(
    ("entity", "verb", "named"),
    [
        ("media_player.tv", "play_pause", "play_pause"),
        ("vacuum.robot", "return_home", "return_home"),
        ("media_player.tv", "toggle", "toggle"),
    ],
)
def test_the_live_activity_names_a_verb_after_the_verb(
    monkeypatch, entity: str, verb: str, named: str
) -> None:
    binding = _gesture_binding(monkeypatch, "double_press", entity, verb)
    binding._report_activity = Mock()

    _press(binding, "double_press")

    pending = [
        call
        for call in binding._report_activity.call_args_list
        if call.args and call.args[0] == "pending"
    ]
    assert pending[0].kwargs["result"]["action"] == named


# -- action sequences --------------------------------------------------------

_PLAY_PAUSE = [
    {
        "action": "media_player.media_play_pause",
        "target": {"entity_id": "media_player.tv"},
    }
]


class _FakeScript:
    """Stands in for Home Assistant's Script: records what it was asked."""

    built: list[_FakeScript] = []

    def __init__(self, hass, sequence, name, domain, **options) -> None:
        self.sequence, self.name, self.options = sequence, name, options
        self.runs: list[tuple[dict, object]] = []
        self.stopped = False
        targets = [step.get("target", {}) for step in sequence]
        self.referenced_entities = {t["entity_id"] for t in targets if "entity_id" in t}
        self.referenced_areas = {t["area_id"] for t in targets if "area_id" in t}
        self.referenced_devices = self.referenced_floors = set()
        self.referenced_labels = set()
        _FakeScript.built.append(self)

    async def async_run(self, run_variables=None, context=None):
        self.runs.append((run_variables, context))

    async def async_stop(self):
        self.stopped = True


def _sequence_binding(monkeypatch, gesture: str, sequence=None, **extra):
    """A binding whose one gesture is set to run ``sequence``; coroutines it
    schedules are collected so a test can run them."""
    _FakeScript.built = []
    validated = []

    async def _validate(hass, actions):
        validated.append(actions)
        return actions

    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_validate_actions_config",
        _validate,
    )
    monkeypatch.setattr("custom_components.ikea_bilresa.binding.Script", _FakeScript)
    sequence = _PLAY_PAUSE if sequence is None else sequence
    overrides = {
        "short_press": {"click_action": "run", "click_sequence": sequence},
        "double_press": {
            "double_press_action": "run",
            "double_press_sequence": sequence,
        },
        "triple_press": {
            "triple_press_action": "run",
            "triple_press_sequence": sequence,
        },
        "hold": {"hold_action": "run", "hold_sequence": sequence},
    }[gesture]
    binding, _i, _w = _binding(monkeypatch, **overrides, **extra)
    binding.validated = validated
    binding.pending = []
    binding.hass.async_create_task = Mock(side_effect=binding.pending.append)
    binding._report_activity = Mock()
    return binding


def _drain(binding) -> None:
    """Run every coroutine the binding handed to Home Assistant, in order."""
    import asyncio

    async def _run() -> None:
        while binding.pending:
            await binding.pending.pop(0)

    asyncio.run(_run())


def _statuses(binding) -> list[str]:
    return [call.args[0] for call in binding._report_activity.call_args_list]


@pytest.mark.parametrize(
    ("gesture", "presses"),
    [("short_press", 1), ("double_press", 2), ("triple_press", 3), ("hold", 0)],
)
def test_a_gesture_set_to_run_runs_its_sequence_with_the_gesture_in_it(
    monkeypatch, gesture: str, presses: int
) -> None:
    binding = _sequence_binding(monkeypatch, gesture)

    _press(binding, gesture)
    _drain(binding)

    [script] = _FakeScript.built
    assert script.sequence == _PLAY_PAUSE
    [(variables, context)] = script.runs
    assert variables["gesture"] == gesture
    assert variables["channel"] == 1
    assert variables["device"] == "Test wheel"
    assert context is not None
    assert _statuses(binding) == ["pending", "accepted"]


def test_runs_are_queued_so_two_quick_presses_keep_their_order(monkeypatch) -> None:
    from custom_components.ikea_bilresa.binding import SCRIPT_MODE_QUEUED

    binding = _sequence_binding(monkeypatch, "double_press")

    _press(binding, "double_press")
    _press(binding, "double_press")
    _drain(binding)

    [script] = _FakeScript.built  # built once, run twice
    assert len(script.runs) == 2
    assert script.options["script_mode"] == SCRIPT_MODE_QUEUED
    assert script.options["max_runs"] == 5
    assert len(binding.validated) == 1


def test_a_sequence_that_no_longer_validates_is_reported_not_raised(
    monkeypatch,
) -> None:
    import voluptuous as vol

    binding = _sequence_binding(monkeypatch, "double_press")

    async def _broken(hass, actions):
        raise vol.Invalid("the integration was removed")

    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_validate_actions_config", _broken
    )

    _press(binding, "double_press")
    _drain(binding)

    assert _FakeScript.built == []
    last = binding._report_activity.call_args_list[-1]
    assert last.args[0] == "failed"
    assert last.kwargs["reason"] == "invalid_actions"


def test_a_gesture_set_to_run_with_no_sequence_is_skipped(monkeypatch) -> None:
    binding = _sequence_binding(monkeypatch, "double_press")
    binding._sequences.clear()

    _press(binding, "double_press")

    assert binding.pending == []
    last = binding._report_activity.call_args_list[-1]
    assert (last.args[0], last.kwargs["reason"]) == ("skipped", "actions_missing")


def test_unloading_the_binding_stops_what_its_sequences_still_do(monkeypatch) -> None:
    binding = _sequence_binding(monkeypatch, "double_press")
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_dispatcher_connect",
        lambda *_args: Mock(),
    )
    unsubscribe = binding.async_attach()
    _press(binding, "double_press")
    _drain(binding)

    unsubscribe()
    _drain(binding)

    [script] = _FakeScript.built
    assert script.stopped


def test_a_sequence_on_a_double_press_rules_out_the_instant_response(
    monkeypatch,
) -> None:
    binding = _sequence_binding(
        monkeypatch,
        "double_press",
        button_response="instant",
        hold_action="none",
    )

    assert binding._instant_single is False


def test_two_quick_first_presses_share_one_script_so_their_runs_queue(
    monkeypatch,
) -> None:
    """Both would build a script while the first awaits its validation."""
    import asyncio

    binding = _sequence_binding(monkeypatch, "double_press")

    async def _slow_validate(hass, actions):
        await asyncio.sleep(0)
        return actions

    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_validate_actions_config",
        _slow_validate,
    )
    _press(binding, "double_press")
    _press(binding, "double_press")

    async def _both() -> None:
        first, second = binding.pending
        binding.pending.clear()
        await asyncio.gather(first, second)

    asyncio.run(_both())
    _drain(binding)

    [script] = _FakeScript.built
    assert len(script.runs) == 2


def test_nothing_starts_after_the_binding_was_unloaded_during_a_build(
    monkeypatch,
) -> None:
    binding = _sequence_binding(monkeypatch, "double_press")
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_dispatcher_connect",
        lambda *_args: Mock(),
    )
    unsubscribe = binding.async_attach()
    _press(binding, "double_press")

    unsubscribe()
    _drain(binding)

    assert all(not script.runs for script in _FakeScript.built)


# -- multi-light bindings ------------------------------------------------------
#
# One binding, several lights. The binding reads the lights only when it has
# nothing tracked, then keeps one brightness and sends that same value to every
# light. A light that acknowledges late is catching up, not changing anything.

_LIGHTS = ["light.left", "light.middle", "light.right"]


def _lights_binding(monkeypatch, levels: dict[str, Any], **overrides):
    """A multi-light binding over real-looking per-entity states."""
    binding, interval_unsub, watchdog_unsub = _binding(
        monkeypatch,
        **{
            CONF_TARGET: list(levels),
            CONF_TRANSITION: 0.0,
            CONF_STEP: 3,
            CONF_ACCELERATION: 0,
            CONF_HOLD_ACTION: HOLD_NONE,
            **overrides,
        },
    )
    del binding._rotate_by  # the real rotation path, not the helper's mock
    states: dict[str, Any] = {}

    def _set(entity_id: str, level: Any) -> SimpleNamespace:
        if isinstance(level, tuple):
            state = SimpleNamespace(
                entity_id=entity_id, state=level[0], attributes=dict(level[1])
            )
        elif isinstance(level, dict):
            state = SimpleNamespace(
                entity_id=entity_id, state="on", attributes=dict(level)
            )
        elif level is None or isinstance(level, str):
            state = SimpleNamespace(
                entity_id=entity_id, state=level or "off", attributes={}
            )
        else:
            state = SimpleNamespace(
                entity_id=entity_id, state="on", attributes={"brightness": level}
            )
        states[entity_id] = state
        return state

    for entity_id, level in levels.items():
        _set(entity_id, level)
    binding.hass.states.get = Mock(side_effect=states.get)
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )

    def report(entity_id: str, level: Any) -> None:
        state = _set(entity_id, level)
        binding._handle_target_state_change(
            SimpleNamespace(data={"entity_id": entity_id, "new_state": state})
        )

    return binding, now, report


def _last_payload(binding: LightBinding) -> dict[str, Any]:
    return binding.hass.services.async_call.call_args.args[2]


def test_one_scroll_sends_one_value_to_every_light(monkeypatch) -> None:
    binding, _now, _report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))

    binding._rotate_by(1, False)

    payload = _last_payload(binding)
    assert payload["entity_id"] == _LIGHTS
    assert payload["brightness"] == round(200 - 7.65)
    assert binding.hass.services.async_call.call_count == 1


def test_lights_at_different_levels_start_from_their_mean(monkeypatch) -> None:
    """Like a light group: the lit lights' mean, and the dark one joins in."""
    binding, _now, _report = _lights_binding(
        monkeypatch, {"light.left": 100, "light.middle": 200, "light.right": None}
    )

    binding._rotate_by(1, True)

    payload = _last_payload(binding)
    assert payload["entity_id"] == ["light.left", "light.middle", "light.right"]
    assert payload["brightness"] == round(150 + 7.65)


def test_a_lagging_light_does_not_make_the_next_gesture_jump(monkeypatch) -> None:
    """The reported multi-light jump, end to end.

    Three lights are scrolled down together. Two acknowledge promptly; the
    third reports a level from the middle of its fade only after the scroll
    and its transition window are long over. The next gesture must continue
    from the brightness the binding sent, not restart from that bulb.
    """
    binding, now, report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 255))

    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    for notch in range(10):
        now[0] = notch * 0.2
        binding._rotate_by(1, False)
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "multi_press_complete", 2)
    sent = round(255 - 10 * 7.65)
    assert _last_payload(binding)["brightness"] == sent

    now[0] = 2.5
    report("light.left", sent)
    report("light.middle", sent)
    # Well after the scroll and its transition: the slow bulb, still fading.
    now[0] = 6.0
    report("light.right", 214)
    assert binding._tracked == pytest.approx(255 - 10 * 7.65)

    # Long enough that a single-target binding would re-read the light.
    now[0] = 12.0
    binding._rotate_by(1, False)

    assert _last_payload(binding)["brightness"] == round(255 - 11 * 7.65)


def test_the_tracked_level_outlives_an_idle_pause(monkeypatch) -> None:
    """With several lights, brightness is not re-read just because time passed."""
    binding, now, _report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._rotate_by(1, False)
    tracked = binding._tracked

    # Every light still claims the old level, as stale state would.
    now[0] = 20.0
    binding._rotate_by(1, False)

    assert _last_payload(binding)["brightness"] == round(tracked - 7.65)


def test_the_tracked_level_does_not_outlive_a_long_pause(monkeypatch) -> None:
    """After half a minute nothing vouches for it, so the lights are read again."""
    binding, now, _report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._rotate_by(1, False)

    now[0] = 60.0
    binding._rotate_by(1, False)

    # The lights still report 200: read again, not 7.65 below the tracked 192.
    assert _last_payload(binding)["brightness"] == round(200 - 7.65)


def test_a_light_changed_elsewhere_still_takes_over(monkeypatch) -> None:
    """A light that settles off its own path was changed by someone else."""
    binding, now, report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._rotate_by(1, False)

    now[0] = 5.0
    report("light.left", 30)
    assert binding._tracked is None

    now[0] = 6.0
    binding._rotate_by(1, False)
    # The next read is the group mean (143) of the three, one of them now at 30.
    assert _last_payload(binding)["brightness"] == round(143 - 7.65)


def test_switching_the_lights_off_elsewhere_is_honoured(monkeypatch) -> None:
    binding, now, report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._rotate_by(1, False)

    now[0] = 5.0
    for entity_id in _LIGHTS:
        report(entity_id, None)

    assert binding._tracked is None
    binding._rotate_by(1, False)
    # Scrolling down does not switch dark lights on.
    assert binding.hass.services.async_call.call_count == 1


def test_an_unavailable_light_is_left_out_without_a_jump(monkeypatch) -> None:
    binding, now, report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._rotate_by(1, False)
    tracked = binding._tracked

    now[0] = 1.0
    report("light.middle", "unavailable")
    assert binding._tracked == tracked

    binding._rotate_by(1, False)
    payload = _last_payload(binding)
    assert payload["entity_id"] == ["light.left", "light.right"]
    assert payload["brightness"] == round(tracked - 7.65)

    # It comes back at whatever level it had: the next command realigns it
    # instead of the binding resyncing everything to it.
    now[0] = 2.0
    report("light.middle", 255)
    binding._rotate_by(1, False)
    payload = _last_payload(binding)
    assert payload["entity_id"] == _LIGHTS
    assert payload["brightness"] == round(tracked - 2 * 7.65)


def test_every_light_unavailable_stops_the_binding(monkeypatch) -> None:
    binding, now, report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._rotate_by(1, False)

    for entity_id in _LIGHTS:
        report(entity_id, "unavailable")

    assert binding._tracked is None
    assert binding._rotate_by(1, False) is False
    assert binding.hass.services.async_call.call_count == 1


def test_a_short_press_switches_the_lights_as_one(monkeypatch) -> None:
    """Toggle must not invert a mixed set: any light on means all go off."""
    binding, _now, report = _lights_binding(
        monkeypatch, {"light.left": 120, "light.middle": None, "light.right": None}
    )

    binding._single_press()
    domain, service, payload = binding.hass.services.async_call.call_args.args[:3]
    assert (domain, service) == ("homeassistant", "turn_off")
    assert payload["entity_id"] == _LIGHTS

    report("light.left", None)
    binding._single_press()
    domain, service, payload = binding.hass.services.async_call.call_args.args[:3]
    assert (domain, service) == ("homeassistant", "turn_on")
    assert payload["entity_id"] == _LIGHTS


def test_an_explicit_click_target_is_still_used_alone(monkeypatch) -> None:
    binding, _now, _report = _lights_binding(
        monkeypatch,
        dict.fromkeys(_LIGHTS, 200),
        **{CONF_CLICK_TARGET: "light.left"},
    )

    binding._single_press()
    assert binding.hass.services.async_call.call_count == 1

    _domain, service, payload = binding.hass.services.async_call.call_args.args[:3]
    assert service == "toggle"
    assert payload["entity_id"] == "light.left"


def test_several_targets_outside_a_light_mode_are_disabled(monkeypatch) -> None:
    binding, _i, _w = _binding(
        monkeypatch,
        **{CONF_TARGET: ["cover.a", "cover.b"], CONF_MODE: MODE_COVER},
    )

    assert binding._mode_target_valid is False


def test_a_single_target_list_behaves_like_the_string(monkeypatch) -> None:
    """A one-entity list is the historic binding, including its payload."""
    binding, _now, _report = _lights_binding(monkeypatch, {"light.left": 200})

    binding._rotate_by(1, False)

    assert binding._multi is False
    assert _last_payload(binding)["entity_id"] == "light.left"


def test_a_multi_light_trace_describes_every_light(monkeypatch) -> None:
    binding, _now, _report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))

    config = binding.trace_config()

    assert config["target"] == "light.left"
    assert config["targets"] == _LIGHTS


def _press_once(binding: LightBinding) -> None:
    binding._handle_action(_action(ACTION_PRESS, presses=1))


def test_a_short_press_that_switches_the_lights_off_resets_the_level(
    monkeypatch,
) -> None:
    """The next scroll down must not relight what the press switched off."""
    binding, now, report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_by(1, False)
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "multi_press_complete", 2)

    now[0] = 0.4  # inside the scroll-authority grace
    _press_once(binding)
    assert binding._tracked is None
    for entity_id in _LIGHTS:
        report(entity_id, None)  # off, reported while the scroll still owns it

    calls = binding.hass.services.async_call.call_count
    now[0] = 5.0
    binding._rotate_by(1, False)

    assert binding.hass.services.async_call.call_count == calls


def test_every_light_going_off_is_honoured_inside_the_scroll_window(
    monkeypatch,
) -> None:
    binding, now, report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_by(1, False)

    now[0] = 0.2
    for entity_id in _LIGHTS:
        report(entity_id, None)

    assert binding._tracked is None


def _colour_lights(monkeypatch, hues: dict[str, tuple[float, float]], **overrides):
    return _lights_binding(
        monkeypatch,
        {entity_id: {"hs_color": list(colour)} for entity_id, colour in hues.items()},
        **{CONF_MODE: MODE_COLOR, CONF_STEP: 10, **overrides},
    )


def test_a_hue_between_the_last_report_and_the_command_is_catching_up(
    monkeypatch,
) -> None:
    binding, now, report = _colour_lights(
        monkeypatch, {"light.a": (0.0, 80.0), "light.b": (0.0, 80.0)}
    )
    binding._rotate_by(1, True)  # sends hue 36 to both
    assert binding._tracked == pytest.approx(36.0)

    now[0] = 6.0  # past the transition and the scroll window
    report("light.a", {"hs_color": [18.0, 80.0]})

    assert binding._tracked == pytest.approx(36.0)


def test_a_hue_off_the_path_still_counts_as_an_outside_change(monkeypatch) -> None:
    binding, now, report = _colour_lights(
        monkeypatch, {"light.a": (0.0, 80.0), "light.b": (0.0, 80.0)}
    )
    binding._rotate_by(1, True)

    now[0] = 6.0
    report("light.a", {"hs_color": [200.0, 80.0]})

    assert binding._tracked is None


def test_a_hue_across_the_wrap_is_on_the_path(monkeypatch) -> None:
    binding, now, report = _colour_lights(
        monkeypatch, {"light.a": (350.0, 80.0), "light.b": (350.0, 80.0)}
    )
    binding._rotate_by(1, True)  # 350 -> 26, through 0

    now[0] = 6.0
    report("light.a", {"hs_color": [5.0, 80.0]})

    assert binding._tracked == pytest.approx(26.0)


def test_the_starting_hue_is_the_mean_of_the_lit_lights(monkeypatch) -> None:
    """Not the first light's hue: 350 and 10 average to 0, not to 350 or 180."""
    binding, _now, _report = _colour_lights(
        monkeypatch, {"light.a": (350.0, 40.0), "light.b": (10.0, 80.0)}
    )

    binding._rotate_by(1, True)

    hue, saturation = _last_payload(binding)["hs_color"]
    assert hue == pytest.approx(36.0)  # mean 0 plus one 36-degree notch
    assert saturation == pytest.approx(60.0)


def _kelvin(low: int, high: int, now: int | None = None) -> dict[str, Any]:
    attributes: dict[str, Any] = {
        "min_color_temp_kelvin": low,
        "max_color_temp_kelvin": high,
    }
    if now is not None:
        attributes["color_temp_kelvin"] = now
    return attributes


def test_an_off_light_limits_the_shared_colour_temperature(monkeypatch) -> None:
    binding, _now, _report = _lights_binding(
        monkeypatch,
        {
            "light.a": _kelvin(2700, 6500, 3900),
            "light.b": ("off", _kelvin(2000, 4000)),
        },
        **{CONF_MODE: MODE_COLOR_TEMP, CONF_STEP: 50},
    )

    binding._rotate_by(1, True)

    payload = _last_payload(binding)
    assert payload["entity_id"] == ["light.a", "light.b"]
    assert payload["color_temp_kelvin"] == 4000  # the lower of the two maxima


def test_lights_with_no_colour_temperature_in_common_are_not_commanded(
    monkeypatch, caplog
) -> None:
    binding, _now, _report = _lights_binding(
        monkeypatch,
        {
            "light.a": _kelvin(2000, 3000, 2500),
            "light.b": _kelvin(4000, 6500, 5000),
        },
        **{CONF_MODE: MODE_COLOR_TEMP},
    )

    binding._rotate_by(1, True)

    assert binding.hass.services.async_call.call_count == 0
    assert "no colour temperature in common" in caplog.text


def test_a_light_that_is_off_joins_the_others_at_the_maximum(monkeypatch) -> None:
    """At the limit the value no longer changes, but the dark light must follow."""
    binding, _now, _report = _lights_binding(
        monkeypatch,
        {"light.a": 255, "light.b": None},
        **{CONF_MODE: MODE_BRIGHTNESS},
    )

    binding._rotate_by(1, True)

    payload = _last_payload(binding)
    assert payload["entity_id"] == ["light.a", "light.b"]
    assert payload["brightness"] == 255


def test_lights_all_at_the_maximum_are_not_commanded_again(monkeypatch) -> None:
    binding, _now, _report = _lights_binding(
        monkeypatch, {"light.a": 255, "light.b": 255}
    )

    binding._rotate_by(1, True)

    assert binding.hass.services.async_call.call_count == 0


def test_a_light_unavailable_at_start_does_not_move_the_others(monkeypatch) -> None:
    binding, now, report = _lights_binding(
        monkeypatch, {"light.a": 200, "light.b": "unavailable"}
    )
    binding._seed_rejoining()
    binding._rotate_by(1, False)
    tracked = binding._tracked

    now[0] = 6.0
    report("light.b", 30)  # it wakes up somewhere else entirely

    assert binding._tracked == tracked


def test_attaching_marks_the_lights_that_are_already_unavailable(monkeypatch) -> None:
    binding, _now, _report = _lights_binding(
        monkeypatch, {"light.a": 200, "light.b": "unavailable"}
    )

    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_dispatcher_connect",
        lambda *_args: Mock(),
    )

    unsubscribe = binding.async_attach()

    assert binding._rejoining == {"light.b"}
    unsubscribe()


def test_a_rejected_dispatch_makes_the_next_gesture_read_the_lights(
    monkeypatch,
) -> None:
    binding, _now, _report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._rotate_by(1, False)
    assert binding._tracked is not None

    async def _rejected() -> None:
        raise RuntimeError("rejected")

    asyncio.run(
        binding._async_dispatch_service(
            "light", "turn_on", _rejected(), result={}, action=None
        )
    )

    assert binding._tracked is None


def test_only_the_click_targets_reports_time_the_latency_trace(monkeypatch) -> None:
    binding, _now, report = _lights_binding(
        monkeypatch, dict.fromkeys(_LIGHTS, 200), **{CONF_CLICK_TARGET: "light.right"}
    )
    binding._handle_latency_target_state_change = Mock()

    report("light.left", 200)
    report("light.right", 200)

    assert binding._handle_latency_target_state_change.call_count == 1


def test_a_light_that_is_off_joins_at_the_colour_temperature_limit(
    monkeypatch,
) -> None:
    binding, _now, _report = _lights_binding(
        monkeypatch,
        {
            "light.a": _kelvin(2700, 6500, 6500),
            "light.b": ("off", _kelvin(2700, 6500)),
        },
        **{CONF_MODE: MODE_COLOR_TEMP},
    )

    binding._rotate_by(1, True)

    payload = _last_payload(binding)
    assert payload["entity_id"] == ["light.a", "light.b"]
    assert payload["color_temp_kelvin"] == 6500


def test_late_reports_do_not_drift_the_saturation(monkeypatch) -> None:
    binding, now, report = _colour_lights(
        monkeypatch, {"light.a": (0.0, 80.0), "light.b": (0.0, 40.0)}
    )
    binding._rotate_by(1, True)
    first = _last_payload(binding)["hs_color"][1]
    assert first == pytest.approx(60.0)

    now[0] = 1.0
    report("light.a", {"hs_color": [36.0, 60.0]})  # one acknowledged, one did not
    binding._rotate_by(1, True)

    assert _last_payload(binding)["hs_color"][1] == pytest.approx(60.0)


def test_a_light_without_kelvin_bounds_keeps_the_fallback_range(monkeypatch) -> None:
    binding, _now, _report = _lights_binding(
        monkeypatch,
        {
            "light.a": {"color_temp_kelvin": 5000},
            "light.b": _kelvin(2000, 9000, 5000),
        },
        **{CONF_MODE: MODE_COLOR_TEMP, CONF_STEP: 100},
    )

    binding._rotate_by(1, True)

    from custom_components.ikea_bilresa.binding import FALLBACK_MAX_KELVIN

    assert _last_payload(binding)["color_temp_kelvin"] <= FALLBACK_MAX_KELVIN


def test_a_single_light_press_cancels_a_rotation_still_queued(monkeypatch) -> None:
    """A pending brightness command must not relight a single light after a press."""
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, click_action="off"
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._min_command_interval = 5.0
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 200}
    )

    binding._rotate_brightness(1, up=False)  # dispatched immediately
    now[0] = 0.05
    binding._rotate_brightness(1, up=False)  # waiting to be sent
    assert binding._pending_command is not None

    binding._handle_action(_action(ACTION_PRESS, presses=1))  # turn the light off

    assert _service_calls(binding)[-1][:2] == ("homeassistant", "turn_off")
    assert binding._pending_command is None
    assert binding._tracked is None
    calls_after_press = binding.hass.services.async_call.call_count
    binding._flush_pending_command()
    assert binding.hass.services.async_call.call_count == calls_after_press


def test_a_single_light_sequence_cancels_a_rotation_still_queued(monkeypatch) -> None:
    """A gesture sequence may turn off the light before a queued dim is sent."""
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch,
        click_action="run",
        click_sequence=[
            {"action": "light.turn_off", "target": {"entity_id": "light.test"}}
        ],
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._min_command_interval = 5.0
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 200}
    )
    binding._rotate_brightness(1, up=False)
    now[0] = 0.05
    binding._rotate_brightness(1, up=False)
    assert binding._pending_command is not None

    binding._handle_action(_action(ACTION_PRESS, presses=1))

    assert binding._pending_command is None
    calls_after_press = binding.hass.services.async_call.call_count
    binding._flush_pending_command()
    assert binding.hass.services.async_call.call_count == calls_after_press


def test_unavailable_single_light_press_does_not_cancel_pending_command(
    monkeypatch,
) -> None:
    """A skipped press should not itself discard a pending rotation."""
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, click_action="off"
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._min_command_interval = 5.0
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 200}
    )
    binding._rotate_brightness(1, up=False)
    now[0] = 0.05
    binding._rotate_brightness(1, up=False)
    pending = binding._pending_command
    assert pending is not None

    binding.hass.states.get.return_value = SimpleNamespace(
        state="unavailable", attributes={}
    )
    binding._handle_action(_action(ACTION_PRESS, presses=1))

    assert binding._pending_command == pending
    assert len(_service_calls(binding)) == 1


def test_a_scene_press_cancels_queued_dimming_for_one_light(monkeypatch) -> None:
    """Scene activation may change the rotating light behind a pending dim."""
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, scenes=["scene.night"]
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._min_command_interval = 5.0
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 200}
    )
    binding._rotate_brightness(1, up=False)
    now[0] = 0.05
    binding._rotate_brightness(1, up=False)
    assert binding._pending_command is not None

    binding._handle_action(_action(ACTION_PRESS, presses=1))

    assert _service_calls(binding)[-1][:2] == ("scene", "turn_on")
    assert binding._pending_command is None
    assert binding._tracked is None


def test_play_pause_keeps_queued_volume_change(monkeypatch) -> None:
    """Playback changes neither volume_level nor a queued volume_set."""
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch,
        **{
            CONF_TARGET: "media_player.test",
            CONF_MODE: MODE_VOLUME,
            "click_action": "play_pause",
        },
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._min_command_interval = 5.0
    binding.hass.states.get.return_value = SimpleNamespace(
        state="playing", attributes={"volume_level": 0.5}
    )
    binding._rotate_volume(1, up=True)
    now[0] = 0.05
    binding._rotate_volume(1, up=True)
    pending = binding._pending_command
    tracked = binding._tracked
    assert pending is not None

    binding._handle_action(_action(ACTION_PRESS, presses=1))

    assert _service_calls(binding)[-1][:2] == ("media_player", "media_play_pause")
    assert binding._pending_command == pending
    assert binding._tracked == tracked


def test_missing_action_sequence_does_not_cancel_queued_rotation(monkeypatch) -> None:
    """A missing sequence never dispatches, so it must not erase queued dimming."""
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch, click_action="run"
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._min_command_interval = 5.0
    binding.hass.states.get.return_value = SimpleNamespace(
        state="on", attributes={"brightness": 200}
    )
    binding._rotate_brightness(1, up=False)
    now[0] = 0.05
    binding._rotate_brightness(1, up=False)
    pending = binding._pending_command
    tracked = binding._tracked
    assert pending is not None

    binding._handle_action(_action(ACTION_PRESS, presses=1))

    assert binding._pending_command == pending
    assert binding._tracked == tracked
    assert len(_service_calls(binding)) == 1


@pytest.mark.parametrize(
    ("press_action", "expected_domain", "expected_service", "should_cancel"),
    [
        ("off", "homeassistant", "turn_off", True),
        ("mute_toggle", "media_player", "volume_mute", False),
    ],
)
def test_media_power_off_cancels_but_mute_preserves_queued_volume(
    monkeypatch, press_action, expected_domain, expected_service, should_cancel
) -> None:
    """Power-off invalidates pending volume, but mute does not change its level."""
    binding, _interval_unsub, _watchdog_unsub = _binding(
        monkeypatch,
        **{
            CONF_TARGET: "media_player.test",
            CONF_MODE: MODE_VOLUME,
            "click_action": press_action,
        },
    )
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    binding._min_command_interval = 5.0
    binding.hass.states.get.return_value = SimpleNamespace(
        state="playing",
        attributes={"volume_level": 0.5, "is_volume_muted": False},
    )
    binding._rotate_volume(1, up=True)
    now[0] = 0.05
    binding._rotate_volume(1, up=True)
    pending = binding._pending_command
    tracked = binding._tracked
    assert pending is not None

    binding._handle_action(_action(ACTION_PRESS, presses=1))

    assert _service_calls(binding)[-1][:2] == (expected_domain, expected_service)
    if should_cancel:
        assert binding._pending_command is None
        assert binding._tracked is None
    else:
        assert binding._pending_command == pending
        assert binding._tracked == tracked


# -- two bindings on one light -------------------------------------------------
#
# A press of one binding must also cancel a rotation another binding still has
# queued for the same light, or the older value relights it (issue #63).


def _signal_bus(monkeypatch) -> dict[str, list]:
    """Deliver dispatcher signals between bindings, as Home Assistant does.

    Install it after the bindings are made: ``_binding`` mocks the sender.
    """
    targets: dict[str, list] = {}

    def connect(_hass, signal, target):
        targets.setdefault(signal, []).append(target)
        return lambda: targets[signal].remove(target)

    def send(_hass, signal, *args):
        for target in list(targets.get(signal, [])):
            target(*args)

    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_dispatcher_connect", connect
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_dispatcher_send", send
    )
    return targets


def _clock(monkeypatch) -> list[float]:
    now = [0.0]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.time.monotonic", lambda: now[0]
    )
    return now


def _queue_rotation(binding, now: list[float], rotate: str, state) -> None:
    """Send one rotation at once and queue a second one behind it."""
    binding._min_command_interval = 5.0
    binding.hass.states.get.return_value = state
    getattr(binding, rotate)(1, up=False)
    now[0] += 0.05
    getattr(binding, rotate)(1, up=False)
    assert binding._pending_command is not None


_LIT = SimpleNamespace(state="on", attributes={"brightness": 200})


def test_a_press_of_another_binding_cancels_a_rotation_still_queued(
    monkeypatch,
) -> None:
    """Wheel A dims, wheel B turns the same light off; A must not relight it."""
    now = _clock(monkeypatch)
    dimmer, _i, _w = _binding(monkeypatch)
    switch, _i2, _w2 = _binding(monkeypatch, **{CONF_CHANNEL: 2, "click_action": "off"})
    _signal_bus(monkeypatch)
    dimmer.async_attach()
    switch.async_attach()
    _queue_rotation(dimmer, now, "_rotate_brightness", _LIT)
    switch.hass.states.get.return_value = _LIT

    switch._handle_action(_action(ACTION_PRESS, presses=1))

    assert _service_calls(switch)[-1][:2] == ("homeassistant", "turn_off")
    assert dimmer._pending_command is None
    assert dimmer._tracked is None
    calls = len(_service_calls(dimmer))
    dimmer._flush_pending_command()
    assert len(_service_calls(dimmer)) == calls


@pytest.mark.parametrize(
    ("acted_on", "cancels"), [("light.test", True), ("light.other", False)]
)
def test_actions_of_another_binding_cancel_a_rotation_only_for_their_light(
    monkeypatch, acted_on: str, cancels: bool
) -> None:
    now = _clock(monkeypatch)
    dimmer, _i, _w = _binding(monkeypatch)
    runner = _sequence_binding(
        monkeypatch,
        "short_press",
        [{"action": "light.turn_off", "target": {"entity_id": acted_on}}],
        **{CONF_CHANNEL: 2, CONF_TARGET: "light.elsewhere"},
    )
    _signal_bus(monkeypatch)
    dimmer.async_attach()
    runner.async_attach()
    _queue_rotation(dimmer, now, "_rotate_brightness", _LIT)
    pending = dimmer._pending_command

    _press(runner, "short_press")
    _drain(runner)

    assert _FakeScript.built[0].runs
    assert dimmer._pending_command == (None if cancels else pending)


def test_a_binding_ignores_its_own_signal(monkeypatch) -> None:
    """A press on a group holding the light keeps this binding's queue, as before.

    Only another binding's press cancels through the signal; the binding's own
    presses keep the rules of issue #59.
    """
    now = _clock(monkeypatch)
    binding, _i, _w = _binding(monkeypatch, **{CONF_DOUBLE_TARGET: "light.group"})
    _signal_bus(monkeypatch)
    binding.async_attach()
    _queue_rotation(binding, now, "_rotate_brightness", _LIT)
    pending = binding._pending_command
    group = SimpleNamespace(state="on", attributes={"entity_id": ["light.test"]})
    binding.hass.states.get = Mock(
        side_effect=lambda entity: group if entity == "light.group" else _LIT
    )

    binding._handle_action(_action(ACTION_PRESS, presses=2))

    assert _service_calls(binding)[-1][:2] == ("homeassistant", "toggle")
    assert binding._pending_command == pending


def test_a_press_of_another_binding_on_another_light_keeps_the_queue(
    monkeypatch,
) -> None:
    now = _clock(monkeypatch)
    dimmer, _i, _w = _binding(monkeypatch)
    switch, _i2, _w2 = _binding(
        monkeypatch,
        **{CONF_CHANNEL: 2, CONF_TARGET: "light.other", "click_action": "off"},
    )
    _signal_bus(monkeypatch)
    dimmer.async_attach()
    switch.async_attach()
    _queue_rotation(dimmer, now, "_rotate_brightness", _LIT)
    pending, tracked = dimmer._pending_command, dimmer._tracked
    switch.hass.states.get.return_value = _LIT

    switch._handle_action(_action(ACTION_PRESS, presses=1))

    assert _service_calls(switch)[-1] == (
        "homeassistant",
        "turn_off",
        {"entity_id": "light.other"},
    )
    assert dimmer._pending_command == pending
    assert dimmer._tracked == tracked


def test_a_press_on_a_nested_group_of_the_light_cancels_the_queue(
    monkeypatch,
) -> None:
    now = _clock(monkeypatch)
    dimmer, _i, _w = _binding(monkeypatch)
    switch, _i2, _w2 = _binding(
        monkeypatch,
        **{CONF_CHANNEL: 2, CONF_CLICK_TARGET: "light.house", "click_action": "off"},
    )
    groups = {
        # A group listing itself must not loop.
        "light.house": ["light.house", "light.room"],
        "light.room": ["light.test"],
    }
    switch.hass.states.get = Mock(
        side_effect=lambda entity: SimpleNamespace(
            state="on", attributes={"entity_id": groups.get(entity, [])}
        )
    )
    _signal_bus(monkeypatch)
    dimmer.async_attach()
    switch.async_attach()
    _queue_rotation(dimmer, now, "_rotate_brightness", _LIT)

    switch._handle_action(_action(ACTION_PRESS, presses=1))

    assert _service_calls(switch)[-1][2] == {"entity_id": "light.house"}
    assert dimmer._pending_command is None


def test_a_press_on_a_light_of_a_rotated_group_cancels_the_queue(
    monkeypatch,
) -> None:
    now = _clock(monkeypatch)
    dimmer, _i, _w = _binding(monkeypatch, **{CONF_TARGET: "light.group"})
    switch, _i2, _w2 = _binding(
        monkeypatch,
        **{CONF_CHANNEL: 2, CONF_CLICK_TARGET: "light.test", "click_action": "off"},
    )
    _signal_bus(monkeypatch)
    dimmer.async_attach()
    switch.async_attach()
    group = SimpleNamespace(
        state="on",
        attributes={"brightness": 200, "entity_id": ["light.test", "light.two"]},
    )
    _queue_rotation(dimmer, now, "_rotate_brightness", group)
    switch.hass.states.get.return_value = _LIT

    switch._handle_action(_action(ACTION_PRESS, presses=1))

    assert dimmer._pending_command is None


def test_actions_on_an_area_of_the_light_cancel_the_queue(monkeypatch) -> None:
    from homeassistant.helpers.target import SelectedEntities

    now = _clock(monkeypatch)
    dimmer, _i, _w = _binding(monkeypatch)
    runner = _sequence_binding(
        monkeypatch,
        "short_press",
        [{"action": "light.turn_off", "target": {"area_id": "living_room"}}],
        **{CONF_CHANNEL: 2, CONF_TARGET: "light.elsewhere"},
    )
    areas = {"living_room": {"light.test"}}

    def _extract(_hass, selection):
        return SelectedEntities(
            indirectly_referenced=set().union(
                *(areas.get(area, set()) for area in selection.area_ids)
            )
        )

    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_extract_referenced_entity_ids",
        _extract,
    )
    _signal_bus(monkeypatch)
    dimmer.async_attach()
    runner.async_attach()
    _queue_rotation(dimmer, now, "_rotate_brightness", _LIT)

    _press(runner, "short_press")
    _drain(runner)

    assert dimmer._pending_command is None


@pytest.mark.parametrize(
    ("press_action", "cancels"), [("mute_toggle", False), ("off", True)]
)
def test_another_binding_mutes_without_cancelling_queued_volume(
    monkeypatch, press_action: str, cancels: bool
) -> None:
    now = _clock(monkeypatch)
    playing = SimpleNamespace(
        state="playing", attributes={"volume_level": 0.5, "is_volume_muted": False}
    )
    volume, _i, _w = _binding(
        monkeypatch, **{CONF_TARGET: "media_player.test", CONF_MODE: MODE_VOLUME}
    )
    remote, _i2, _w2 = _binding(
        monkeypatch,
        **{
            CONF_CHANNEL: 2,
            CONF_TARGET: "light.other",
            CONF_CLICK_TARGET: "media_player.test",
            "click_action": press_action,
        },
    )
    _signal_bus(monkeypatch)
    volume.async_attach()
    remote.async_attach()
    _queue_rotation(volume, now, "_rotate_volume", playing)
    pending = volume._pending_command
    remote.hass.states.get.return_value = playing

    remote._handle_action(_action(ACTION_PRESS, presses=1))

    assert _service_calls(remote)
    assert volume._pending_command == (None if cancels else pending)


def test_unloading_a_binding_releases_its_command_signal(monkeypatch) -> None:
    from custom_components.ikea_bilresa.const import SIGNAL_TARGETS_COMMANDED

    binding, _i, _w = _binding(monkeypatch)
    bus = _signal_bus(monkeypatch)
    unsubscribe = binding.async_attach()
    assert bus[SIGNAL_TARGETS_COMMANDED] == [binding._handle_targets_commanded]

    unsubscribe()

    assert bus[SIGNAL_TARGETS_COMMANDED] == []


def test_a_press_cancels_a_rotation_still_queued(monkeypatch) -> None:
    """A coalesced value must not fire afterwards and relight the lights."""
    binding, _now, _report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._min_command_interval = 5.0
    binding._rotate_by(1, False)  # sent at once
    binding._rotate_by(1, False)  # queued behind it
    assert binding._pending_command is not None

    _press_once(binding)
    calls = binding.hass.services.async_call.call_count
    binding._flush_pending_command()

    assert binding._pending_command is None
    assert binding.hass.services.async_call.call_count == calls


def test_a_scroll_right_after_a_press_off_does_not_relight_the_lights(
    monkeypatch,
) -> None:
    """The lights have not reported off yet; the press is what counts."""
    binding, now, _report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._rotate_by(1, False)
    now[0] = 1.0
    _press_once(binding)  # off: the mocked lights still say 'on'
    calls = binding.hass.services.async_call.call_count

    now[0] = 1.5
    binding._rotate_by(1, False)

    assert binding.hass.services.async_call.call_count == calls


def test_a_failed_older_call_does_not_discard_a_newer_level(monkeypatch) -> None:
    binding, _now, _report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._min_command_interval = 0.0
    binding._rotate_by(1, False)
    older = binding._command_seq
    binding._rotate_by(1, False)
    assert binding._command_seq == older + 1

    async def _rejected() -> None:
        raise RuntimeError("rejected")

    asyncio.run(
        binding._async_dispatch_service(
            "light", "turn_on", _rejected(), result={}, action=None, seq=older
        )
    )

    assert binding._tracked is not None


def test_scrolling_up_switches_on_lights_that_are_all_off(monkeypatch) -> None:
    binding, _now, _report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, None))

    binding._rotate_by(1, True)

    payload = _last_payload(binding)
    assert payload["entity_id"] == _LIGHTS
    assert payload["brightness"] > 0


def test_scrolling_down_does_not_switch_on_lights_that_are_all_off(
    monkeypatch,
) -> None:
    binding, _now, _report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, None))

    binding._rotate_by(1, False)

    assert binding.hass.services.async_call.call_count == 0


def test_a_light_at_another_level_still_gets_the_value_at_the_maximum(
    monkeypatch,
) -> None:
    binding, _now, report = _lights_binding(
        monkeypatch, {"light.a": 255, "light.b": 255}
    )
    binding._rotate_by(1, True)
    assert binding.hass.services.async_call.call_count == 0
    binding._rejoining.add("light.b")
    report("light.b", 100)  # it came back at its own level
    assert binding._tracked == pytest.approx(255)

    binding._rotate_by(1, True)

    payload = _last_payload(binding)
    assert payload["entity_id"] == ["light.a", "light.b"]
    assert payload["brightness"] == 255


def test_one_light_off_the_path_takes_over_even_mid_scroll(monkeypatch) -> None:
    binding, now, report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._handle_raw_input(ROLE_SCROLL_DOWN, "initial_press", 2)
    binding._rotate_by(1, False)

    now[0] = 0.2
    report("light.left", 30)

    assert binding._tracked is None


def test_running_actions_invalidates_the_tracked_level(monkeypatch) -> None:
    binding, _now, _report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._sequences["short_press"] = [
        {"action": "light.turn_off", "target": {"entity_id": "light.left"}}
    ]
    binding._rotate_by(1, False)
    assert binding._tracked is not None

    binding._run_sequence("short_press")

    assert binding._tracked is None


def test_a_hue_half_way_round_is_on_the_path_either_way(monkeypatch) -> None:
    binding, now, report = _colour_lights(
        monkeypatch,
        {"light.a": (0.0, 80.0), "light.b": (0.0, 80.0)},
        **{CONF_STEP: 50},
    )
    binding._rotate_by(1, True)  # 0 -> 180
    assert binding._tracked == pytest.approx(180.0)

    now[0] = 6.0
    report("light.a", {"hs_color": [90.0, 80.0]})

    assert binding._tracked == pytest.approx(180.0)


def test_every_light_going_off_cancels_a_rotation_still_queued(monkeypatch) -> None:
    binding, now, report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._min_command_interval = 5.0
    binding._rotate_by(1, False)
    binding._rotate_by(1, False)
    assert binding._pending_command is not None

    now[0] = 2.0
    for entity_id in _LIGHTS:
        report(entity_id, None)

    assert binding._pending_command is None


def test_a_failed_call_keeps_the_level_while_a_newer_one_is_queued(
    monkeypatch,
) -> None:
    binding, _now, _report = _lights_binding(monkeypatch, dict.fromkeys(_LIGHTS, 200))
    binding._min_command_interval = 5.0
    binding._rotate_by(1, False)
    sent = binding._command_seq
    binding._rotate_by(1, False)  # queued, not dispatched: the seq is unchanged

    async def _rejected() -> None:
        raise RuntimeError("rejected")

    asyncio.run(
        binding._async_dispatch_service(
            "light", "turn_on", _rejected(), result={}, action=None, seq=sent
        )
    )

    assert binding._tracked is not None


@pytest.mark.parametrize(
    ("maximum", "current", "notches", "up", "expected"),
    [
        (40, 0.39, 1, True, 0.4),
        (40, 0.1, 100, True, 0.4),
        (40, 0.8, 1, True, 0.4),
        (40, 0.8, 1, False, 0.4),
        (40, 0.3, 1, False, 0.27),
        (40, 0.01, 1, False, 0.0),
        (0, 0.3, 1, True, 0.0),
        (None, 0.99, 1, True, 1.0),
    ],
)
def test_volume_rotation_respects_maximum(
    monkeypatch, maximum, current, notches, up, expected
) -> None:
    overrides = {CONF_TARGET: "media_player.test", CONF_MODE: MODE_VOLUME, CONF_STEP: 3}
    if maximum is not None:
        overrides[CONF_MAX_VOLUME] = maximum
    binding, _, _ = _binding(monkeypatch, **overrides)
    binding.hass.states.get.return_value = SimpleNamespace(
        state="playing", attributes={"volume_level": current}
    )

    binding._rotate_volume(notches, up)

    call = binding.hass.services.async_call.call_args.args
    assert call[:2] == ("media_player", "volume_set")
    assert call[2]["volume_level"] == expected


def test_volume_rotation_at_maximum_sends_no_command(monkeypatch) -> None:
    binding, _, _ = _binding(
        monkeypatch,
        **{
            CONF_TARGET: "media_player.test",
            CONF_MODE: MODE_VOLUME,
            CONF_MAX_VOLUME: 40,
        },
    )
    binding.hass.states.get.return_value = SimpleNamespace(
        state="playing", attributes={"volume_level": 0.4}
    )

    binding._rotate_volume(10, up=True)

    binding.hass.services.async_call.assert_not_called()
