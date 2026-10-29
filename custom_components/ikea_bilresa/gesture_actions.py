"""What a press gesture does to its target: one table for every consumer.

A press, a double press, a triple press and a hold each act on one entity with
one of three actions, ``toggle``, ``on`` or ``off``. What those mean depends on
the entity, and the runtime, the validation and the gesture ledger must agree,
so the rules live here and nowhere else:

* a light, a switch or anything else switchable goes through ``homeassistant``;
* a script is its own domain: ``on`` runs it (and can pass variables),
  ``off`` stops it, ``toggle`` runs it or stops it when it runs;
* a scene can only be run. It has no ``toggle`` and no ``turn_off``.
"""

from __future__ import annotations

from .const import CLICK_OFF, CLICK_ON, CLICK_TOGGLE, is_scene_target

GESTURE_SHORT_PRESS = "short_press"
GESTURE_DOUBLE_PRESS = "double_press"
GESTURE_TRIPLE_PRESS = "triple_press"
GESTURE_HOLD = "hold"
GESTURE_RELEASE = "release"

_SERVICE = {CLICK_TOGGLE: "toggle", CLICK_ON: "turn_on", CLICK_OFF: "turn_off"}

# What the live activity calls what was done; Home Assistant's own words for
# a switchable entity, "run" and "stop" for a script, "run" for a scene.
_RESULT = {
    ("script", "turn_on"): "run",
    ("script", "turn_off"): "stop",
    ("script", "toggle"): "toggle",
}


def action_is_supported(entity_id: str | None, action: str) -> bool:
    """Whether this action can be carried out on this entity."""
    return not (is_scene_target(entity_id) and action == CLICK_OFF)


def target_service(entity_id: str, action: str) -> tuple[str, str] | None:
    """The ``(domain, service)`` that carries out ``action``, or ``None``.

    ``None`` means the combination has no service (a scene cannot be turned
    off); validation refuses it when a binding is saved, and the runtime skips
    it for data that predates the check.
    """
    if not action_is_supported(entity_id, action):
        return None
    domain = entity_id.split(".", 1)[0]
    if domain == "scene":
        return "scene", "turn_on"
    service = _SERVICE.get(action, "toggle")
    if domain == "script":
        return "script", service
    return "homeassistant", service


def result_label(entity_id: str, action: str) -> str:
    """The word the live activity uses for what was done."""
    call = target_service(entity_id, action)
    if call is None:
        return "skipped"
    domain, service = call
    if domain == "scene":
        return "run"
    return _RESULT.get((domain, service), service)


def passes_variables(entity_id: str, action: str) -> bool:
    """Only ``script.turn_on`` takes variables; ``script.toggle`` cannot."""
    return target_service(entity_id, action) == ("script", "turn_on")
