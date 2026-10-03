"""Every user-visible string is translated, in every shipped language.

The owner's rule: no user-visible text is hard-coded in Python, and English
and Czech always ship together. `test_panel_strings.py` holds the same rule
for the panel; this file covers what Home Assistant itself renders: entity
names, gesture names, triggers and Repairs.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockEntityPlatform,
)
import yaml

from custom_components.ikea_bilresa import event, number, switch
from custom_components.ikea_bilresa.channel_controls import DEFAULT_SETTINGS
from custom_components.ikea_bilresa.const import (
    DOMAIN,
    ISSUE_CANNOT_CONNECT,
    ISSUE_LEGACY_DEVICE_TRIGGERS,
    WHEEL_EVENT_TYPES,
    button_event_types,
)
from custom_components.ikea_bilresa.device_link import MatterDeviceLink
from custom_components.ikea_bilresa.event import BilresaButtonEvent, BilresaChannelEvent
from custom_components.ikea_bilresa.number import BilresaChannelDial
from custom_components.ikea_bilresa.switch import BilresaChannelButtonSwitch
from custom_components.ikea_bilresa.trigger import GESTURES

COMPONENT = Path(__file__).parent.parent / "custom_components" / "ikea_bilresa"
LANGUAGES = sorted(path.stem for path in (COMPONENT / "translations").glob("*.json"))
PLACEHOLDER = re.compile(r"\{[a-z_]+\}")


def _load(name: str) -> dict[str, Any]:
    return json.loads((COMPONENT / name).read_text(encoding="utf-8"))


def _flatten(node: Any, prefix: str = "") -> dict[str, str]:
    if isinstance(node, dict):
        flat: dict[str, str] = {}
        for key, value in node.items():
            flat.update(_flatten(value, f"{prefix}.{key}" if prefix else key))
        return flat
    return {prefix: node}


STRINGS = _flatten(_load("strings.json"))
TRANSLATIONS = {
    language: _flatten(_load(f"translations/{language}.json")) for language in LANGUAGES
}


def test_english_and_czech_are_shipped() -> None:
    assert {"cs", "en"} <= set(LANGUAGES)


def test_english_translation_is_the_source_strings() -> None:
    assert TRANSLATIONS["en"] == STRINGS


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_language_has_exactly_the_source_keys(language: str) -> None:
    assert sorted(TRANSLATIONS[language]) == sorted(STRINGS)


@pytest.mark.parametrize("language", LANGUAGES)
def test_placeholders_match_the_source(language: str) -> None:
    mismatched = {
        key: (sorted(PLACEHOLDER.findall(STRINGS[key])), sorted(found))
        for key, text in TRANSLATIONS[language].items()
        if sorted(found := PLACEHOLDER.findall(text))
        != sorted(PLACEHOLDER.findall(STRINGS[key]))
    }
    assert mismatched == {}


@pytest.mark.parametrize("language", LANGUAGES)
def test_no_string_is_empty(language: str) -> None:
    assert [
        key for key, text in TRANSLATIONS[language].items() if not text.strip()
    ] == []


def test_czech_entity_and_trigger_text_is_actually_translated() -> None:
    """A copied English string passes the key check and helps nobody."""
    same = [
        key
        for key, text in TRANSLATIONS["cs"].items()
        if key.startswith(("entity.", "triggers.", "issues.")) and text == STRINGS[key]
    ]
    assert same == []


# -- every gesture, trigger and notice has its text -------------------------


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_wheel_gesture_has_a_name(language: str) -> None:
    for event_type in WHEEL_EVENT_TYPES:
        key = f"entity.event.channel.state_attributes.event_type.state.{event_type}"
        assert key in TRANSLATIONS[language]


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_button_gesture_has_a_name(language: str) -> None:
    for event_type in button_event_types(3):
        key = f"entity.event.button.state_attributes.event_type.state.{event_type}"
        assert key in TRANSLATIONS[language]


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_trigger_is_named_and_described(language: str) -> None:
    for trigger in GESTURES:
        assert f"triggers.{trigger}.name" in TRANSLATIONS[language]
        assert f"triggers.{trigger}.description" in TRANSLATIONS[language]
    described = {key.split(".")[1] for key in STRINGS if key.startswith("triggers.")}
    assert described == set(GESTURES)


def test_trigger_descriptions_and_icons_cover_every_trigger() -> None:
    descriptions = yaml.safe_load((COMPONENT / "triggers.yaml").read_text("utf-8"))
    assert set(descriptions) == set(GESTURES)
    for description in descriptions.values():
        # Offered wherever one of our event entities is, whoever owns the device.
        assert description["target"]["entity"] == {
            "integration": DOMAIN,
            "domain": "event",
        }
    assert set(_load("icons.json")["triggers"]) == set(GESTURES)


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_repairs_issue_has_its_text(language: str) -> None:
    for issue in (ISSUE_CANNOT_CONNECT, ISSUE_LEGACY_DEVICE_TRIGGERS):
        assert f"issues.{issue}.title" in TRANSLATIONS[language]
        assert f"issues.{issue}.description" in TRANSLATIONS[language]


def test_no_entity_name_is_hard_coded() -> None:
    offenders = [
        f"{source.name}:{number}"
        for source in sorted(COMPONENT.glob("*.py"))
        for number, line in enumerate(
            source.read_text(encoding="utf-8").splitlines(), start=1
        )
        if re.search(r"\b_attr_name\s*=", line)
    ]
    assert offenders == []


# -- what Home Assistant actually renders -----------------------------------

EXPECTED_NAMES = {
    "en": {
        "event": "Wheel Channel 2",
        "number": "Wheel Dial 2",
        "switch": "Wheel Button 2",
        "dual": "Wheel Button 1",
    },
    "cs": {
        "event": "Wheel Kanál 2",
        "number": "Wheel Číselník 2",
        "switch": "Wheel Tlačítko 2",
        "dual": "Wheel Tlačítko 1",
    },
}


@pytest.mark.usefixtures("enable_custom_integrations")
@pytest.mark.parametrize("language", ["en", "cs"])
async def test_entity_names_follow_the_instance_language(
    hass: HomeAssistant, language: str
) -> None:
    hass.config.language = language
    matter = MockConfigEntry(domain="matter")
    matter.add_to_hass(hass)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=matter.entry_id,
        identifiers={("matter", "serial_NAMES")},
        name="Wheel",
    )
    link = MatterDeviceLink(device)
    wheel = SimpleNamespace(node_id=21, name="Wheel")
    coordinator = SimpleNamespace(
        connected=True,
        channel_enabled=lambda node_id, channel: True,
        settings_for=lambda node_id: DEFAULT_SETTINGS,
    )
    entities = {
        "event": (event, BilresaChannelEvent(coordinator, wheel, 2, link)),
        "number": (number, BilresaChannelDial(coordinator, wheel, 2, link)),
        "switch": (switch, BilresaChannelButtonSwitch(coordinator, wheel, 2, link)),
    }
    dual = BilresaButtonEvent(coordinator, wheel, 1, 1, 2, link)

    names: dict[str, str] = {}
    for domain, (_module, entity) in entities.items():
        platform = MockEntityPlatform(hass, domain=domain, platform_name=DOMAIN)
        platform.config_entry = entry
        await platform.platform_data.async_load_translations()
        await platform.async_add_entities(
            [entity, dual] if domain == "event" else [entity]
        )
        state = hass.states.get(entity.entity_id)
        assert state is not None
        names[domain] = state.attributes["friendly_name"]
    dual_state = hass.states.get(dual.entity_id)
    assert dual_state is not None
    names["dual"] = dual_state.attributes["friendly_name"]

    assert names == EXPECTED_NAMES[language]
