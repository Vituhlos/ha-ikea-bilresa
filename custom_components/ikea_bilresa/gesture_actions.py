"""What a press gesture does to its target: one table for every consumer.

A press, a double press, a triple press and a hold each act on one entity with
one verb. Which verbs an entity offers, and which service each calls, is the
table in ``gesture_verbs``; the runtime, the validation and the gesture ledger
must agree, so they all ask here:

* a light, a switch or anything else switchable goes through ``homeassistant``
  with ``toggle``, ``on`` or ``off``;
* a media player, a cover, a vacuum and the other kinds have verbs of their own
  (``play_pause``, ``open``, ``return_home``, ...);
* a script is its own domain: ``on`` runs it (and can pass variables), ``off``
  stops it, ``toggle`` runs it or stops it when it runs;
* a scene can only be run. It has no ``toggle`` and no ``turn_off``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .gesture_verbs import NO_ACTION, verb_for

GESTURE_SHORT_PRESS = "short_press"
GESTURE_DOUBLE_PRESS = "double_press"
GESTURE_TRIPLE_PRESS = "triple_press"
GESTURE_HOLD = "hold"
GESTURE_RELEASE = "release"

# What the live activity calls what was done: Home Assistant's own words for a
# switchable entity, "run" and "stop" for a script, "run" for a scene, and the
# verb itself for the rest.
_RESULT = {
    ("script", "turn_on"): "run",
    ("script", "turn_off"): "stop",
    ("script", "toggle"): "toggle",
    ("homeassistant", "toggle"): "toggle",
    ("homeassistant", "turn_on"): "turn_on",
    ("homeassistant", "turn_off"): "turn_off",
}


def action_is_supported(entity_id: str | None, action: str) -> bool:
    """Whether this action can be carried out on this entity.

    "none" is no action at all, which every entity accepts.
    """
    return action == NO_ACTION or verb_for(entity_id, action) is not None


def target_service(entity_id: str, action: str) -> tuple[str, str] | None:
    """The ``(domain, service)`` that carries out ``action``, or ``None``.

    ``None`` means the combination has no service (a scene cannot be turned
    off, a lock cannot be told to play); validation refuses it when a binding
    is saved, and the runtime skips it for data that predates the check.
    """
    verb = verb_for(entity_id, action)
    return None if verb is None else (verb.domain, verb.service)


def needs_state(entity_id: str, action: str) -> bool:
    """Whether the verb computes its data from the entity's state."""
    verb = verb_for(entity_id, action)
    return verb is not None and verb.invert is not None


def gesture_call(
    entity_id: str, action: str, attributes: Mapping[str, Any] | None = None
) -> tuple[str, str, dict[str, Any]] | None:
    """The service call for ``action``: ``(domain, service, data)``.

    ``None`` when there is no such verb for the entity, or when the verb needs
    state that cannot be read (``attributes`` missing or the attribute is not
    a boolean). Nothing is guessed: a mute toggled the wrong way, or a step in
    the wrong direction, is worse than a press that did nothing.
    """
    verb = verb_for(entity_id, action)
    if verb is None:
        return None
    data = dict(verb.data)
    if verb.invert is not None:
        attribute, field = verb.invert
        current = (attributes or {}).get(attribute)
        if not isinstance(current, bool):
            return None
        data[field] = not current
    return verb.domain, verb.service, data


def result_label(entity_id: str, action: str) -> str:
    """The word the live activity uses for what was done."""
    verb = verb_for(entity_id, action)
    if verb is None:
        return "skipped"
    if verb.domain == "scene":
        return "run"
    key = (verb.domain, verb.service)
    if key in _RESULT:
        return _RESULT[key]
    return action


def passes_variables(entity_id: str, action: str) -> bool:
    """Only ``script.turn_on`` takes variables; ``script.toggle`` cannot."""
    return target_service(entity_id, action) == ("script", "turn_on")
