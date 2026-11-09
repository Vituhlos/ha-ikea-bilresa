"""Shared validation and serialization for BILRESA binding configuration.

The native config-subentry flow and the panel editor must accept exactly the
same configuration. Keeping validation here prevents the two write paths from
quietly drifting apart.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    ACTION_RUN,
    BUTTON_RESPONSE_FAST,
    BUTTON_RESPONSE_INSTANT,
    BUTTON_RESPONSES,
    CLICK_ACTIONS,
    CLICK_NONE,
    CLICK_OFF,
    CONF_ACCELERATION,
    CONF_BUTTON_RESPONSE,
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_CLICK_SEQUENCE,
    CONF_CLICK_TARGET,
    CONF_DOUBLE_ACTION,
    CONF_DOUBLE_SEQUENCE,
    CONF_DOUBLE_TARGET,
    CONF_ENDPOINT,
    CONF_HOLD_ACTION,
    CONF_HOLD_SEQUENCE,
    CONF_HOLD_TARGET,
    CONF_HOLD_TARGET_ACTION,
    CONF_MAX_BRIGHTNESS,
    CONF_MIN_BRIGHTNESS,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_RAMP_DIRECTION,
    CONF_SCENES,
    CONF_STEP,
    CONF_STEP_CURVE,
    CONF_TARGET,
    CONF_TRANSITION,
    CONF_TRIPLE_ACTION,
    CONF_TRIPLE_SEQUENCE,
    CONF_TRIPLE_TARGET,
    DEFAULT_ACCELERATION,
    DEFAULT_BUTTON_RESPONSE,
    DEFAULT_CLICK_ACTION,
    DEFAULT_HOLD_ACTION,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MODE,
    DEFAULT_RAMP_DIRECTION,
    DEFAULT_STEP,
    DEFAULT_STEP_CURVE,
    DEFAULT_TARGET_ACTION,
    DEFAULT_TRANSITION,
    HOLD_ACTIONS,
    HOLD_NONE,
    HOLD_RAMP,
    HOLD_RUN,
    HOLD_TOGGLE,
    MAX_BINDING_TARGETS,
    MODES,
    MULTI_TARGET_MODES,
    RAMP_DIRECTIONS,
    STEP_CURVES,
    TARGET_ACTIONS,
    binding_targets,
    is_scene_target,
    mode_supports_target,
)
from .gesture_actions import action_is_supported
from .panel_schema import BINDING_NUMBERS

BINDING_OPTIONAL_FIELDS = (
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_TRIPLE_TARGET,
    CONF_HOLD_TARGET,
    CONF_SCENES,
    CONF_CLICK_SEQUENCE,
    CONF_DOUBLE_SEQUENCE,
    CONF_TRIPLE_SEQUENCE,
    CONF_HOLD_SEQUENCE,
)

# Each gesture that can run an action sequence, with the field that says what it
# does and the field that holds the sequence. A sequence is only kept while its
# gesture is set to "run".
_SEQUENCE_GESTURES = (
    (CONF_CLICK_ACTION, CONF_CLICK_SEQUENCE),
    (CONF_DOUBLE_ACTION, CONF_DOUBLE_SEQUENCE),
    (CONF_TRIPLE_ACTION, CONF_TRIPLE_SEQUENCE),
    (CONF_HOLD_ACTION, CONF_HOLD_SEQUENCE),
)

SEQUENCE_FIELDS = tuple(sequence for _action, sequence in _SEQUENCE_GESTURES)

BINDING_EDIT_FIELDS = (
    CONF_TARGET,
    CONF_MODE,
    CONF_STEP,
    CONF_STEP_CURVE,
    CONF_ACCELERATION,
    CONF_MIN_BRIGHTNESS,
    CONF_MAX_BRIGHTNESS,
    CONF_TRANSITION,
    CONF_CLICK_ACTION,
    CONF_BUTTON_RESPONSE,
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_DOUBLE_ACTION,
    CONF_TRIPLE_TARGET,
    CONF_TRIPLE_ACTION,
    CONF_HOLD_TARGET,
    CONF_HOLD_TARGET_ACTION,
    CONF_HOLD_ACTION,
    CONF_SCENES,
    CONF_CLICK_SEQUENCE,
    CONF_DOUBLE_SEQUENCE,
    CONF_TRIPLE_SEQUENCE,
    CONF_HOLD_SEQUENCE,
)

BUTTON_BINDING_EDIT_FIELDS = (
    CONF_CLICK_ACTION,
    CONF_BUTTON_RESPONSE,
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_DOUBLE_ACTION,
    CONF_HOLD_TARGET,
    CONF_HOLD_TARGET_ACTION,
    CONF_HOLD_ACTION,
    CONF_RAMP_DIRECTION,
    CONF_CLICK_SEQUENCE,
    CONF_DOUBLE_SEQUENCE,
    CONF_HOLD_SEQUENCE,
)

_ENTITY_ID = vol.Match(r"^[a-z0-9_]+\.[a-z0-9_]+$")
# The rotation target: one entity id, or a list of them for a multi-light
# binding. Normalization below stores a single entity as a plain string.
_TARGETS = vol.Any(
    _ENTITY_ID,
    vol.All([_ENTITY_ID], vol.Length(min=1, max=MAX_BINDING_TARGETS)),
)

_MAX_SEQUENCE_ACTIONS = 50


def _sequence(value: Any) -> list[dict[str, Any]]:
    """Accept a Home Assistant action sequence and keep it as it was written.

    The sequence is checked with Home Assistant's own action schema, so a
    mistake is refused when the binding is saved. What is stored is the plain
    data the editor produced (templates stay text), because a config entry
    holds JSON; the runtime validates it again when it builds the script.
    """
    if not isinstance(value, list) or not 1 <= len(value) <= _MAX_SEQUENCE_ACTIONS:
        raise vol.Invalid("actions must be a list of 1 to 50 actions")
    try:
        cv.SCRIPT_SCHEMA(value)
        json.dumps(value)
    except (vol.Invalid, TypeError, ValueError) as err:
        raise vol.Invalid("not a valid action sequence") from err
    return value


_WHEEL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NODE_ID): vol.All(str, vol.Length(min=1)),
        vol.Required(CONF_CHANNEL): vol.In(("1", "2", "3")),
        vol.Required(CONF_TARGET): _TARGETS,
        vol.Required(CONF_MODE, default=DEFAULT_MODE): vol.In(MODES),
        vol.Required(CONF_STEP, default=DEFAULT_STEP): BINDING_NUMBERS[
            CONF_STEP
        ].validator(),
        vol.Required(CONF_STEP_CURVE, default=DEFAULT_STEP_CURVE): vol.In(STEP_CURVES),
        vol.Required(CONF_ACCELERATION, default=DEFAULT_ACCELERATION): BINDING_NUMBERS[
            CONF_ACCELERATION
        ].validator(),
        vol.Required(
            CONF_MIN_BRIGHTNESS, default=DEFAULT_MIN_BRIGHTNESS
        ): BINDING_NUMBERS[CONF_MIN_BRIGHTNESS].validator(),
        vol.Required(
            CONF_MAX_BRIGHTNESS, default=DEFAULT_MAX_BRIGHTNESS
        ): BINDING_NUMBERS[CONF_MAX_BRIGHTNESS].validator(),
        vol.Required(CONF_TRANSITION, default=DEFAULT_TRANSITION): BINDING_NUMBERS[
            CONF_TRANSITION
        ].validator(),
        vol.Required(CONF_CLICK_ACTION, default=DEFAULT_CLICK_ACTION): vol.In(
            CLICK_ACTIONS
        ),
        vol.Required(CONF_BUTTON_RESPONSE, default=DEFAULT_BUTTON_RESPONSE): vol.In(
            BUTTON_RESPONSES
        ),
        vol.Optional(CONF_CLICK_TARGET): _ENTITY_ID,
        vol.Optional(CONF_CLICK_SEQUENCE): _sequence,
        vol.Optional(CONF_DOUBLE_TARGET): _ENTITY_ID,
        vol.Optional(CONF_DOUBLE_SEQUENCE): _sequence,
        vol.Required(CONF_DOUBLE_ACTION, default=DEFAULT_TARGET_ACTION): vol.In(
            TARGET_ACTIONS
        ),
        vol.Optional(CONF_TRIPLE_TARGET): _ENTITY_ID,
        vol.Optional(CONF_TRIPLE_SEQUENCE): _sequence,
        vol.Required(CONF_TRIPLE_ACTION, default=DEFAULT_TARGET_ACTION): vol.In(
            TARGET_ACTIONS
        ),
        vol.Optional(CONF_HOLD_TARGET): _ENTITY_ID,
        vol.Optional(CONF_HOLD_SEQUENCE): _sequence,
        vol.Required(CONF_HOLD_TARGET_ACTION, default=DEFAULT_TARGET_ACTION): vol.In(
            TARGET_ACTIONS
        ),
        vol.Required(CONF_HOLD_ACTION, default=DEFAULT_HOLD_ACTION): vol.In(
            HOLD_ACTIONS
        ),
        vol.Optional(CONF_SCENES): vol.All([_ENTITY_ID], vol.Length(max=50)),
    },
    extra=vol.PREVENT_EXTRA,
)

_BUTTON_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NODE_ID): vol.All(str, vol.Length(min=1)),
        vol.Required(CONF_ENDPOINT): vol.All(str, vol.Match(r"^[1-9]\d*$")),
        vol.Required(CONF_CLICK_ACTION, default=DEFAULT_CLICK_ACTION): vol.In(
            CLICK_ACTIONS
        ),
        vol.Required(CONF_BUTTON_RESPONSE, default=DEFAULT_BUTTON_RESPONSE): vol.In(
            BUTTON_RESPONSES
        ),
        vol.Optional(CONF_CLICK_TARGET): _ENTITY_ID,
        vol.Optional(CONF_CLICK_SEQUENCE): _sequence,
        vol.Optional(CONF_DOUBLE_TARGET): _ENTITY_ID,
        vol.Optional(CONF_DOUBLE_SEQUENCE): _sequence,
        vol.Required(CONF_DOUBLE_ACTION, default=DEFAULT_TARGET_ACTION): vol.In(
            TARGET_ACTIONS
        ),
        vol.Optional(CONF_HOLD_TARGET): _ENTITY_ID,
        vol.Optional(CONF_HOLD_SEQUENCE): _sequence,
        vol.Required(CONF_HOLD_TARGET_ACTION, default=DEFAULT_TARGET_ACTION): vol.In(
            TARGET_ACTIONS
        ),
        vol.Required(CONF_HOLD_ACTION, default=DEFAULT_HOLD_ACTION): vol.In(
            HOLD_ACTIONS
        ),
        vol.Required(CONF_RAMP_DIRECTION, default=DEFAULT_RAMP_DIRECTION): vol.In(
            RAMP_DIRECTIONS
        ),
    },
    extra=vol.PREVENT_EXTRA,
)


def binding_revision(subentry: Any) -> str:
    """Return a stable optimistic-concurrency token for one subentry."""
    canonical = json.dumps(
        {
            "id": subentry.subentry_id,
            "title": subentry.title,
            "data": dict(subentry.data),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return sha256(canonical.encode()).hexdigest()[:16]


def editor_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return only fields the panel is allowed to edit."""
    fields = (
        BUTTON_BINDING_EDIT_FIELDS if CONF_ENDPOINT in data else BINDING_EDIT_FIELDS
    )
    return {field: data[field] for field in fields if field in data}


