"""Presentation helpers for Home Assistant-generated entry titles."""

from __future__ import annotations

import re

_GENERATED_BINDING_SUFFIX = re.compile(
    r"(?P<label>.+?)\s+·\s+(?:channel|kanál)\s+[123]$",
    re.IGNORECASE,
)


def generated_binding_title(label: str, channel: str) -> str:
    """Return a compact, language-neutral title for a binding subentry."""
    return f"{label} · CH {channel}"


def generated_button_binding_title(label: str, button: str) -> str:
    """Return a compact, language-neutral title for a button binding."""
    return f"{label} · BTN {button}"


def migrate_generated_binding_title(title: str) -> str:
    """Normalize only titles created by earlier integration versions."""
    match = _GENERATED_BINDING_SUFFIX.fullmatch(title)
    if match is None:
        return title
    channel = title.rsplit(" ", 1)[-1]
    return generated_binding_title(match.group("label"), channel)
