"""Drive a real binding through a captured rotation, offline.

A capture from `ikea_bilresa/trace` carries the raw Matter gesture boundaries,
the target's own state reports and the decoded rotations, each with a relative
timestamp. That is everything needed to put a real `LightBinding` through the
same sequence without Home Assistant, without Matter and without the wheel.

Two things this buys, both of which today's session did without:

* a defect seen on the physical wheel is reproduced here in milliseconds, and
  the same capture keeps reproducing it, so it becomes a regression test;
* two candidate fixes are compared on *identical* input, instead of on two
  different turns of a wheel that can never be repeated exactly.

The simulated target deliberately models the real one: it applies whatever
absolute value it is sent, and it only *reports* that value back when the
capture says a report arrived. That separation is the whole point — the defect
under investigation lives in the gap between the two.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

from custom_components.ikea_bilresa.binding import LightBinding
from custom_components.ikea_bilresa.const import (
    CONF_ACCELERATION,
    CONF_CHANNEL,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_STEP,
    CONF_TARGET,
    CONF_TRANSITION,
    DIRECTION_UP,
)

_VALUE_KEYS = ("brightness", "color_temp_kelvin", "volume_level", "position")


@dataclass
class ReplayResult:
    """What a replayed capture produced, ready to assert on or to score."""

    sent: list[float] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    final_value: float | None = None

    @property
    def rotations(self) -> list[dict[str, Any]]:
        return [row for row in self.rows if row["kind"] == "rotate"]

    @property
    def forgets(self) -> list[dict[str, Any]]:
        return [row for row in self.rows if row["kind"] == "forget"]

    @property
    def notches(self) -> int:
        """Total notches the capture asked the binding to apply."""
        return sum(row["notches"] for row in self.rotations)


class _Clock:
    """Monotonic time driven by the capture's own relative timestamps."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _Target:
    """A light that obeys absolute commands and reports back only on cue."""

    def __init__(self, value: float, state: str = "on") -> None:
        self.applied = value
        self.reported = value
        self.state = state

    def snapshot(self) -> SimpleNamespace:
        return SimpleNamespace(
            state=self.state, attributes={"brightness": self.reported}
        )


def _binding_data(config: dict[str, Any], node_id: int, channel: int) -> dict[str, Any]:
    return {
        CONF_NODE_ID: node_id,
        CONF_CHANNEL: channel,
        CONF_TARGET: config.get("target") or "light.replay",
        CONF_MODE: config.get("mode", "brightness"),
        CONF_STEP: config.get("step", 3),
        CONF_ACCELERATION: config.get("acceleration", 0),
        CONF_TRANSITION: config.get("transition", 0.0),
    }


def simulate_target(
    capture: dict[str, Any],
    *,
    profile: str = "instant",
    delay: float = 0.25,
    travel: float = 0.0,
    quantum: float = 0.0,
    initial_value: float = 255,
    floor: float = 3.0,
) -> dict[str, Any]:
    """Add the state reports a given class of target would have produced.

    A capture recorded against one device only proves the behaviour on that
    device. These profiles let the same gesture be replayed against the kinds
    of target the integration actually claims to support:

    * ``instant`` — reports the commanded value after ``delay`` (WLED, a fast
      Wi-Fi dimmer);
    * ``fade`` — travels at ``travel`` units per second and reports where it
      has got to, so it emits values that were never commanded (Shelly with a
      fade, and any Zigbee bulb with a default transition);
    * ``slow`` — the same, at cover-motor speed, where a single move outlasts
      the whole gesture.

    ``quantum`` rounds reports the way a device storing whole percent does, and
    ``floor`` is the minimum the binding itself clamps to — a simulated target
    that ignores it would report "off" for a light the binding is holding lit,
    which is a fault in the simulation rather than in the code under test.
    """
    rows = [row for row in capture["rows"] if row["kind"] != "state"]
    commands: list[tuple[float, float]] = []
    value = initial_value
    for row in sorted(rows, key=lambda item: item["t"]):
        if row["kind"] != "rotate":
            continue
        step = row["notches"] * 7.65
        value = max(
            floor,
            min(255.0, value + (step if row["direction"] == DIRECTION_UP else -step)),
        )
        commands.append((row["t"], value))

    reports: list[dict[str, Any]] = []
    position = initial_value
    previous_time = commands[0][0] if commands else 0.0
    for issued_at, commanded in commands:
        at = round(issued_at + delay, 4)
        if profile == "instant":
            position = commanded
        else:
            # How far the target could travel since the last report, capped by
            # the command it is heading for.
            reach = travel * max(0.0, at - previous_time)
            if commanded > position:
                position = min(commanded, position + reach)
            else:
                position = max(commanded, position - reach)
        previous_time = at
        reported = position
        if quantum:
            reported = round(reported / quantum) * quantum
        reports.append(
            {
                "kind": "state",
                "binding": next(r["binding"] for r in rows if r.get("binding")),
                "t": at,
                "state": "on" if reported > 0 else "off",
                "value": round(reported),
            }
        )

    merged = sorted(
        rows + reports, key=lambda item: (item["t"], item["kind"] != "state")
    )
    for index, row in enumerate(merged):
        row["seq"] = index + 1
    return {**capture, "rows": merged, "expect": None}


