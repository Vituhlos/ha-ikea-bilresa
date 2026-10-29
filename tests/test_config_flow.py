"""Unit tests for binding profile and copy defaults."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.ikea_bilresa.config_flow import (
    BindingSubentryFlowHandler,
    _run_scripts_and_scenes,
    _with_explicit_actions,
)
from custom_components.ikea_bilresa.const import (
    BINDING_PROFILE_CLIMATE,
    BINDING_PROFILE_COVER,
    BINDING_PROFILE_LIGHT,
    BINDING_PROFILE_MEDIA,
    BINDING_PROFILE_SCENES,
    BUTTON_RESPONSE_FAST,
    BUTTON_RESPONSE_INSTANT,
    BUTTON_RESPONSE_MULTI_PRESS,
    CLICK_NONE,
    CONF_ACCELERATION,
    CONF_BINDING_PROFILE,
    CONF_BUTTON_RESPONSE,
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_CLICK_TARGET,
    CONF_COPY_FROM,
    CONF_DOUBLE_ACTION,
    CONF_DOUBLE_TARGET,
    CONF_ENDPOINT,
    CONF_HOLD_ACTION,
    CONF_HOLD_TARGET,
    CONF_HOLD_TARGET_ACTION,
    CONF_MAX_BRIGHTNESS,
    CONF_MIN_BRIGHTNESS,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_RAMP_DIRECTION,
    CONF_SCENES,
    CONF_STEP,
    CONF_TARGET,
    CONF_TRANSITION,
    CONF_TRIPLE_ACTION,
    CONF_TRIPLE_TARGET,
    HOLD_NONE,
    HOLD_RAMP,
    HOLD_TOGGLE,
    MODE_BRIGHTNESS,
    MODE_COVER,
    MODE_TEMPERATURE,
    MODE_VOLUME,
    RAMP_DIRECTION_DOWN,
    ROLE_BUTTON,
    ROLE_SCROLL_UP,
    SUBENTRY_BINDING,
)
from custom_components.ikea_bilresa.model import (
    BilresaWheel,
    SwitchEndpoint,
    parse_node,
)

DUAL_BUTTON_FIXTURE = (
    Path(__file__).parent / "fixtures" / "bilresa_dual_button_node.json"
)


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        (
            BINDING_PROFILE_LIGHT,
            {CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST, CONF_MODE: MODE_BRIGHTNESS},
        ),
        (
            BINDING_PROFILE_MEDIA,
            {CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST, CONF_MODE: MODE_VOLUME},
        ),
        (
            BINDING_PROFILE_COVER,
            {CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST, CONF_MODE: MODE_COVER},
        ),
        (
            BINDING_PROFILE_CLIMATE,
            {CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST, CONF_MODE: MODE_TEMPERATURE},
        ),
        (
            BINDING_PROFILE_SCENES,
            {
                CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST,
                CONF_MODE: MODE_BRIGHTNESS,
                CONF_CLICK_ACTION: CLICK_NONE,
            },
        ),
    ],
)
def test_profile_defaults(profile: str, expected: dict) -> None:
    assert (
        BindingSubentryFlowHandler._creation_defaults({CONF_BINDING_PROFILE: profile})
        == expected
    )


def test_copy_existing_binding_preserves_source_defaults() -> None:
    flow = object.__new__(BindingSubentryFlowHandler)
    copied = SimpleNamespace(
        subentry_type=SUBENTRY_BINDING,
        data={CONF_MODE: MODE_VOLUME, CONF_STEP: 7},
    )
    flow._get_entry = lambda: SimpleNamespace(subentries={"copy-id": copied})

    assert flow._copy_defaults("copy-id") == {
        CONF_MODE: MODE_VOLUME,
        CONF_STEP: 7,
    }


@pytest.mark.asyncio
async def test_copy_flow_keeps_actions_but_uses_selected_destination_device() -> None:
    flow = object.__new__(BindingSubentryFlowHandler)
    copied = SimpleNamespace(
        subentry_type=SUBENTRY_BINDING,
        data={
            CONF_NODE_ID: "999",
            CONF_ENDPOINT: "1",
            CONF_CLICK_TARGET: "light.copied",
            CONF_CLICK_ACTION: "toggle",
            CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_MULTI_PRESS,
            CONF_HOLD_ACTION: HOLD_NONE,
        },
    )
    flow._get_entry = lambda: SimpleNamespace(subentries={"copy-id": copied})
    flow._device_options = lambda: [{"value": "101", "label": "Dual A"}]
    flow._async_step_form = AsyncMock(return_value={"type": "form"})

    result = await flow.async_step_user(
        {CONF_NODE_ID: "101", CONF_COPY_FROM: "copy-id"}
    )

    assert result == {"type": "form"}
    assert flow._pending_defaults[CONF_NODE_ID] == "101"
    assert flow._pending_defaults[CONF_CLICK_TARGET] == "light.copied"
    flow._async_step_form.assert_awaited_once_with("user", None)


def _device_flow() -> BindingSubentryFlowHandler:
    flow = object.__new__(BindingSubentryFlowHandler)
    dual_a = BilresaWheel(
        node_id=101,
        name="Dual A",
        product_name="BILRESA dual button",
        serial=None,
        endpoints={
            1: SwitchEndpoint(1, None, ROLE_BUTTON, 2),
            2: SwitchEndpoint(2, None, ROLE_BUTTON, 2),
        },
    )
    dual_b = BilresaWheel(
        node_id=202,
        name="Dual B",
        product_name="BILRESA dual button",
        serial=None,
        endpoints={
            1: SwitchEndpoint(1, None, ROLE_BUTTON, 2),
            2: SwitchEndpoint(2, None, ROLE_BUTTON, 2),
        },
    )
    wheel = BilresaWheel(
        node_id=303,
        name="Wheel",
        product_name="BILRESA scroll wheel",
        serial=None,
        endpoints={
            1: SwitchEndpoint(1, 1, ROLE_SCROLL_UP, 18),
            3: SwitchEndpoint(3, 1, ROLE_BUTTON, 3),
        },
    )
    entry = SimpleNamespace(
        runtime_data=SimpleNamespace(wheels={101: dual_a, 202: dual_b, 303: wheel}),
        subentries={},
    )
    flow._get_entry = lambda: entry
    return flow


def _schema_keys(schema) -> set[str]:
    return {str(marker.schema) for marker in schema.schema}


def test_dual_button_schema_uses_real_endpoint_shape_and_hides_rotary_fields() -> None:
    flow = _device_flow()

    keys = _schema_keys(flow._schema({CONF_NODE_ID: "101"}))

    assert {
        CONF_ENDPOINT,
        CONF_CLICK_ACTION,
        CONF_BUTTON_RESPONSE,
        CONF_CLICK_TARGET,
        CONF_DOUBLE_TARGET,
        CONF_HOLD_ACTION,
        CONF_HOLD_TARGET,
        CONF_RAMP_DIRECTION,
    } <= keys
    assert {
        CONF_CHANNEL,
        CONF_TARGET,
        CONF_MODE,
        CONF_STEP,
        CONF_ACCELERATION,
        CONF_MIN_BRIGHTNESS,
        CONF_MAX_BRIGHTNESS,
        CONF_TRANSITION,
        CONF_TRIPLE_TARGET,
        CONF_SCENES,
    }.isdisjoint(keys)
    assert flow._button_options("101") == [
        {"value": "1", "label": "1"},
        {"value": "2", "label": "2"},
    ]
    # A second physical dual button may reuse endpoint ids without sharing a
    # node/address; both still expose their own two independent controls.
    assert flow._button_options("202") == flow._button_options("101")


def test_live_e2489_shape_offers_endpoint_binding_schema() -> None:
    """Regression: the exact live TagList must unlock button bindings."""
    device = parse_node(json.loads(DUAL_BUTTON_FIXTURE.read_text(encoding="utf-8")))
    assert device is not None
    flow = object.__new__(BindingSubentryFlowHandler)
    flow._get_entry = lambda: SimpleNamespace(
        runtime_data=SimpleNamespace(wheels={9001: device}),
        subentries={},
    )

    keys = _schema_keys(flow._schema({CONF_NODE_ID: "9001"}))

    assert CONF_ENDPOINT in keys
    assert {
        CONF_CHANNEL,
        CONF_MODE,
        CONF_SCENES,
        CONF_TRIPLE_TARGET,
    }.isdisjoint(keys)


def test_wheel_schema_keeps_rotary_and_triple_press_options() -> None:
    flow = _device_flow()

    keys = _schema_keys(flow._schema({CONF_NODE_ID: "303"}))

    assert {
        CONF_CHANNEL,
        CONF_TARGET,
        CONF_MODE,
        CONF_STEP,
        CONF_ACCELERATION,
        CONF_MIN_BRIGHTNESS,
        CONF_MAX_BRIGHTNESS,
        CONF_TRANSITION,
        CONF_TRIPLE_TARGET,
        CONF_SCENES,
    } <= keys
    assert CONF_ENDPOINT not in keys
    assert CONF_RAMP_DIRECTION not in keys


def test_reconfigure_device_choices_stay_within_the_current_variant() -> None:
    flow = _device_flow()
    flow._device_options = lambda: [
        {"value": "101", "label": "Dual A"},
        {"value": "202", "label": "Dual B"},
        {"value": "303", "label": "Wheel"},
    ]

    assert [item["value"] for item in flow._same_variant_device_options("101")] == [
        "101",
        "202",
    ]
    assert [item["value"] for item in flow._same_variant_device_options("303")] == [
        "303"
    ]


def test_copying_wheel_defaults_to_button_drops_unsupported_rotary_options() -> None:
    normalized, errors = BindingSubentryFlowHandler._normalize_and_validate(
        {
            CONF_NODE_ID: "101",
            CONF_ENDPOINT: "2",
            CONF_CLICK_ACTION: CLICK_NONE,
            CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_MULTI_PRESS,
            CONF_HOLD_ACTION: HOLD_NONE,
            CONF_RAMP_DIRECTION: RAMP_DIRECTION_DOWN,
            CONF_MODE: MODE_VOLUME,
            CONF_TARGET: "media_player.test",
            CONF_TRIPLE_TARGET: "switch.never_exposed",
            CONF_STEP: 7,
        }
    )

    assert errors == {}
    assert normalized is not None
    assert normalized[CONF_ENDPOINT] == "2"
    assert CONF_CHANNEL not in normalized
    assert CONF_MODE not in normalized
    assert CONF_TARGET not in normalized
    assert CONF_TRIPLE_TARGET not in normalized
    assert CONF_STEP not in normalized


def test_button_ramp_requires_a_light_and_keeps_fixed_direction() -> None:
    normalized, errors = BindingSubentryFlowHandler._normalize_and_validate(
        {
            CONF_NODE_ID: "101",
            CONF_ENDPOINT: "1",
            CONF_CLICK_ACTION: CLICK_NONE,
            CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_MULTI_PRESS,
            CONF_HOLD_ACTION: HOLD_RAMP,
            CONF_HOLD_TARGET: "switch.not_a_light",
            CONF_RAMP_DIRECTION: RAMP_DIRECTION_DOWN,
        }
    )
    assert normalized is None
    assert errors == {CONF_HOLD_TARGET: "ramp_requires_light"}

    normalized, errors = BindingSubentryFlowHandler._normalize_and_validate(
        {
            CONF_NODE_ID: "101",
            CONF_ENDPOINT: "1",
            CONF_CLICK_ACTION: CLICK_NONE,
            CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_MULTI_PRESS,
            CONF_HOLD_ACTION: HOLD_RAMP,
            CONF_HOLD_TARGET: "light.shared",
            CONF_RAMP_DIRECTION: RAMP_DIRECTION_DOWN,
        }
    )
    assert errors == {}
    assert normalized is not None
    assert normalized[CONF_RAMP_DIRECTION] == RAMP_DIRECTION_DOWN


def test_binding_title_uses_compact_channel_suffix() -> None:
    flow = object.__new__(BindingSubentryFlowHandler)
    flow._device_options = lambda: [
        {"value": "101", "label": "Kitchen wheel (node 101)"}
    ]

    assert flow._title({CONF_NODE_ID: "101", CONF_CHANNEL: "2"}) == (
        "Kitchen wheel · CH 2"
    )


def test_button_binding_title_uses_physical_button_index() -> None:
    flow = object.__new__(BindingSubentryFlowHandler)
    flow._device_options = lambda: [
        {"value": "101", "label": "Hall buttons (node 101)"}
    ]
    flow._button_options = lambda _node: [
        {"value": "7", "label": "1"},
        {"value": "9", "label": "2"},
    ]

    assert flow._title({CONF_NODE_ID: "101", CONF_ENDPOINT: "9"}) == (
        "Hall buttons · BTN 2"
    )


def test_fast_response_rejects_configured_multi_press_target() -> None:
    assert BindingSubentryFlowHandler._validate_binding(
        {
            CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST,
            CONF_DOUBLE_TARGET: "switch.test",
            CONF_MODE: MODE_BRIGHTNESS,
            CONF_TARGET: "light.test",
        }
    ) == {CONF_BUTTON_RESPONSE: "fast_response_conflicts_with_multi_press"}


def test_multi_press_response_accepts_configured_multi_press_target() -> None:
    assert (
        BindingSubentryFlowHandler._validate_binding(
            {
                CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_MULTI_PRESS,
                CONF_DOUBLE_TARGET: "switch.test",
                CONF_MODE: MODE_BRIGHTNESS,
                CONF_TARGET: "light.test",
            }
        )
        == {}
    )


def test_instant_response_rejects_multi_press_target() -> None:
    assert BindingSubentryFlowHandler._validate_binding(
        {
            CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_INSTANT,
            CONF_DOUBLE_TARGET: "switch.test",
            CONF_HOLD_ACTION: HOLD_NONE,
            CONF_MODE: MODE_BRIGHTNESS,
            CONF_TARGET: "light.test",
        }
    ) == {CONF_BUTTON_RESPONSE: "instant_response_conflicts_with_multi_press"}


def test_instant_response_rejects_separate_hold_action() -> None:
    assert BindingSubentryFlowHandler._validate_binding(
        {
            CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_INSTANT,
            CONF_HOLD_ACTION: HOLD_RAMP,
            CONF_HOLD_TARGET: "light.test",
            CONF_MODE: MODE_BRIGHTNESS,
            CONF_TARGET: "light.test",
        }
    ) == {CONF_BUTTON_RESPONSE: "instant_response_conflicts_with_hold"}


def test_instant_response_accepts_unambiguous_single_action() -> None:
    assert (
        BindingSubentryFlowHandler._validate_binding(
            {
                CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_INSTANT,
                CONF_HOLD_ACTION: HOLD_NONE,
                CONF_MODE: MODE_BRIGHTNESS,
                CONF_TARGET: "light.test",
            }
        )
        == {}
    )


@pytest.mark.parametrize(
    ("mode", "target"),
    [
        (MODE_BRIGHTNESS, "light.test"),
        (MODE_VOLUME, "media_player.test"),
        (MODE_COVER, "cover.test"),
        (MODE_TEMPERATURE, "climate.test"),
        ("fan_speed", "fan.test"),
        ("number", "number.test"),
        ("number", "input_number.test"),
    ],
)
def test_mode_accepts_compatible_target(mode: str, target: str) -> None:
    assert (
        BindingSubentryFlowHandler._validate_binding(
            {
                CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_MULTI_PRESS,
                CONF_MODE: mode,
                CONF_TARGET: target,
            }
        )
        == {}
    )


def test_mode_rejects_incompatible_target() -> None:
    assert BindingSubentryFlowHandler._validate_binding(
        {
            CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_MULTI_PRESS,
            CONF_MODE: MODE_VOLUME,
            CONF_TARGET: "light.test",
        }
    ) == {CONF_TARGET: "mode_target_mismatch"}


def test_a_scene_cannot_be_turned_off() -> None:
    """A scene is only ever run; "off" would need a service that does not exist."""
    assert BindingSubentryFlowHandler._validate_binding(
        {
            CONF_CLICK_ACTION: "off",
            CONF_CLICK_TARGET: "scene.evening",
            CONF_MODE: MODE_BRIGHTNESS,
            CONF_TARGET: "light.test",
        }
    ) == {CONF_CLICK_ACTION: "scene_cannot_turn_off"}


@pytest.mark.parametrize(
    ("click", "target"),
    [
        ("toggle", "scene.evening"),
        ("on", "scene.evening"),
        ("none", "scene.evening"),
        ("toggle", "script.go"),
        ("on", "script.go"),
        ("off", "script.go"),
    ],
)
def test_what_a_scene_or_script_can_do_is_accepted(click: str, target: str) -> None:
    assert (
        BindingSubentryFlowHandler._validate_binding(
            {
                CONF_CLICK_ACTION: click,
                CONF_CLICK_TARGET: target,
                CONF_MODE: MODE_BRIGHTNESS,
                CONF_TARGET: "light.test",
            }
        )
        == {}
    )


def test_a_light_may_still_be_turned_off() -> None:
    assert (
        BindingSubentryFlowHandler._validate_binding(
            {
                CONF_CLICK_ACTION: "off",
                CONF_CLICK_TARGET: "light.test",
                CONF_MODE: MODE_BRIGHTNESS,
                CONF_TARGET: "light.test",
            }
        )
        == {}
    )


def test_the_native_form_offers_an_action_per_gesture() -> None:
    wheel = {
        str(key)
        for key in BindingSubentryFlowHandler._button_action_fields({}, wheel=True)
    }
    button = {
        str(key)
        for key in BindingSubentryFlowHandler._button_action_fields({}, wheel=False)
    }

    assert {CONF_DOUBLE_ACTION, CONF_TRIPLE_ACTION, CONF_HOLD_TARGET_ACTION} <= wheel
    # A dual button has no triple press.
    assert {CONF_DOUBLE_ACTION, CONF_HOLD_TARGET_ACTION} <= button
    assert CONF_TRIPLE_ACTION not in button


def test_the_form_shows_the_stored_actions_and_leaves_the_rest_empty() -> None:
    fields = BindingSubentryFlowHandler._button_action_fields(
        {CONF_DOUBLE_ACTION: "on", CONF_TRIPLE_ACTION: "off"}, wheel=True
    )
    suggested = {
        str(key): (key.description or {}).get("suggested_value")
        for key in fields
        if getattr(key, "description", None) is not None
    }

    assert suggested[CONF_DOUBLE_ACTION] == "on"
    assert suggested[CONF_CLICK_ACTION] is None
    assert suggested[CONF_TRIPLE_ACTION] == "off"
    # Nothing stored: empty, so the person is not made to choose, and the stored
    # default (toggle) applies unless the target is a script or a scene.
    assert suggested[CONF_HOLD_TARGET_ACTION] is None


@pytest.mark.parametrize("target", ["script.go", "scene.evening"])
def test_a_new_script_or_scene_is_run_unless_an_action_was_chosen(target) -> None:
    filled = _run_scripts_and_scenes(
        {
            CONF_DOUBLE_TARGET: target,
            CONF_TRIPLE_TARGET: target,
            CONF_HOLD_ACTION: HOLD_TOGGLE,
            CONF_HOLD_TARGET: target,
        }
    )

    assert filled[CONF_DOUBLE_ACTION] == "on"
    assert filled[CONF_TRIPLE_ACTION] == "on"
    assert filled[CONF_HOLD_TARGET_ACTION] == "on"


def test_a_chosen_action_and_other_targets_are_left_alone() -> None:
    filled = _run_scripts_and_scenes(
        {
            CONF_DOUBLE_TARGET: "script.go",
            CONF_DOUBLE_ACTION: "toggle",
            CONF_TRIPLE_TARGET: "light.hall",
            CONF_HOLD_ACTION: HOLD_TOGGLE,
        }
    )

    assert filled[CONF_DOUBLE_ACTION] == "toggle"
    assert CONF_TRIPLE_ACTION not in filled
    assert CONF_HOLD_TARGET_ACTION not in filled


def test_a_hold_that_ramps_is_given_no_action() -> None:
    filled = _run_scripts_and_scenes(
        {CONF_HOLD_ACTION: HOLD_RAMP, CONF_HOLD_TARGET: "script.go"}
    )

    assert CONF_HOLD_TARGET_ACTION not in filled


@pytest.mark.parametrize("target", ["script.go", "scene.evening"])
def test_a_new_short_press_on_a_script_or_scene_is_run_unless_chosen(target) -> None:
    assert _run_scripts_and_scenes({CONF_CLICK_TARGET: target})[CONF_CLICK_ACTION] == (
        "on"
    )
    # An explicit choice, including "no action", is the person's.
    for chosen in ("toggle", "off", "none"):
        kept = _run_scripts_and_scenes(
            {CONF_CLICK_TARGET: target, CONF_CLICK_ACTION: chosen}
        )
        assert kept[CONF_CLICK_ACTION] == chosen


def test_a_short_press_with_no_script_target_gets_no_action_filled_in() -> None:
    assert CONF_CLICK_ACTION not in _run_scripts_and_scenes({})
    assert CONF_CLICK_ACTION not in _run_scripts_and_scenes(
        {CONF_CLICK_TARGET: "light.hall"}
    )


def test_a_copy_does_what_its_source_does_for_a_gesture_with_no_action() -> None:
    """A missing action toggled; an empty select on a new binding would run."""
    source = {
        CONF_CLICK_TARGET: "script.go",
        CONF_DOUBLE_TARGET: "script.go",
        CONF_TRIPLE_TARGET: "scene.evening",
        CONF_TRIPLE_ACTION: "on",
        CONF_HOLD_TARGET: "script.go",
    }

    copied = _with_explicit_actions(source)

    assert copied[CONF_CLICK_ACTION] == "toggle"
    assert copied[CONF_DOUBLE_ACTION] == "toggle"
    assert copied[CONF_TRIPLE_ACTION] == "on"
    assert copied[CONF_HOLD_TARGET_ACTION] == "toggle"
    # The copy then goes through the new-binding fill and keeps toggling.
    assert _run_scripts_and_scenes(copied)[CONF_DOUBLE_ACTION] == "toggle"


def test_a_copy_gains_no_action_for_a_gesture_without_a_target() -> None:
    copied = _with_explicit_actions({CONF_DOUBLE_TARGET: "light.hall"})

    assert copied == {CONF_DOUBLE_TARGET: "light.hall", CONF_DOUBLE_ACTION: "toggle"}


def _form_flow() -> BindingSubentryFlowHandler:
    """A flow that can be submitted without a Home Assistant around it."""
    flow = object.__new__(BindingSubentryFlowHandler)
    flow._pending_node_id = "101"
    flow._pending_defaults = {CONF_NODE_ID: "101"}
    flow._title = lambda _data: "title"
    flow._get_entry = lambda: "entry"
    flow._get_reconfigure_subentry = lambda: "subentry"
    flow.async_create_entry = lambda *, title, data: {
        "type": "create_entry",
        "data": data,
    }
    flow.async_update_and_abort = lambda _entry, _subentry, *, title, data: {
        "type": "abort",
        "data": data,
    }
    return flow


_WHEEL_FORM = {
    CONF_CHANNEL: "1",
    CONF_MODE: MODE_BRIGHTNESS,
    CONF_TARGET: "light.main",
    CONF_CLICK_TARGET: "script.go",
    CONF_DOUBLE_TARGET: "scene.evening",
    CONF_TRIPLE_TARGET: "script.go",
    CONF_HOLD_ACTION: HOLD_TOGGLE,
    CONF_HOLD_TARGET: "script.go",
}


async def test_submitting_a_new_binding_runs_its_scripts_and_scenes() -> None:
    """Through the real submit path: no action chosen, so a script is run."""
    result = await _form_flow()._async_step_form("user", dict(_WHEEL_FORM))

    assert result["type"] == "create_entry"
    stored = result["data"]
    assert stored[CONF_CLICK_ACTION] == "on"
    assert stored[CONF_DOUBLE_ACTION] == "on"
    assert stored[CONF_TRIPLE_ACTION] == "on"
    assert stored[CONF_HOLD_TARGET_ACTION] == "on"


async def test_submitting_a_new_binding_keeps_a_chosen_action_and_other_targets() -> (
    None
):
    form = {
        **_WHEEL_FORM,
        CONF_CLICK_ACTION: "toggle",
        CONF_TRIPLE_TARGET: "light.hall",
    }

    stored = (await _form_flow()._async_step_form("user", form))["data"]

    assert stored[CONF_CLICK_ACTION] == "toggle"
    # A light with no action chosen toggles, as it always did.
    assert stored[CONF_TRIPLE_ACTION] == "toggle"


async def test_saving_an_edited_binding_does_not_start_running_its_script() -> None:
    """A binding that toggled a script keeps toggling it when its form is saved."""
    result = await _form_flow()._async_step_form("reconfigure", dict(_WHEEL_FORM))

    assert result["type"] == "abort"  # the update is applied, then the flow ends
    stored = result["data"]
    assert stored[CONF_CLICK_ACTION] == "toggle"
    assert stored[CONF_DOUBLE_ACTION] == "toggle"
    assert stored[CONF_TRIPLE_ACTION] == "toggle"
    assert stored[CONF_HOLD_TARGET_ACTION] == "toggle"


async def test_a_copied_binding_keeps_toggling_when_it_is_saved() -> None:
    flow = _form_flow()
    flow._pending_defaults = _with_explicit_actions(
        {CONF_NODE_ID: "101", **_WHEEL_FORM}
    )
    # The copy's form shows its defaults and the person saves it untouched.
    untouched = {
        field: value
        for field, value in flow._pending_defaults.items()
        if field != CONF_NODE_ID
    }

    stored = (await flow._async_step_form("user", untouched))["data"]

    assert stored[CONF_CLICK_ACTION] == "toggle"
    assert stored[CONF_DOUBLE_ACTION] == "toggle"
    assert stored[CONF_TRIPLE_ACTION] == "toggle"
    assert stored[CONF_HOLD_TARGET_ACTION] == "toggle"
