"""Wire the production code to the lab doubles, and nothing else.

Production code used, unchanged, in this order:

``BilresaCoordinator._on_event`` -> ``parse_node`` / ``decode_event`` ->
``GestureEngine.process`` (with the lab clock) -> the coordinator's dispatch ->
``LightBinding`` (attached through ``async_setup_bindings``) -> its service call.

What is replaced is only what leaves the process: ``hass`` (four attributes),
the dispatcher, the timers, the state tracking, ``Script`` and the registry
helpers. Each replacement is a module-level name inside ``binding`` or
``coordinator`` rebound with ``monkeypatch``; ``time.monotonic`` itself is never
touched. No calculation of the binding is repeated here.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
from types import SimpleNamespace
from typing import Any

import pytest

from custom_components.ikea_bilresa import binding as binding_module
from custom_components.ikea_bilresa import coordinator as coordinator_module
from custom_components.ikea_bilresa.const import (
    EVENT_BILRESA,
    SIGNAL_BINDING_ACTIVITY,
    SUBENTRY_BINDING,
)
from custom_components.ikea_bilresa.coordinator import BilresaCoordinator
from custom_components.ikea_bilresa.engine import GestureEngine

from .fake_clock import START, FakeClock, FakeScheduler, fake_time_module
from .service_spy import (
    FailClosedHass,
    FakeBus,
    ForbiddenScript,
    LabSafetyViolation,
    SafetyLog,
    ServiceSpy,
    blocked_registry_access,
    blocked_validator,
)
from .targets import Target, TargetRegistry

_ACTION_KEYS = (
    "node_id",
    "channel",
    "endpoint_id",
    "type",
    "direction",
    "notches",
    "presses",
    "observed_duration_ms",
)


class _TaskHandle:
    def cancel(self) -> bool:
        return True


class TaskQueue:
    """``hass.async_create_task`` without a loop.

    A task runs to completion when the harness settles. One that would have to
    wait for something real is refused: nothing in the lab may block.
    """

    def __init__(self, safety: SafetyLog) -> None:
        self._safety = safety
        self._queue: list[Any] = []

    def create(self, coro: Any, *_args: Any, **_kwargs: Any) -> _TaskHandle:
        self._queue.append(coro)
        return _TaskHandle()

    def drain(self) -> bool:
        ran = False
        while self._queue:
            self.run_now(self._queue.pop(0))
            ran = True
        return ran

    def run_now(self, coro: Any) -> Any:
        try:
            coro.send(None)
        except StopIteration as stop:
            return stop.value
        coro.close()
        self._safety.record("task_suspended")
        raise LabSafetyViolation("a task tried to wait for something real")

    def pending(self) -> int:
        return len(self._queue)

    def discard(self) -> None:
        for coro in self._queue:
            coro.close()
        self._queue.clear()


class FakeDispatcher:
    """``async_dispatcher_connect`` / ``async_dispatcher_send`` in memory."""

    def __init__(self, clock: FakeClock) -> None:
        self._clock = clock
        self._subscribers: dict[str, list[Callable[..., None]]] = {}
        self.activity: list[dict[str, Any]] = []
        self.sent: list[str] = []

    def connect(
        self, _hass: Any, signal: str, target: Callable[..., None]
    ) -> Callable[[], None]:
        self._subscribers.setdefault(signal, []).append(target)

        def unsubscribe() -> None:
            callbacks = self._subscribers.get(signal, [])
            if target in callbacks:
                callbacks.remove(target)

        return unsubscribe

    def send(self, _hass: Any, signal: str, *args: Any) -> None:
        self.sent.append(signal)
        if signal == SIGNAL_BINDING_ACTIVITY and args:
            payload = args[0]
            self.activity.append(
                {
                    "t": self._clock.elapsed(),
                    "status": payload.get("dispatch_status"),
                    "reason": payload.get("reason"),
                    "type": payload.get("type"),
                    "channel": payload.get("channel"),
                    "endpoint_id": payload.get("endpoint_id"),
                }
            )
        for callback in list(self._subscribers.get(signal, [])):
            callback(*args)

    @property
    def subscribers(self) -> int:
        return sum(len(callbacks) for callbacks in self._subscribers.values())


class LabHarness:
    """One scenario's world. Build it through the ``lab`` fixture."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.safety = SafetyLog()
        self.clock = FakeClock()
        self.tasks = TaskQueue(self.safety)
        self.scheduler = FakeScheduler(self.clock, after_step=self.tasks.drain)
        self.registry = TargetRegistry(self.clock, self.scheduler, self.safety)
        self.spy = ServiceSpy(self.registry, self.clock, self.safety)
        self.bus = FakeBus(self.clock, self.safety)
        self.dispatcher = FakeDispatcher(self.clock)
        self.hass = FailClosedHass(
            states=self.registry,
            services=self.spy,
            bus=self.bus,
            create_task=self.tasks.create,
            safety=self.safety,
        )
        self._settling = False
        self._patch(monkeypatch)
        # The double has exactly the attributes the integration touches.
        self.coordinator = BilresaCoordinator(
            self.hass,  # type: ignore[arg-type]
            "ws://lab.invalid/ws",
        )

    # -- wiring ---------------------------------------------------------

    def _patch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def call_later(_hass: Any, delay: Any, action: Callable[[float], None]):
            return self.scheduler.call_later(delay, action, _label(action))

        def track_interval(_hass: Any, action: Callable[[float], None], interval: Any):
            return self.scheduler.every(interval, action, _label(action))

        def track_state(_hass: Any, entity_ids: Any, action: Callable[[Any], None]):
            ids = [entity_ids] if isinstance(entity_ids, str) else list(entity_ids)
            return self.registry.track(ids, action)

        ForbiddenScript.safety = self.safety
        monkeypatch.setattr(binding_module, "time", fake_time_module(self.clock))
        monkeypatch.setattr(binding_module, "async_call_later", call_later)
        monkeypatch.setattr(binding_module, "async_track_time_interval", track_interval)
        monkeypatch.setattr(
            binding_module, "async_track_state_change_event", track_state
        )
        monkeypatch.setattr(
            binding_module, "async_dispatcher_send", self.dispatcher.send
        )
        monkeypatch.setattr(
            binding_module, "async_dispatcher_connect", self.dispatcher.connect
        )
        monkeypatch.setattr(binding_module, "Script", ForbiddenScript)
        monkeypatch.setattr(
            binding_module,
            "async_validate_actions_config",
            blocked_validator(self.safety),
        )
        monkeypatch.setattr(
            binding_module,
            "async_extract_referenced_entity_ids",
            blocked_registry_access(self.safety),
        )
        monkeypatch.setattr(
            coordinator_module, "async_dispatcher_send", self.dispatcher.send
        )
        monkeypatch.setattr(coordinator_module, "async_call_later", call_later)
        # The engine takes its clock as an argument; the coordinator builds it
        # without one, so hand it the lab clock at construction.
        monkeypatch.setattr(
            coordinator_module, "GestureEngine", lambda: GestureEngine(clock=self.clock)
        )

    # -- building the world ---------------------------------------------

    def add_target(self, target: Target) -> Target:
        return self.registry.add(target)

    def load(self, *nodes: dict[str, Any]) -> None:
        """Give the integration its node list, as ``start_listening`` does."""
        self.coordinator._on_event("__nodes__", list(nodes))
        self.settle()

    def setup_bindings(self, *configs: dict[str, Any]) -> None:
        """Attach bindings through the production path, from config data."""
        subentries = {
            f"binding-{index}": SimpleNamespace(
                subentry_type=SUBENTRY_BINDING, data=config
            )
            for index, config in enumerate(configs)
        }
        self.coordinator.async_setup_bindings(
            SimpleNamespace(subentries=subentries)  # type: ignore[arg-type]
        )

    # -- driving time and events ----------------------------------------

    def settle(self) -> None:
        """Run queued tasks and every timer that is already due."""
        if self._settling:
            return
        self._settling = True
        try:
            for _ in range(1000):
                ran = self.tasks.drain()
                fired = self.scheduler.fired
                self.scheduler.advance_to(self.clock.now)
                if not ran and self.scheduler.fired == fired:
                    return
            raise RuntimeError("settle did not converge")
        finally:
            self._settling = False

    def at(self, seconds_from_start: float) -> None:
        """Move time forward (never back) and run what falls due."""
        self.scheduler.advance_to(START + seconds_from_start)
        self.settle()

    def advance(self, seconds: float) -> None:
        self.scheduler.advance_to(self.clock.now + seconds)
        self.settle()

    def emit(self, event: dict[str, Any]) -> None:
        self.coordinator._on_event("node_event", event)
        self.settle()

    def attribute_updated(self, node_id: int, path: str, value: Any) -> None:
        self.coordinator._on_event("attribute_updated", [node_id, path, value])
        self.settle()

    def play(self, timeline: list[tuple[float, dict[str, Any]]]) -> None:
        """Deliver events at their times (seconds from the start), in order."""
        for when, event in sorted(timeline, key=lambda item: item[0]):
            self.at(when)
            self.emit(event)

    def close(self) -> None:
        """Stop the coordinator through its own shutdown path."""
        self.tasks.run_now(self.coordinator.async_stop())
        self.settle()
        self.leftovers_at_close = self.leftovers()
        # What is still queued is the lab's own (device echoes), not production's.
        self.scheduler.cancel_all()

    # -- what happened ---------------------------------------------------

    def actions(self) -> list[dict[str, Any]]:
        """The decoded ``WheelAction`` stream, as the public event shows it."""
        return [
            {key: fired["data"].get(key) for key in _ACTION_KEYS}
            for fired in self.bus.fired
            if fired["event_type"] == EVENT_BILRESA
        ]

    def rotations(self) -> list[tuple[int | None, str | None, int]]:
        return [
            (a["channel"], a["direction"], a["notches"])
            for a in self.actions()
            if a["type"] == "rotate"
        ]

    def intents(self) -> list[dict[str, Any]]:
        return [dict(intent) for intent in self.spy.intents]

    def leftovers(self) -> dict[str, Any]:
        """What a clean shutdown must leave empty."""
        return {
            "timers": [
                t for t in self.scheduler.pending() if not t.startswith("echo:")
            ],
            "subscribers": self.dispatcher.subscribers,
            "state_listeners": self.registry.listeners,
            "tasks": self.tasks.pending(),
        }

    def record(self) -> dict[str, Any]:
        """Everything a scenario produced, normalized and free of random ids."""
        return {
            "actions": self.actions(),
            "intents": self.intents(),
            "timeline": list(self.registry.history),
            "activity": list(self.dispatcher.activity),
            "ignored": dict(
                sorted(self.coordinator.telemetry["ignored_counts"].items())
            ),
            "safety": self.safety.kinds(),
        }

    def digest(self) -> str:
        encoded = json.dumps(self.record(), sort_keys=True, default=str)
        return hashlib.sha256(encoded.encode()).hexdigest()


def _label(action: Callable[..., Any]) -> str:
    return getattr(action, "__name__", "callback")
