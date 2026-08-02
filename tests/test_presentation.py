"""Tests for user-facing generated titles."""

from custom_components.ikea_bilresa.presentation import (
    generated_binding_title,
    generated_button_binding_title,
    migrate_generated_binding_title,
)


def test_generated_binding_title_is_compact_and_language_neutral() -> None:
    assert generated_binding_title("Kitchen wheel", "2") == "Kitchen wheel · CH 2"
    assert generated_button_binding_title("Hall buttons", "1") == "Hall buttons · BTN 1"


def test_migration_normalizes_only_generated_titles() -> None:
    assert (
        migrate_generated_binding_title("Kitchen wheel · channel 3")
        == "Kitchen wheel · CH 3"
    )
    assert (
        migrate_generated_binding_title("Kolečko v kuchyni · Kanál 1")
        == "Kolečko v kuchyni · CH 1"
    )
    assert migrate_generated_binding_title("My evening scenes") == "My evening scenes"
