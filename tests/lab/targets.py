"""In-memory targets: a light, a number, a thermostat and a media player.

A target models the *device and its service validation*, not the binding. It
accepts a service call, remembers what was requested and reports it back after
a delay the scenario chooses (``echo_delay``; ``None`` never reports). None of
the binding's arithmetic is repeated here.

Three different things are kept apart:

* *requested* / *applied*: what the device actually is (``_applied``). A service
  call changes it at once, and so does an outside change.
* *reported*: what Home Assistant sees (``_reported``). It follows the device
  only when a report arrives: a delayed echo of a command, or the report that
  goes with an outside change.
* an *echo* only moves the reported value. It never changes the device.

An outside change (``TargetRegistry.external_change``) moves both. An echo that
was already in flight when it happened is, by default, superseded and dropped:
the device reports in order, and its newest state supersedes older reports.
``stale_echoes="deliver"`` models the opposite, a reordered stale report that
arrives after the change and leaves reported and device disagreeing.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from homeassistant.core import State

from .fake_clock import FakeClock, FakeScheduler
from .service_spy import LabSafetyViolation, SafetyLog, TargetRejected

_STAMP = datetime(2026, 1, 1, tzinfo=UTC)


class Target:
    """One simulated entity. ``apply`` returns (snapshot, extra report delay)."""

    def __init__(self, entity_id: str, *, echo_delay: float | None = 0.0) -> None:
        self.entity_id = entity_id
        self.echo_delay = echo_delay
        self.available = True

    def services(self) -> frozenset[tuple[str, str]]:
        """The (domain, service) pairs this kind of entity understands."""
        raise NotImplementedError

    def accepts(self, domain: str, service: str) -> bool:
        return (domain, service) in self.services()

    def apply(self, service: str, data: dict[str, Any]) -> tuple[Any, float]:
        raise NotImplementedError

    def publish(self, snapshot: Any) -> None:
        """A report arrived: only what Home Assistant sees changes."""
        raise NotImplementedError

    def set_device(self, snapshot: Any) -> None:
        """Somebody else changed the device: it is that now, and it says so."""
        raise NotImplementedError

    def reported_state(self) -> tuple[str, dict[str, Any]]:
        raise NotImplementedError

    def requested(self) -> dict[str, Any]:
        raise NotImplementedError

    def value(self) -> Any:
        """The one number a timeline prints for this target's reported state."""
        raise NotImplementedError


