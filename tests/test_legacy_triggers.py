"""The Repairs notice for automations that still use the retired device triggers."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ikea_bilresa.const import DOMAIN, ISSUE_LEGACY_DEVICE_TRIGGERS
from custom_components.ikea_bilresa.legacy_triggers import (
    async_refresh_legacy_trigger_notice,
    async_setup_legacy_trigger_notice,
    uses_legacy_device_trigger,
)

LEGACY = {
    "platform": "device",
    "domain": DOMAIN,
    "device_id": "0123456789abcdef0123456789abcdef",
    "type": "rotate_up",
    "subtype": "channel_1",
}


@pytest.mark.parametrize(
    "raw_config",
    [
        {"trigger": LEGACY},
        {"trigger": [LEGACY]},
        {"triggers": [LEGACY]},
        # 2024.10 renamed the type key from `platform` to `trigger`.
        {
            "triggers": [
                {
                    **{k: v for k, v in LEGACY.items() if k != "platform"},
                    "trigger": "device",
                }
            ]
        },
        {"triggers": [{"trigger": "state", "entity_id": "light.a"}, LEGACY]},
        # A trigger list entry may itself be a group of triggers.
        {"triggers": [{"triggers": [LEGACY]}]},
    ],
)
def test_finds_our_device_trigger_however_it_is_written(raw_config: Any) -> None:
    assert uses_legacy_device_trigger(raw_config) is True


@pytest.mark.parametrize(
    "raw_config",
    [
        None,
        {},
        {"triggers": []},
        {"triggers": [{"trigger": "state", "entity_id": "light.a"}]},
        # Another integration's device trigger is none of our business.
        {"triggers": [{**LEGACY, "domain": "zha"}]},
        # The replacement trigger, and the bus event, are not device triggers.
        {"triggers": [{"trigger": f"{DOMAIN}.rotated_up", "target": {}}]},
        {"triggers": [{"trigger": "event", "event_type": "ikea_bilresa_event"}]},
        # A device action of ours would not be a trigger.
        {"actions": [LEGACY]},
        # Blueprint automations carry no trigger list of their own.
        {"use_blueprint": {"path": "ikea_bilresa/smooth_dimming.yaml"}},
    ],
)
def test_leaves_everything_else_alone(raw_config: Any) -> None:
    assert uses_legacy_device_trigger(raw_config) is False


def _issue(hass: HomeAssistant) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_LEGACY_DEVICE_TRIGGERS)


async def test_no_automation_integration_means_no_notice(hass: HomeAssistant) -> None:
    async_refresh_legacy_trigger_notice(hass)

    assert _issue(hass) is None


async def test_notice_names_the_affected_automations_and_clears(
    hass: HomeAssistant,
) -> None:
    """Run through the real automation integration.

    The legacy trigger does not validate any more, which is exactly the state
    a user is left in: the automation is there, unavailable, and still holds
    its raw config.
    """
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": [
                {
                    "alias": "Kitchen wheel dims the lamp",
                    "triggers": [LEGACY],
                    "actions": [],
                },
                {
                    "alias": "Unrelated",
                    "triggers": [{"trigger": "event", "event_type": "something"}],
                    "actions": [],
                },
            ]
        },
    )
    await hass.async_block_till_done()

    async_refresh_legacy_trigger_notice(hass)

    issue = _issue(hass)
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.is_fixable is False
    assert issue.translation_key == ISSUE_LEGACY_DEVICE_TRIGGERS
    assert issue.translation_placeholders == {
        "automations": "- Kitchen wheel dims the lamp"
    }

    # The user replaces the trigger; Home Assistant reloads automations.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "homeassistant.config.load_yaml_config_file",
            lambda *_args, **_kwargs: {
                "automation": [
                    {
                        "alias": "Kitchen wheel dims the lamp",
                        "triggers": [{"trigger": "event", "event_type": "x"}],
                        "actions": [],
                    }
                ]
            },
        )
        await hass.services.async_call("automation", "reload", blocking=True)
    await hass.async_block_till_done()

    async_refresh_legacy_trigger_notice(hass)

    assert _issue(hass) is None


async def test_setup_checks_at_start_and_after_an_automation_reload(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    affected: list[str] = ["Kitchen wheel dims the lamp"]
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.legacy_triggers._affected_automations",
        lambda _hass: list(affected),
    )
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    # Home Assistant is already running in the test, so the start check is due.
    async_setup_legacy_trigger_notice(hass, entry)
    await hass.async_block_till_done()
    assert _issue(hass) is not None

    affected.clear()
    hass.bus.async_fire("automation_reloaded")
    await hass.async_block_till_done()
    assert _issue(hass) is None
