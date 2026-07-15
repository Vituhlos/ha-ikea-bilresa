"""Turnkey control bindings configured via config subentries.

A binding subscribes to one wheel channel and drives a target entity directly.
Depending on its *mode*, scrolling adjusts a light's brightness / colour
temperature / colour, a media player's volume, a cover's position, a climate
target temperature, a fan's speed, or a number's value. A single / double /
triple press and a hold each run an optional action, which may target a
*different* entity (e.g. dim a bulb but toggle the Shelly in the wall switch).

Values are tracked internally as an absolute target rather than issued as
relative steps. This avoids reading a mid-transition value back from the entity
(a race during fast scrolling) and the abrupt "snap off" of relative steps.
``step`` is interpreted as a percentage of the mode's range per notch, so one
setting feels consistent across every kind of target.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import (
    ACTION_HOLD,
    ACTION_PRESS,
    ACTION_RELEASE,
    ACTION_ROTATE,
    BUTTON_RESPONSE_FAST,
    CLICK_NONE,
    CLICK_OFF,
    CLICK_ON,
    CONF_ACCELERATION,
    CONF_BUTTON_RESPONSE,
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_HOLD_ACTION,
    CONF_HOLD_TARGET,
    CONF_MAX_BRIGHTNESS,
    CONF_MIN_BRIGHTNESS,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_SCENES,
    CONF_STEP,
    CONF_TARGET,
    CONF_TRANSITION,
    CONF_TRIPLE_TARGET,
    DEFAULT_ACCELERATION,
    DEFAULT_BUTTON_RESPONSE,
    DEFAULT_CLICK_ACTION,
    DEFAULT_HOLD_ACTION,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MODE,
    DEFAULT_STEP,
    DEFAULT_TRANSITION,
    DIRECTION_UP,
    EVT_INITIAL_PRESS,
    EVT_MULTI_PRESS_COMPLETE,
    EVT_SHORT_RELEASE,
    FALLBACK_MAX_KELVIN,
    FALLBACK_MIN_KELVIN,
    HOLD_RAMP,
    HOLD_TOGGLE,
    MODE_COLOR,
    MODE_COLOR_TEMP,
    MODE_COVER,
    MODE_FAN,
    MODE_NUMBER,
    MODE_TEMPERATURE,
    MODE_VOLUME,
    ROLE_BUTTON,
    ROLE_SCROLL_DOWN,
    ROLE_SCROLL_UP,
    SIGNAL_CONNECTION,
    SWITCH_EVENT_NAMES,
    mode_supports_target,
    signal_channel,
    signal_raw_button,
)
from .engine import WheelAction

_LOGGER = logging.getLogger(__name__)

ATTR_BRIGHTNESS = "brightness"
ATTR_TRANSITION = "transition"
ATTR_COLOR_TEMP_KELVIN = "color_temp_kelvin"
ATTR_HS_COLOR = "hs_color"
ATTR_MIN_KELVIN = "min_color_temp_kelvin"
ATTR_MAX_KELVIN = "max_color_temp_kelvin"

_CLICK_SERVICE = {"toggle": "toggle", CLICK_ON: "turn_on", CLICK_OFF: "turn_off"}

_UNAVAILABLE = (None, "unknown", "unavailable")

# How long our tracked target stays authoritative before we resync from state.
_RESYNC_AFTER = 3.0
_STATE_ECHO_MARGIN = 0.25

# A missing gesture boundary must not suppress rotation indefinitely.
_TRAILING_GESTURE_TIMEOUT = 2.0

# Acceleration is derived from recent decoded velocity, never a single Matter
# batch size. Defaults remain disabled until physical tuning is complete.
_VELOCITY_WINDOW = 2.0
_VELOCITY_IDLE_RESET = 1.5
_VELOCITY_FLOOR = 2.0
_VELOCITY_FULL_SCALE = 10.0
_MAX_ACCELERATION_MULTIPLIER = 3.0

# If a MultiPressComplete is lost, allow a clearly later gesture to recover
# instead of leaving fast single-press handling blocked indefinitely.
_FAST_PRESS_GESTURE_TIMEOUT = 2.0

_INITIAL_PRESS = SWITCH_EVENT_NAMES[EVT_INITIAL_PRESS]
_COMPLETE = SWITCH_EVENT_NAMES[EVT_MULTI_PRESS_COMPLETE]
_SHORT_RELEASE = SWITCH_EVENT_NAMES[EVT_SHORT_RELEASE]

# Hold-to-ramp: how often and by how much to step while the button is held.
_RAMP_INTERVAL = timedelta(seconds=0.2)
_RAMP_NOTCHES = 1
# A lost Matter LongRelease event must never leave a target changing forever.
_RAMP_WATCHDOG_SECONDS = 30


def _pct_to_units(pct: float) -> int:
    return round(pct / 100 * 255)


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class LightBinding:
    """Runtime for one GUI-configured wheel-channel -> entity binding."""

    def __init__(self, hass: HomeAssistant, data: dict[str, Any]) -> None:
        self.hass = hass
        self._node_id = int(data[CONF_NODE_ID])
        self._channel = int(data[CONF_CHANNEL])
        self._target = data[CONF_TARGET]
        self._mode = data.get(CONF_MODE, DEFAULT_MODE)
        self._mode_target_valid = mode_supports_target(self._mode, self._target)
        if not self._mode_target_valid:
            _LOGGER.error(
                "Disabling incompatible BILRESA binding mode %s for target %s",
                self._mode,
                self._target,
            )
        self._step = float(data.get(CONF_STEP, DEFAULT_STEP))
        self._accel = float(data.get(CONF_ACCELERATION, DEFAULT_ACCELERATION)) / 100
        self._min_units = _pct_to_units(
            float(data.get(CONF_MIN_BRIGHTNESS, DEFAULT_MIN_BRIGHTNESS))
        )
        self._max_units = _pct_to_units(
            float(data.get(CONF_MAX_BRIGHTNESS, DEFAULT_MAX_BRIGHTNESS))
        )
        self._transition = float(data.get(CONF_TRANSITION, DEFAULT_TRANSITION))
        self._click = data.get(CONF_CLICK_ACTION, DEFAULT_CLICK_ACTION)
        self._click_target = data.get(CONF_CLICK_TARGET) or self._target
        self._double_target = data.get(CONF_DOUBLE_TARGET)
        self._triple_target = data.get(CONF_TRIPLE_TARGET)
        self._hold_target = data.get(CONF_HOLD_TARGET)
        self._hold_action = data.get(CONF_HOLD_ACTION, DEFAULT_HOLD_ACTION)
        self._scenes: list[str] = list(data.get(CONF_SCENES) or [])
        self._scene_index = 0
        self._ramp_up = True
        self._ramp_unsub: Callable[[], None] | None = None
        self._ramp_watchdog_unsub: Callable[[], None] | None = None
        self._tracked: float | None = None
        self._command_authoritative_until = 0.0
        self._last_direction: str | None = None
        self._saturation = 100.0
        self._last = 0.0
        self._scroll_gesture = 0
        self._button_scroll_boundary: int | None = None
        self._suppress_scroll_through = -1
        self._suppress_scroll_until = 0.0
        self._velocity_samples: deque[tuple[float, int]] = deque()
        self._velocity_direction: str | None = None
        self._reset_velocity_after_rotate = False
        self._unavailable_targets: set[str] = set()
        self._fast_single = (
            data.get(CONF_BUTTON_RESPONSE, DEFAULT_BUTTON_RESPONSE)
            == BUTTON_RESPONSE_FAST
        )
        self._fast_press_started: float | None = None
        self._latency_trace_sequence = 0
        self._latency_trace_started_at: float | None = None
        self._latency_trace_target_seen = False

    @callback
    def async_attach(self) -> Callable[[], None]:
        """Start listening for this channel's actions; returns an unsubscribe."""
        action_unsub = async_dispatcher_connect(
            self.hass,
            signal_channel(self._node_id, self._channel),
            self._handle_action,
        )
        raw_button_unsub = async_dispatcher_connect(
            self.hass,
            signal_raw_button(self._node_id, self._channel),
            self._handle_raw_input,
        )
        connection_unsub = async_dispatcher_connect(
            self.hass, SIGNAL_CONNECTION, self._handle_connection_change
        )
        state_unsub = async_track_state_change_event(
            self.hass, [self._target], self._handle_target_state_change
        )
        trace_state_unsub = (
            async_track_state_change_event(
                self.hass,
                [self._click_target],
                self._handle_latency_target_state_change,
            )
            if self._click_target != self._target
            else None
        )

        @callback
        def unsubscribe() -> None:
            self._stop_ramp(change_direction=False)
            self._fast_press_started = None
            self._reset_latency_trace()
            if trace_state_unsub is not None:
                trace_state_unsub()
            state_unsub()
            connection_unsub()
            raw_button_unsub()
            action_unsub()

        return unsubscribe

    @callback
    def _handle_action(self, action: WheelAction) -> None:
        if self._ramp_unsub is not None and action.type in (
            ACTION_ROTATE,
            ACTION_PRESS,
        ):
            # Any new gesture supersedes a hold whose release may have been lost.
            self._stop_ramp(change_direction=False)
        if action.type == ACTION_ROTATE:
            self._rotate(action)
        elif action.type == ACTION_PRESS:
            self._hold_off_rotation()
            if self._fast_press_started is not None:
                # The binding already ran one immediate single-press action.
                # MultiPressComplete still reaches event entities/device
                # triggers, but must not execute the binding a second time.
                self._log_latency_stage("multi_press_complete", presses=action.presses)
                self._fast_press_started = None
                return
            if action.presses == 1:
                self._single_press()
            elif action.presses == 2:
                self._toggle(self._double_target)
            elif action.presses == 3:
                self._toggle(self._triple_target)
        elif action.type == ACTION_HOLD:
            self._hold_off_rotation()
            if self._hold_action == HOLD_RAMP:
                self._start_ramp()
            elif self._hold_action == HOLD_TOGGLE:
                self._toggle(self._hold_target)
        elif action.type == ACTION_RELEASE and self._hold_action == HOLD_RAMP:
            self._stop_ramp(change_direction=True)

    @callback
    def _handle_connection_change(self) -> None:
        """Stop safety-critical timers whenever Matter connectivity changes."""
        self._fast_press_started = None
        self._reset_latency_trace()
        self._tracked = None
        self._command_authoritative_until = 0.0
        self._last_direction = None
        self._button_scroll_boundary = None
        self._suppress_scroll_through = -1
        self._suppress_scroll_until = 0.0
        self._reset_velocity()
        self._stop_ramp(change_direction=False)

    @callback
    def _handle_target_state_change(self, event) -> None:
        """Rebase the next action after a genuine external target change."""
        if self._click_target == self._target:
            self._handle_latency_target_state_change(event)
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in _UNAVAILABLE:
            self._tracked = None
            self._command_authoritative_until = 0.0
            self._stop_ramp(change_direction=False)
            return
        # Ignore bounded state echoes from our own in-flight service/transition.
        # Once that window closes, any state event invalidates the desired value
        # and the next wheel action reads reality again.
        if time.monotonic() >= self._command_authoritative_until:
            self._tracked = None

    @callback
    def _handle_latency_target_state_change(self, event) -> None:
        """Record the first target-state acknowledgement for an active trace."""
        if (
            self._latency_trace_started_at is None
            or self._latency_trace_target_seen
            or event.data.get("new_state") is None
        ):
            return
        self._latency_trace_target_seen = True
        self._log_latency_stage("target_state_change")

    @callback
    def _handle_raw_input(self, role: str, event_type: str) -> None:
        """Track private gesture boundaries and forward button hints."""
        if role in (ROLE_SCROLL_UP, ROLE_SCROLL_DOWN):
            if event_type == _INITIAL_PRESS:
                self._scroll_gesture += 1
                self._reset_velocity()
            elif event_type == _COMPLETE:
                # The raw completion precedes its possible final delta action.
                self._reset_velocity_after_rotate = True
            return
        if role != ROLE_BUTTON:
            return
        if event_type == _INITIAL_PRESS:
            self._button_scroll_boundary = self._scroll_gesture
        self._handle_raw_button(event_type)

    @callback
    def _handle_raw_button(self, event_type: str) -> None:
        """Run an unambiguous single-press binding on ShortRelease."""
        if not self._fast_single:
            return
        now = time.monotonic()
        if event_type == _INITIAL_PRESS:
            if (
                self._fast_press_started is not None
                and now - self._fast_press_started > _FAST_PRESS_GESTURE_TIMEOUT
            ):
                self._fast_press_started = None
            return
        if event_type != _SHORT_RELEASE or self._fast_press_started is not None:
            return

        # A hold ends with LongRelease, so ShortRelease is safe for the normal
        # click action. Further releases in the same multi-press gesture are
        # collapsed until its public MultiPressComplete action arrives.
        self._fast_press_started = now
        self._start_latency_trace(now)
        if self._ramp_unsub is not None:
            self._stop_ramp(change_direction=False)
        self._hold_off_rotation()
        self._single_press()

    def _start_latency_trace(self, now: float) -> None:
        """Start a privacy-safe fast-press trace only while DEBUG is enabled."""
        if not _LOGGER.isEnabledFor(logging.DEBUG):
            self._reset_latency_trace()
            return
        self._latency_trace_sequence += 1
        self._latency_trace_started_at = now
        self._latency_trace_target_seen = False
        self._log_latency_stage("short_release", now=now)

    def _reset_latency_trace(self) -> None:
        """Discard transient latency measurement state."""
        self._latency_trace_started_at = None
        self._latency_trace_target_seen = False

    def _log_latency_stage(
        self,
        stage: str,
        *,
        now: float | None = None,
        presses: int | None = None,
    ) -> None:
        """Log one trace stage without household or Matter identifiers."""
        started_at = self._latency_trace_started_at
        if started_at is None:
            return
        elapsed_ms = ((time.monotonic() if now is None else now) - started_at) * 1000
        _LOGGER.debug(
            "BILRESA latency trace=%s channel=%s stage=%s elapsed_ms=%.1f presses=%s",
            self._latency_trace_sequence,
            self._channel,
            stage,
            elapsed_ms,
            presses if presses is not None else "-",
        )

    @callback
    def _hold_off_rotation(self) -> None:
        boundary = self._button_scroll_boundary
        self._suppress_scroll_through = (
            self._scroll_gesture if boundary is None else boundary
        )
        self._suppress_scroll_until = time.monotonic() + _TRAILING_GESTURE_TIMEOUT

    # -- rotation ---------------------------------------------------------

    @callback
    def _rotate(self, action: WheelAction) -> None:
        if self._suppress_trailing_rotation():
            return
        # A direction reversal intentionally starts from the last desired
        # target, not a mid-transition state echo, preventing a visible jump.
        self._last_direction = action.direction
        notches = self._accelerate(action.notches, action.direction)
        up = action.direction == DIRECTION_UP
        self._rotate_by(notches, up)
        if self._reset_velocity_after_rotate:
            self._reset_velocity()

    def _suppress_trailing_rotation(self) -> bool:
        """Suppress only rotations from the gesture preceding a button action."""
        if self._suppress_scroll_through < 0:
            return False
        if time.monotonic() >= self._suppress_scroll_until:
            self._suppress_scroll_through = -1
            return False
        if self._scroll_gesture <= self._suppress_scroll_through:
            return True
        self._suppress_scroll_through = -1
        return False

    @callback
    def _rotate_by(self, notches: int, up: bool) -> None:
        if not self._mode_target_valid or self._available_state(self._target) is None:
            self._tracked = None
            self._stop_ramp(change_direction=False)
            return
        if self._mode == MODE_COLOR_TEMP:
            self._rotate_color_temp(notches, up)
        elif self._mode == MODE_COLOR:
            self._rotate_color(notches, up)
        elif self._mode == MODE_VOLUME:
            self._rotate_volume(notches, up)
        elif self._mode == MODE_COVER:
            self._rotate_cover(notches, up)
        elif self._mode == MODE_TEMPERATURE:
            self._rotate_temperature(notches, up)
        elif self._mode == MODE_FAN:
            self._rotate_fan(notches, up)
        elif self._mode == MODE_NUMBER:
            self._rotate_number(notches, up)
        else:
            self._rotate_brightness(notches, up)

    # -- hold-to-ramp -----------------------------------------------------

    @callback
    def _start_ramp(self) -> None:
        if (
            self._ramp_unsub is not None
            or not self._mode_target_valid
            or self._available_state(self._target) is None
        ):
            return
        self._rotate_by(_RAMP_NOTCHES, self._ramp_up)
        self._ramp_unsub = async_track_time_interval(
            self.hass, self._ramp_tick, _RAMP_INTERVAL
        )
        self._ramp_watchdog_unsub = async_call_later(
            self.hass, _RAMP_WATCHDOG_SECONDS, self._ramp_watchdog
        )

    @callback
    def _ramp_tick(self, _now) -> None:
        self._rotate_by(_RAMP_NOTCHES, self._ramp_up)

    @callback
    def _ramp_watchdog(self, _now) -> None:
        _LOGGER.warning(
            "Stopping hold-to-ramp after %s seconds without a release event",
            _RAMP_WATCHDOG_SECONDS,
        )
        self._ramp_watchdog_unsub = None
        self._stop_ramp(change_direction=False)

    @callback
    def _stop_ramp(self, *, change_direction: bool) -> None:
        if self._ramp_unsub is None:
            return
        self._ramp_unsub()
        self._ramp_unsub = None
        if self._ramp_watchdog_unsub is not None:
            self._ramp_watchdog_unsub()
            self._ramp_watchdog_unsub = None
        if change_direction:
            self._ramp_up = not self._ramp_up

    def _accelerate(self, notches: int, direction: str | None = None) -> int:
        if self._accel <= 0:
            return notches
        now = time.monotonic()
        if (
            self._velocity_direction != direction
            or not self._velocity_samples
            or now - self._velocity_samples[-1][0] > _VELOCITY_IDLE_RESET
        ):
            self._velocity_samples.clear()
        self._velocity_direction = direction
        self._velocity_samples.append((now, notches))
        while (
            len(self._velocity_samples) > 1
            and now - self._velocity_samples[0][0] > _VELOCITY_WINDOW
        ):
            self._velocity_samples.popleft()
        if len(self._velocity_samples) < 2:
            return notches

        elapsed = now - self._velocity_samples[0][0]
        if elapsed <= 0:
            return notches
        # The first sample establishes the time boundary; later deltas belong
        # to the measured interval and are independent of its initial batch.
        velocity = (
            sum(sample[1] for sample in list(self._velocity_samples)[1:]) / elapsed
        )
        intensity = min(
            1.0,
            max(
                0.0,
                (velocity - _VELOCITY_FLOOR) / (_VELOCITY_FULL_SCALE - _VELOCITY_FLOOR),
            ),
        )
        multiplier = 1 + self._accel * intensity * (_MAX_ACCELERATION_MULTIPLIER - 1)
        return max(notches, round(notches * multiplier))

    def _reset_velocity(self) -> None:
        self._velocity_samples.clear()
        self._velocity_direction = None
        self._reset_velocity_after_rotate = False

    def _resync(self, current: float | None, fallback: float) -> float:
        """Return the tracked target, resyncing from reality when idle."""
        now = time.monotonic()
        recent = self._tracked is not None and (now - self._last) < _RESYNC_AFTER
        self._last = now
        if recent and self._tracked is not None:
            return self._tracked
        value = current if current is not None else fallback
        self._tracked = value
        return value

    @staticmethod
    def _delta(step_pct: float, span: float, notches: int, up: bool) -> float:
        magnitude = step_pct / 100 * span * notches
        return magnitude if up else -magnitude

    @callback
    def _rotate_brightness(self, notches: int, up: bool) -> None:
        state = self._available_state(self._target)
        if state is None:
            return
        state_on = state.state == "on"
        current = state.attributes.get(ATTR_BRIGHTNESS) if state_on else 0
        tracked = self._resync(current, 0)
        if not state_on and tracked <= 0 and not up:
            return  # don't switch a light on by scrolling down

        if not state_on and up:
            first_step = self._delta(self._step, 255, 1, True)
            start = max(self._min_units, first_step)
            target = start + self._delta(self._step, 255, max(0, notches - 1), True)
        else:
            target = tracked + self._delta(self._step, 255, notches, up)
        if target >= self._max_units:
            target = self._max_units
        elif target <= self._min_units:
            if self._min_units <= 0:
                self._tracked = 0
                self._call("light", "turn_off", {ATTR_TRANSITION: self._transition})
                return
            target = self._min_units
        self._tracked = target
        self._call(
            "light",
            "turn_on",
            {ATTR_BRIGHTNESS: round(target), ATTR_TRANSITION: self._transition},
        )

    @callback
    def _rotate_color_temp(self, notches: int, up: bool) -> None:
        state = self._lit_state()
        if state is None:
            return
        min_k = state.attributes.get(ATTR_MIN_KELVIN, FALLBACK_MIN_KELVIN)
        max_k = state.attributes.get(ATTR_MAX_KELVIN, FALLBACK_MAX_KELVIN)
        tracked = self._resync(
            state.attributes.get(ATTR_COLOR_TEMP_KELVIN), (min_k + max_k) / 2
        )
        target = tracked + self._delta(self._step, max(max_k - min_k, 1), notches, up)
        target = min(max_k, max(min_k, target))
        self._tracked = target
        self._call(
            "light",
            "turn_on",
            {ATTR_COLOR_TEMP_KELVIN: round(target), ATTR_TRANSITION: self._transition},
        )

    @callback
    def _rotate_color(self, notches: int, up: bool) -> None:
        state = self._lit_state()
        if state is None:
            return
        hs_color = state.attributes.get(ATTR_HS_COLOR)
        if hs_color:
            self._saturation = float(hs_color[1])
        tracked = self._resync(hs_color[0] if hs_color else None, 0.0)
        hue = (tracked + self._delta(self._step, 360, notches, up)) % 360
        self._tracked = hue
        self._call(
            "light",
            "turn_on",
            {
                ATTR_HS_COLOR: [round(hue, 1), self._saturation],
                ATTR_TRANSITION: self._transition,
            },
        )

    @callback
    def _rotate_volume(self, notches: int, up: bool) -> None:
        state = self._available_state(self._target)
        if state is None:
            return
        tracked = self._resync(_as_float(state.attributes.get("volume_level")), 0.5)
        target = min(1.0, max(0.0, tracked + self._delta(self._step, 1, notches, up)))
        self._tracked = target
        self._call("media_player", "volume_set", {"volume_level": round(target, 3)})

    @callback
    def _rotate_cover(self, notches: int, up: bool) -> None:
        state = self._available_state(self._target)
        if state is None:
            return
        tracked = self._resync(_as_float(state.attributes.get("current_position")), 50)
        target = min(
            100, max(0, round(tracked + self._delta(self._step, 100, notches, up)))
        )
        self._tracked = target
        self._call("cover", "set_cover_position", {"position": target})

    @callback
    def _rotate_temperature(self, notches: int, up: bool) -> None:
        state = self._available_state(self._target)
        if state is None:
            return
        min_t = _as_float(state.attributes.get("min_temp")) or 7.0
        max_t = _as_float(state.attributes.get("max_temp")) or 35.0
        temp_step = _as_float(state.attributes.get("target_temp_step")) or 0.5
        tracked = self._resync(
            _as_float(state.attributes.get("temperature")), (min_t + max_t) / 2
        )
        target = tracked + self._delta(self._step, max(max_t - min_t, 1), notches, up)
        target = min(max_t, max(min_t, round(target / temp_step) * temp_step))
        self._tracked = target
        self._call("climate", "set_temperature", {"temperature": round(target, 2)})

    @callback
    def _rotate_fan(self, notches: int, up: bool) -> None:
        state = self._available_state(self._target)
        if state is None:
            return
        tracked = self._resync(_as_float(state.attributes.get("percentage")), 50)
        target = min(
            100, max(0, round(tracked + self._delta(self._step, 100, notches, up)))
        )
        self._tracked = target
        self._call("fan", "set_percentage", {"percentage": target})

    @callback
    def _rotate_number(self, notches: int, up: bool) -> None:
        state = self._available_state(self._target)
        if state is None:
            return
        min_n = _as_float(state.attributes.get("min")) or 0.0
        max_n = _as_float(state.attributes.get("max")) or 100.0
        num_step = _as_float(state.attributes.get("step")) or 1.0
        current = _as_float(state.state)
        tracked = self._resync(current, (min_n + max_n) / 2)
        target = tracked + self._delta(
            self._step, max(max_n - min_n, num_step), notches, up
        )
        target = min(max_n, max(min_n, round(target / num_step) * num_step))
        self._tracked = target
        domain = self._target.split(".", 1)[0]
        self._call(domain, "set_value", {"value": round(target, 4)})

    def _lit_state(self) -> State | None:
        state = self._available_state(self._target)
        return state if state is not None and state.state == "on" else None

    def _available_state(self, entity_id: str) -> State | None:
        """Return an available state and log only availability transitions."""
        state = self.hass.states.get(entity_id)
        if state is None or state.state in _UNAVAILABLE:
            if entity_id not in self._unavailable_targets:
                self._unavailable_targets.add(entity_id)
                _LOGGER.warning(
                    "Skipping BILRESA action while target %s is unavailable",
                    entity_id,
                )
            return None

        if entity_id in self._unavailable_targets:
            self._unavailable_targets.remove(entity_id)
            if entity_id == self._target:
                self._tracked = None
            _LOGGER.info("BILRESA target %s is available again", entity_id)
        return state

    # -- button presses ---------------------------------------------------

    @callback
    def _single_press(self) -> None:
        if self._scenes:
            scene = self._scenes[self._scene_index]
            if self._call_entity("scene", "turn_on", scene):
                self._scene_index = (self._scene_index + 1) % len(self._scenes)
            return
        if self._click == CLICK_NONE:
            return
        service = _CLICK_SERVICE.get(self._click, "toggle")
        self._call_entity("homeassistant", service, self._click_target)

    @callback
    def _toggle(self, target: str | None) -> None:
        if target:
            self._call_entity("homeassistant", "toggle", target)

    # -- service helpers --------------------------------------------------

    @callback
    def _call(self, domain: str, service: str, data: dict[str, Any]) -> None:
        if self._available_state(self._target) is None:
            return
        transition = _as_float(data.get(ATTR_TRANSITION)) or 0.0
        self._command_authoritative_until = (
            time.monotonic() + transition + _STATE_ECHO_MARGIN
        )
        payload = {ATTR_ENTITY_ID: self._target, **data}
        self.hass.async_create_task(
            self.hass.services.async_call(domain, service, payload, blocking=False)
        )

    @callback
    def _call_entity(self, domain: str, service: str, entity_id: str) -> bool:
        if self._available_state(entity_id) is None:
            return False
        if entity_id == self._click_target:
            self._log_latency_stage("service_dispatch")
        self.hass.async_create_task(
            self.hass.services.async_call(
                domain, service, {ATTR_ENTITY_ID: entity_id}, blocking=False
            )
        )
        return True
