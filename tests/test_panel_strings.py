"""The panel's two languages must not drift apart."""

from __future__ import annotations

from pathlib import Path
import re

from custom_components.ikea_bilresa.panel_strings import (
    DEFAULT_LANGUAGE,
    STRINGS,
    localize,
    panel_strings,
    resolve_language,
)

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def test_every_language_has_every_key() -> None:
    """The whole reason both languages live in one file.

    PANEL_ROADMAP.md requires English and Czech to stay aligned. Two JSON files
    drift silently — someone adds an English key and the Czech side falls back
    without anyone noticing. This makes it a build failure.
    """
    reference = set(STRINGS[DEFAULT_LANGUAGE])
    for language, strings in STRINGS.items():
        missing = reference - set(strings)
        extra = set(strings) - reference
        assert not missing, f"{language} is missing: {sorted(missing)}"
        assert not extra, f"{language} has keys English lacks: {sorted(extra)}"


def test_placeholders_match_across_languages() -> None:
    """A translation that drops {count} renders a sentence with a hole in it."""
    for key, template in STRINGS[DEFAULT_LANGUAGE].items():
        expected = set(_PLACEHOLDER.findall(template))
        for language, strings in STRINGS.items():
            actual = set(_PLACEHOLDER.findall(strings[key]))
            assert actual == expected, (
                f"{language}.{key} has placeholders {actual}, English has {expected}"
            )


def test_no_string_is_empty() -> None:
    for language, strings in STRINGS.items():
        for key, value in strings.items():
            assert value.strip(), f"{language}.{key} is empty"


def test_czech_is_actually_translated() -> None:
    """Guards against a copy-paste that leaves English behind.

    A few keys are legitimately identical across the two ("Matter" is a proper
    noun), so this checks the bulk rather than demanding every single one differ.
    """
    same = [k for k, v in STRINGS["cs"].items() if v == STRINGS["en"][k]]
    assert len(same) < len(STRINGS["en"]) // 4, f"suspiciously untranslated: {same}"


def test_regional_tag_falls_back_to_its_base_language() -> None:
    """`hass.config.language` can be en-GB; that is still English."""
    assert resolve_language("cs") == "cs"
    assert resolve_language("en-GB") == "en"
    assert resolve_language("cs-CZ") == "cs"
    assert resolve_language("de") == DEFAULT_LANGUAGE
    assert resolve_language(None) == DEFAULT_LANGUAGE
    assert resolve_language("") == DEFAULT_LANGUAGE


def test_localize_fills_placeholders() -> None:
    assert localize("cs", "summary_connected", count=2) == "2 připojeno"
    assert localize("en", "summary_connected", count=2) == "2 connected"
    assert localize("cs", "mode_scenes", count=3) == "Scény (3)"


def test_localize_survives_a_missing_placeholder() -> None:
    """A template rendered without its argument must not raise at a user."""
    assert "{" in localize("en", "summary_connected")


def test_unknown_key_returns_the_key_not_a_crash() -> None:
    assert localize("cs", "no_such_key") == "no_such_key"


def test_panel_strings_returns_a_copy() -> None:
    """It travels into panel config; a caller must not be able to mutate STRINGS."""
    strings = panel_strings("cs")
    strings["connected"] = "mutated"
    assert STRINGS["cs"]["connected"] == "Připojeno"


def test_the_frontend_does_not_hard_code_user_facing_english() -> None:
    """Strings live in Python so the two languages cannot drift.

    A second copy in JavaScript is exactly how that happens, and the panel
    shipped English-only to a Czech user once already.
    """
    asset = (
        Path(__file__).parents[1]
        / "custom_components"
        / "ikea_bilresa"
        / "frontend"
        / "ikea_bilresa_panel.js"
    ).read_text(encoding="utf-8")
    # strip comments and the CSS block, which are not user-facing
    body = re.sub(r"/\*.*?\*/", "", asset, flags=re.S)
    body = re.sub(r"//.*", "", body)
    body = re.sub(r"const STYLES = `.*?`;", "", body, flags=re.S)

    for phrase in (
        "Connected",
        "Not configured",
        "Add a control binding",
        "Matter connected",
        "No activity yet",
        "Try again",
        "Open Home Assistant sidebar",
        "Live test",
        "Calculated result not reported",
        "Dispatch outcome not reported",
        "Recommended action",
    ):
        assert f'"{phrase}"' not in body, f"hard-coded in the frontend: {phrase}"
