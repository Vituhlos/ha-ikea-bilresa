"""Unit tests for binding profile and copy defaults."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.ikea_bilresa.config_flow import BindingSubentryFlowHandler
from custom_components.ikea_bilresa.const import (
    BINDING_PROFILE_CLIMATE,
    BINDING_PROFILE_COVER,
    BINDING_PROFILE_LIGHT,
    BINDING_PROFILE_MEDIA,
    BINDING_PROFILE_SCENES,
    BUTTON_RESPONSE_FAST,
    BUTTON_RESPONSE_MULTI_PRESS,
    CLICK_NONE,
    CONF_BINDING_PROFILE,
    CONF_BUTTON_RESPONSE,
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_COPY_FROM,
    CONF_DOUBLE_TARGET,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_STEP,
    CONF_TARGET,
    MODE_BRIGHTNESS,
    MODE_COVER,
    MODE_TEMPERATURE,
    MODE_VOLUME,
    SUBENTRY_BINDING,
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
    flow = object.__new__(BindingSubentryFlowHandler)
    flow._get_entry = lambda: SimpleNamespace(subentries={})

    assert flow._creation_defaults({CONF_BINDING_PROFILE: profile}) == expected


def test_copy_existing_binding_takes_precedence() -> None:
    flow = object.__new__(BindingSubentryFlowHandler)
    copied = SimpleNamespace(
        subentry_type=SUBENTRY_BINDING,
        data={CONF_MODE: MODE_VOLUME, CONF_STEP: 7},
    )
    flow._get_entry = lambda: SimpleNamespace(subentries={"copy-id": copied})

    assert flow._creation_defaults(
        {
            CONF_BINDING_PROFILE: BINDING_PROFILE_LIGHT,
            CONF_COPY_FROM: "copy-id",
        }
    ) == {CONF_MODE: MODE_VOLUME, CONF_STEP: 7}


def test_binding_title_uses_compact_channel_suffix() -> None:
    flow = object.__new__(BindingSubentryFlowHandler)
    flow._wheel_options = lambda: [
        {"value": "101", "label": "Kitchen wheel (node 101)"}
    ]

    assert flow._title({CONF_NODE_ID: "101", CONF_CHANNEL: "2"}) == (
        "Kitchen wheel · CH 2"
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
