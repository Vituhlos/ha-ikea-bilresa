"""Deterministic time for the lab: a clock and a scheduler that never sleep.

Nothing here touches ``time.monotonic`` of the process. The binding reads its
clock through the name ``time`` in its own module; the harness rebinds that one
name (see ``harness.py``), so the rest of the process keeps the real clock.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
import heapq
import itertools
from types import SimpleNamespace
from typing import Any

# A monotonic clock never starts at zero, and the binding treats "no command
# yet" separately from "a command at time zero".
START = 1000.0

_MAX_STEPS = 100_000


def seconds(value: float | timedelta) -> float:
    """Home Assistant timers take seconds or a timedelta; accept both."""
    return value.total_seconds() if isinstance(value, timedelta) else float(value)


class FakeClock:
    """Monotonic time that only moves when the scheduler moves it."""

    def __init__(self, start: float = START) -> None:
        self.start = start
        self.now = start

    def __call__(self) -> float:
        return self.now

    def elapsed(self) -> float:
        """Seconds since the scenario started; what reports print."""
        return round(self.now - self.start, 6)


def fake_time_module(clock: FakeClock) -> Any:
    """A stand-in for the ``time`` module as the binding uses it."""
    return SimpleNamespace(monotonic=clock)


@dataclass(order=True)
class _Timer:
    due: float
    seq: int
    callback: Callable[[float], None] = field(compare=False)
    interval: float | None = field(compare=False, default=None)
    label: str = field(compare=False, default="")
    cancelled: bool = field(compare=False, default=False)


class FakeScheduler:
    """``call_later`` and ``track_time_interval`` without an event loop."""

    def __init__(
        self, clock: FakeClock, after_step: Callable[[], object] | None = None
    ) -> None:
        self._clock = clock
        self._after_step = after_step or (lambda: None)
        self._heap: list[_Timer] = []
        self._seq = itertools.count()
        self.fired = 0

    def call_later(
        self,
        delay: float | timedelta,
        callback: Callable[[float], None],
        label: str = "",
    ) -> Callable[[], None]:
        timer = _Timer(
            self._clock.now + seconds(delay), next(self._seq), callback, None, label
        )
        heapq.heappush(self._heap, timer)
        return self._canceller(timer)

    def every(
        self,
        interval: float | timedelta,
        callback: Callable[[float], None],
        label: str = "",
    ) -> Callable[[], None]:
        step = seconds(interval)
        timer = _Timer(self._clock.now + step, next(self._seq), callback, step, label)
        heapq.heappush(self._heap, timer)
        return self._canceller(timer)

    @staticmethod
    def _canceller(timer: _Timer) -> Callable[[], None]:
        def cancel() -> None:
            timer.cancelled = True

        return cancel

    def advance(self, delta: float) -> None:
        self.advance_to(self._clock.now + delta)

    def advance_to(self, target: float) -> None:
        """Run every timer due up to ``target``, in order, then stop there."""
        steps = 0
        while self._heap and self._heap[0].due <= target:
            timer = heapq.heappop(self._heap)
            if timer.cancelled:
                continue
            self._clock.now = max(self._clock.now, timer.due)
            if timer.interval is not None:
                timer.due += timer.interval
                timer.seq = next(self._seq)
                heapq.heappush(self._heap, timer)
            timer.callback(self._clock.now)
            self.fired += 1
            self._after_step()
            steps += 1
            if steps > _MAX_STEPS:
                raise RuntimeError("scheduler ran away: more than 100000 timers")
        self._clock.now = max(self._clock.now, target)

    def pending(self) -> list[str]:
        """Labels of the timers still waiting, for the cleanup assertions."""
        return sorted(t.label or "?" for t in self._heap if not t.cancelled)

    def cancel_all(self) -> None:
        for timer in self._heap:
            timer.cancelled = True
