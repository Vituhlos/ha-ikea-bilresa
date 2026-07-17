"""Shared validation and serialization for BILRESA binding configuration.

The native config-subentry flow and the panel editor must accept exactly the
same configuration. Keeping validation here prevents the two write paths from
quietly drifting apart.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

import voluptuous as vol

from .const import (
    BUTTON_RESPONSE_FAST,
    BUTTON_RESPONSES,
    CLICK_ACTIONS,
    CONF_ACCELERATION,
    CONF_BUTTON_RESPONSE,
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_HOLD_ACTION,
    CONF_HOLD_TARGET,
    CONF_MAX_BRIGHTNESS,
    CONF_MIN_BRIGHTNESS,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_SCENES,
    CONF_STEP,
    CONF_TARGET,
    CONF_TRANSITION,
    CONF_TRIPLE_TARGET,
    DEFAULT_ACCELERATION,
    DEFAULT_BUTTON_RESPONSE,
    DEFAULT_CLICK_ACTION,
    DEFAULT_HOLD_ACTION,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MODE,
    DEFAULT_STEP,
    DEFAULT_TRANSITION,
    HOLD_ACTIONS,
    MODES,
    mode_supports_target,
)

BINDING_OPTIONAL_FIELDS = (
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_TRIPLE_TARGET,
    CONF_HOLD_TARGET,
    CONF_SCENES,
)

BINDING_EDIT_FIELDS = (
    CONF_TARGET,
    CONF_MODE,
    CONF_STEP,
    CONF_ACCELERATION,
    CONF_MIN_BRIGHTNESS,
    CONF_MAX_BRIGHTNESS,
    CONF_TRANSITION,
    CONF_CLICK_ACTION,
    CONF_BUTTON_RESPONSE,
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_TRIPLE_TARGET,
    CONF_HOLD_TARGET,
    CONF_HOLD_ACTION,
    CONF_SCENES,
)

_ENTITY_ID = vol.Match(r"^[a-z0-9_]+\.[a-z0-9_]+$")

_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NODE_ID): vol.All(str, vol.Length(min=1)),
        vol.Required(CONF_CHANNEL): vol.In(("1", "2", "3")),
        vol.Required(CONF_TARGET): _ENTITY_ID,
        vol.Required(CONF_MODE, default=DEFAULT_MODE): vol.In(MODES),
        vol.Required(CONF_STEP, default=DEFAULT_STEP): vol.All(
            vol.Coerce(float), vol.Range(min=1, max=25)
        ),
        vol.Required(CONF_ACCELERATION, default=DEFAULT_ACCELERATION): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=100)
        ),
        vol.Required(CONF_MIN_BRIGHTNESS, default=DEFAULT_MIN_BRIGHTNESS): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=50)
        ),
        vol.Required(CONF_MAX_BRIGHTNESS, default=DEFAULT_MAX_BRIGHTNESS): vol.All(
            vol.Coerce(float), vol.Range(min=1, max=100)
        ),
        vol.Required(CONF_TRANSITION, default=DEFAULT_TRANSITION): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=5)
        ),
        vol.Required(CONF_CLICK_ACTION, default=DEFAULT_CLICK_ACTION): vol.In(
            CLICK_ACTIONS
        ),
        vol.Required(CONF_BUTTON_RESPONSE, default=DEFAULT_BUTTON_RESPONSE): vol.In(
            BUTTON_RESPONSES
        ),
        vol.Optional(CONF_CLICK_TARGET): _ENTITY_ID,
        vol.Optional(CONF_DOUBLE_TARGET): _ENTITY_ID,
        vol.Optional(CONF_TRIPLE_TARGET): _ENTITY_ID,
        vol.Optional(CONF_HOLD_TARGET): _ENTITY_ID,
        vol.Required(CONF_HOLD_ACTION, default=DEFAULT_HOLD_ACTION): vol.In(
            HOLD_ACTIONS
        ),
        vol.Optional(CONF_SCENES): vol.All([_ENTITY_ID], vol.Length(max=50)),
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
    return {field: data[field] for field in BINDING_EDIT_FIELDS if field in data}


def normalize_binding_data(
    data: dict[str, Any], *, node_id: int | str, channel: int | str
) -> dict[str, Any]:
    """Normalize panel or config-flow input to the stored subentry shape."""
    candidate = {
        CONF_NODE_ID: str(node_id),
        CONF_CHANNEL: str(channel),
        **{field: data[field] for field in BINDING_EDIT_FIELDS if field in data},
    }
    for field in BINDING_OPTIONAL_FIELDS:
        if candidate.get(field) in (None, "", []):
            candidate.pop(field, None)
    return dict(_SCHEMA(candidate))


def binding_errors(data: dict[str, Any]) -> dict[str, str]:
    """Return field-addressable semantic errors for normalized binding data."""
    errors: dict[str, str] = {}
    if not mode_supports_target(data[CONF_MODE], data[CONF_TARGET]):
        errors[CONF_TARGET] = "mode_target_mismatch"
    if data[CONF_MIN_BRIGHTNESS] >= data[CONF_MAX_BRIGHTNESS]:
        errors[CONF_MAX_BRIGHTNESS] = "maximum_must_exceed_minimum"
    if data.get(CONF_BUTTON_RESPONSE) == BUTTON_RESPONSE_FAST and (
        data.get(CONF_DOUBLE_TARGET) or data.get(CONF_TRIPLE_TARGET)
    ):
        errors[CONF_BUTTON_RESPONSE] = "fast_response_conflicts_with_multi_press"
    return errors


def validate_binding_data(
    data: dict[str, Any], *, node_id: int | str, channel: int | str
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """Normalize and validate a binding without raising into the UI."""
    try:
        normalized = normalize_binding_data(data, node_id=node_id, channel=channel)
    except vol.Invalid as err:
        path = str(err.path[-1]) if err.path else "base"
        return None, {path: "invalid_value"}
    errors = binding_errors(normalized)
    return (None, errors) if errors else (normalized, {})
