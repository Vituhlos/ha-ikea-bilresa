"""User-facing strings for the panel, in every language it speaks.

**Why these are not in `strings.json`.** Home Assistant's translation files have
fixed categories — `config`, `selector`, `system_health`, `issues`,
`device_automation` — and none of them describes a custom panel. HA has no
translation category for one. Inventing a category risks hassfest, and the
frontend would not fetch it anyway.

`PANEL_ROADMAP.md` requires English and Czech to stay aligned. Two JSON files in
two directories is precisely how they drift: someone adds an English key and the
Czech one silently falls back or vanishes. Here the two languages sit on adjacent
lines, and `test_panel_strings.py` fails the build if one gains a key the other
lacks. Alignment by construction rather than by discipline.

The language is `hass.config.language` — the instance's, not the individual
user's. Home Assistant has no per-user language available to a WebSocket handler
or to panel registration, so a household where one person reads English and
another Czech gets one of them. Recorded as a known limitation rather than
pretended away; revisit if HA exposes a per-connection locale.
"""

from __future__ import annotations

from typing import Any

DEFAULT_LANGUAGE = "en"

# Both languages adjacent, deliberately. Add a key to one, add it to the other.
STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # status
        "connected": "Connected",
        "unavailable": "Unavailable",
        "unknown": "Not reporting",
        # channels
        "not_configured": "Not configured",
        "add_binding": "Add a control binding",
        "target_unavailable": "{target} — unavailable",
        "configured": "Configured",
        # scroll modes — what a rotation does
        "mode_brightness": "Smooth dimming",
        "mode_color_temp": "Colour temperature",
        "mode_color": "Colour",
        "mode_volume": "Volume",
        "mode_cover_position": "Cover position",
        "mode_temperature": "Temperature",
        "mode_fan_speed": "Fan speed",
        "mode_number": "Value",
        "mode_scenes": "Scenes ({count})",
        # wheel card
        "no_activity": "No activity yet",
        "last_on_channel": "last on channel {channel}",
        # summary
        "summary_connected": "{count} connected",
        "summary_unavailable": "{count} unavailable",
        "summary_unknown": "{count} not reporting",
        "matter_connected": "Matter connected",
        "matter_offline": "Matter offline",
        # banners
        "banner_matter_offline": (
            "Matter is disconnected. The wheels below show their last known state."
        ),
        "banner_updates_stopped": "Live updates stopped. This view may be out of date.",
        "banner_target_missing": (
            "A control binding points at something Home Assistant can no longer "
            "find ({count})."
        ),
        # states
        "empty_title": "No BILRESA wheels found",
        "empty_connected": (
            "The integration is connected but has not discovered a wheel yet."
        ),
        "empty_offline": (
            "Home Assistant is not connected to Matter, so no wheel can be seen."
        ),
        "error_title": "Cannot reach the integration",
        "retry": "Try again",
        # detail
        "back": "Back to all wheels",
        "detail_soon": (
            "Channels, live test and diagnostics arrive in the next package."
        ),
        # a11y
        "menu": "Open Home Assistant sidebar",
    },
    "cs": {
        "connected": "Připojeno",
        "unavailable": "Nedostupné",
        "unknown": "Nehlásí se",
        "not_configured": "Nenastaveno",
        "add_binding": "Přidat propojení",
        "target_unavailable": "{target} — nedostupné",
        "configured": "Nastaveno",
        "mode_brightness": "Plynulé stmívání",
        "mode_color_temp": "Teplota bílé",
        "mode_color": "Barva",
        "mode_volume": "Hlasitost",
        "mode_cover_position": "Poloha žaluzie",
        "mode_temperature": "Teplota",
        "mode_fan_speed": "Rychlost ventilátoru",
        "mode_number": "Hodnota",
        "mode_scenes": "Scény ({count})",
        "no_activity": "Zatím žádná aktivita",
        "last_on_channel": "naposledy na kanálu {channel}",
        "summary_connected": "{count} připojeno",
        "summary_unavailable": "{count} nedostupné",
        "summary_unknown": "{count} se nehlásí",
        "matter_connected": "Matter připojen",
        "matter_offline": "Matter odpojen",
        "banner_matter_offline": (
            "Matter je odpojený. Kolečka níže ukazují svůj poslední známý stav."
        ),
        "banner_updates_stopped": (
            "Živé aktualizace se zastavily. Tento pohled může být zastaralý."
        ),
        "banner_target_missing": (
            "Propojení míří na něco, co už Home Assistant nenajde ({count})."
        ),
        "empty_title": "Nenalezeno žádné kolečko BILRESA",
        "empty_connected": "Integrace je připojená, ale zatím nenašla žádné kolečko.",
        "empty_offline": (
            "Home Assistant není připojený k Matteru, takže nevidí žádné kolečko."
        ),
        "error_title": "Integrace není dostupná",
        "retry": "Zkusit znovu",
        "back": "Zpět na všechna kolečka",
        "detail_soon": ("Kanály, živý test a diagnostika přijdou v dalším balíčku."),
        "menu": "Otevřít postranní panel Home Assistant",
    },
}


def resolve_language(language: str | None) -> str:
    """Pick the closest language we speak.

    `hass.config.language` can be a regional tag such as `en-GB`; match on the
    base tag before giving up, so a British install does not silently fall back
    when English exists.
    """
    if not language:
        return DEFAULT_LANGUAGE
    if language in STRINGS:
        return language
    base = language.split("-", 1)[0].lower()
    return base if base in STRINGS else DEFAULT_LANGUAGE


def panel_strings(language: str | None) -> dict[str, str]:
    """Every string the frontend renders, in the instance's language."""
    return dict(STRINGS[resolve_language(language)])


def localize(language: str | None, key: str, **placeholders: Any) -> str:
    """One string, with its placeholders filled.

    Falls back to English for a key missing from another language rather than
    rendering the raw key at a user. The alignment test should make that
    unreachable, but a user seeing `mode_brightness` is worse than a user seeing
    English.
    """
    resolved = resolve_language(language)
    template = STRINGS[resolved].get(key) or STRINGS[DEFAULT_LANGUAGE].get(key, key)
    try:
        return template.format(**placeholders)
    except (KeyError, IndexError):
        return template