def normalize_binding_data(
    data: dict[str, Any],
    *,
    node_id: int | str,
    channel: int | str | None = None,
    endpoint: int | str | None = None,
) -> dict[str, Any]:
    """Normalize panel or config-flow input to the stored subentry shape."""
    if (channel is None) == (endpoint is None):
        raise vol.Invalid("exactly one binding address is required")
    is_button = endpoint is not None
    address = (
        {CONF_ENDPOINT: str(endpoint)} if is_button else {CONF_CHANNEL: str(channel)}
    )
    edit_fields = BUTTON_BINDING_EDIT_FIELDS if is_button else BINDING_EDIT_FIELDS
    candidate = {
        CONF_NODE_ID: str(node_id),
        **address,
        **{field: data[field] for field in edit_fields if field in data},
    }
    for field in BINDING_OPTIONAL_FIELDS:
        if candidate.get(field) in (None, "", []):
            candidate.pop(field, None)
    for action_field, sequence_field in _SEQUENCE_GESTURES:
        if candidate.get(action_field) != ACTION_RUN:
            candidate.pop(sequence_field, None)
    if not is_button and isinstance(candidate.get(CONF_TARGET), list | tuple):
        # One entity keeps the historic string shape, so a binding saved with
        # a single light reads exactly like one saved before multi-light
        # support. Duplicates are dropped; an empty list stays invalid.
        targets = binding_targets(candidate[CONF_TARGET])
        candidate[CONF_TARGET] = targets[0] if len(targets) == 1 else targets
    return dict((_BUTTON_SCHEMA if is_button else _WHEEL_SCHEMA)(candidate))


