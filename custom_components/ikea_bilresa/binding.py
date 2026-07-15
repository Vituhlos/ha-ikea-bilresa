"""Turnkey light bindings configured via config subentries.

A binding subscribes to one wheel channel and drives a target light directly.
Scrolling adjusts brightness, colour temperature or colour (the binding's
*mode*); a single / double / triple press and a hold each run an optional
action, which may target a *different* entity (e.g. dim a bulb but toggle the
Shelly in the wall switch).

Values are tracked internally as an absolute target rather than issued as
relative steps. This avoids reading a mid-transition value back from the light
(a race during fast scrolling) and the abrupt "snap off" of ``*_step`` calls.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
import time
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    ACTION_HOLD,
    ACTION_PRESS,
    ACTION_ROTATE,
    CLICK_NONE,
    CLICK_OFF,
    CLICK_ON,
    CONF_ACCELERATION,
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_HOLD_TARGET,
    CONF_MAX_BRIGHTNESS,
    CONF_MIN_BRIGHTNESS,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_STEP,
    CONF_TARGET,
    CONF_TRANSITION,
    CONF_TRIPLE_TARGET,
    DEFAULT_ACCELERATION,
    DEFAULT_CLICK_ACTION,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MODE,
    DEFAULT_STEP,
    DEFAULT_TRANSITION,
    DIRECTION_UP,
    FALLBACK_MAX_KELVIN,
    FALLBACK_MIN_KELVIN,
    MODE_COLOR,
    MODE_COLOR_TEMP,
    signal_channel,
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

# How long our tracked target stays authoritative before we resync from state.
_RESYNC_AFTER = 3.0

# After a button press, ignore scroll events briefly so trailing rotation events
# (the wheel keeps emitting its batch for ~1 s) can't override a press-to-off.
_SUPPRESS_ROTATE_AFTER_PRESS = 0.8


def _pct_to_units(pct: float) -> int:
    return round(pct / 100 * 255)


class LightBinding:
    """Runtime for one GUI-configured wheel-channel -> light binding."""

    def __init__(self, hass: HomeAssistant, data: dict[str, Any]) -> None:
        self.hass = hass
        self._node_id = int(data[CONF_NODE_ID])
        self._channel = int(data[CONF_CHANNEL])
        self._target = data[CONF_TARGET]
        self._mode = data.get(CONF_MODE, DEFAULT_MODE)
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
        # per-mode tracked target and the last-touched timestamp
        self._tracked: float | None = None
        self._saturation = 100.0
        self._last = 0.0
        self._suppress_rotate_until = 0.0

    @callback
    def async_attach(self) -> Callable[[], None]:
        """Start listening for this channel's actions; returns an unsubscribe."""
        return async_dispatcher_connect(
            self.hass,
            signal_channel(self._node_id, self._channel),
            self._handle_action,
        )

    @callback
    def _handle_action(self, action: WheelAction) -> None:
        if action.type == ACTION_ROTATE:
            if time.monotonic() < self._suppress_rotate_until:
                return
            self._rotate(action)
        elif action.type == ACTION_PRESS:
            self._hold_off_rotation()
            if action.presses == 1:
                self._single_press()
            elif action.presses == 2:
                self._toggle(self._double_target)
            elif action.presses == 3:
                self._toggle(self._triple_target)
        elif action.type == ACTION_HOLD:
            self._hold_off_rotation()
            self._toggle(self._hold_target)

    @callback
    def _hold_off_rotation(self) -> None:
        self._suppress_rotate_until = time.monotonic() + _SUPPRESS_ROTATE_AFTER_PRESS

    # -- rotation ---------------------------------------------------------

    @callback
    def _rotate(self, action: WheelAction) -> None:
        notches = self._accelerate(action.notches)
        up = action.direction == DIRECTION_UP
        if self._mode == MODE_COLOR_TEMP:
            self._rotate_color_temp(notches, up)
        elif self._mode == MODE_COLOR:
            self._rotate_color(notches, up)
        else:
            self._rotate_brightness(notches, up)

    def _accelerate(self, notches: int) -> int:
        if self._accel <= 0:
            return notches
        return max(1, round(notches * (1 + self._accel * (notches - 1))))

    def _resync(self, current: float | None, fallback: float) -> float:
        """Return the tracked target, resyncing from reality when idle."""
        now = time.monotonic()
        recent = self._tracked is not None and (now - self._last) < _RESYNC_AFTER
        self._last = now
        if not recent:
            self._tracked = current if current is not None else fallback
        return self._tracked

    @callback
    def _rotate_brightness(self, notches: int, up: bool) -> None:
        state = self.hass.states.get(self._target)
        state_on = state is not None and state.state == "on"
        current = state.attributes.get(ATTR_BRIGHTNESS) if state_on else 0
        tracked = self._resync(current, 0)
        if not state_on and tracked <= 0 and not up:
            return  # don't switch a light on by scrolling down

        step = _pct_to_units(self._step) * notches
        target = tracked + (step if up else -step)
        if target >= self._max_units:
            target = self._max_units
        elif target <= self._min_units:
            if self._min_units <= 0:
                self._tracked = 0
                self._call_light("turn_off", {ATTR_TRANSITION: self._transition})
                return
            target = self._min_units
        self._tracked = target
        self._call_light(
            "turn_on",
            {ATTR_BRIGHTNESS: round(target), ATTR_TRANSITION: self._transition},
        )

    @callback
    def _rotate_color_temp(self, notches: int, up: bool) -> None:
        state = self.hass.states.get(self._target)
        if state is None or state.state != "on":
            return  # colour changes only make sense on a lit light
        min_k = state.attributes.get(ATTR_MIN_KELVIN, FALLBACK_MIN_KELVIN)
        max_k = state.attributes.get(ATTR_MAX_KELVIN, FALLBACK_MAX_KELVIN)
        tracked = self._resync(
            state.attributes.get(ATTR_COLOR_TEMP_KELVIN), (min_k + max_k) / 2
        )
        step = self._step / 100 * max(max_k - min_k, 1) * notches
        target = min(max_k, max(min_k, tracked + (step if up else -step)))
        self._tracked = target
        self._call_light(
            "turn_on",
            {ATTR_COLOR_TEMP_KELVIN: round(target), ATTR_TRANSITION: self._transition},
        )

    @callback
    def _rotate_color(self, notches: int, up: bool) -> None:
        state = self.hass.states.get(self._target)
        if state is None or state.state != "on":
            return
        hs_color = state.attributes.get(ATTR_HS_COLOR)
        if hs_color:
            self._saturation = float(hs_color[1])
        tracked = self._resync(hs_color[0] if hs_color else None, 0.0)
        step = self._step / 100 * 360 * notches
        hue = (tracked + (step if up else -step)) % 360
        self._tracked = hue
        self._call_light(
            "turn_on",
            {
                ATTR_HS_COLOR: [round(hue, 1), self._saturation],
                ATTR_TRANSITION: self._transition,
            },
        )

    # -- button presses ---------------------------------------------------

    @callback
    def _single_press(self) -> None:
        if self._click == CLICK_NONE:
            return
        service = _CLICK_SERVICE.get(self._click, "toggle")
        self._call("homeassistant", service, self._click_target)

    @callback
    def _toggle(self, target: str | None) -> None:
        if target:
            self._call("homeassistant", "toggle", target)

    # -- service helpers --------------------------------------------------

    @callback
    def _call_light(self, service: str, data: dict[str, Any]) -> None:
        payload = {ATTR_ENTITY_ID: self._target, **data}
        self.hass.async_create_task(
            self.hass.services.async_call("light", service, payload, blocking=False)
        )

    @callback
    def _call(self, domain: str, service: str, entity_id: str) -> None:
        self.hass.async_create_task(
            self.hass.services.async_call(
                domain, service, {ATTR_ENTITY_ID: entity_id}, blocking=False
            )
        )
