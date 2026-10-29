"""The verbs a press gesture may carry out, per kind of target.

One table, read by the runtime, the validation, the panel and the native form,
so they cannot disagree about what a gesture can do. A verb is a stable id the
user's choice is stored as (``play_pause``); this table says which Home
Assistant service it calls.

Checked against Home Assistant core 2026.8 to 2026.10 (``services.yaml`` and
``__init__.py`` of each domain). What is left out on purpose:

* ``lock.unlock``, ``lock.open``, a lock toggle, ``alarm_control_panel`` disarm
  and ``trigger``: one stray press on a remote anyone can pick up must not open
  a door or disarm an alarm;
* ``siren.turn_on`` (a false alarm) and ``valve`` open and toggle (water, gas);
* ``vacuum`` toggle and ``start_pause``: core does not register them;
* ``camera`` and ``notify``: they do not act on one entity the way a button does.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# A gesture that does nothing.
NO_ACTION = "none"

# The words that mean the same on every switchable entity.
VERB_TOGGLE = "toggle"
VERB_ON = "on"
VERB_OFF = "off"


@dataclass(frozen=True)
class Verb:
    """One verb: the service it calls and the data it needs."""

    domain: str
    service: str
    data: tuple[tuple[str, Any], ...] = ()
    # ``(attribute, field)``: the service field takes the opposite of the
    # entity's boolean attribute, read when the button is pressed. A verb that
    # needs state cannot run without a readable one.
    invert: tuple[str, str] | None = None


def _homeassistant(verb: str) -> Verb:
    service = {"toggle": "toggle", "on": "turn_on", "off": "turn_off"}[verb]
    return Verb("homeassistant", service)


_SWITCHABLE = {verb: _homeassistant(verb) for verb in (VERB_TOGGLE, VERB_ON, VERB_OFF)}


def _own(domain: str, **services: str) -> dict[str, Verb]:
    """Verbs whose service lives in the entity's own domain."""
    return {verb: Verb(domain, service) for verb, service in services.items()}


_SELECT_VERBS = {
    "next_option": "select_next",
    "previous_option": "select_previous",
    "first_option": "select_first",
    "last_option": "select_last",
}

# Domain -> verb id -> verb. The order is the order the panel lists them in.
VERBS: dict[str, dict[str, Verb]] = {
    "light": dict(_SWITCHABLE),
    "switch": dict(_SWITCHABLE),
    "input_boolean": dict(_SWITCHABLE),
    "humidifier": dict(_SWITCHABLE),
    "remote": dict(_SWITCHABLE),
    "climate": dict(_SWITCHABLE),
    "fan": {
        **_SWITCHABLE,
        **_own("fan", speed_up="increase_speed", speed_down="decrease_speed"),
    },
    "media_player": {
        **_SWITCHABLE,
        **_own(
            "media_player",
            play_pause="media_play_pause",
            play="media_play",
            pause="media_pause",
            stop="media_stop",
            next="media_next_track",
            previous="media_previous_track",
            volume_up="volume_up",
            volume_down="volume_down",
        ),
        "mute_toggle": Verb(
            "media_player",
            "volume_mute",
            invert=("is_volume_muted", "is_volume_muted"),
        ),
    },
    "cover": _own(
        "cover",
        toggle="toggle",
        open="open_cover",
        close="close_cover",
        stop="stop_cover",
    ),
    "lock": _own("lock", lock="lock"),
    "vacuum": _own(
        "vacuum",
        start="start",
        pause="pause",
        stop="stop",
        return_home="return_to_base",
        locate="locate",
    ),
    "valve": _own("valve", close="close_valve", stop="stop_valve"),
    "siren": _own("siren", off="turn_off"),
    "button": _own("button", press="press"),
    "input_button": _own("input_button", press="press"),
    "automation": _own("automation", trigger="trigger"),
    "input_select": _own("input_select", **_SELECT_VERBS),
    "select": _own("select", **_SELECT_VERBS),
    "input_number": _own("input_number", step_up="increment", step_down="decrement"),
    # A script is run, stopped or toggled; a scene can only be run (it has no
    # off, and its state is the time it was last activated).
    "script": _own("script", on="turn_on", off="turn_off", toggle="toggle"),
    # "toggle" on a scene is what bindings saved before the choice existed
    # hold; it keeps meaning "run" and is not offered any more.
    "scene": _own("scene", on="turn_on", toggle="turn_on"),
}

# Verbs that only exist so older stored data keeps working. They run, but the
# pickers do not list them.
_LEGACY = {("scene", "toggle")}

# Entity domains a gesture may act on, in the order the pickers list them.
TARGET_DOMAINS = tuple(VERBS)

# Every verb id, once, in a stable order: the switchable words first, so the
# choices a binding saved long ago stored stay at the front of every list.
ALL_VERBS = tuple(dict.fromkeys(verb for verbs in VERBS.values() for verb in verbs))

# Entities whose state is not an on/off answer, or that have none worth
# waiting for: a scene reports when it was last activated and "unknown" before
# the first time, a script is idle or running, and a button reports the time of
# its last press and "unknown" until it was pressed once.
ACTS_WHILE_UNKNOWN = ("script", "scene", "button", "input_button")


def verbs_for(entity_id: str | None) -> tuple[str, ...]:
    """The verbs the entity's kind can carry out, in listing order."""
    domain = str(entity_id or "").split(".", 1)[0]
    return tuple(v for v in VERBS.get(domain, ()) if (domain, v) not in _LEGACY)


# Kinds of target that never take the switchable words from outside their own
# list: a scene has no off, and one stray toggle must not open a lock, sound a
# siren or open a valve.
_OWN_VERBS_ONLY = ("scene", "lock", "siren", "valve", "alarm_control_panel")


def verb_for(entity_id: str | None, action: str) -> Verb | None:
    """The verb ``action`` means for this entity, or ``None``.

    The entity's own list first. Before the verbs existed a gesture acted on
    anything with toggle, on or off through ``homeassistant``, including the
    entity a wheel's short press shares with its rotation (a number, a
    climate); that stays true, so a binding saved then still validates and
    runs, except for the kinds listed above.
    """
    domain = str(entity_id or "").split(".", 1)[0]
    verbs = VERBS.get(domain, {})
    if action in verbs:
        return verbs[action]
    if domain in _OWN_VERBS_ONLY:
        return None
    return _SWITCHABLE.get(action)


def schema_verbs() -> dict[str, list[str]]:
    """What the panel needs: the verbs of every kind of target it may offer."""
    return {
        domain: [v for v in verbs if (domain, v) not in _LEGACY]
        for domain, verbs in VERBS.items()
    }
