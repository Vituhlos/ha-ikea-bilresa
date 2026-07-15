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
    CLICK_NONE,
    CONF_BINDING_PROFILE,
    CONF_CLICK_ACTION,
    CONF_COPY_FROM,
    CONF_MODE,
    CONF_STEP,
    MODE_BRIGHTNESS,
    MODE_COVER,
    MODE_TEMPERATURE,
    MODE_VOLUME,
    SUBENTRY_BINDING,
)


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        (BINDING_PROFILE_LIGHT, {CONF_MODE: MODE_BRIGHTNESS}),
        (BINDING_PROFILE_MEDIA, {CONF_MODE: MODE_VOLUME}),
        (BINDING_PROFILE_COVER, {CONF_MODE: MODE_COVER}),
        (BINDING_PROFILE_CLIMATE, {CONF_MODE: MODE_TEMPERATURE}),
        (
            BINDING_PROFILE_SCENES,
            {CONF_MODE: MODE_BRIGHTNESS, CONF_CLICK_ACTION: CLICK_NONE},
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
