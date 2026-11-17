"""Fail-closed doubles for everything the binding could use to act for real.

The binding reaches the outside through ``hass.services``, ``hass.bus``, the
registries, ``Script`` runs and tasks. Here every one of those either records
and refuses, or records and updates an in-memory target. Nothing is ever sent.
A refusal is never silent: it lands in ``SafetyLog``, and the fixture fails a
test that leaves one unacknowledged.
"""

from __future__ import annotations

from collections.abc import Coroutine
import copy
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from .fake_clock import FakeClock
    from .targets import TargetRegistry


class LabSafetyViolation(Exception):
    """Something tried to leave the sandbox. It was stopped and recorded.

    Deliberately not an ``AssertionError``: an expected failure declared with
    ``raises=AssertionError`` must never be able to hide a safety violation.
    """


class TargetRejected(HomeAssistantError):
    """The simulated device or service refused a value (out of range, ...)."""


class SafetyLog:
    """Every refusal and every blocked attempt, in order."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._acknowledged = 0

    def record(self, kind: str, **detail: Any) -> None:
        self.events.append({"kind": kind, **detail})

    @property
    def unacknowledged(self) -> list[dict[str, Any]]:
        return self.events[self._acknowledged :]

    def acknowledge(self) -> list[dict[str, Any]]:
        """Return what is new and mark it as expected by the test."""
        new = self.unacknowledged
        self._acknowledged = len(self.events)
        return new

    def kinds(self) -> list[str]:
        return [event["kind"] for event in self.events]


# The only service calls a lab target understands. Anything else is refused, so
# an action the lab has no model for can never pass as a success.
ALLOWED_SERVICES = frozenset(
    {
        ("light", "turn_on"),
        ("light", "turn_off"),
        ("light", "toggle"),
        # gesture_verbs sends a switchable entity's toggle/on/off through the
        # ``homeassistant`` domain, whatever the entity's own domain is.
        ("homeassistant", "toggle"),
        ("homeassistant", "turn_on"),
        ("homeassistant", "turn_off"),
        ("input_number", "set_value"),
        ("number", "set_value"),
        ("climate", "set_temperature"),
        ("media_player", "volume_set"),
    }
)


async def _done() -> None:
    return None


def _failing(error: Exception) -> Coroutine[Any, Any, None]:
    async def raise_it() -> None:
        raise error

    return raise_it()


def _entity_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


class ServiceSpy:
    """Stands in for ``hass.services``: records intents, never executes them."""

    def __init__(
        self, registry: TargetRegistry, clock: FakeClock, safety: SafetyLog
    ) -> None:
        self._registry = registry
        self._clock = clock
        self._safety = safety
        self.intents: list[dict[str, Any]] = []

    def async_call(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None = None,
        blocking: bool = False,
        context: Any = None,
        target: Any = None,
        return_response: bool = False,
    ) -> Coroutine[Any, Any, None]:
        data = copy.deepcopy(dict(service_data or {}))
        entity_ids = _entity_list(data.pop("entity_id", None))
        intent: dict[str, Any] = {
            "t": self._clock.elapsed(),
            "domain": domain,
            "service": service,
            "entity_id": entity_ids[0] if len(entity_ids) == 1 else entity_ids,
            "data": data,
            "status": "accepted",
        }
        self.intents.append(intent)

        refusal = self._screen(domain, service, entity_ids, target, context)
        if refusal is not None:
            intent["status"] = f"rejected:{refusal}"
            self._safety.record(refusal, domain=domain, service=service)
            return _failing(LabSafetyViolation(f"lab refused {domain}.{service}"))
        try:
            for entity_id in entity_ids:
                self._registry.apply(entity_id, service, data)
        except TargetRejected as err:
            intent["status"] = f"rejected_by_target:{err}"
            return _failing(err)
        return _done()

    def _screen(
        self,
        domain: str,
        service: str,
        entity_ids: list[str],
        target: Any,
        context: Any,
    ) -> str | None:
        if (domain, service) not in ALLOWED_SERVICES:
            return "service_not_allowed"
        if target is not None:
            return "target_parameter_not_allowed"
        if not entity_ids:
            return "no_entity_id"
        if any(not self._registry.owns(entity_id) for entity_id in entity_ids):
            return "entity_not_lab_owned"
        if any(
            not self._registry.target(entity_id).accepts(domain, service)
            for entity_id in entity_ids
        ):
            return "service_not_allowed_for_entity"
        return None

    def __getattr__(self, name: str) -> Any:
        self._safety.record("services_attribute_blocked", name=name)
        raise LabSafetyViolation(f"the lab services have no {name!r}")

    def accepted(self) -> list[dict[str, Any]]:
        return [i for i in self.intents if i["status"] == "accepted"]

    def refused(self) -> list[dict[str, Any]]:
        return [i for i in self.intents if i["status"].startswith("rejected:")]


class FakeBus:
    """Records what would have been fired on the public event bus."""

    def __init__(self, clock: FakeClock, safety: SafetyLog) -> None:
        self._clock = clock
        self._safety = safety
        self.fired: list[dict[str, Any]] = []

    def async_fire(self, event_type: str, event_data: Any = None, *_: Any, **__: Any):
        self.fired.append(
            {
                "t": self._clock.elapsed(),
                "event_type": event_type,
                "data": copy.deepcopy(dict(event_data or {})),
            }
        )

    def __getattr__(self, name: str) -> Any:
        self._safety.record("bus_attribute_blocked", name=name)
        raise LabSafetyViolation(f"the lab bus has no {name!r}")


class FailClosedHass:
    """``hass`` with exactly four attributes; any other access is a violation."""

    def __init__(
        self,
        *,
        states: Any,
        services: ServiceSpy,
        bus: FakeBus,
        create_task: Any,
        safety: SafetyLog,
    ) -> None:
        self.states = states
        self.services = services
        self.bus = bus
        self.async_create_task = create_task
        self._safety = safety

    def __getattr__(self, name: str) -> Any:
        self._safety.record("hass_attribute_blocked", name=name)
        raise LabSafetyViolation(f"the lab hass has no {name!r}")


class ForbiddenScript:
    """Replaces ``homeassistant.helpers.script.Script`` for the binding."""

    safety: SafetyLog | None = None

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        if self.safety is not None:
            self.safety.record("script_blocked", where="Script()")
        raise LabSafetyViolation("user scripts are never built in the lab")


def blocked_validator(safety: SafetyLog) -> Any:
    """Replaces ``async_validate_actions_config``: user actions never validate."""

    async def blocked(_hass: Any, sequence: Any) -> Any:
        safety.record("script_blocked", where="validate", actions=len(sequence))
        raise HomeAssistantError("lab: user actions are never run")

    return blocked


def blocked_registry_access(safety: SafetyLog) -> Any:
    """Replaces ``async_extract_referenced_entity_ids`` (reads the registries)."""

    def blocked(*_args: Any, **_kwargs: Any) -> Any:
        safety.record("registry_access_blocked")
        raise LabSafetyViolation("the lab never reads the real registries")

    return blocked
