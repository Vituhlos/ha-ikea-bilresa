"""Tell the user which automations still use the retired device triggers.

Device triggers only work on a device this integration owns, and since Home
Assistant 2026.8 the wheel's device belongs to core Matter alone. They were
replaced by the entity-targeted triggers in `trigger.py`. An automation that
still holds a `device` trigger of this domain no longer loads; without this
notice the only sign would be an unavailable automation and a log line.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DOMAIN, CONF_PLATFORM
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.start import async_at_started

from .const import DOMAIN, ISSUE_LEGACY_DEVICE_TRIGGERS

_TRIGGER_KEYS = ("triggers", "trigger")
# `trigger:` replaced `platform:` as the type key in 2024.10; stored
# automations may still use either.
_TYPE_KEYS = ("trigger", CONF_PLATFORM)
_NESTED_TRIGGER_KEY = "triggers"


def _device_triggers(node: Any) -> Iterator[dict[str, Any]]:
    """Yield every device trigger in a trigger list, however it is nested."""
    if isinstance(node, list):
        for item in node:
            yield from _device_triggers(item)
        return
    if not isinstance(node, dict):
        return
    if any(node.get(key) == "device" for key in _TYPE_KEYS):
        yield node
    # A trigger list entry may itself be a `triggers:` group.
    yield from _device_triggers(node.get(_NESTED_TRIGGER_KEY))


def uses_legacy_device_trigger(raw_config: Any) -> bool:
    """Return whether an automation's raw config holds one of our device triggers."""
    if not isinstance(raw_config, dict):
        return False
    return any(
        trigger.get(CONF_DOMAIN) == DOMAIN
        for key in _TRIGGER_KEYS
        for trigger in _device_triggers(raw_config.get(key))
    )


@callback
def _affected_automations(hass: HomeAssistant) -> list[str]:
    """Names of the loaded automations that still use our device triggers."""
    # Imported here: the automation integration is optional for this one, and
    # this module must import cleanly without it.
    from homeassistant.components.automation import (  # noqa: PLC0415
        DATA_COMPONENT,
    )

    component = hass.data.get(DATA_COMPONENT)
    if component is None:
        return []
    return sorted(
        automation.name or automation.entity_id
        for automation in component.entities
        if uses_legacy_device_trigger(automation.raw_config)
    )


@callback
def async_refresh_legacy_trigger_notice(hass: HomeAssistant) -> None:
    """Raise or clear the Repairs notice to match the loaded automations."""
    affected = _affected_automations(hass)
    if not affected:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_LEGACY_DEVICE_TRIGGERS)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_LEGACY_DEVICE_TRIGGERS,
        is_fixable=False,
        is_persistent=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_LEGACY_DEVICE_TRIGGERS,
        translation_placeholders={
            "automations": "\n".join(f"- {name}" for name in affected),
        },
    )


@callback
def async_setup_legacy_trigger_notice(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Check once Home Assistant has started, and again when automations reload."""

    @callback
    def _refresh(_event: Event | HomeAssistant | None = None) -> None:
        async_refresh_legacy_trigger_notice(hass)

    # Automations load after integrations, so there is nothing to scan earlier.
    entry.async_on_unload(async_at_started(hass, _refresh))
    entry.async_on_unload(hass.bus.async_listen("automation_reloaded", _refresh))
