"""What a press does to its target: the table, the stored shape, the checks."""

from __future__ import annotations

import pytest

from custom_components.ikea_bilresa.binding_config import (
    binding_errors,
    editor_data,
    normalize_binding_data,
    validate_binding_data,
)
from custom_components.ikea_bilresa.const import (
    CONF_CLICK_ACTION,
    CONF_CLICK_TARGET,
    CONF_DOUBLE_ACTION,
    CONF_DOUBLE_TARGET,
    CONF_HOLD_ACTION,
    CONF_HOLD_TARGET,
    CONF_HOLD_TARGET_ACTION,
    CONF_MODE,
    CONF_SCENES,
    CONF_TARGET,
    CONF_TRIPLE_ACTION,
    CONF_TRIPLE_TARGET,
    HOLD_NONE,
    HOLD_RAMP,
    HOLD_TOGGLE,
    MODE_BRIGHTNESS,
    is_scene_target,
)
from custom_components.ikea_bilresa.gesture_actions import (
    action_is_supported,
    passes_variables,
    result_label,
    target_service,
)


@pytest.mark.parametrize(
    ("entity", "action", "expected"),
    [
        ("light.a", "toggle", ("homeassistant", "toggle")),
        ("light.a", "on", ("homeassistant", "turn_on")),
        ("light.a", "off", ("homeassistant", "turn_off")),
        ("switch.a", "toggle", ("homeassistant", "toggle")),
        ("script.a", "toggle", ("script", "toggle")),
        ("script.a", "on", ("script", "turn_on")),
        ("script.a", "off", ("script", "turn_off")),
        ("scene.a", "toggle", ("scene", "turn_on")),
        ("scene.a", "on", ("scene", "turn_on")),
        ("scene.a", "off", None),
    ],
)
def test_the_service_for_each_target_and_action(entity, action, expected) -> None:
    assert target_service(entity, action) == expected


@pytest.mark.parametrize(
    ("entity", "action", "named"),
    [
        ("light.a", "toggle", "toggle"),
        ("light.a", "on", "turn_on"),
        ("light.a", "off", "turn_off"),
        ("script.a", "on", "run"),
        ("script.a", "off", "stop"),
        ("script.a", "toggle", "toggle"),
        ("scene.a", "on", "run"),
        ("scene.a", "toggle", "run"),
    ],
)
def test_the_word_the_live_activity_uses(entity, action, named) -> None:
    assert result_label(entity, action) == named


def test_only_running_a_script_carries_variables() -> None:
    """``script.toggle`` and ``script.turn_off`` cannot take any."""
    assert passes_variables("script.a", "on")
    assert not passes_variables("script.a", "toggle")
    assert not passes_variables("script.a", "off")
    assert not passes_variables("scene.a", "on")
    assert not passes_variables("light.a", "on")


def test_only_a_scene_refuses_off() -> None:
    assert not action_is_supported("scene.a", "off")
    assert action_is_supported("scene.a", "on")
    assert action_is_supported("script.a", "off")
    assert action_is_supported("light.a", "off")
    assert is_scene_target("scene.a") and not is_scene_target("script.a")
    assert not is_scene_target(None)


# -- the stored shape ------------------------------------------------------

_WHEEL = {
    CONF_MODE: MODE_BRIGHTNESS,
    CONF_TARGET: "light.main",
}


def _normalize(**fields):
    return normalize_binding_data({**_WHEEL, **fields}, node_id=1, channel=1)


def test_data_stored_before_the_choice_existed_loads_as_toggle() -> None:
    """Old bindings have no action fields; they get the behaviour they had."""
    stored = _normalize(**{CONF_DOUBLE_TARGET: "script.go"})

    assert stored[CONF_DOUBLE_ACTION] == "toggle"
    assert stored[CONF_TRIPLE_ACTION] == "toggle"
    assert stored[CONF_HOLD_TARGET_ACTION] == "toggle"


