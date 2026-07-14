"""Turnkey light bindings configured via config subentries.

A binding subscribes to one wheel channel and drives a target light directly:
scrolling adjusts brightness (per-notch delta x step, with a transition so the
light ramps smoothly between the wheel's batched updates), and a single button
press runs the configured action.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
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
    CONF_NODE_ID,
    CONF_STEP,
    CONF_TARGET,
    CONF_TRANSITION,
    DEFAULT_CLICK_ACTION,
    DEFAULT_STEP,
    DEFAULT_TRANSITION,
    DIRECTION_UP,
    signal_channel,
)
from .engine import WheelAction

_LOGGER = logging.getLogger(__name__)

_CLICK_SERVICE = {"toggle": "toggle", CLICK_ON: "turn_on", CLICK_OFF: "turn_off"}


class LightBinding:
    """Runtime for one GUI-configured wheel-channel -> light binding."""

    def __init__(self, hass: HomeAssistant, data: dict[str, Any]) -> None:
        self.hass = hass
        self._node_id = int(data[CONF_NODE_ID])
        self._channel = int(data[CONF_CHANNEL])
        self._target = data[CONF_TARGET]
        self._step = float(data.get(CONF_STEP, DEFAULT_STEP))
        self._transition = float(data.get(CONF_TRANSITION, DEFAULT_TRANSITION))
        self._click = data.get(CONF_CLICK_ACTION, DEFAULT_CLICK_ACTION)

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
        step_pct = self._step * max(action.notches, 1)
        if action.direction != DIRECTION_UP:
            step_pct = -step_pct
        self._call(
            "turn_on",
            {
                "brightness_step_pct": step_pct,
                "transition": self._transition,
            },
        )

    @callback
    def _click_button(self) -> None:
        if self._click == CLICK_NONE:
            return
        self._call(_CLICK_SERVICE.get(self._click, "toggle"))

    @callback
    def _call(self, service: str, data: dict[str, Any] | None = None) -> None:
        payload = {ATTR_ENTITY_ID: self._target}
        if data:
            payload.update(data)
        self.hass.async_create_task(
            self.hass.services.async_call("light", service, payload, blocking=False)
        )
