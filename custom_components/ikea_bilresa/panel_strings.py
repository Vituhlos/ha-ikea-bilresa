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
        "edit_binding": "Edit binding",
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
        "wheel_switcher": "Wheels",
        "detail_views": "Wheel detail views",
        "tab_channels": "Channels",
        "tab_live": "Live test",
        "tab_diagnostics": "Diagnostics",
        "detail_area_none": "No area",
        "detail_last_activity": "Last activity",
        "detail_last_channel": "Last active channel",
        "detail_no_last_channel": "No channel observed yet",
        "detail_channels_heading": "Channel behaviour",
        "detail_channels_intro": (
            "Review and assign what rotation, presses and holds control."
        ),
        "channel_title": "Channel {channel}",
        "channel_binding": "Binding",
        "target_none": "No target configured",
        # binding editor
        "binding_editor_title": "Edit channel {channel} binding",
        "field_mode": "Rotation mode",
        "field_target": "Rotation target",
        "field_step": "Step per notch",
        "field_acceleration": "Acceleration",
        "field_transition": "Transition",
        "field_min_brightness": "Minimum brightness",
        "field_max_brightness": "Maximum brightness",
        "field_click_action": "Short press",
        "field_click_target": "Short-press target",
        "field_button_response": "Button response",
        "field_double_target": "Double-press target",
        "field_triple_target": "Triple-press target",
        "field_hold_action": "Hold",
        "field_hold_target": "Hold target",
        "field_scenes": "Scenes",
        "field_scenes_help": (
            "Select multiple scenes to cycle through them on each short press."
        ),
        "field_unit": "Range unit: {unit}",
        "advanced_options": "Advanced options",
        "click_toggle": "Toggle target",
        "click_on": "Turn target on",
        "click_off": "Turn target off",
        "click_none": "No action",
        "hold_toggle": "Toggle hold target",
        "hold_ramp": "Ramp rotation target",
        "hold_none": "No action",
        "button_response_multi_press": "Wait for single/double/triple press",
        "button_response_fast": "Run single press immediately",
        "save_binding": "Save binding",
        "cancel_edit": "Cancel editing",
        "delete_binding": "Delete binding",
        "keep_binding": "Keep binding",
        "delete_binding_confirm": (
            "Delete this channel binding? The wheel will stop controlling its targets."
        ),
        "binding_saved": "Binding saved and activated.",
        "binding_validation_failed": "Fix the marked fields and save again.",
        "binding_conflict": (
            "This binding changed elsewhere. The latest saved values are shown; "
            "review them before saving."
        ),
        "binding_save_failed": "Could not save the binding: {error}",
        "binding_delete_failed": "Could not delete the binding: {error}",
        "binding_test_failed": "Could not run the test: {error}",
        "binding_error_unloaded": "The integration is not loaded.",
        "binding_error_wheel_missing": "The wheel is no longer available.",
        "binding_error_binding_missing": "The binding no longer exists.",
        "binding_error_channel_occupied": (
            "This wheel channel already has another binding."
        ),
        "binding_error_binding_not_configured": (
            "Configure this channel before testing it."
        ),
        "validation_invalid_value": "Choose or enter a valid value.",
        "validation_mode_target_mismatch": (
            "The selected rotation mode cannot control this entity."
        ),
        "validation_maximum_must_exceed_minimum": (
            "Maximum brightness must be greater than minimum brightness."
        ),
        "validation_fast_response_conflicts_with_multi_press": (
            "Immediate single press cannot be combined with double or triple press."
        ),
        "binding_gesture_rotation": "Rotate left / right",
        "binding_gesture_short_press": "Short press",
        "binding_gesture_double_press": "Double press",
        "binding_gesture_triple_press": "Triple press",
        "binding_gesture_hold": "Hold",
        "binding_gesture_release": "Release",
        "action_adjust": "Adjust target",
        "action_toggle": "Toggle",
        "action_turn_on": "Turn on",
        "action_turn_off": "Turn off",
        "action_none": "No action",
        "action_cycle_scenes": "Cycle scenes",
        "action_ramp": "Ramp target",
        "action_stop_ramp": "Stop ramp",
        "wheel_missing_title": "Wheel no longer available",
        "wheel_missing_body": (
            "The wheel was removed or the integration reloaded. Return to the overview."
        ),
        # live test
        "live_listening": "Listening",
        "live_stopped": "Listening stopped",
        "live_waiting_title": "Waiting for the wheel",
        "live_waiting_body": (
            "Turn or press this wheel. Activity appears only while this view is open."
        ),
        "live_error": (
            "Live activity stopped. Leave and reopen Live test to try again."
        ),
        "result_unavailable": "Calculated result not reported",
        "result_unavailable_detail": (
            "The binding runtime does not expose its calculated result in this version."
        ),
        "dispatch_success": "Action dispatched",
        "dispatch_accepted": "Home Assistant accepted the action",
        "dispatch_pending": "Sending action to Home Assistant",
        "dispatch_skipped": "Binding skipped the action",
        "dispatch_not_configured": "No binding is configured for this channel",
        "dispatch_completed": "Local binding action completed",
        "dispatch_received": "Gesture received; calculating result",
        "dispatch_failed": "Action not dispatched",
        "dispatch_unknown": "Dispatch outcome not reported",
        "result_scene": "Scene {position}/{total} · {target}",
        "result_entity_action": "{action} · {target}",
        "result_ramp_stopped": "Hold ramp stopped",
        "result_fast_press_complete": "Immediate single press already dispatched",
        "service_toggle": "Toggle",
        "service_turn_on": "Turn on",
        "service_turn_off": "Turn off",
        "source_panel_test": "Triggered from the panel test controls",
        "test_controls_heading": "Test configured actions",
        "test_controls_intro": (
            "These controls run the real binding without a physical wheel. They can "
            "change target entities immediately."
        ),
        "test_channel": "Test channel {channel}",
        "test_rotate_down": "Rotate down",
        "test_rotate_up": "Rotate up",
        "test_single": "Single press",
        "test_double": "Double press",
        "test_triple": "Triple press",
        "test_hold": "Start hold",
        "test_release": "Release hold",
        "test_no_bindings": "Configure a channel to enable panel tests.",
        "direction_up": "up",
        "direction_down": "down",
        "gesture_rotate": "Channel {channel} · rotate {direction} · {delta} steps",
        "gesture_press_single": "Channel {channel} · single press",
        "gesture_press_double": "Channel {channel} · double press",
        "gesture_press_triple": "Channel {channel} · triple press",
        "gesture_hold": "Channel {channel} · hold",
        "gesture_release": "Channel {channel} · release",
        "gesture_unknown": "Channel {channel} · activity received",
        "live_recent": "Recent activity",
        # diagnostics
        "diagnostics_heading": "Wheel status",
        "diagnostics_intro": (
            "Read-only status from Home Assistant. Private Matter identifiers are "
            "not shown."
        ),
        "diagnostic_availability": "Wheel availability",
        "diagnostic_matter": "Matter connection",
        "diagnostic_source": "Event source",
        "diagnostic_link": "Matter device link",
        "diagnostic_linked": "Linked",
        "diagnostic_not_linked": "Not linked",
        "diagnostic_contract": "Panel contract",
        "source_core": "Home Assistant Matter client",
        "source_fallback": "Passive WebSocket fallback",
        "source_unloaded": "Integration unloaded",
        "recovery_heading": "Recommended action",
        "recovery_ok": "No recovery action is needed.",
        "recovery_matter": (
            "Check the Matter integration and the Matter Server connection."
        ),
        "recovery_unavailable": (
            "Check the wheel battery and bring it closer to the Matter network."
        ),
        "recovery_unknown": (
            "Check that the wheel is present in Home Assistant, then reload the "
            "integration."
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
        "edit_binding": "Upravit propojení",
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
        "wheel_switcher": "Kolečka",
        "detail_views": "Pohledy detailu kolečka",
        "tab_channels": "Kanály",
        "tab_live": "Živý test",
        "tab_diagnostics": "Diagnostika",
        "detail_area_none": "Bez oblasti",
        "detail_last_activity": "Poslední aktivita",
        "detail_last_channel": "Naposledy aktivní kanál",
        "detail_no_last_channel": "Zatím nebyl pozorován žádný kanál",
        "detail_channels_heading": "Chování kanálů",
        "detail_channels_intro": (
            "Zkontrolujte a přiřaďte, co ovládá otáčení, stisky a podržení."
        ),
        "channel_title": "Kanál {channel}",
        "channel_binding": "Propojení",
        "target_none": "Není nastaven žádný cíl",
        "binding_editor_title": "Upravit propojení kanálu {channel}",
        "field_mode": "Režim otáčení",
        "field_target": "Cíl otáčení",
        "field_step": "Krok na jeden zub",
        "field_acceleration": "Zrychlení",
        "field_transition": "Přechod",
        "field_min_brightness": "Minimální jas",
        "field_max_brightness": "Maximální jas",
        "field_click_action": "Krátký stisk",
        "field_click_target": "Cíl krátkého stisku",
        "field_button_response": "Odezva tlačítka",
        "field_double_target": "Cíl dvojitého stisku",
        "field_triple_target": "Cíl trojitého stisku",
        "field_hold_action": "Podržení",
        "field_hold_target": "Cíl podržení",
        "field_scenes": "Scény",
        "field_scenes_help": ("Vyberte více scén; každý krátký stisk přejde na další."),
        "field_unit": "Jednotka rozsahu: {unit}",
        "advanced_options": "Pokročilé možnosti",
        "click_toggle": "Přepnout cíl",
        "click_on": "Zapnout cíl",
        "click_off": "Vypnout cíl",
        "click_none": "Bez akce",
        "hold_toggle": "Přepnout cíl podržení",
        "hold_ramp": "Plynule měnit cíl otáčení",
        "hold_none": "Bez akce",
        "button_response_multi_press": "Počkat na jednoduchý/dvojitý/trojitý stisk",
        "button_response_fast": "Spustit jednoduchý stisk okamžitě",
        "save_binding": "Uložit propojení",
        "cancel_edit": "Zrušit úpravy",
        "delete_binding": "Smazat propojení",
        "keep_binding": "Ponechat propojení",
        "delete_binding_confirm": (
            "Smazat propojení tohoto kanálu? Kolečko přestane ovládat jeho cíle."
        ),
        "binding_saved": "Propojení bylo uloženo a aktivováno.",
        "binding_validation_failed": "Opravte označená pole a uložte znovu.",
        "binding_conflict": (
            "Propojení bylo mezitím změněno jinde. Zobrazují se nejnovější uložené "
            "hodnoty; před uložením je zkontrolujte."
        ),
        "binding_save_failed": "Propojení se nepodařilo uložit: {error}",
        "binding_delete_failed": "Propojení se nepodařilo smazat: {error}",
        "binding_test_failed": "Test se nepodařilo spustit: {error}",
        "binding_error_unloaded": "Integrace není načtená.",
        "binding_error_wheel_missing": "Kolečko už není dostupné.",
        "binding_error_binding_missing": "Propojení už neexistuje.",
        "binding_error_channel_occupied": ("Tento kanál kolečka už má jiné propojení."),
        "binding_error_binding_not_configured": (
            "Před testem nejdřív nastavte tento kanál."
        ),
        "validation_invalid_value": "Vyberte nebo zadejte platnou hodnotu.",
        "validation_mode_target_mismatch": (
            "Vybraný režim otáčení nemůže ovládat tuto entitu."
        ),
        "validation_maximum_must_exceed_minimum": (
            "Maximální jas musí být vyšší než minimální jas."
        ),
        "validation_fast_response_conflicts_with_multi_press": (
            "Okamžitý jednoduchý stisk nelze kombinovat s dvojitým nebo trojitým."
        ),
        "binding_gesture_rotation": "Otočení doleva / doprava",
        "binding_gesture_short_press": "Krátký stisk",
        "binding_gesture_double_press": "Dvojitý stisk",
        "binding_gesture_triple_press": "Trojitý stisk",
        "binding_gesture_hold": "Podržení",
        "binding_gesture_release": "Uvolnění",
        "action_adjust": "Upravit cíl",
        "action_toggle": "Přepnout",
        "action_turn_on": "Zapnout",
        "action_turn_off": "Vypnout",
        "action_none": "Bez akce",
        "action_cycle_scenes": "Procházet scény",
        "action_ramp": "Plynule měnit cíl",
        "action_stop_ramp": "Zastavit změnu",
        "wheel_missing_title": "Kolečko už není dostupné",
        "wheel_missing_body": (
            "Kolečko bylo odebráno nebo se integrace znovu načetla. Vraťte se na "
            "přehled."
        ),
        "live_listening": "Naslouchám",
        "live_stopped": "Naslouchání zastaveno",
        "live_waiting_title": "Čekám na kolečko",
        "live_waiting_body": (
            "Otočte kolečkem nebo ho stiskněte. Aktivita se zobrazuje jen v tomto "
            "pohledu."
        ),
        "live_error": (
            "Živá aktivita se zastavila. Odejděte z Živého testu a znovu ho otevřete."
        ),
        "result_unavailable": "Vypočtený výsledek se nehlásí",
        "result_unavailable_detail": (
            "Běh propojení v této verzi nezveřejňuje vypočtený výsledek."
        ),
        "dispatch_success": "Akce byla odeslána",
        "dispatch_accepted": "Home Assistant akci přijal",
        "dispatch_pending": "Odesílám akci do Home Assistantu",
        "dispatch_skipped": "Propojení akci přeskočilo",
        "dispatch_not_configured": "Tento kanál nemá nastavené propojení",
        "dispatch_completed": "Místní akce propojení byla dokončena",
        "dispatch_received": "Gesto přijato; počítám výsledek",
        "dispatch_failed": "Akce nebyla odeslána",
        "dispatch_unknown": "Výsledek odeslání se nehlásí",
        "result_scene": "Scéna {position}/{total} · {target}",
        "result_entity_action": "{action} · {target}",
        "result_ramp_stopped": "Plynulá změna byla zastavena",
        "result_fast_press_complete": ("Okamžitý jednoduchý stisk už byl odeslán"),
        "service_toggle": "Přepnout",
        "service_turn_on": "Zapnout",
        "service_turn_off": "Vypnout",
        "source_panel_test": "Spuštěno testovacími ovladači v panelu",
        "test_controls_heading": "Otestovat nastavené akce",
        "test_controls_intro": (
            "Tyto ovladače spustí skutečné propojení bez fyzického kolečka. "
            "Cílové entity se mohou okamžitě změnit."
        ),
        "test_channel": "Test kanálu {channel}",
        "test_rotate_down": "Otočit dolů",
        "test_rotate_up": "Otočit nahoru",
        "test_single": "Jednoduchý stisk",
        "test_double": "Dvojitý stisk",
        "test_triple": "Trojitý stisk",
        "test_hold": "Začít podržení",
        "test_release": "Uvolnit podržení",
        "test_no_bindings": "Pro testování nejdřív nastavte některý kanál.",
        "direction_up": "nahoru",
        "direction_down": "dolů",
        "gesture_rotate": "Kanál {channel} · otočení {direction} · {delta} kroků",
        "gesture_press_single": "Kanál {channel} · jednoduchý stisk",
        "gesture_press_double": "Kanál {channel} · dvojitý stisk",
        "gesture_press_triple": "Kanál {channel} · trojitý stisk",
        "gesture_hold": "Kanál {channel} · podržení",
        "gesture_release": "Kanál {channel} · uvolnění",
        "gesture_unknown": "Kanál {channel} · přijata aktivita",
        "live_recent": "Nedávná aktivita",
        "diagnostics_heading": "Stav kolečka",
        "diagnostics_intro": (
            "Stav z Home Assistantu pouze pro čtení. Soukromé identifikátory Matter "
            "se nezobrazují."
        ),
        "diagnostic_availability": "Dostupnost kolečka",
        "diagnostic_matter": "Připojení Matter",
        "diagnostic_source": "Zdroj událostí",
        "diagnostic_link": "Propojení se zařízením Matter",
        "diagnostic_linked": "Propojeno",
        "diagnostic_not_linked": "Nepropojeno",
        "diagnostic_contract": "Kontrakt panelu",
        "source_core": "Matter klient Home Assistantu",
        "source_fallback": "Pasivní záložní WebSocket",
        "source_unloaded": "Integrace není načtená",
        "recovery_heading": "Doporučený krok",
        "recovery_ok": "Není potřeba žádný opravný krok.",
        "recovery_matter": (
            "Zkontrolujte integraci Matter a připojení k Matter Serveru."
        ),
        "recovery_unavailable": (
            "Zkontrolujte baterii kolečka a přibližte ho k síti Matter."
        ),
        "recovery_unknown": (
            "Zkontrolujte, že je kolečko v Home Assistantu, a potom integraci znovu "
            "načtěte."
        ),
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
