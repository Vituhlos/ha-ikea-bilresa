"""Turnkey control bindings configured via config subentries.

A binding subscribes either to one wheel channel or to one endpoint of a dual
button. Depending on its *mode*, wheel scrolling adjusts a light's brightness /
colour temperature / colour, a media player's volume, a cover's position, a
climate target temperature, a fan's speed, or a number's value. Button-only
bindings omit all rotary configuration while retaining single / double press
and hold actions.

Values are tracked internally as an absolute target rather than issued as
relative steps. This avoids reading a mid-transition value back from the entity
(a race during fast scrolling) and the abrupt "snap off" of relative steps.
``step`` is interpreted as a percentage of the mode's range per notch, so one
setting feels consistent across every kind of target.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Awaitable, Callable
from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
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
    BUTTON_RESPONSE_INSTANT,
    CLICK_NONE,
    CLICK_OFF,
    CLICK_ON,
    CONF_ACCELERATION,
    CONF_BUTTON_RESPONSE,
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_ENDPOINT,
    CONF_HOLD_ACTION,
    CONF_HOLD_TARGET,
    CONF_MAX_BRIGHTNESS,
    CONF_MIN_BRIGHTNESS,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_RAMP_DIRECTION,
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
    DEFAULT_RAMP_DIRECTION,
    DEFAULT_STEP,
    DEFAULT_TRANSITION,
    DIRECTION_UP,
    EVT_INITIAL_PRESS,
    EVT_MULTI_PRESS_COMPLETE,
    EVT_SHORT_RELEASE,
    FALLBACK_MAX_KELVIN,
    FALLBACK_MIN_KELVIN,
    HOLD_NONE,
    HOLD_RAMP,
    HOLD_TOGGLE,
    MODE_COLOR,
    MODE_COLOR_TEMP,
    MODE_COVER,
    MODE_FAN,
    MODE_NUMBER,
    MODE_TEMPERATURE,
    MODE_VOLUME,
    RAMP_DIRECTION_ALTERNATE,
    RAMP_DIRECTION_DOWN,
    ROLE_BUTTON,
    ROLE_SCROLL_DOWN,
    ROLE_SCROLL_UP,
    SIGNAL_BINDING_ACTIVITY,
    SIGNAL_CONNECTION,
    SWITCH_EVENT_NAMES,
    mode_supports_target,
    signal_channel,
    signal_raw_button,
)
from .engine import WheelAction
from .trace import RotationTrace

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
# Matter rotary batches observed on the physical E2490 arrive roughly every
# 0.5 seconds. Four such intervals protect an active target calculation while
# still recovering promptly if MultiPressComplete is lost.
_ACTIVE_SCROLL_TIMEOUT = 2.0
# One continuous physical scroll reaches Home Assistant as several Matter
# gestures: MultiPressComplete ends one and the next InitialPress opens the
# following one. A delayed absolute echo landing in that gap would otherwise
# rebase the next notch from state that is still catching up. Two observed
# batch intervals, bounded by the same hard timeout as an active gesture.
_SCROLL_AUTHORITY_GRACE = 1.0
# A target echoes an absolute value quantized to its own resolution — a Shelly
# Plus 0-10V dimmer stores whole percent, so 156/255 returns as 155. Recognize
# our own value within a fraction of the mode's full range instead of by
# equality; anything further away is a genuine third-party change.
_ECHO_MATCH_FRACTION = 0.01
# Enough dispatched values to cover several delayed batches without keeping an
# unbounded history.
_COMMAND_HISTORY = 8

# The largest single rotary batch recorded on the physical E2490 during the
# uncontrolled fast-scroll stress run (batches of 14, 9, 6 and 14 notches). A
# batch that size receives the whole configured transition; smaller batches
# receive proportionally less, so the smoothing tracks how far the light has
# to travel. No duration is claimed here: the ceiling is the owner's own
# setting and remains subject to a controlled Hardware A/B.
_SMOOTHING_FULL_BATCH = 14

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
    """Runtime for one GUI-configured wheel channel or button endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        data: dict[str, Any],
        trace: RotationTrace | None = None,
    ) -> None:
        self.hass = hass
        # Optional so a binding constructed without a coordinator - in tests,
        # and in any future caller - still works, with tracing simply absent.
        self._trace = trace or RotationTrace()
        self._trace_from: float | None = None
        self._trace_source: str | None = None
        self._node_id = int(data[CONF_NODE_ID])
        raw_channel = data.get(CONF_CHANNEL)
        raw_endpoint = data.get(CONF_ENDPOINT)
        self._channel = int(raw_channel) if raw_channel is not None else None
        self._endpoint_id = int(raw_endpoint) if raw_endpoint is not None else None
        if (self._channel is None) == (self._endpoint_id is None):
            raise ValueError(
                "A BILRESA binding must contain exactly one of channel or endpoint"
            )
        self._hold_action = data.get(CONF_HOLD_ACTION, DEFAULT_HOLD_ACTION)
        self._hold_target = data.get(CONF_HOLD_TARGET)
        self._target: str = data.get(CONF_TARGET) or ""
        if self._endpoint_id is not None and self._hold_action == HOLD_RAMP:
            # A button has no rotary target. Its hold target becomes the
            # brightness-ramp target while the rotary-only mode remains hidden.
            self._target = self._hold_target or ""
        if self._channel is not None and not self._target:
            raise ValueError("A wheel-channel binding requires a target")
        self._mode = data.get(CONF_MODE, DEFAULT_MODE)
        self._mode_target_valid = bool(self._target) and mode_supports_target(
            self._mode, self._target
        )
        if not self._mode_target_valid and (
            self._channel is not None
            or (self._endpoint_id is not None and self._hold_action == HOLD_RAMP)
        ):
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
        self._click_target: str | None = data.get(CONF_CLICK_TARGET) or self._target
        self._double_target = data.get(CONF_DOUBLE_TARGET)
        self._triple_target = data.get(CONF_TRIPLE_TARGET)
        self._scenes: list[str] = list(data.get(CONF_SCENES) or [])
        self._scene_index = 0
        self._ramp_direction = data.get(CONF_RAMP_DIRECTION, DEFAULT_RAMP_DIRECTION)
        self._ramp_up = self._ramp_direction != RAMP_DIRECTION_DOWN
        self._ramp_active = False
        self._ramp_unsub: Callable[[], None] | None = None
        self._ramp_watchdog_unsub: Callable[[], None] | None = None
        self._tracked: float | None = None
        self._command_authoritative_until = 0.0
        self._last_direction: str | None = None
        self._saturation = 100.0
        self._last = 0.0
        self._scroll_gesture = 0
        self._active_scrolls: dict[int | None, float] = {}
        self._last_scroll_seen: float | None = None
        # Where the target last said it was. One end of the path it is on.
        self._last_reported: float | None = None
        # Recently calculated targets with the range they were derived from,
        # so a later absolute state report can be recognized as our own echo.
        self._commanded: deque[tuple[float, float]] = deque(maxlen=_COMMAND_HISTORY)
        self._button_scroll_boundary: int | None = None
        self._suppress_scroll_through = -1
        self._suppress_scroll_until = 0.0
        self._velocity_samples: deque[tuple[float, int]] = deque()
        self._velocity_direction: str | None = None
        self._reset_velocity_after_rotate = False
        self._unavailable_targets: set[str] = set()
        button_response = data.get(CONF_BUTTON_RESPONSE, DEFAULT_BUTTON_RESPONSE)
        instant_requested = button_response == BUTTON_RESPONSE_INSTANT
        self._instant_single = (
            instant_requested
            and self._double_target is None
            and self._triple_target is None
            and self._hold_action == HOLD_NONE
        )
        if instant_requested and not self._instant_single:
            _LOGGER.error(
                "Disabling ambiguous BILRESA Instant response; use validation "
                "to remove multi-press and hold actions"
            )
        self._fast_single = button_response == BUTTON_RESPONSE_FAST
        self._fast_press_started: float | None = None
        self._latency_trace_sequence = 0
        self._latency_trace_started_at: float | None = None
        self._latency_trace_target_seen = False
        self._active_action: WheelAction | None = None
        self._ramp_action: WheelAction | None = None

    @property
    def node_id(self) -> int:
        """Matter node ID used only inside the integration runtime."""
        return self._node_id

    @property
    def channel(self) -> int | None:
        """Physical wheel channel, or None for a button endpoint binding."""
        return self._channel

    @property
    def endpoint_id(self) -> int | None:
        """Physical button endpoint, or None for a wheel-channel binding."""
        return self._endpoint_id

    @property
    def binding_key(self) -> tuple[int, str, int]:
        """Collision-free runtime key across wheels, buttons and devices."""
        if self._channel is not None:
            return (self._node_id, CONF_CHANNEL, self._channel)
        assert self._endpoint_id is not None
        return (self._node_id, CONF_ENDPOINT, self._endpoint_id)

    @property
    def trace_key(self) -> str:
        """Stable, printable identity for this binding inside a capture."""
        node, kind, address = self.binding_key
        return f"{node}:{kind}:{address}"

    @callback
    def trace_config(self) -> dict[str, Any]:
        """The settings a replay needs to rebuild this binding exactly.

        Only rotation-relevant values, and the target is included so a replay
        can seed its simulated entity — diagnostics redacts it by key.
        """
        return {
            "mode": self._mode,
            "target": self._target,
            "step": self._step,
            "acceleration": self._accel * 100,
            "min_units": self._min_units,
            "max_units": self._max_units,
            "transition": self._transition,
        }

    @callback
    def test_action(self, action: WheelAction) -> None:
        """Run a panel-requested action through the normal binding path."""
        self._handle_action(action)

    @callback
    def async_attach(self) -> Callable[[], None]:
        """Start listening for this channel's actions; returns an unsubscribe."""
        action_unsub = async_dispatcher_connect(
            self.hass,
            signal_channel(self._node_id, self._channel),
            self._handle_dispatched_action,
        )
        raw_button_unsub = async_dispatcher_connect(
            self.hass,
            signal_raw_button(self._node_id, self._channel),
            self._handle_raw_input,
        )
        connection_unsub = async_dispatcher_connect(
            self.hass, SIGNAL_CONNECTION, self._handle_connection_change
        )
        state_unsub = (
            async_track_state_change_event(
                self.hass, [self._target], self._handle_target_state_change
            )
            if self._target
            else None
        )
        trace_state_unsub = (
            async_track_state_change_event(
                self.hass,
                [self._click_target],
                self._handle_latency_target_state_change,
            )
            if self._click_target is not None and self._click_target != self._target
            else None
        )

        @callback
        def unsubscribe() -> None:
            self._stop_ramp(change_direction=False)
            self._fast_press_started = None
            self._reset_latency_trace()
            if trace_state_unsub is not None:
                trace_state_unsub()
            if state_unsub is not None:
                state_unsub()
            connection_unsub()
            raw_button_unsub()
            action_unsub()

        return unsubscribe

    @callback
    def _handle_dispatched_action(self, action: WheelAction) -> None:
        """Filter the shared channel=None signal to this physical endpoint."""
        if action.node_id != self._node_id or (
            self._endpoint_id is not None and action.endpoint_id != self._endpoint_id
        ):
            return
        self._handle_action(action)

    @callback
    def _handle_action(self, action: WheelAction) -> None:
        previous_action = self._active_action
        self._active_action = action
        try:
            if self._ramp_active and action.type in (
                ACTION_ROTATE,
                ACTION_PRESS,
                ACTION_HOLD,
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
                    self._log_latency_stage(
                        "multi_press_complete", presses=action.presses
                    )
                    self._fast_press_started = None
                    self._report_activity(
                        "completed",
                        result={"kind": "press", "action": "already_dispatched"},
                    )
                    return
                if action.presses == 1:
                    self._single_press()
                elif action.presses == 2:
                    self._toggle(self._double_target)
                elif action.presses == 3:
                    self._toggle(self._triple_target)
                else:
                    self._report_activity("skipped", reason="unsupported_press_count")
            elif action.type == ACTION_HOLD:
                self._hold_off_rotation()
                if self._hold_action == HOLD_RAMP:
                    self._start_ramp()
                elif self._hold_action == HOLD_TOGGLE:
                    self._toggle(self._hold_target)
                else:
                    self._report_activity("skipped", reason="hold_not_configured")
            elif action.type == ACTION_RELEASE and self._hold_action == HOLD_RAMP:
                self._stop_ramp(change_direction=True)
                self._report_activity(
                    "completed", result={"kind": "hold", "action": "ramp_stopped"}
                )
            else:
                self._report_activity("skipped", reason="gesture_not_configured")
        finally:
            self._active_action = previous_action

    @callback
    def _handle_connection_change(self) -> None:
        """Stop safety-critical timers whenever Matter connectivity changes."""
        self._fast_press_started = None
        self._reset_latency_trace()
        self._forget_target("matter_connection_change")
        # Across a reconnect nothing is known about where the target got to.
        self._commanded.clear()
        self._last_reported = None
        self._command_authoritative_until = 0.0
        self._last_direction = None
        self._active_scrolls.clear()
        self._last_scroll_seen = None
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
        # An input row: a replay needs the target's own reports, with their
        # timing, to reproduce what the binding was reacting to.
        if self._trace.enabled:
            self._trace.record(
                "state",
                binding=self.trace_key,
                state=None if new_state is None else new_state.state,
                value=None if new_state is None else self._observed_value(new_state),
            )
        if new_state is None or new_state.state in _UNAVAILABLE:
            self._forget_target("target_unavailable")
            # An unavailable target is not travelling anywhere we can describe.
            self._commanded.clear()
            self._last_reported = None
            self._command_authoritative_until = 0.0
            self._stop_ramp(change_direction=False)
            return
        # Matter may batch one continuous scroll for several seconds while the
        # target reports older absolute values between decoded deltas. Keep the
        # newest calculated target authoritative for as long as that scroll is
        # under way; otherwise a delayed zero-transition echo erases confirmed
        # notches. A report that is not one of our own recent values is a real
        # third-party change and still rebases immediately, even mid-scroll.
        now = time.monotonic()
        self._active_scrolls = {
            endpoint_id: last_seen
            for endpoint_id, last_seen in self._active_scrolls.items()
            if now - last_seen < _ACTIVE_SCROLL_TIMEOUT
        }
        observed = self._observed_value(new_state)
        own_echo = self._is_own_echo(new_state)
        # Recorded after the decision, so the next report is judged against
        # where the target has actually got to.
        if observed is not None:
            self._last_reported = observed
        if self._scroll_authoritative(now):
            if not own_echo:
                self._forget_target("unrecognized_value_during_scroll", observed)
            else:
                self._trace.record(
                    "echo_ignored",
                    node_id=self._node_id,
                    channel=self._channel,
                    endpoint=self._endpoint_id,
                    reported=observed,
                    tracked=None if self._tracked is None else round(self._tracked, 2),
                )
            return
        # Outside a scroll, ignore only state echoes covered by the configured
        # service transition. A later external update invalidates the desired
        # value so the next gesture reads reality again.
        if now >= self._command_authoritative_until:
            self._forget_target("outside_scroll_authority", observed)

    def _scroll_authoritative(self, now: float) -> bool:
        """Report whether one continuous scroll still owns the target value."""
        if self._active_scrolls:
            return True
        if self._last_scroll_seen is None:
            return False
        return now - self._last_scroll_seen < _SCROLL_AUTHORITY_GRACE

    def _is_own_echo(self, state: State) -> bool:
        """Report whether a report is consistent with the target catching up.

        Matching the reported value against the ones we sent is wrong for any
        target that moves gradually. A dimmer with its own fade, a Zigbee bulb
        with a default transition, a cover motor travelling for half a minute —
        all report values *between* our commands, which are values we never
        sent and equality can never recognize. Captured on a Shelly Plus 0-10V:
        after commanding 84.15 the target reported 71, which sits between two
        earlier commands, and treating it as somebody else's change threw away
        nine notches at once.

        What identifies our own movement is the trajectory, not the value: the
        target travels from where it last reported towards the newest value we
        gave it, so anything along that path — widened by the mode's own
        quantization — is us. A report off that path is a third-party change.

        Deliberately unaddressed: a light *group* reports the average of its
        members, so no path we describe can contain it. See the group caveat in
        PROJECT_STATUS.
        """
        observed = self._observed_value(state)
        if observed is None or not self._commanded:
            return True
        values = [value for value, _span in self._commanded]
        if self._last_reported is not None:
            values.append(self._last_reported)
        span = max(span for _value, span in self._commanded)
        tolerance = span * _ECHO_MATCH_FRACTION
        if self._mode == MODE_COLOR:
            # Hue wraps, so "between two values" has no meaning; proximity to
            # something we sent is the only usable test.
            return any(
                min(abs(observed - value), span - abs(observed - value)) <= tolerance
                for value in values
            )
        return min(values) - tolerance <= observed <= max(values) + tolerance

    def _observed_value(self, state: State) -> float | None:
        """Return the state value this binding's mode actually rotates."""
        # A state without attributes carries no value to compare against, and
        # this runs on the hot path for every report, so it must not raise.
        attributes = getattr(state, "attributes", None) or {}
        if self._mode == MODE_COLOR_TEMP:
            return _as_float(attributes.get(ATTR_COLOR_TEMP_KELVIN))
        if self._mode == MODE_COLOR:
            hs_color = attributes.get(ATTR_HS_COLOR)
            return _as_float(hs_color[0]) if hs_color else None
        if self._mode == MODE_VOLUME:
            return _as_float(attributes.get("volume_level"))
        if self._mode == MODE_COVER:
            return _as_float(attributes.get("current_position"))
        if self._mode == MODE_TEMPERATURE:
            return _as_float(attributes.get("temperature"))
        if self._mode == MODE_FAN:
            return _as_float(attributes.get("percentage"))
        if self._mode == MODE_NUMBER:
            return _as_float(state.state)
        if state.state != "on":
            return 0.0
        return _as_float(attributes.get(ATTR_BRIGHTNESS))

    @callback
    def _set_target(self, value: float, span: float) -> None:
        """Record the newest calculated target and the range it came from."""
        self._tracked = value
        self._commanded.append((value, max(span, 1e-9)))

    @callback
    def _forget_target(self, reason: str = "unspecified", reported: Any = None) -> None:
        """Drop the calculated target so the next rotation reads reality.

        Every caller names why. A scroll that loses steps almost always lost
        them here, and the reason plus the value that triggered it is what
        turns "steps went missing" into a specific defect.
        """
        if self._tracked is not None:
            self._trace.record(
                "forget",
                node_id=self._node_id,
                channel=self._channel,
                endpoint=self._endpoint_id,
                reason=reason,
                had_tracked=round(self._tracked, 2),
                reported=reported,
                recent_commands=[round(value, 2) for value, _span in self._commanded],
            )
        self._tracked = None
        # The command history is deliberately kept. It describes where the
        # target is still travelling to, and that stays true after we give up
        # our calculated value — clearing it made the very next report look
        # unrecognizable too, turning one rebase into a cascade.

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
    def _handle_raw_input(
        self, role: str, event_type: str, endpoint_id: int | None = None
    ) -> None:
        """Track private gesture boundaries and forward button hints."""
        if self._endpoint_id is not None and endpoint_id != self._endpoint_id:
            return
        if self._trace.enabled:
            # An input row: gesture boundaries drive the authority window, so a
            # replay is not faithful without them.
            self._trace.describe_binding(self.trace_key, self.trace_config())
            self._trace.record(
                "raw",
                binding=self.trace_key,
                role=role,
                event_type=event_type,
                endpoint=endpoint_id,
            )
        if role in (ROLE_SCROLL_UP, ROLE_SCROLL_DOWN):
            now = time.monotonic()
            # Every raw scroll event extends the window in which our own
            # calculated target outranks a lagging absolute state report,
            # including the completion that ends one Matter gesture of a
            # longer physical rotation.
            self._last_scroll_seen = now
            if event_type == _INITIAL_PRESS:
                self._scroll_gesture += 1
                self._active_scrolls[endpoint_id] = now
                self._reset_velocity()
            elif event_type == _COMPLETE:
                # The raw completion precedes its possible final delta action.
                self._active_scrolls.pop(endpoint_id, None)
                self._reset_velocity_after_rotate = True
            elif endpoint_id in self._active_scrolls:
                self._active_scrolls[endpoint_id] = now
            return
        if role != ROLE_BUTTON:
            return
        if event_type == _INITIAL_PRESS:
            self._button_scroll_boundary = self._scroll_gesture
        self._handle_raw_button(event_type)

    @callback
    def _handle_raw_button(self, event_type: str) -> None:
        """Run an unambiguous early single-press binding exactly once."""
        if not self._fast_single and not self._instant_single:
            return
        now = time.monotonic()
        if event_type == _INITIAL_PRESS:
            if (
                self._fast_press_started is not None
                and now - self._fast_press_started > _FAST_PRESS_GESTURE_TIMEOUT
            ):
                self._fast_press_started = None
            if self._instant_single and self._fast_press_started is None:
                self._run_early_single(now, _INITIAL_PRESS)
            return
        if (
            not self._fast_single
            or event_type != _SHORT_RELEASE
            or self._fast_press_started is not None
        ):
            return

        # A hold ends with LongRelease, so ShortRelease is safe for the normal
        # click action. Further releases in the same multi-press gesture are
        # collapsed until its public MultiPressComplete action arrives.
        self._run_early_single(now, _SHORT_RELEASE)

    @callback
    def _run_early_single(self, now: float, stage: str) -> None:
        """Execute the configured single action and arm completion suppression."""
        self._fast_press_started = now
        self._start_latency_trace(now, stage)
        if self._ramp_active:
            self._stop_ramp(change_direction=False)
        self._hold_off_rotation()
        previous_action = self._active_action
        self._active_action = WheelAction(
            node_id=self._node_id,
            wheel_name="",
            channel=self._channel,
            endpoint_id=self._endpoint_id or 0,
            type=ACTION_PRESS,
            presses=1,
        )
        try:
            self._single_press()
        finally:
            self._active_action = previous_action

    def _start_latency_trace(self, now: float, stage: str) -> None:
        """Start a privacy-safe fast-press trace only while DEBUG is enabled."""
        if not _LOGGER.isEnabledFor(logging.DEBUG):
            self._reset_latency_trace()
            return
        self._latency_trace_sequence += 1
        self._latency_trace_started_at = now
        self._latency_trace_target_seen = False
        self._log_latency_stage(stage, now=now)

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

    @callback
    def _report_activity(
        self,
        status: str,
        *,
        result: dict[str, Any] | None = None,
        reason: str | None = None,
        action: WheelAction | None = None,
    ) -> None:
        """Publish one privacy-bounded execution update for the panel."""
        current = action or self._active_action
        if current is None:
            return
        dispatched = (
            True
            if status == "accepted"
            else False
            if status
            in {
                "failed",
                "skipped",
            }
            else None
        )
        async_dispatcher_send(
            self.hass,
            SIGNAL_BINDING_ACTIVITY,
            {
                "action_id": current.action_id,
                "node_id": self._node_id,
                "channel": self._channel,
                "endpoint_id": self._endpoint_id,
                "type": current.type,
                "direction": current.direction,
                "notches": current.notches,
                "presses": current.presses,
                "observed_duration_ms": current.observed_duration_ms,
                "source": current.source,
                "result": result,
                "dispatch_status": status,
                "dispatched": dispatched,
                "reason": reason,
            },
        )

    @staticmethod
    def _value_result(
        kind: str,
        before: float | int,
        after: float | int,
        unit: str,
    ) -> dict[str, Any]:
        """Build the structured result rendered by the live-test view."""
        return {
            "kind": kind,
            "before": before,
            "after": after,
            "unit": unit,
        }

    @callback
    def _call_value_if_changed(
        self,
        domain: str,
        service: str,
        data: dict[str, Any],
        *,
        before: float | int,
        after: float | int,
        result: dict[str, Any],
    ) -> bool:
        """Dispatch a bounded value only when its service payload can change."""
        if before == after:
            self._report_activity(
                "completed",
                result=result,
                reason="target_unchanged",
            )
            return False
        self._call(domain, service, data, result=result)
        return True

    # -- rotation ---------------------------------------------------------

    @callback
    def _rotate(self, action: WheelAction) -> None:
        # The arriving action, before any filter. A capture that only records
        # applied steps cannot show a notch the binding dropped on the way in,
        # which is exactly the kind of loss worth finding.
        suppressed = self._suppress_trailing_rotation()
        if self._trace.enabled:
            self._trace.describe_binding(self.trace_key, self.trace_config())
            self._trace.record(
                "action",
                binding=self.trace_key,
                notches=action.notches,
                direction=action.direction,
                suppressed=suppressed,
            )
        if suppressed:
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
    def _rotate_by(self, notches: int, up: bool) -> bool:
        if not self._mode_target_valid:
            self._report_activity("skipped", reason="mode_target_mismatch")
            self._forget_target("mode_target_mismatch")
            self._stop_ramp(change_direction=False)
            return False
        if self._available_state(self._target) is None:
            self._report_activity("skipped", reason="target_unavailable")
            self._forget_target("target_unavailable")
            self._stop_ramp(change_direction=False)
            return False
        if not self._trace.enabled:
            return self._rotate_mode(notches, up)
        # One row per applied step, covering every mode through the same path.
        # `from_source` is the field worth reading first: "tracked" means the
        # step continued our own calculation, "state" means it restarted from
        # whatever the entity was reporting at that instant.
        self._trace_source = None
        self._trace_from = None
        state = self._available_state(self._target)
        observed = self._observed_value(state) if state is not None else None
        changed = self._rotate_mode(notches, up)
        self._trace.describe_binding(self.trace_key, self.trace_config())
        self._trace.record(
            "rotate",
            binding=self.trace_key,
            node_id=self._node_id,
            channel=self._channel,
            endpoint=self._endpoint_id,
            notches=notches,
            direction=DIRECTION_UP if up else "down",
            from_source=self._trace_source,
            from_value=None if self._trace_from is None else round(self._trace_from, 2),
            state_value=None if observed is None else round(observed, 2),
            target=None if self._tracked is None else round(self._tracked, 2),
            dispatched=changed,
        )
        return changed

    @callback
    def _rotate_mode(self, notches: int, up: bool) -> bool:
        if self._mode == MODE_COLOR_TEMP:
            return self._rotate_color_temp(notches, up)
        if self._mode == MODE_COLOR:
            return self._rotate_color(notches, up)
        if self._mode == MODE_VOLUME:
            return self._rotate_volume(notches, up)
        if self._mode == MODE_COVER:
            return self._rotate_cover(notches, up)
        if self._mode == MODE_TEMPERATURE:
            return self._rotate_temperature(notches, up)
        if self._mode == MODE_FAN:
            return self._rotate_fan(notches, up)
        if self._mode == MODE_NUMBER:
            return self._rotate_number(notches, up)
        return self._rotate_brightness(notches, up)

    # -- hold-to-ramp -----------------------------------------------------

    @callback
    def _start_ramp(self) -> None:
        if (
            self._ramp_active
            or not self._target
            or not self._mode_target_valid
            or self._available_state(self._target) is None
        ):
            self._report_activity("skipped", reason="ramp_unavailable")
            return
        self._ramp_active = True
        self._ramp_action = self._active_action
        changed = self._rotate_by(_RAMP_NOTCHES, self._ramp_up)
        if not self._ramp_active:
            return
        if changed:
            self._ramp_unsub = async_track_time_interval(
                self.hass, self._ramp_tick, _RAMP_INTERVAL
            )
        self._ramp_watchdog_unsub = async_call_later(
            self.hass, _RAMP_WATCHDOG_SECONDS, self._ramp_watchdog
        )

    @callback
    def _ramp_tick(self, _now) -> None:
        previous_action = self._active_action
        self._active_action = self._ramp_action
        try:
            if not self._rotate_by(_RAMP_NOTCHES, self._ramp_up):
                self._pause_ramp_at_limit()
        finally:
            self._active_action = previous_action

    @callback
    def _pause_ramp_at_limit(self) -> None:
        """Stop recurring ticks while retaining release/watchdog accounting."""
        if self._ramp_unsub is None:
            return
        self._ramp_unsub()
        self._ramp_unsub = None

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
        if (
            not self._ramp_active
            and self._ramp_action is None
            and self._ramp_unsub is None
            and self._ramp_watchdog_unsub is None
        ):
            return
        if self._ramp_unsub is not None:
            self._ramp_unsub()
            self._ramp_unsub = None
        if self._ramp_watchdog_unsub is not None:
            self._ramp_watchdog_unsub()
            self._ramp_watchdog_unsub = None
        if change_direction and self._ramp_direction == RAMP_DIRECTION_ALTERNATE:
            self._ramp_up = not self._ramp_up
        self._ramp_active = False
        self._ramp_action = None

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
            # Recorded for the trace: which of these two branches ran is the
            # single most useful fact when a scroll loses steps.
            self._trace_source = "tracked"
            self._trace_from = self._tracked
            return self._tracked
        value = current if current is not None else fallback
        self._trace_source = "state" if current is not None else "fallback"
        self._trace_from = value
        if current is not None:
            # Where the target stands as we start moving it: the far end of the
            # path any report during this gesture will be travelling along.
            # Without it, the first report from a slow target — a cover motor
            # that has barely set off — looks like it came from nowhere.
            self._last_reported = current
        self._tracked = value
        return value

    @staticmethod
    def _delta(step_pct: float, span: float, notches: int, up: bool) -> float:
        magnitude = step_pct / 100 * span * notches
        return magnitude if up else -magnitude

    def _smoothing_transition(self, notches: int) -> float:
        """Return the service transition for one batch of decoded notches.

        A single notch is never smoothed. The eager first notch of a gesture
        is the whole point of the RC.5 optimization, and hold-to-ramp steps
        one notch at a time, so both stay immediate however this is
        configured. Larger batches are the firmware bundling a fast rotation
        into one jump; they are spread proportionally to their size, up to
        the configured transition. Zero disables smoothing entirely.

        The configured value is used as given. A transition longer than the
        roughly 0.5-second spacing between batches will be interrupted by the
        next batch, which is a real effect the owner can hear out during the
        Hardware A/B rather than something to clamp away silently.
        """
        if notches <= 1 or self._transition <= 0:
            return 0.0
        return self._transition * min(1.0, notches / _SMOOTHING_FULL_BATCH)

    @callback
    def _rotate_brightness(self, notches: int, up: bool) -> bool:
        state = self._available_state(self._target)
        if state is None:
            return False
        state_on = state.state == "on"
        current = state.attributes.get(ATTR_BRIGHTNESS) if state_on else 0
        tracked = self._resync(current, 0)
        if not state_on and tracked <= 0 and not up:
            self._report_activity("skipped", reason="light_already_off")
            return False  # don't switch a light on by scrolling down

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
                self._set_target(0, 255)
                self._call(
                    "light",
                    "turn_off",
                    {ATTR_TRANSITION: self._smoothing_transition(notches)},
                    result=self._value_result(
                        "brightness",
                        round(tracked / 255 * 100),
                        0,
                        "%",
                    ),
                )
                return True
            target = self._min_units
        self._set_target(target, 255)
        result = self._value_result(
            "brightness",
            round(tracked / 255 * 100),
            round(target / 255 * 100),
            "%",
        )
        return self._call_value_if_changed(
            "light",
            "turn_on",
            {
                ATTR_BRIGHTNESS: round(target),
                ATTR_TRANSITION: self._smoothing_transition(notches),
            },
            before=round(tracked),
            after=round(target),
            result=result,
        )

    @callback
    def _rotate_color_temp(self, notches: int, up: bool) -> bool:
        state = self._lit_state()
        if state is None:
            return False
        min_k = state.attributes.get(ATTR_MIN_KELVIN, FALLBACK_MIN_KELVIN)
        max_k = state.attributes.get(ATTR_MAX_KELVIN, FALLBACK_MAX_KELVIN)
        tracked = self._resync(
            state.attributes.get(ATTR_COLOR_TEMP_KELVIN), (min_k + max_k) / 2
        )
        target = tracked + self._delta(self._step, max(max_k - min_k, 1), notches, up)
        target = min(max_k, max(min_k, target))
        self._set_target(target, max(max_k - min_k, 1))
        result = self._value_result(
            "color_temperature", round(tracked), round(target), "K"
        )
        return self._call_value_if_changed(
            "light",
            "turn_on",
            {
                ATTR_COLOR_TEMP_KELVIN: round(target),
                ATTR_TRANSITION: self._smoothing_transition(notches),
            },
            before=round(tracked),
            after=round(target),
            result=result,
        )

    @callback
    def _rotate_color(self, notches: int, up: bool) -> bool:
        state = self._lit_state()
        if state is None:
            return False
        hs_color = state.attributes.get(ATTR_HS_COLOR)
        if hs_color:
            self._saturation = float(hs_color[1])
        tracked = self._resync(hs_color[0] if hs_color else None, 0.0)
        hue = (tracked + self._delta(self._step, 360, notches, up)) % 360
        self._set_target(hue, 360)
        self._call(
            "light",
            "turn_on",
            {
                ATTR_HS_COLOR: [round(hue, 1), self._saturation],
                ATTR_TRANSITION: self._smoothing_transition(notches),
            },
            result=self._value_result("hue", round(tracked, 1), round(hue, 1), "°"),
        )
        return True

    @callback
    def _rotate_volume(self, notches: int, up: bool) -> bool:
        state = self._available_state(self._target)
        if state is None:
            return False
        tracked = self._resync(_as_float(state.attributes.get("volume_level")), 0.5)
        target = min(1.0, max(0.0, tracked + self._delta(self._step, 1, notches, up)))
        self._set_target(target, 1)
        result = self._value_result(
            "volume", round(tracked * 100), round(target * 100), "%"
        )
        return self._call_value_if_changed(
            "media_player",
            "volume_set",
            {"volume_level": round(target, 3)},
            before=round(tracked, 3),
            after=round(target, 3),
            result=result,
        )

    @callback
    def _rotate_cover(self, notches: int, up: bool) -> bool:
        state = self._available_state(self._target)
        if state is None:
            return False
        tracked = self._resync(_as_float(state.attributes.get("current_position")), 50)
        target = min(
            100, max(0, round(tracked + self._delta(self._step, 100, notches, up)))
        )
        self._set_target(target, 100)
        result = self._value_result("cover_position", round(tracked), target, "%")
        return self._call_value_if_changed(
            "cover",
            "set_cover_position",
            {"position": target},
            before=round(tracked),
            after=target,
            result=result,
        )

    @callback
    def _rotate_temperature(self, notches: int, up: bool) -> bool:
        state = self._available_state(self._target)
        if state is None:
            return False
        min_t = _as_float(state.attributes.get("min_temp")) or 7.0
        max_t = _as_float(state.attributes.get("max_temp")) or 35.0
        temp_step = _as_float(state.attributes.get("target_temp_step")) or 0.5
        tracked = self._resync(
            _as_float(state.attributes.get("temperature")), (min_t + max_t) / 2
        )
        target = tracked + self._delta(self._step, max(max_t - min_t, 1), notches, up)
        target = min(max_t, max(min_t, round(target / temp_step) * temp_step))
        self._set_target(target, max(max_t - min_t, 1))
        result = self._value_result(
            "temperature",
            round(tracked, 2),
            round(target, 2),
            str(state.attributes.get("unit_of_measurement") or "°"),
        )
        return self._call_value_if_changed(
            "climate",
            "set_temperature",
            {"temperature": round(target, 2)},
            before=round(tracked, 2),
            after=round(target, 2),
            result=result,
        )

    @callback
    def _rotate_fan(self, notches: int, up: bool) -> bool:
        state = self._available_state(self._target)
        if state is None:
            return False
        tracked = self._resync(_as_float(state.attributes.get("percentage")), 50)
        target = min(
            100, max(0, round(tracked + self._delta(self._step, 100, notches, up)))
        )
        self._set_target(target, 100)
        result = self._value_result("fan_speed", round(tracked), target, "%")
        return self._call_value_if_changed(
            "fan",
            "set_percentage",
            {"percentage": target},
            before=round(tracked),
            after=target,
            result=result,
        )

    @callback
    def _rotate_number(self, notches: int, up: bool) -> bool:
        state = self._available_state(self._target)
        if state is None:
            return False
        min_n = _as_float(state.attributes.get("min")) or 0.0
        max_n = _as_float(state.attributes.get("max")) or 100.0
        num_step = _as_float(state.attributes.get("step")) or 1.0
        current = _as_float(state.state)
        tracked = self._resync(current, (min_n + max_n) / 2)
        target = tracked + self._delta(
            self._step, max(max_n - min_n, num_step), notches, up
        )
        target = min(max_n, max(min_n, round(target / num_step) * num_step))
        self._set_target(target, max(max_n - min_n, num_step))
        domain = self._target.split(".", 1)[0]
        result = self._value_result(
            "number",
            round(tracked, 4),
            round(target, 4),
            str(state.attributes.get("unit_of_measurement") or ""),
        )
        return self._call_value_if_changed(
            domain,
            "set_value",
            {"value": round(target, 4)},
            before=round(tracked, 4),
            after=round(target, 4),
            result=result,
        )

    def _lit_state(self) -> State | None:
        state = self._available_state(self._target)
        if state is None:
            self._report_activity("skipped", reason="target_unavailable")
            return None
        if state.state != "on":
            self._report_activity("skipped", reason="light_is_off")
            return None
        return state

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
                self._forget_target("target_became_available")
            _LOGGER.info("BILRESA target %s is available again", entity_id)
        return state

    # -- button presses ---------------------------------------------------

    @callback
    def _single_press(self) -> None:
        if self._scenes:
            scene = self._scenes[self._scene_index]
            if self._call_entity(
                "scene",
                "turn_on",
                scene,
                result={
                    "kind": "scene",
                    "action": "activate",
                    "target": scene,
                    "position": self._scene_index + 1,
                    "total": len(self._scenes),
                },
            ):
                self._scene_index = (self._scene_index + 1) % len(self._scenes)
            return
        if self._click == CLICK_NONE:
            self._report_activity("skipped", reason="short_press_not_configured")
            return
        service = _CLICK_SERVICE.get(self._click, "toggle")
        if self._click_target is None:
            self._report_activity("skipped", reason="target_not_configured")
            return
        self._call_entity(
            "homeassistant",
            service,
            self._click_target,
            result={
                "kind": "entity_action",
                "action": service,
                "target": self._click_target,
            },
        )

    @callback
    def _toggle(self, target: str | None) -> None:
        if target:
            self._call_entity(
                "homeassistant",
                "toggle",
                target,
                result={
                    "kind": "entity_action",
                    "action": "toggle",
                    "target": target,
                },
            )
            return
        self._report_activity("skipped", reason="target_not_configured")

    # -- service helpers --------------------------------------------------

    @callback
    def _call(
        self,
        domain: str,
        service: str,
        data: dict[str, Any],
        *,
        result: dict[str, Any],
    ) -> None:
        if self._available_state(self._target) is None:
            self._report_activity("skipped", result=result, reason="target_unavailable")
            return
        transition = _as_float(data.get(ATTR_TRANSITION)) or 0.0
        self._command_authoritative_until = (
            time.monotonic() + transition + _STATE_ECHO_MARGIN
        )
        payload = {ATTR_ENTITY_ID: self._target, **data}
        action = self._active_action
        self._report_activity("pending", result=result, action=action)
        service_call = self.hass.services.async_call(
            domain, service, payload, blocking=False
        )
        self.hass.async_create_task(
            self._async_dispatch_service(
                domain,
                service,
                service_call,
                result=result,
                action=action,
            )
        )

    @callback
    def _call_entity(
        self,
        domain: str,
        service: str,
        entity_id: str,
        *,
        result: dict[str, Any],
    ) -> bool:
        if self._available_state(entity_id) is None:
            self._report_activity("skipped", result=result, reason="target_unavailable")
            return False
        if entity_id == self._click_target:
            self._log_latency_stage("service_dispatch")
        action = self._active_action
        self._report_activity("pending", result=result, action=action)
        service_call = self.hass.services.async_call(
            domain, service, {ATTR_ENTITY_ID: entity_id}, blocking=False
        )
        self.hass.async_create_task(
            self._async_dispatch_service(
                domain,
                service,
                service_call,
                result=result,
                action=action,
            )
        )
        return True

    async def _async_dispatch_service(
        self,
        domain: str,
        service: str,
        service_call: Awaitable[Any],
        *,
        result: dict[str, Any],
        action: WheelAction | None,
    ) -> None:
        """Report whether Home Assistant accepted this exact service action.

        ``blocking=False`` preserves the tuned dispatch latency. ``accepted``
        means Home Assistant validated and scheduled the service call; it is not
        a claim that the target device physically changed.
        """
        try:
            await service_call
        except Exception as err:
            _LOGGER.warning(
                "BILRESA service dispatch failed: %s.%s (%s)",
                domain,
                service,
                type(err).__name__,
            )
            self._report_activity(
                "failed",
                result=result,
                reason=type(err).__name__,
                action=action,
            )
            return
        self._report_activity("accepted", result=result, action=action)
