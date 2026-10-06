"""Turn raw BILRESA switch events into clean, per-gesture wheel actions.

The device starts a scroll with ``initial_press``, then reports
``multi_press_ongoing`` counts that are **cumulative within a gesture** and may
jump by several notches at a time behind a firmware batching delay. A final
``multi_press_complete`` carries the total.

Every confirmed notch carried by ``initial_press`` is emitted immediately.
Later cumulative reports subtract those already-dispatched previews and emit
only the remaining delta. This preserves exact totals while avoiding the
firmware's wait before visible response.

State is keyed by ``(node_id, endpoint_id)``, so any number of wheels and
channels are handled independently.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import logging
import time
from uuid import uuid4

from .const import (
    ACTION_HOLD,
    ACTION_PRESS,
    ACTION_RELEASE,
    ACTION_ROTATE,
    DIRECTION_DOWN,
    DIRECTION_UP,
    EVT_INITIAL_PRESS,
    EVT_LONG_PRESS,
    EVT_LONG_RELEASE,
    EVT_MULTI_PRESS_COMPLETE,
    EVT_MULTI_PRESS_ONGOING,
    EVT_SHORT_RELEASE,
    ROLE_BUTTON,
    ROLE_SCROLL_DOWN,
    ROLE_SCROLL_UP,
    SWITCH_EVENT_NAMES,
)
from .model import BilresaWheel

_LOGGER = logging.getLogger(__name__)

_ONGOING = SWITCH_EVENT_NAMES[EVT_MULTI_PRESS_ONGOING]
_COMPLETE = SWITCH_EVENT_NAMES[EVT_MULTI_PRESS_COMPLETE]
_INITIAL_PRESS = SWITCH_EVENT_NAMES[EVT_INITIAL_PRESS]
_LONG_PRESS = SWITCH_EVENT_NAMES[EVT_LONG_PRESS]
_LONG_RELEASE = SWITCH_EVENT_NAMES[EVT_LONG_RELEASE]


@dataclass(slots=True)
class WheelAction:
    """A decoded, high-level action ready to drive entities and bindings."""

    node_id: int
    wheel_name: str
    channel: int | None
    endpoint_id: int
    type: str  # ACTION_ROTATE / _PRESS / _HOLD / _RELEASE
    direction: str | None = None  # DIRECTION_UP / DIRECTION_DOWN for rotate
    notches: int = 0  # rotate delta (this event only)
    presses: int = 0  # 1 / 2 / 3 for press
    observed_duration_ms: int | None = None
    action_id: str = field(default_factory=lambda: uuid4().hex)
    source: str = "matter"


class GestureEngine:
    """Stateful decoder: raw switch events -> WheelAction stream."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        # cumulative press count seen so far in the current gesture, per endpoint
        self._counts: dict[tuple[int, int], int] = {}
        # InitialPress notches already emitted before a cumulative report.
        self._previewed_notches: dict[tuple[int, int], int] = {}
        self._press_started: dict[tuple[int, int], float] = {}
        # Best-effort Switch.CurrentPosition state. Attribute reports may be
        # coalesced by matterjs-server, so this is only a stuck-state safety
        # signal; actions are always derived from ordered node_event messages.
        self._positions: dict[tuple[int, int], int] = {}

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

        if event_type == _INITIAL_PRESS:
            self._previewed_notches[key] = self._previewed_notches.get(key, 0) + 1
            delta = 1
        elif event_type in (_ONGOING, _COMPLETE):
            switch = wheel.endpoints.get(decoded["endpoint_id"])
            multi_press_max = switch.multi_press_max if switch is not None else None
            valid_count = (
                isinstance(count, int)
                and not isinstance(count, bool)
                and count >= 0
                and (multi_press_max is None or count <= multi_press_max)
            )
            if not valid_count or count == 0:
                # A completion is still an authoritative sequence boundary even
                # when its uint8 count is absent, malformed or the Matter 1.6
                # overflow sentinel zero. Confirmed InitialPress actions cannot
                # be undone, but stale accounting must not leak forward.
                if event_type == _COMPLETE:
                    self._counts.pop(key, None)
                    self._previewed_notches.pop(key, None)
                return None

            assert isinstance(count, int) and not isinstance(count, bool)
            counted = count
            last = self._counts.get(key, 0)
            if counted < last:  # counter wrapped -> a new gesture started
                last = 0
            cumulative_delta = max(counted - last, 0)
            previewed = self._previewed_notches.get(key, 0)
            credited = min(cumulative_delta, previewed)
            delta = cumulative_delta - credited
            previewed -= credited

            if event_type == _COMPLETE:
                self._counts.pop(key, None)
                self._previewed_notches.pop(key, None)
            else:
                self._counts[key] = counted
                if previewed:
                    self._previewed_notches[key] = previewed
                else:
                    self._previewed_notches.pop(key, None)
        else:
            # short_release / long_* carry no additional scroll delta
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
        endpoint_id = decoded["endpoint_id"]
        key = (wheel.node_id, endpoint_id)
        if event_type == SWITCH_EVENT_NAMES[EVT_INITIAL_PRESS]:
            self._press_started[key] = self._clock()
            return None
        if event_type == SWITCH_EVENT_NAMES[EVT_SHORT_RELEASE]:
            self._press_started.pop(key, None)
            return None

        observed_duration_ms = self._observed_duration_ms(key)
        base = {
            "node_id": wheel.node_id,
            "wheel_name": wheel.name,
            "channel": decoded["channel"],
            "endpoint_id": endpoint_id,
        }
        if event_type == _COMPLETE:
            self._press_started.pop(key, None)
            count = decoded.get("count")
            if count is None:
                presses = 1
            elif not isinstance(count, int) or isinstance(count, bool) or count <= 0:
                # Matter 1.6 explicitly permits a zero completion count when
                # MultiPressMax was exceeded. Never reinterpret that as a
                # single press.
                return None
            else:
                presses = count
            switch = wheel.endpoints.get(decoded["endpoint_id"])
            if (
                switch is not None
                and switch.multi_press_max is not None
                and presses > switch.multi_press_max
            ):
                return None
            return WheelAction(**base, type=ACTION_PRESS, presses=presses)
        if event_type == _LONG_PRESS:
            return WheelAction(
                **base,
                type=ACTION_HOLD,
                observed_duration_ms=observed_duration_ms,
            )
        if event_type == _LONG_RELEASE:
            self._press_started.pop(key, None)
            return WheelAction(
                **base,
                type=ACTION_RELEASE,
                observed_duration_ms=observed_duration_ms,
            )
        # initial_press / short_release / ongoing -> not actionable on a button
        return None

    def _observed_duration_ms(self, key: tuple[int, int]) -> int | None:
        """Return a bounded host-observed duration for one uninterrupted press."""
        started = self._press_started.get(key)
        if started is None:
            return None
        elapsed = self._clock() - started
        if elapsed < 0:
            return None
        return min(round(elapsed * 1000), 3_600_000)

    def observe_position(self, node_id: int, endpoint_id: int, position: int) -> None:
        """Observe Switch.CurrentPosition without synthesizing an action.

        matterjs-server 1.2.x coalesces attribute reports under backpressure.
        Position changes must never be counted as clicks, chords or sequences.
        A scroll endpoint returns to zero for an individual notch while its
        cumulative multi-press sequence may still be active, so this hint must
        not clear scroll counts or an eager first-notch credit.
        """
        key = (node_id, endpoint_id)
        self._positions[key] = position
        if position == 0:
            self._press_started.pop(key, None)

    def reset(self) -> None:
        """Drop all gesture state (e.g. on reconnect)."""
        self._counts.clear()
        self._previewed_notches.clear()
        self._positions.clear()
        self._press_started.clear()
