"""A bounded black box for absolute-value rotation, readable from diagnostics.

Rotation bugs in this integration are not visible in a text log. What matters
is *why* one step started from the value it did — whether the binding used its
own calculated target or re-read the entity, and if it re-read it, which state
report threw the calculated one away. Text logs answer neither question, and in
practice a busy Home Assistant log rotates the interesting lines out of reach
before they can be read.

So each step is recorded as a structured row in a ring buffer, and the buffer
is served through the existing diagnostics download. Nothing is written unless
tracing is switched on, and the buffer is bounded, so leaving it on costs a
fixed amount of memory and no I/O.

**A capture is also an input, not only a report.** Rows carry the raw Matter
events, the target's own state reports and their relative timing, which is
everything `tests/replay.py` needs to drive a binding through the same sequence
offline — no Home Assistant, no hardware, no waiting for a release cycle. A
capture of a real defect therefore becomes a permanent regression test, and two
candidate fixes can be compared on identical input instead of on two different
turns of a wheel.

Household identifiers are not special-cased here: rows carry ``node_id`` and
``target`` under exactly those keys, and ``diagnostics.py`` redacts them by key
along with everything else.
"""

from __future__ import annotations

from collections import deque
import time
from typing import Any

# Roughly twenty seconds of the fastest scrolling observed on the E2490, which
# covers any single gesture plus the gaps around it.
TRACE_LIMIT = 400

CAPTURE_VERSION = 1


class RotationTrace:
    """Bounded, opt-in record of how each rotation step reached its value."""

    def __init__(self, limit: int = TRACE_LIMIT, clock=time.monotonic) -> None:
        self._rows: deque[dict[str, Any]] = deque(maxlen=limit)
        self._clock = clock
        self._enabled = False
        self._sequence = 0
        self._started_at: float | None = None
        # One entry per binding that recorded anything, so a replay can rebuild
        # the binding under test without the operator retyping its settings.
        self._bindings: dict[str, dict[str, Any]] = {}

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Turn recording on or off. Turning it on starts from a clean buffer.

        Clearing on enable means a captured window always begins at a known
        point, instead of blending into whatever happened to be in memory.
        """
        if enabled and not self._enabled:
            self.clear()
        self._enabled = enabled

    def describe_binding(self, key: str, config: dict[str, Any]) -> None:
        """Record the settings a replay needs to reconstruct this binding."""
        if not self._enabled:
            return
        self._bindings[key] = config

    def record(self, kind: str, **fields: Any) -> None:
        """Append one row. A no-op while disabled, so callers need no guard."""
        if not self._enabled:
            return
        now = self._clock()
        if self._started_at is None:
            self._started_at = now
        self._sequence += 1
        self._rows.append(
            {
                "seq": self._sequence,
                # Relative, so a capture carries no wall-clock timestamp and
                # replays identically wherever it is opened.
                "t": round(now - self._started_at, 4),
                "kind": kind,
                **fields,
            }
        )

    def dump(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def capture(self) -> dict[str, Any]:
        """Return a self-contained capture: settings plus the recorded rows."""
        return {
            "capture_version": CAPTURE_VERSION,
            "bindings": dict(self._bindings),
            "rows": self.dump(),
        }

    def clear(self) -> None:
        self._rows.clear()
        self._bindings.clear()
        self._sequence = 0
        self._started_at = None