def test_the_chosen_actions_are_kept_and_sent_to_the_editor() -> None:
    stored = _normalize(
        **{
            CONF_DOUBLE_TARGET: "script.go",
            CONF_DOUBLE_ACTION: "on",
            CONF_TRIPLE_TARGET: "script.go",
            CONF_TRIPLE_ACTION: "off",
            CONF_HOLD_TARGET: "scene.a",
            CONF_HOLD_TARGET_ACTION: "on",
        }
    )

    shown = editor_data(stored)

    assert shown[CONF_DOUBLE_ACTION] == "on"
    assert shown[CONF_TRIPLE_ACTION] == "off"
    assert shown[CONF_HOLD_TARGET_ACTION] == "on"


def test_an_action_that_is_not_one_is_refused() -> None:
    normalized, errors = validate_binding_data(
        {**_WHEEL, CONF_DOUBLE_TARGET: "script.go", CONF_DOUBLE_ACTION: "none"},
        node_id=1,
        channel=1,
    )

    assert normalized is None
    assert errors == {CONF_DOUBLE_ACTION: "invalid_value"}


def test_a_dual_button_has_no_triple_press_action() -> None:
    stored = normalize_binding_data(
        {CONF_CLICK_ACTION: "none", CONF_HOLD_ACTION: HOLD_NONE},
        node_id=1,
        endpoint=1,
    )

    assert CONF_TRIPLE_ACTION not in stored
    assert stored[CONF_DOUBLE_ACTION] == "toggle"


# -- the checks ------------------------------------------------------------


@pytest.mark.parametrize(
    ("target_field", "action_field"),
    [
        (CONF_CLICK_TARGET, CONF_CLICK_ACTION),
        (CONF_DOUBLE_TARGET, CONF_DOUBLE_ACTION),
        (CONF_TRIPLE_TARGET, CONF_TRIPLE_ACTION),
        (CONF_HOLD_TARGET, CONF_HOLD_TARGET_ACTION),
    ],
)
def test_a_scene_cannot_be_turned_off_by_any_gesture(
    target_field, action_field
) -> None:
    stored = _normalize(
        **{
            target_field: "scene.evening",
            action_field: "off",
            CONF_HOLD_ACTION: HOLD_TOGGLE,
        }
    )

    assert binding_errors(stored) == {action_field: "scene_cannot_turn_off"}


@pytest.mark.parametrize(
    ("target_field", "action_field"),
    [
        (CONF_CLICK_TARGET, CONF_CLICK_ACTION),
        (CONF_DOUBLE_TARGET, CONF_DOUBLE_ACTION),
        (CONF_TRIPLE_TARGET, CONF_TRIPLE_ACTION),
        (CONF_HOLD_TARGET, CONF_HOLD_TARGET_ACTION),
    ],
)
def test_a_script_or_a_light_may_be_turned_off_by_any_gesture(
    target_field, action_field
) -> None:
    for target in ("script.go", "light.other"):
        stored = _normalize(
            **{
                target_field: target,
                action_field: "off",
                CONF_HOLD_ACTION: HOLD_TOGGLE,
            }
        )

        assert binding_errors(stored) == {}


def test_a_scene_turn_off_is_ignored_where_the_gesture_is_not_used() -> None:
    """Scene cycling replaces the short press; a ramp ignores the hold target."""
    cycling = _normalize(
        **{
            CONF_CLICK_TARGET: "scene.a",
            CONF_CLICK_ACTION: "off",
            CONF_SCENES: ["scene.a", "scene.b"],
        }
    )
    ramping = _normalize(
        **{
            CONF_HOLD_TARGET: "scene.a",
            CONF_HOLD_TARGET_ACTION: "off",
            CONF_HOLD_ACTION: HOLD_RAMP,
        }
    )

    assert binding_errors(cycling) == {}
    assert binding_errors(ramping) == {}


# -- the table of verbs ------------------------------------------------------