def replay(
    capture: dict[str, Any],
    monkeypatch,
    *,
    binding_key: str | None = None,
    initial_value: float = 255,
) -> ReplayResult:
    """Replay one binding's rows from a capture and report what it sent."""
    rows = capture["rows"]
    key = binding_key or next(
        (row["binding"] for row in rows if row.get("binding")), None
    )
    if key is None:
        raise ValueError("capture contains no binding rows")
    config = capture.get("bindings", {}).get(key, {})
    node_id, _kind, address = key.split(":")

    clock = _Clock()
    monkeypatch.setattr("custom_components.ikea_bilresa.binding.time.monotonic", clock)
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_track_time_interval",
        lambda *_a: Mock(),
    )

    # The binding defers coalesced commands with async_call_later, so a replay
    # that ignored it would drop exactly the sends the real runtime makes.
    timers: list[list[Any]] = []

    def _later(_hass, delay, callback_fn):
        entry = [clock.now + delay, callback_fn, False]
        timers.append(entry)

        def cancel() -> None:
            entry[2] = True

        return cancel

    def _run_due_timers() -> None:
        for entry in list(timers):
            due, callback_fn, cancelled = entry
            if not cancelled and due <= clock.now:
                entry[2] = True
                callback_fn(clock.now)

    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_call_later", _later
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_track_state_change_event",
        lambda *_a: Mock(),
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.binding.async_dispatcher_send", Mock()
    )

    target = _Target(initial_value)
    result = ReplayResult()

    def _service_call(domain, service, payload, **_kw):
        if service == "turn_off":
            target.applied = 0
            target.state = "off"
        else:
            for name in _VALUE_KEYS:
                if name in payload:
                    target.applied = payload[name]
                    target.state = "on"
                    break
        result.sent.append(target.applied)
        return object()

    def _close(coro):
        coro.close()
        return Mock()

    hass = SimpleNamespace(
        states=SimpleNamespace(get=lambda _entity: target.snapshot()),
        services=SimpleNamespace(async_call=Mock(side_effect=_service_call)),
        async_create_task=Mock(side_effect=_close),
    )

    from custom_components.ikea_bilresa.trace import RotationTrace

    trace = RotationTrace(clock=clock)
    trace.set_enabled(True)
    binding = LightBinding(
        hass, _binding_data(config, int(node_id), int(address)), trace=trace
    )

    for row in rows:
        if row.get("binding") not in (None, key):
            continue
        clock.now = row["t"]
        _run_due_timers()
        kind = row["kind"]
        if kind == "raw":
            binding._handle_raw_input(row["role"], row["event_type"], row["endpoint"])
        elif kind == "state":
            # The captured report, not the value the target actually holds:
            # reproducing the lag is the point of the exercise.
            if row.get("value") is not None:
                target.reported = row["value"]
            if row.get("state"):
                target.state = row["state"]
            binding._handle_target_state_change(
                SimpleNamespace(data={"new_state": target.snapshot()})
            )
        elif kind == "rotate":
            binding._rotate_by(row["notches"], row["direction"] == DIRECTION_UP)

    # A gesture's last value is usually still queued when the rows run out;
    # the real runtime would fire it a fraction of a second later.
    clock.now += 1.0
    _run_due_timers()

    result.rows = trace.dump()
    result.final_value = target.applied
    return result
