"""Turnkey light bindings configured via config subentries.

A binding subscribes to one wheel channel and drives a target light directly:
scrolling adjusts brightness and a single button press runs the configured
action (optionally on a *different* entity — e.g. dim a bulb but toggle the
Shelly in the wall switch).

Brightness is tracked internally as an absolute target rather than issued as
percentage steps. This avoids two problems: reading a mid-transition brightness
back from the light (a race during fast scrolling), and the abrupt "hold near
the bottom then snap off" behaviour of ``brightness_step_pct``. Scrolling down
eases to a configurable **minimum** and stays there; only ``min_brightness = 0``
lets a downward scroll switch the light off.
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
    ACTION_PRESS,
    ACTION_ROTATE,
    CLICK_NONE,
    CLICK_OFF,
    CLICK_ON,
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_CLICK_TARGET,
    CONF_MIN_BRIGHTNESS,
    CONF_NODE_ID,
    CONF_STEP,
    CONF_TARGET,
    CONF_TRANSITION,
    DEFAULT_CLICK_ACTION,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_STEP,
    DEFAULT_TRANSITION,
    DIRECTION_UP,
    signal_channel,
)
from .engine import WheelAction

_LOGGER = logging.getLogger(__name__)

ATTR_BRIGHTNESS = "brightness"
ATTR_TRANSITION = "transition"

_CLICK_SERVICE = {"toggle": "toggle", CLICK_ON: "turn_on", CLICK_OFF: "turn_off"}

# How long our tracked target stays authoritative before we resync from the
# light's real state (to pick up brightness changed elsewhere).
_RESYNC_AFTER = 3.0


def _pct_to_units(pct: float) -> int:
    return round(pct / 100 * 255)


class LightBinding:
    """Runtime for one GUI-configured wheel-channel -> light binding."""

    def __init__(self, hass: HomeAssistant, data: dict[str, Any]) -> None:
        self.hass = hass
        self._node_id = int(data[CONF_NODE_ID])
        self._channel = int(data[CONF_CHANNEL])
        self._target = data[CONF_TARGET]
        self._step = float(data.get(CONF_STEP, DEFAULT_STEP))
        self._min_units = _pct_to_units(
            float(data.get(CONF_MIN_BRIGHTNESS, DEFAULT_MIN_BRIGHTNESS))
        )
        self._transition = float(data.get(CONF_TRANSITION, DEFAULT_TRANSITION))
        self._click = data.get(CONF_CLICK_ACTION, DEFAULT_CLICK_ACTION)
        self._click_target = data.get(CONF_CLICK_TARGET) or self._target
        self._tracked: int | None = None
        self._last = 0.0

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
            self._rotate(action)
        elif action.type == ACTION_PRESS and action.presses == 1:
            self._click_button()

    @callback
    def _rotate(self, action: WheelAction) -> None:
        now = time.monotonic()
        recent = self._tracked is not None and (now - self._last) < _RESYNC_AFTER
        state = self.hass.states.get(self._target)
        state_on = state is not None and state.state == "on"

        if not recent:
            # Resync our target from reality when idle or first use.
            current = state.attributes.get(ATTR_BRIGHTNESS) if state_on else 0
            self._tracked = int(current) if current is not None else 0

        self._last = now
        up = action.direction == DIRECTION_UP
        effective_on = state_on or (self._tracked or 0) > 0
        if not effective_on and not up:
            # Don't switch a light on just by scrolling down.
            return

        step_units = _pct_to_units(self._step) * max(action.notches, 1)
        target = (self._tracked or 0) + (step_units if up else -step_units)

        if target >= 255:
            target = 255
        elif target <= self._min_units:
            if self._min_units <= 0:
                self._tracked = 0
                self._call_light("turn_off", {ATTR_TRANSITION: self._transition})
                return
            target = self._min_units

        self._tracked = target
        self._call_light(
            "turn_on", {ATTR_BRIGHTNESS: target, ATTR_TRANSITION: self._transition}
        )

    @callback
    def _click_button(self) -> None:
        if self._click == CLICK_NONE:
            return
        service = _CLICK_SERVICE.get(self._click, "toggle")
        # Use the universal homeassistant domain so the button can target any
        # toggleable entity (a Shelly switch, a light, an input_boolean, ...).
        self.hass.async_create_task(
            self.hass.services.async_call(
                "homeassistant",
                service,
                {ATTR_ENTITY_ID: self._click_target},
                blocking=False,
            )
        )

    @callback
    def _call_light(self, service: str, data: dict[str, Any]) -> None:
        payload = {ATTR_ENTITY_ID: self._target, **data}
        self.hass.async_create_task(
            self.hass.services.async_call("light", service, payload, blocking=False)
        )