def test_every_verb_has_words_in_both_languages_and_in_the_native_form() -> None:
    """A verb without a label is a blank row in a picker."""
    import json
    from pathlib import Path

    from custom_components.ikea_bilresa.gesture_verbs import ALL_VERBS
    from custom_components.ikea_bilresa.panel_strings import STRINGS

    root = Path(__file__).parents[1] / "custom_components/ikea_bilresa"
    native = [
        json.loads((root / name).read_text(encoding="utf-8"))
        for name in ("strings.json", "translations/en.json", "translations/cs.json")
    ]
    own = [verb for verb in ALL_VERBS if verb not in ("toggle", "on", "off")]
    assert own, "no verbs of their own"
    for language, strings in STRINGS.items():
        for verb in own:
            assert f"click_{verb}" in strings, (language, verb)
            assert f"action_{verb}" in strings, (language, verb)
    for catalog in native:
        for selector_name in ("target_action", "click_action"):
            options = catalog["selector"][selector_name]["options"]
            for verb in ALL_VERBS:
                assert verb in options, (selector_name, verb)


def test_the_panel_is_told_the_same_verbs_the_server_validates() -> None:
    from custom_components.ikea_bilresa.const import PRESS_TARGET_DOMAINS
    from custom_components.ikea_bilresa.gesture_verbs import VERBS, schema_verbs

    offered = schema_verbs()
    assert tuple(offered) == tuple(PRESS_TARGET_DOMAINS)
    for domain, verbs in offered.items():
        assert verbs, domain
        for verb in verbs:
            assert action_is_supported(f"{domain}.x", verb), (domain, verb)
            assert target_service(f"{domain}.x", verb) is not None, (domain, verb)
    # What older bindings hold keeps running but is no longer offered.
    assert "toggle" in VERBS["scene"] and "toggle" not in offered["scene"]


@pytest.mark.parametrize(
    ("entity", "action", "supported"),
    [
        ("media_player.a", "play_pause", True),
        ("media_player.a", "open", False),
        ("cover.a", "open", True),
        ("cover.a", "play_pause", False),
        ("lock.a", "lock", True),
        ("lock.a", "toggle", False),
        ("lock.a", "off", False),
        ("siren.a", "off", True),
        ("siren.a", "on", False),
        ("valve.a", "close", True),
        ("valve.a", "on", False),
        # Before the verbs a gesture toggled anything, including the target a
        # wheel's short press shares with its rotation; that still validates.
        ("number.a", "toggle", True),
        ("input_number.a", "toggle", True),
        ("climate.a", "on", True),
        ("number.a", "play_pause", False),
        ("light.a", "none", True),
        ("lock.a", "none", True),
    ],
)
def test_which_verbs_a_kind_of_target_accepts(entity, action, supported) -> None:
    assert action_is_supported(entity, action) is supported


def test_a_stateful_verb_needs_a_boolean_attribute() -> None:
    from custom_components.ikea_bilresa.gesture_actions import gesture_call, needs_state

    assert needs_state("media_player.a", "mute_toggle")
    assert not needs_state("media_player.a", "play_pause")
    assert gesture_call("media_player.a", "mute_toggle", {"is_volume_muted": True}) == (
        "media_player",
        "volume_mute",
        {"is_volume_muted": False},
    )
    for attributes in (None, {}, {"is_volume_muted": None}, {"is_volume_muted": 1}):
        assert gesture_call("media_player.a", "mute_toggle", attributes) is None


@pytest.mark.parametrize(
    ("entity", "action", "error"),
    [
        ("lock.door", "play_pause", "action_not_supported"),
        ("media_player.tv", "open", "action_not_supported"),
        ("scene.evening", "off", "scene_cannot_turn_off"),
    ],
)
def test_a_verb_the_target_lacks_is_refused_when_the_binding_is_saved(
    entity: str, action: str, error: str
) -> None:
    stored = _normalize(**{CONF_DOUBLE_TARGET: entity, CONF_DOUBLE_ACTION: action})

    assert binding_errors(stored) == {CONF_DOUBLE_ACTION: error}


def test_a_verb_of_the_targets_own_kind_is_accepted_and_stored() -> None:
    stored = _normalize(
        **{CONF_DOUBLE_TARGET: "media_player.tv", CONF_DOUBLE_ACTION: "play_pause"}
    )

    assert binding_errors(stored) == {}
    assert editor_data(stored)[CONF_DOUBLE_ACTION] == "play_pause"