def _number(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TargetRejected(f"{key}_not_numeric")
    return float(value)


def _only(data: dict[str, Any], allowed: set[str]) -> None:
    extra = set(data) - allowed
    if extra:
        raise TargetRejected(f"unsupported_attribute:{sorted(extra)[0]}")


class LightTarget(Target):
    """A dimmable light; ``transition`` delays the report, as a real fade does."""

    def __init__(
        self,
        entity_id: str,
        *,
        on: bool = True,
        brightness: int = 128,
        echo_delay: float | None = 0.0,
    ) -> None:
        super().__init__(entity_id, echo_delay=echo_delay)
        self._applied = (on, brightness)
        self._reported = (on, brightness)

    def services(self) -> frozenset[tuple[str, str]]:
        own = {("light", name) for name in ("turn_on", "turn_off", "toggle")}
        # gesture_verbs sends toggle/on/off through the ``homeassistant`` domain.
        shared = {("homeassistant", name) for name in ("turn_on", "turn_off", "toggle")}
        return frozenset(own | shared)

    def apply(self, service: str, data: dict[str, Any]) -> tuple[Any, float]:
        _only(data, {"brightness", "transition"})
        transition = float(data["transition"]) if "transition" in data else 0.0
        on, brightness = self._applied
        if service == "turn_off" or (service == "toggle" and on):
            on = False
        else:
            if "brightness" in data:
                brightness = int(_number(data, "brightness"))
                if not 1 <= brightness <= 255:
                    raise TargetRejected("brightness_out_of_range")
            elif not on:
                brightness = 255
            on = True
        self._applied = (on, brightness)
        return self._applied, max(transition, 0.0)

    def publish(self, snapshot: Any) -> None:
        self._reported = snapshot

    def set_device(self, snapshot: Any) -> None:
        self._applied = snapshot
        self._reported = snapshot

    def reported_state(self) -> tuple[str, dict[str, Any]]:
        on, brightness = self._reported
        attributes: dict[str, Any] = {
            "supported_color_modes": ["brightness"],
            "brightness": brightness if on else None,
        }
        return ("on" if on else "off"), attributes

    def requested(self) -> dict[str, Any]:
        on, brightness = self._applied
        return {"state": "on" if on else "off", "brightness": brightness}

    def value(self) -> Any:
        on, brightness = self._reported
        return brightness if on else 0


class NumberTarget(Target):
    """``number`` / ``input_number`` with a range; out-of-range is refused."""

    def __init__(
        self,
        entity_id: str,
        *,
        minimum: float,
        maximum: float,
        step: float,
        value: float,
        echo_delay: float | None = 0.0,
    ) -> None:
        super().__init__(entity_id, echo_delay=echo_delay)
        self.minimum, self.maximum, self.step = minimum, maximum, step
        self._applied = float(value)
        self._reported = float(value)

    def services(self) -> frozenset[tuple[str, str]]:
        return frozenset({(self.entity_id.partition(".")[0], "set_value")})

    def apply(self, service: str, data: dict[str, Any]) -> tuple[Any, float]:
        _only(data, {"value"})
        value = _number(data, "value")
        if not self.minimum <= value <= self.maximum:
            raise TargetRejected("value_out_of_range")
        self._applied = value
        return value, 0.0

    def publish(self, snapshot: Any) -> None:
        self._reported = snapshot

    def set_device(self, snapshot: Any) -> None:
        self._applied = float(snapshot)
        self._reported = float(snapshot)

    def reported_state(self) -> tuple[str, dict[str, Any]]:
        return str(self._reported), {
            "min": self.minimum,
            "max": self.maximum,
            "step": self.step,
            "mode": "slider",
        }

    def requested(self) -> dict[str, Any]:
        return {"value": self._applied}

    def value(self) -> Any:
        return self._reported


class ClimateTarget(Target):
    """A thermostat: ``set_temperature`` inside ``min_temp``..``max_temp``."""

    def __init__(
        self,
        entity_id: str,
        *,
        min_temp: float,
        max_temp: float,
        temperature: float,
        target_temp_step: float | None = 0.5,
        echo_delay: float | None = 0.0,
    ) -> None:
        super().__init__(entity_id, echo_delay=echo_delay)
        self.min_temp, self.max_temp = min_temp, max_temp
        self.target_temp_step = target_temp_step
        self._applied = float(temperature)
        self._reported = float(temperature)

    def services(self) -> frozenset[tuple[str, str]]:
        return frozenset({("climate", "set_temperature")})

    def apply(self, service: str, data: dict[str, Any]) -> tuple[Any, float]:
        _only(data, {"temperature"})
        value = _number(data, "temperature")
        if not self.min_temp <= value <= self.max_temp:
            raise TargetRejected("temperature_out_of_range")
        self._applied = value
        return value, 0.0

    def publish(self, snapshot: Any) -> None:
        self._reported = snapshot

    def set_device(self, snapshot: Any) -> None:
        self._applied = float(snapshot)
        self._reported = float(snapshot)

    def reported_state(self) -> tuple[str, dict[str, Any]]:
        attributes: dict[str, Any] = {
            "temperature": self._reported,
            "current_temperature": self._reported,
            "min_temp": self.min_temp,
            "max_temp": self.max_temp,
            "hvac_modes": ["off", "heat"],
        }
        if self.target_temp_step is not None:
            attributes["target_temp_step"] = self.target_temp_step
        return "heat", attributes

    def requested(self) -> dict[str, Any]:
        return {"temperature": self._applied}

    def value(self) -> Any:
        return self._reported


class MediaPlayerTarget(Target):
    """A media player with ``volume_level`` 0.0-1.0."""

    def __init__(
        self,
        entity_id: str,
        *,
        volume: float,
        echo_delay: float | None = 0.0,
    ) -> None:
        super().__init__(entity_id, echo_delay=echo_delay)
        self._applied = float(volume)
        self._reported = float(volume)

    def services(self) -> frozenset[tuple[str, str]]:
        return frozenset({("media_player", "volume_set")})

    def apply(self, service: str, data: dict[str, Any]) -> tuple[Any, float]:
        _only(data, {"volume_level"})
        value = _number(data, "volume_level")
        if not 0.0 <= value <= 1.0:
            raise TargetRejected("volume_out_of_range")
        self._applied = value
        return value, 0.0

    def publish(self, snapshot: Any) -> None:
        self._reported = snapshot

    def set_device(self, snapshot: Any) -> None:
        self._applied = float(snapshot)
        self._reported = float(snapshot)

    def reported_state(self) -> tuple[str, dict[str, Any]]:
        return "playing", {"volume_level": self._reported, "is_volume_muted": False}

    def requested(self) -> dict[str, Any]:
        return {"volume_level": self._applied}

    def value(self) -> Any:
        return self._reported


class TargetRegistry:
    """``hass.states`` for the lab: the only entities that exist are ours."""

    def __init__(
        self, clock: FakeClock, scheduler: FakeScheduler, safety: SafetyLog
    ) -> None:
        self._clock = clock
        self._scheduler = scheduler
        self._safety = safety
        self._targets: dict[str, Target] = {}
        # Bumped by every outside change; an echo remembers the one it was made in.
        self._generation: dict[str, int] = {}
        self._drop_below: dict[str, int] = {}
        self._listeners: list[tuple[frozenset[str], Callable[[Any], None]]] = []
        self.history: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        self._safety.record("states_attribute_blocked", name=name)
        raise LabSafetyViolation(f"the lab states have no {name!r}")

    # -- what the binding sees ------------------------------------------

    def get(self, entity_id: str) -> State | None:
        target = self._targets.get(entity_id)
        if target is None:
            return None
        if not target.available:
            return self._state(entity_id, "unavailable", {})
        state, attributes = target.reported_state()
        return self._state(entity_id, state, attributes)

    def track(
        self, entity_ids: list[str], action: Callable[[Any], None]
    ) -> Callable[[], None]:
        entry = (frozenset(entity_ids), action)
        self._listeners.append(entry)

        def unsubscribe() -> None:
            if entry in self._listeners:
                self._listeners.remove(entry)

        return unsubscribe

    @property
    def listeners(self) -> int:
        return len(self._listeners)

    # -- what the spy and the scenarios use ------------------------------

    def add(self, target: Target) -> Target:
        self._targets[target.entity_id] = target
        self._generation[target.entity_id] = 0
        self._drop_below[target.entity_id] = 0
        return target

    def owns(self, entity_id: str) -> bool:
        return entity_id in self._targets

    def target(self, entity_id: str) -> Target:
        return self._targets[entity_id]

    def apply(self, entity_id: str, service: str, data: dict[str, Any]) -> None:
        target = self._targets[entity_id]
        snapshot, extra = target.apply(service, data)
        self.history.append(
            {
                "t": self._clock.elapsed(),
                "entity_id": entity_id,
                "event": "requested",
                **target.requested(),
            }
        )
        if target.echo_delay is None:
            return

        made_in = self._generation[entity_id]

        def report(_now: float) -> None:
            if made_in < self._drop_below[entity_id]:
                self.history.append(
                    {
                        "t": self._clock.elapsed(),
                        "entity_id": entity_id,
                        "event": "stale_echo_dropped",
                    }
                )
                return
            self._publish(target, snapshot, stale=made_in < self._generation[entity_id])

        self._scheduler.call_later(
            target.echo_delay + extra, report, label=f"echo:{entity_id}"
        )

    def external_change(
        self, entity_id: str, snapshot: Any, *, stale_echoes: str = "drop"
    ) -> None:
        """Somebody else changed the entity.

        The device really is in the new state (``_applied``) and reports it at
        once (``_reported``). Echoes of earlier commands still in flight are
        dropped (``"drop"``, the default: the device's newest state supersedes
        older reports) or delivered after all (``"deliver"``: a reordered stale
        report, which then leaves the reported value and the device apart).
        """
        if stale_echoes not in ("drop", "deliver"):
            raise ValueError(stale_echoes)
        target = self._targets[entity_id]
        self._generation[entity_id] += 1
        if stale_echoes == "drop":
            self._drop_below[entity_id] = self._generation[entity_id]
        before = self.get(entity_id)
        target.set_device(snapshot)
        self.history.append(
            {
                "t": self._clock.elapsed(),
                "entity_id": entity_id,
                "event": "external",
                "value": target.value(),
                **target.requested(),
            }
        )
        self._notify(entity_id, before)

    def set_available(self, entity_id: str, available: bool) -> None:
        target = self._targets[entity_id]
        target.available = available
        self._notify(entity_id, None)

    # -- internals ------------------------------------------------------

    def _publish(self, target: Target, snapshot: Any, *, stale: bool = False) -> None:
        before = self.get(target.entity_id)
        target.publish(snapshot)
        row: dict[str, Any] = {
            "t": self._clock.elapsed(),
            "entity_id": target.entity_id,
            "event": "reported",
            "value": target.value(),
        }
        if stale:
            row["stale"] = True
        self.history.append(row)
        self._notify(target.entity_id, before)

    def _notify(self, entity_id: str, before: State | None) -> None:
        after = self.get(entity_id)
        event = SimpleNamespace(
            data={"entity_id": entity_id, "old_state": before, "new_state": after}
        )
        for ids, action in list(self._listeners):
            if entity_id in ids:
                action(event)

    @staticmethod
    def _state(entity_id: str, state: str, attributes: dict[str, Any]) -> State:
        return State(
            entity_id, state, attributes, last_changed=_STAMP, last_updated=_STAMP
        )
