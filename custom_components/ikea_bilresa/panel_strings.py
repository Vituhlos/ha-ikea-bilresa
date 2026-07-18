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
        "button_actions": "Button actions",
        "multiple_targets": "{count} targets",
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
        "last_on_button": "last on button {button}",
        # summary
        "overview_title": "BILRESA devices",
        "summary_connected": "{count} connected",
        "summary_unavailable": "{count} unavailable",
        "summary_unknown": "{count} not reporting",
        "matter_connected": "Matter connected",
        "matter_offline": "Matter offline",
        # banners
        "banner_matter_offline": (
            "Matter is disconnected. The devices below show their last known state."
        ),
        "banner_updates_stopped": "Live updates stopped. This view may be out of date.",
        "banner_target_missing": (
            "Bindings on {count} devices point to targets Home Assistant can no "
            "longer find. Open a marked control to repair it."
        ),
        "banner_target_missing_named": (
            "{wheel} has an unavailable binding target on channel {channel}. "
            "Open the channel and repair the binding."
        ),
        "banner_target_missing_button_named": (
            "{wheel} has an unavailable binding target on button {button}. "
            "Open the button and repair the binding."
        ),
        # states
        "empty_title": "No BILRESA devices found",
        "empty_connected": (
            "The integration is connected but has not discovered a device yet."
        ),
        "empty_offline": (
            "Home Assistant is not connected to Matter, so no device can be seen."
        ),
        "error_title": "Cannot reach the integration",
        "retry": "Try again",
        # detail
        "back": "Back to all BILRESA devices",
        "wheel_switcher": "BILRESA devices",
        "detail_views": "Device detail views",
        "tab_channels": "Channels",
        "tab_buttons": "Buttons",
        "tab_live": "Live test",
        "tab_diagnostics": "Diagnostics",
        "detail_area_none": "No area",
        "detail_last_activity": "Last activity",
        "detail_last_channel": "Last active channel",
        "detail_no_last_channel": "No channel observed yet",
        "detail_last_button": "Last active button",
        "detail_no_last_button": "No button observed yet",
        "detail_channels_heading": "Physical position behaviour",
        "detail_channels_intro": (
            "The three selector positions on the wheel are also the navigation. "
            "Pick a position to review or edit its gestures in place."
        ),
        "channel_spine": "Wheel channels",
        "channel_empty_title": "Channel {channel} is waiting for a binding",
        "channel_empty_body": (
            "Pick a behaviour and a target. The other two physical positions "
            "stay unchanged."
        ),
        "channel_title": "Channel {channel}",
        "channel_binding": "Binding",
        "detail_buttons_intro": (
            "The two physical buttons are also the navigation. Pick a button to "
            "review or edit its gestures in place."
        ),
        "button_spine": "Dual-button controls",
        "button_empty_title": "Button {button} is waiting for a binding",
        "button_empty_body": (
            "Choose what a short press, double press and hold should control."
        ),
        "button_title": "Button {button}",
        "target_none": "No target configured",
        # binding editor
        "binding_editor_title": "Edit channel {channel} binding",
        "binding_editor_button_title": "Edit button {button} binding",
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
        "field_ramp_direction": "Hold ramp direction",
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
        "ramp_direction_alternate": "Alternate up and down",
        "ramp_direction_up": "Always brighten",
        "ramp_direction_down": "Always dim",
        "button_response_instant": "Run on initial press",
        "button_response_fast": "Run after the first short release",
        "button_response_multi_press": "Wait for single/double/triple press",
        "dual_button_response_instant": "Run on initial press",
        "dual_button_response_fast": "Run after the first short release",
        "dual_button_response_multi_press": "Wait for single or double press",
        "save_binding": "Save binding",
        "cancel_edit": "Cancel editing",
        "delete_binding": "Delete binding",
        "keep_binding": "Keep binding",
        "delete_binding_confirm": (
            "Delete this channel binding? The wheel will stop controlling its targets."
        ),
        "delete_button_binding_confirm": (
            "Delete this button binding? The button will stop controlling its targets."
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
        "binding_error_button_occupied": ("This button already has another binding."),
        "binding_error_control_mismatch": (
            "This control does not belong to the selected BILRESA device."
        ),
        "binding_error_control_missing": "This control is no longer available.",
        "binding_error_binding_address_mismatch": (
            "This binding belongs to another control. Reload the panel and try again."
        ),
        "binding_error_gesture_unsupported": (
            "This BILRESA device does not support that gesture."
        ),
        "binding_error_binding_not_configured": (
            "Configure this control before testing it."
        ),
        "validation_invalid_value": "Choose or enter a valid value.",
        "validation_mode_target_mismatch": (
            "The selected rotation mode cannot control this entity."
        ),
        "validation_maximum_must_exceed_minimum": (
            "Maximum brightness must be greater than minimum brightness."
        ),
        "validation_fast_response_conflicts_with_multi_press": (
            "Fast release cannot be combined with double or triple press."
        ),
        "validation_instant_response_conflicts_with_multi_press": (
            "Instant response cannot be combined with double or triple press."
        ),
        "validation_instant_response_conflicts_with_hold": (
            "Instant response requires the hold action to be set to No action."
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
        "action_ramp_alternate": "Ramp up or down",
        "action_ramp_up": "Brighten",
        "action_ramp_down": "Dim",
        "action_stop_ramp": "Stop ramp",
        "wheel_missing_title": "BILRESA device no longer available",
        "wheel_missing_body": (
            "The device was removed or the integration reloaded. Return to the "
            "overview."
        ),
        # live test
        "live_intro": (
            "Turn or press the wheel. You will see the recognized gesture first "
            "and, for configured channels, the action sent to its target."
        ),
        "live_button_intro": (
            "Press either button. You will see the recognized gesture first and, "
            "for configured buttons, the action sent to its target."
        ),
        "live_result_label": "Action result",
        "live_event_label": "Latest gesture",
        "live_listening": "Listening",
        "live_stopped": "Listening stopped",
        "live_waiting_title": "Waiting for the wheel",
        "live_waiting_body": (
            "Turn or press this wheel. Activity appears only while this view is open."
        ),
        "live_button_waiting_title": "Waiting for a button press",
        "live_button_waiting_body": (
            "Press, double-press or hold either button. Activity appears only while "
            "this view is open."
        ),
        "live_error": (
            "Live activity stopped. Leave and reopen Live test to try again."
        ),
        "result_unavailable": "Gesture recognized",
        "result_unavailable_detail": (
            "No detailed result is available for this event."
        ),
        "result_pending_detail": "Waiting for the configured action to finish.",
        "result_not_configured_channel_detail": ("The gesture reached Home Assistant."),
        "result_not_configured_button_detail": ("The gesture reached Home Assistant."),
        "result_gesture_rotate": "Rotation recognized",
        "result_gesture_press": "Press recognized",
        "result_gesture_double_press": "Double press recognized",
        "result_gesture_triple_press": "Triple press recognized",
        "result_gesture_hold": "Hold recognized",
        "result_gesture_release": "Release recognized",
        "result_gesture_received": "Gesture recognized",
        "dispatch_success": "Action dispatched",
        "dispatch_accepted": "Home Assistant accepted the action",
        "dispatch_pending": "Sending action to Home Assistant",
        "dispatch_skipped": "Binding skipped the action",
        "dispatch_not_configured": "This channel does not control anything yet",
        "dispatch_not_configured_button": ("This button does not control anything yet"),
        "dispatch_completed": "Binding action completed",
        "dispatch_received": "Gesture received; waiting for the result",
        "dispatch_failed": "Action not dispatched",
        "dispatch_unknown": "Action status is not available",
        "result_kind_brightness": "Brightness",
        "result_kind_color_temperature": "Colour temperature",
        "result_kind_color": "Colour",
        "result_kind_volume": "Volume",
        "result_kind_position": "Position",
        "result_kind_temperature": "Temperature",
        "result_kind_fan_speed": "Fan speed",
        "result_kind_value": "Value",
        "result_scene": "Scene {position}/{total} · {target}",
        "result_entity_action": "{action} · {target}",
        "result_ramp_stopped": "Hold ramp stopped",
        "result_fast_press_complete": "Single press dispatched immediately",
        "service_toggle": "Toggle",
        "service_turn_on": "Turn on",
        "service_turn_off": "Turn off",
        "source_panel_test": "Triggered from the panel test controls",
        "test_controls_heading": "Test configured actions",
        "test_controls_intro": (
            "These controls run the real binding without a physical wheel. They can "
            "change target entities immediately."
        ),
        "test_controls_button_intro": (
            "These controls run the real binding without pressing the physical "
            "button. They can change target entities immediately."
        ),
        "test_channel": "Test channel {channel}",
        "test_button": "Test button {button}",
        "test_rotate_down": "Rotate down",
        "test_rotate_up": "Rotate up",
        "test_single": "Single press",
        "test_double": "Double press",
        "test_triple": "Triple press",
        "test_hold": "Start hold",
        "test_release": "Release hold",
        "test_no_bindings": "Configure a channel to enable panel tests.",
        "test_no_button_bindings": "Configure a button to enable panel tests.",
        "direction_up": "up",
        "direction_down": "down",
        "gesture_rotate": "Channel {channel} · rotate {direction} · {delta} steps",
        "gesture_press_single": "Channel {channel} · single press",
        "gesture_press_double": "Channel {channel} · double press",
        "gesture_press_triple": "Channel {channel} · triple press",
        "gesture_hold": "Channel {channel} · hold",
        "gesture_release": "Channel {channel} · release",
        "gesture_unknown": "Channel {channel} · activity received",
        "live_channels_heading": "Channels",
        "gesture_button_press_single": "Button {button} · single press",
        "gesture_button_press_double": "Button {button} · double press",
        "gesture_button_hold": "Button {button} · hold",
        "gesture_button_release": "Button {button} · release",
        "gesture_button_unknown": "Button {button} · activity received",
        "gesture_observed_duration": "{duration} s observed",
        "live_buttons_heading": "Buttons",
        "live_recent": "Latest events",
        "live_setup_channel": "Configure channel {channel}",
        "live_setup_button": "Configure button {button}",
        # diagnostics
        "diagnostics_heading": "Device status",
        "diagnostics_intro": (
            "Read-only status from Home Assistant. Private Matter identifiers are "
            "not shown."
        ),
        "diagnostic_availability": "Device availability",
        "diagnostic_matter": "Matter connection",
        "diagnostic_source": "Event source",
        "diagnostic_link": "Matter device link",
        "diagnostic_linked": "Linked",
        "diagnostic_not_linked": "Not linked",
        "diagnostic_health_ok": "Wheel is ready",
        "diagnostic_health_attention": "Wheel needs attention",
        "diagnostic_health_ok_body": ("Matter and live event delivery are connected."),
        "diagnostic_connection_heading": "Connection",
        "diagnostic_activity_heading": "Activity",
        "diagnostic_technical_details": "Technical details",
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
        "button_actions": "Akce tlačítka",
        "multiple_targets": "{count} cíle",
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
        "last_on_button": "naposledy na tlačítku {button}",
        "overview_title": "Zařízení BILRESA",
        "summary_connected": "{count} připojeno",
        "summary_unavailable": "{count} nedostupné",
        "summary_unknown": "{count} se nehlásí",
        "matter_connected": "Matter připojen",
        "matter_offline": "Matter odpojen",
        "banner_matter_offline": (
            "Matter je odpojený. Zařízení níže ukazují svůj poslední známý stav."
        ),
        "banner_updates_stopped": (
            "Živé aktualizace se zastavily. Tento pohled může být zastaralý."
        ),
        "banner_target_missing": (
            "{count} zařízení má nedostupný cíl propojení. Otevřete označený "
            "ovládací prvek a propojení opravte."
        ),
        "banner_target_missing_named": (
            "{wheel} má na kanálu {channel} nedostupný cíl propojení. "
            "Otevřete kanál a propojení opravte."
        ),
        "banner_target_missing_button_named": (
            "{wheel} má na tlačítku {button} nedostupný cíl propojení. "
            "Otevřete tlačítko a propojení opravte."
        ),
        "empty_title": "Nenalezeno žádné zařízení BILRESA",
        "empty_connected": "Integrace je připojená, ale zatím nenašla žádné zařízení.",
        "empty_offline": (
            "Home Assistant není připojený k Matteru, takže nevidí žádné zařízení."
        ),
        "error_title": "Integrace není dostupná",
        "retry": "Zkusit znovu",
        "back": "Zpět na všechna zařízení BILRESA",
        "wheel_switcher": "Zařízení BILRESA",
        "detail_views": "Pohledy detailu zařízení",
        "tab_channels": "Kanály",
        "tab_buttons": "Tlačítka",
        "tab_live": "Živý test",
        "tab_diagnostics": "Diagnostika",
        "detail_area_none": "Bez oblasti",
        "detail_last_activity": "Poslední aktivita",
        "detail_last_channel": "Naposledy aktivní kanál",
        "detail_no_last_channel": "Zatím nebyl pozorován žádný kanál",
        "detail_last_button": "Naposledy aktivní tlačítko",
        "detail_no_last_button": "Zatím nebylo pozorováno žádné tlačítko",
        "detail_channels_heading": "Chování fyzických poloh",
        "detail_channels_intro": (
            "Tři polohy přepínače na kolečku jsou zároveň navigací. Vyberte "
            "polohu a upravte její gesta bez přesunu na další stránku."
        ),
        "channel_spine": "Kanály kolečka",
        "channel_empty_title": "Kanál {channel} čeká na propojení",
        "channel_empty_body": (
            "Zvolte chování a cíl. Ostatní dvě fyzické polohy kolečka zůstanou "
            "beze změny."
        ),
        "channel_title": "Kanál {channel}",
        "channel_binding": "Propojení",
        "detail_buttons_intro": (
            "Dvě fyzická tlačítka jsou zároveň navigací. Vyberte tlačítko a "
            "upravte jeho gesta bez přesunu na další stránku."
        ),
        "button_spine": "Tlačítka dvoutlačítka",
        "button_empty_title": "Tlačítko {button} čeká na propojení",
        "button_empty_body": (
            "Zvolte, co má ovládat krátký stisk, dvojitý stisk a podržení."
        ),
        "button_title": "Tlačítko {button}",
        "target_none": "Není nastaven žádný cíl",
        "binding_editor_title": "Upravit propojení kanálu {channel}",
        "binding_editor_button_title": "Upravit propojení tlačítka {button}",
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
        "field_ramp_direction": "Směr plynulé změny při podržení",
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
        "ramp_direction_alternate": "Střídat zesílení a zeslabení",
        "ramp_direction_up": "Vždy zesílit",
        "ramp_direction_down": "Vždy zeslabit",
        "button_response_instant": "Spustit už při prvním stisku",
        "button_response_fast": "Spustit po prvním krátkém uvolnění",
        "button_response_multi_press": "Počkat na jednoduchý/dvojitý/trojitý stisk",
        "dual_button_response_instant": "Spustit už při prvním stisku",
        "dual_button_response_fast": "Spustit po prvním krátkém uvolnění",
        "dual_button_response_multi_press": "Počkat na jednoduchý nebo dvojitý stisk",
        "save_binding": "Uložit propojení",
        "cancel_edit": "Zrušit úpravy",
        "delete_binding": "Smazat propojení",
        "keep_binding": "Ponechat propojení",
        "delete_binding_confirm": (
            "Smazat propojení tohoto kanálu? Kolečko přestane ovládat jeho cíle."
        ),
        "delete_button_binding_confirm": (
            "Smazat propojení tohoto tlačítka? Tlačítko přestane ovládat své cíle."
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
        "binding_error_button_occupied": "Toto tlačítko už má jiné propojení.",
        "binding_error_control_mismatch": (
            "Tento ovládací prvek nepatří k vybranému zařízení BILRESA."
        ),
        "binding_error_control_missing": "Tento ovládací prvek už není dostupný.",
        "binding_error_binding_address_mismatch": (
            "Toto propojení patří jinému ovládacímu prvku. Obnovte panel a zkuste "
            "to znovu."
        ),
        "binding_error_gesture_unsupported": (
            "Toto zařízení BILRESA dané gesto nepodporuje."
        ),
        "binding_error_binding_not_configured": (
            "Před testem nejdřív nastavte tento ovládací prvek."
        ),
        "validation_invalid_value": "Vyberte nebo zadejte platnou hodnotu.",
        "validation_mode_target_mismatch": (
            "Vybraný režim otáčení nemůže ovládat tuto entitu."
        ),
        "validation_maximum_must_exceed_minimum": (
            "Maximální jas musí být vyšší než minimální jas."
        ),
        "validation_fast_response_conflicts_with_multi_press": (
            "Rychlé uvolnění nelze kombinovat s dvojitým nebo trojitým stiskem."
        ),
        "validation_instant_response_conflicts_with_multi_press": (
            "Okamžitou odezvu nelze kombinovat s dvojitým nebo trojitým stiskem."
        ),
        "validation_instant_response_conflicts_with_hold": (
            "Okamžitá odezva vyžaduje nastavit podržení na Bez akce."
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
        "action_ramp_alternate": "Plynule zesílit nebo zeslabit",
        "action_ramp_up": "Zesílit",
        "action_ramp_down": "Zeslabit",
        "action_stop_ramp": "Zastavit změnu",
        "wheel_missing_title": "Zařízení BILRESA už není dostupné",
        "wheel_missing_body": (
            "Zařízení bylo odebráno nebo se integrace znovu načetla. Vraťte se na "
            "přehled."
        ),
        "live_intro": (
            "Otočte kolečkem nebo ho stiskněte. Hned uvidíte rozpoznané gesto "
            "a u nastaveného kanálu také akci odeslanou do cíle."
        ),
        "live_button_intro": (
            "Stiskněte jedno z tlačítek. Hned uvidíte rozpoznané gesto a u "
            "nastaveného tlačítka také akci odeslanou do cíle."
        ),
        "live_result_label": "Výsledek akce",
        "live_event_label": "Poslední gesto",
        "live_listening": "Naslouchám",
        "live_stopped": "Naslouchání zastaveno",
        "live_waiting_title": "Čekám na kolečko",
        "live_waiting_body": (
            "Otočte kolečkem nebo ho stiskněte. Aktivita se zobrazuje jen v tomto "
            "pohledu."
        ),
        "live_button_waiting_title": "Čekám na stisk tlačítka",
        "live_button_waiting_body": (
            "Stiskněte, dvakrát stiskněte nebo podržte libovolné tlačítko. Aktivita "
            "se zobrazuje jen v tomto pohledu."
        ),
        "live_error": (
            "Živá aktivita se zastavila. Odejděte z Živého testu a znovu ho otevřete."
        ),
        "result_unavailable": "Gesto rozpoznáno",
        "result_unavailable_detail": (
            "Pro tuto událost nejsou dostupné podrobnosti výsledku."
        ),
        "result_pending_detail": "Čekám na dokončení nastavené akce.",
        "result_not_configured_channel_detail": ("Gesto dorazilo do Home Assistantu."),
        "result_not_configured_button_detail": ("Gesto dorazilo do Home Assistantu."),
        "result_gesture_rotate": "Otočení rozpoznáno",
        "result_gesture_press": "Stisk rozpoznán",
        "result_gesture_double_press": "Dvojitý stisk rozpoznán",
        "result_gesture_triple_press": "Trojitý stisk rozpoznán",
        "result_gesture_hold": "Podržení rozpoznáno",
        "result_gesture_release": "Uvolnění rozpoznáno",
        "result_gesture_received": "Gesto rozpoznáno",
        "dispatch_success": "Akce byla odeslána",
        "dispatch_accepted": "Home Assistant akci přijal",
        "dispatch_pending": "Odesílám akci do Home Assistantu",
        "dispatch_skipped": "Propojení akci přeskočilo",
        "dispatch_not_configured": "Tento kanál zatím nic neovládá",
        "dispatch_not_configured_button": ("Toto tlačítko zatím nic neovládá"),
        "dispatch_completed": "Akce propojení byla dokončena",
        "dispatch_received": "Gesto přijato; čekám na výsledek",
        "dispatch_failed": "Akce nebyla odeslána",
        "dispatch_unknown": "Stav akce není dostupný",
        "result_kind_brightness": "Jas",
        "result_kind_color_temperature": "Teplota barvy",
        "result_kind_color": "Barva",
        "result_kind_volume": "Hlasitost",
        "result_kind_position": "Poloha",
        "result_kind_temperature": "Teplota",
        "result_kind_fan_speed": "Rychlost ventilátoru",
        "result_kind_value": "Hodnota",
        "result_scene": "Scéna {position}/{total} · {target}",
        "result_entity_action": "{action} · {target}",
        "result_ramp_stopped": "Plynulá změna byla zastavena",
        "result_fast_press_complete": ("Jednoduchý stisk byl odeslán okamžitě"),
        "service_toggle": "Přepnout",
        "service_turn_on": "Zapnout",
        "service_turn_off": "Vypnout",
        "source_panel_test": "Spuštěno testovacími ovladači v panelu",
        "test_controls_heading": "Otestovat nastavené akce",
        "test_controls_intro": (
            "Tyto ovladače spustí skutečné propojení bez fyzického kolečka. "
            "Cílové entity se mohou okamžitě změnit."
        ),
        "test_controls_button_intro": (
            "Tyto ovladače spustí skutečné propojení bez stisku fyzického tlačítka. "
            "Cílové entity se mohou okamžitě změnit."
        ),
        "test_channel": "Test kanálu {channel}",
        "test_button": "Test tlačítka {button}",
        "test_rotate_down": "Otočit dolů",
        "test_rotate_up": "Otočit nahoru",
        "test_single": "Jednoduchý stisk",
        "test_double": "Dvojitý stisk",
        "test_triple": "Trojitý stisk",
        "test_hold": "Začít podržení",
        "test_release": "Uvolnit podržení",
        "test_no_bindings": "Pro testování nejdřív nastavte některý kanál.",
        "test_no_button_bindings": ("Pro testování nejdřív nastavte některé tlačítko."),
        "direction_up": "nahoru",
        "direction_down": "dolů",
        "gesture_rotate": "Kanál {channel} · otočení {direction} · {delta} kroků",
        "gesture_press_single": "Kanál {channel} · jednoduchý stisk",
        "gesture_press_double": "Kanál {channel} · dvojitý stisk",
        "gesture_press_triple": "Kanál {channel} · trojitý stisk",
        "gesture_hold": "Kanál {channel} · podržení",
        "gesture_release": "Kanál {channel} · uvolnění",
        "gesture_unknown": "Kanál {channel} · přijata aktivita",
        "live_channels_heading": "Kanály",
        "gesture_button_press_single": "Tlačítko {button} · jednoduchý stisk",
        "gesture_button_press_double": "Tlačítko {button} · dvojitý stisk",
        "gesture_button_hold": "Tlačítko {button} · podržení",
        "gesture_button_release": "Tlačítko {button} · uvolnění",
        "gesture_button_unknown": "Tlačítko {button} · přijata aktivita",
        "gesture_observed_duration": "zachyceno {duration} s",
        "live_buttons_heading": "Tlačítka",
        "live_recent": "Poslední události",
        "live_setup_channel": "Nastavit kanál {channel}",
        "live_setup_button": "Nastavit tlačítko {button}",
        "diagnostics_heading": "Stav zařízení",
        "diagnostics_intro": (
            "Stav z Home Assistantu pouze pro čtení. Soukromé identifikátory Matter "
            "se nezobrazují."
        ),
        "diagnostic_availability": "Dostupnost zařízení",
        "diagnostic_matter": "Připojení Matter",
        "diagnostic_source": "Zdroj událostí",
        "diagnostic_link": "Propojení se zařízením Matter",
        "diagnostic_linked": "Propojeno",
        "diagnostic_not_linked": "Nepropojeno",
        "diagnostic_health_ok": "Kolečko je připravené",
        "diagnostic_health_attention": "Kolečko vyžaduje pozornost",
        "diagnostic_health_ok_body": (
            "Matter i živé doručování událostí jsou připojené."
        ),
        "diagnostic_connection_heading": "Připojení",
        "diagnostic_activity_heading": "Aktivita",
        "diagnostic_technical_details": "Technické podrobnosti",
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
