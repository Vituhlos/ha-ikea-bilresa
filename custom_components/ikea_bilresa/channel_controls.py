"""Per-wheel channel settings, the shared scroll accelerator, and dial math.

Pure logic, importable without Home Assistant, so it stays unit-testable the
same way `engine.py` is.

`ScrollAccelerator` was lifted out of `BindingRuntime` unchanged: the channel
dials must accelerate by the same law as a light on the same wheel, and one
`Acceleration` setting that meant two different things depending on which
consumer read it would be a trap. Batch size is deliberately *not* the input —
rc.5 emits an eager notch per `InitialPress`, so a fast rotation arrives as
alternating one-notch and multi-notch rows and batch size measures our own
dispatch shape rather than how fast the wheel is turning.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
import time
from typing import Any

from .const import (
    CONF_ACCELERATION,
    CONF_CHANNEL_ENABLED,
    CONF_NODE_ID,
    CONF_STEP,
    DEFAULT_ACCELERATION,
    DEFAULT_DIAL_STEP,
    DIAL_MAX,
    DIAL_MIN,
)

# Velocity model tuning. Moved here with the accelerator; `binding.py` keeps
# importing them so the values stay a single source of truth.
VELOCITY_WINDOW = 2.0
VELOCITY_IDLE_RESET = 1.5
VELOCITY_FLOOR = 2.0
VELOCITY_FULL_SCALE = 10.0
MAX_ACCELERATION_MULTIPLIER = 3.0


class ScrollAccelerator:
    """Scale a notch delta by how fast the wheel is actually turning.

    Samples are kept over a moving window rather than judged one batch at a
    time, and the multiplier is capped, so a single large batch cannot slam a
    bounded target to its limit.
    """

    def __init__(
        self,
        acceleration: float,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """Take acceleration as the stored 0-100 percentage.

        The clock is resolved per call rather than bound here: `time.monotonic`
        captured as a default would freeze the original function at import and
        silently ignore a monkeypatched one.
        """
        self._fraction = float(acceleration) / 100
        self._clock = clock
        self._samples: deque[tuple[float, int]] = deque()
        self._direction: str | None = None

    def _now(self) -> float:
        return self._clock() if self._clock is not None else time.monotonic()

    @property
    def percent(self) -> float:
        """The configured acceleration as stored, for diagnostics."""
        return self._fraction * 100

    @property
    def enabled(self) -> bool:
        """Whether acceleration does anything at all."""
        return self._fraction > 0

    def accelerate(self, notches: int, direction: str | None = None) -> int:
        """Scale one arriving rotation by the measured velocity."""
        if self._fraction <= 0:
            return notches
        now = self._now()
        if (
            self._direction != direction
            or not self._samples
            or now - self._samples[-1][0] > VELOCITY_IDLE_RESET
        ):
            self._samples.clear()
        self._direction = direction
        self._samples.append((now, notches))
        while len(self._samples) > 1 and now - self._samples[0][0] > VELOCITY_WINDOW:
            self._samples.popleft()
        if len(self._samples) < 2:
            return notches

        elapsed = now - self._samples[0][0]
        if elapsed <= 0:
            return notches
        # The first sample establishes the time boundary; later deltas belong
        # to the measured interval and are independent of its initial batch.
        velocity = sum(sample[1] for sample in list(self._samples)[1:]) / elapsed
        intensity = min(
            1.0,
            max(
                0.0,
                (velocity - VELOCITY_FLOOR) / (VELOCITY_FULL_SCALE - VELOCITY_FLOOR),
            ),
        )
        multiplier = 1 + self._fraction * intensity * (MAX_ACCELERATION_MULTIPLIER - 1)
        return max(notches, round(notches * multiplier))

    def reset(self) -> None:
        """Forget the measured velocity, e.g. on reconnect or a new gesture."""
        self._samples.clear()
        self._direction = None


@dataclass(slots=True, frozen=True)
class WheelSettings:
    """Settings for one wheel: which channels act, and how its dials move.

    Persisted in a `wheel_settings` config subentry, but edited from the panel
    rather than a config-flow handler, so there is no flow to keep in step.
    """

    node_id: int | None
    disabled_channels: frozenset[int]
    step: float
    acceleration: float

    @classmethod
    def from_data(cls, data: Mapping[str, Any]) -> WheelSettings:
        """Build settings from a `wheel_settings` subentry's stored data."""
        raw_node = data.get(CONF_NODE_ID)
        try:
            node_id = int(raw_node) if raw_node is not None else None
        except (TypeError, ValueError):
            node_id = None
        # Stored as a map of channel -> bool. Absent means enabled, so a wheel
        # whose channel set grows later does not silently gain dead channels.
        raw_enabled = data.get(CONF_CHANNEL_ENABLED) or {}
        disabled: set[int] = set()
        if isinstance(raw_enabled, Mapping):
            for key, value in raw_enabled.items():
                try:
                    channel = int(key)
                except (TypeError, ValueError):
                    continue
                if not value:
                    disabled.add(channel)
        return cls(
            node_id=node_id,
            disabled_channels=frozenset(disabled),
            step=float(data.get(CONF_STEP, DEFAULT_DIAL_STEP)),
            acceleration=float(data.get(CONF_ACCELERATION, DEFAULT_ACCELERATION)),
        )

    def channel_enabled(self, channel: int | None) -> bool:
        """Whether actions on this channel should be processed at all.

        A `None` channel is a dual button's endpoint, which has no channel to
        disable, so it is always allowed through.
        """
        return channel is None or channel not in self.disabled_channels


DEFAULT_SETTINGS = WheelSettings.from_data({})


def apply_rotation(value: float, notches: int, up: bool, step: float) -> float:
    """Move a dial value by an already-accelerated rotation, clamped to range."""
    delta = step * notches
    target = value + delta if up else value - delta
    return min(DIAL_MAX, max(DIAL_MIN, target))
