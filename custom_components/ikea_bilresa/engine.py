"""Turn raw BILRESA switch events into clean, per-gesture wheel actions.

The device reports a scroll as a stream of ``multi_press_ongoing`` events whose
``currentNumberOfPressesCounted`` is **cumulative within a gesture** and jumps
by several notches at a time (the wheel batches them behind a ~1 s anti-flood
delay), followed by a ``multi_press_complete`` with the final total. To move a
light by the right amount in real time we therefore track the running count per
endpoint and emit the **delta** on every update.

State is keyed by ``(node_id, endpoint_id)``, so any number of wheels and
channels are handled independently.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging

from .const import (
    ACTION_HOLD,
    ACTION_PRESS,
    ACTION_RELEASE,
    ACTION_ROTATE,
    DIRECTION_DOWN,
    DIRECTION_UP,
    EVT_LONG_PRESS,
    EVT_LONG_RELEASE,
    EVT_MULTI_PRESS_COMPLETE,
    EVT_MULTI_PRESS_ONGOING,
    ROLE_BUTTON,
    ROLE_SCROLL_DOWN,
    ROLE_SCROLL_UP,
    SWITCH_EVENT_NAMES,
)
from .model import BilresaWheel

_LOGGER = logging.getLogger(__name__)

_ONGOING = SWITCH_EVENT_NAMES[EVT_MULTI_PRESS_ONGOING]
_COMPLETE = SWITCH_EVENT_NAMES[EVT_MULTI_PRESS_COMPLETE]
_LONG_PRESS = SWITCH_EVENT_NAMES[EVT_LONG_PRESS]
_LONG_RELEASE = SWITCH_EVENT_NAMES[EVT_LONG_RELEASE]


@dataclass(slots=True)
class WheelAction:
    """A decoded, high-level action ready to drive entities and bindings."""

    node_id: int
    wheel_name: str
    channel: int | None
    endpoint_id: int
    type: str                     # ACTION_ROTATE / ACTION_PRESS / ACTION_HOLD / ACTION_RELEASE
    direction: str | None = None  # DIRECTION_UP / DIRECTION_DOWN for rotate
    notches: int = 0              # rotate delta (this event only)
    presses: int = 0             # 1 / 2 / 3 for press


class GestureEngine:
    """Stateful decoder: raw switch events -> WheelAction stream."""

    def __init__(self) -> None:
        # cumulative press count seen so far in the current gesture, per endpoint
        self._counts: dict[tuple[int, int], int] = {}

    def process(self, wheel: BilresaWheel, decoded: dict) -> WheelAction | None:
        """Feed one decoded raw event; return a clean action or None."""
        role = decoded["role"]
        if role in (ROLE_SCROLL_UP, ROLE_SCROLL_DOWN):
            return self._rotate(wheel, decoded, role)
        if role == ROLE_BUTTON:
            return self._button(wheel, decoded)
        return None

    def _rotate(
        self, wheel: BilresaWheel, decoded: dict, role: str
    ) -> WheelAction | None:
        event_type = decoded["event_type"]
        count = decoded.get("count")
        key = (wheel.node_id, decoded["endpoint_id"])

        if event_type == _ONGOING and count is not None:
            last = self._counts.get(key, 0)
            if count <= last:  # counter wrapped -> a new gesture started
                last = 0
            delta = count - last
            self._counts[key] = count
        elif event_type == _COMPLETE and count is not None:
            last = self._counts.get(key, 0)
            if count < last:
                last = 0
            delta = count - last
            self._counts[key] = 0  # gesture finished, reset baseline
        else:
            # initial_press / short_release / long_* carry no scroll delta
            return None

        if delta <= 0:
            return None

        return WheelAction(
            node_id=wheel.node_id,
            wheel_name=wheel.name,
            channel=decoded["channel"],
            endpoint_id=decoded["endpoint_id"],
            type=ACTION_ROTATE,
            direction=DIRECTION_UP if role == ROLE_SCROLL_UP else DIRECTION_DOWN,
            notches=delta,
        )

    def _button(self, wheel: BilresaWheel, decoded: dict) -> WheelAction | None:
        event_type = decoded["event_type"]
        base = {
            "node_id": wheel.node_id,
            "wheel_name": wheel.name,
            "channel": decoded["channel"],
            "endpoint_id": decoded["endpoint_id"],
        }
        if event_type == _COMPLETE:
            presses = decoded.get("count") or 1
            return WheelAction(**base, type=ACTION_PRESS, presses=presses)
        if event_type == _LONG_PRESS:
            return WheelAction(**base, type=ACTION_HOLD)
        if event_type == _LONG_RELEASE:
            return WheelAction(**base, type=ACTION_RELEASE)
        # initial_press / short_release / ongoing -> not actionable on a button
        return None

    def reset(self) -> None:
        """Drop all gesture state (e.g. on reconnect)."""
        self._counts.clear()