def binding_errors(data: dict[str, Any]) -> dict[str, str]:
    """Return field-addressable semantic errors for normalized binding data."""
    errors: dict[str, str] = {}
    is_button = CONF_ENDPOINT in data
    # A scene can only be run: it has no off, whichever gesture asks for one.
    # Scene cycling replaces the short press, so its stored action is unused.
    gestures = [
        (
            CONF_DOUBLE_ACTION,
            data.get(CONF_DOUBLE_TARGET),
            data.get(CONF_DOUBLE_ACTION, DEFAULT_TARGET_ACTION),
        ),
        (
            CONF_TRIPLE_ACTION,
            data.get(CONF_TRIPLE_TARGET),
            data.get(CONF_TRIPLE_ACTION, DEFAULT_TARGET_ACTION),
        ),
    ]
    if not data.get(CONF_SCENES):
        gestures.append(
            (
                CONF_CLICK_ACTION,
                data.get(CONF_CLICK_TARGET) or data.get(CONF_TARGET),
                data.get(CONF_CLICK_ACTION, DEFAULT_CLICK_ACTION),
            )
        )
    if data.get(CONF_HOLD_ACTION) == HOLD_TOGGLE:
        gestures.append(
            (
                CONF_HOLD_TARGET_ACTION,
                data.get(CONF_HOLD_TARGET),
                data.get(CONF_HOLD_TARGET_ACTION, DEFAULT_TARGET_ACTION),
            )
        )
    for field, target, action in gestures:
        # The short press may default to the rotation target, which is a list
        # in a multi-light binding: every light has to support the action.
        for single in binding_targets(target):
            if not action_is_supported(single, action):
                errors[field] = (
                    "scene_cannot_turn_off"
                    if is_scene_target(single) and action == CLICK_OFF
                    else "action_not_supported"
                )
                break
    # A gesture set to run needs something to run. Scene cycling replaces the
    # short press, so a sequence on it would never run.
    for action_field, sequence_field in _SEQUENCE_GESTURES:
        if data.get(action_field) == ACTION_RUN and not data.get(sequence_field):
            errors[action_field] = "actions_required"
    if data.get(CONF_SCENES) and data.get(CONF_CLICK_ACTION) == ACTION_RUN:
        errors[CONF_CLICK_ACTION] = "scenes_replace_short_press"
    if is_button:
        if data[CONF_CLICK_ACTION] not in (CLICK_NONE, ACTION_RUN) and not data.get(
            CONF_CLICK_TARGET
        ):
            errors[CONF_CLICK_TARGET] = "target_required"
        hold_action = data[CONF_HOLD_ACTION]
        hold_target = data.get(CONF_HOLD_TARGET)
        if hold_action not in (HOLD_NONE, HOLD_RUN) and not hold_target:
            errors[CONF_HOLD_TARGET] = "target_required"
        elif hold_action == HOLD_RAMP and not str(hold_target).startswith("light."):
            errors[CONF_HOLD_TARGET] = "ramp_requires_light"
    else:
        targets = binding_targets(data[CONF_TARGET])
        if len(targets) > 1 and data[CONF_MODE] not in MULTI_TARGET_MODES:
            errors[CONF_TARGET] = "multiple_targets_require_light_mode"
        elif not all(mode_supports_target(data[CONF_MODE], t) for t in targets):
            errors[CONF_TARGET] = "mode_target_mismatch"
        if data[CONF_MIN_BRIGHTNESS] >= data[CONF_MAX_BRIGHTNESS]:
            errors[CONF_MAX_BRIGHTNESS] = "maximum_must_exceed_minimum"
    multi_press = bool(
        data.get(CONF_DOUBLE_TARGET)
        or data.get(CONF_TRIPLE_TARGET)
        or data.get(CONF_DOUBLE_ACTION) == ACTION_RUN
        or data.get(CONF_TRIPLE_ACTION) == ACTION_RUN
    )
    if data.get(CONF_BUTTON_RESPONSE) == BUTTON_RESPONSE_FAST and multi_press:
        errors[CONF_BUTTON_RESPONSE] = "fast_response_conflicts_with_multi_press"
    if data.get(CONF_BUTTON_RESPONSE) == BUTTON_RESPONSE_INSTANT:
        if multi_press:
            errors[CONF_BUTTON_RESPONSE] = "instant_response_conflicts_with_multi_press"
        elif data.get(CONF_HOLD_ACTION) != HOLD_NONE:
            errors[CONF_BUTTON_RESPONSE] = "instant_response_conflicts_with_hold"
    return errors


def validate_binding_data(
    data: dict[str, Any],
    *,
    node_id: int | str,
    channel: int | str | None = None,
    endpoint: int | str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """Normalize and validate a binding without raising into the UI."""
    try:
        normalized = normalize_binding_data(
            data, node_id=node_id, channel=channel, endpoint=endpoint
        )
    except vol.Invalid as err:
        path = str(err.path[-1]) if err.path else "base"
        return None, {path: "invalid_value"}
    errors = binding_errors(normalized)
    return (None, errors) if errors else (normalized, {})
