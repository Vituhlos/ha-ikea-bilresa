"""The field schema is one table: validation and the panel must agree."""

from __future__ import annotations

import pytest
import voluptuous as vol

from custom_components.ikea_bilresa.const import (
    CONF_ACCELERATION,
    CONF_MAX_BRIGHTNESS,
    CONF_MIN_BRIGHTNESS,
    CONF_STEP,
    CONF_TRANSITION,
    MODES,
)
from custom_components.ikea_bilresa.panel_schema import (
    BINDING_NUMBERS,
    SETTINGS_NUMBERS,
    panel_schema,
)


def test_every_numeric_binding_field_is_described() -> None:
    assert set(BINDING_NUMBERS) == {
        CONF_STEP,
        CONF_ACCELERATION,
        CONF_MIN_BRIGHTNESS,
        CONF_MAX_BRIGHTNESS,
        CONF_TRANSITION,
    }


@pytest.mark.parametrize(
    "field", [*BINDING_NUMBERS.values(), *SETTINGS_NUMBERS.values()]
)
def test_the_validator_accepts_exactly_the_described_range(field) -> None:
    """What the panel offers on a slider is what the server accepts."""
    validate = vol.Schema(field.validator())

    assert validate(field.min) == field.min
    assert validate(field.max) == field.max
    with pytest.raises(vol.Invalid):
        validate(field.min - field.step)
    with pytest.raises(vol.Invalid):
        validate(field.max + field.step)


def test_the_panel_schema_is_plain_json_and_covers_every_mode() -> None:
    schema = panel_schema()

    assert set(schema["mode_domains"]) == set(MODES)
    assert schema["binding_numbers"][CONF_STEP] == {
        "min": 1,
        "max": 25,
        "step": 1,
        "unit": "%",
    }
    # The dial's step is in the dial's own units, so it carries no unit.
    assert schema["settings_numbers"]["step"]["unit"] is None
    assert schema["press_target_domains"] == ["light", "switch"]
    assert schema["ramp_target_domains"] == ["light"]


def test_the_frontend_fallback_matches_the_server_schema() -> None:
    """The fallback serves an older backend; it must not drift from this one."""
    from pathlib import Path
    import re

    asset = (
        Path(__file__).parents[1]
        / "custom_components/ikea_bilresa/frontend/ikea_bilresa_panel.js"
    ).read_text(encoding="utf-8")
    block = asset[asset.index("const FALLBACK_SCHEMA = {") :]
    block = block[: block.index("\n};") + 3]

    for group, fields in (
        ("binding_numbers", BINDING_NUMBERS),
        ("settings_numbers", SETTINGS_NUMBERS),
    ):
        section = block[block.index(f"{group}: {{") :]
        for name, field in fields.items():
            match = re.search(
                rf"{name}: {{ min: ([\d.]+), max: ([\d.]+), step: ([\d.]+), "
                rf"unit: (\"[^\"]*\"|null) }}",
                section,
            )
            assert match, (group, name)
            assert float(match[1]) == field.min
            assert float(match[2]) == field.max
            assert float(match[3]) == field.step
            assert match[4] == ("null" if field.unit is None else f'"{field.unit}"')
