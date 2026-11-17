"""The ledger of what the lab does not test yet, and why.

Every entry is a pattern (``fnmatch``) over the feature ids of ``catalog`` plus
the reason and the planned work. ``test_catalog.py`` keeps this honest:

* a feature that is neither covered by a test (``@covers``) nor matched here
  fails the build, so nothing new can slip in unnoticed;
* an entry that no longer matches any uncovered feature fails too, so the
  ledger shrinks as the lab grows and cannot keep a gap nobody has.

Patterns are written out one by one on purpose. A pattern made from the
production code itself would accept every new feature as a gap.

The planned work names (LAB-01a ... d) are the packages of the lab plan: 01a
colour, 01b cover/fan/unavailable, 01c press verbs, scenes and response modes,
01d acceleration and soak. "OUT OF SCOPE" is for what is not runtime behaviour
of the wheel or the button and is tested elsewhere.
"""

from __future__ import annotations

NEEDS_SCRIPT_SPY = (
    "LAB-01c: a press that runs an action sequence needs a recording stand-in"
    " for scripts; the lab refuses to run user actions (test_safety)"
)
PRESS_VERBS = "LAB-01c: the verb of this kind of entity is not exercised yet"

GAPS: dict[str, str] = {
    # -- settings ------------------------------------------------------------
    "conf:acceleration": "LAB-01d: slow/medium/fast acceleration is not simulated",
    "conf:binding_profile": "OUT OF SCOPE: config-flow only, belongs in tests/",
    "conf:copy_from": "OUT OF SCOPE: config-flow only, belongs in tests/",
    "conf:button_response": "LAB-01c: instant / fast / multi-press timing",
    "conf:channel_enabled": "LAB-01c: a disabled channel must send nothing",
    "conf:double_press_action": "LAB-01c: double-press verb",
    "conf:double_press_target": "LAB-01c: double-press target",
    "conf:triple_press_action": "LAB-01c: triple-press verb",
    "conf:triple_press_target": "LAB-01c: triple-press target",
    "conf:hold_target_action": "LAB-01c: verb used by the hold toggle",
    "conf:click_sequence": NEEDS_SCRIPT_SPY,
    "conf:double_press_sequence": NEEDS_SCRIPT_SPY,
    "conf:triple_press_sequence": NEEDS_SCRIPT_SPY,
    "conf:hold_sequence": NEEDS_SCRIPT_SPY,
    "conf:max_brightness": "LAB-01a: the brightness ceiling below 100 %",
    "conf:ramp_direction": "LAB-01c: paired hold ramp of the dual button",
    "conf:scenes": "LAB-01c: scene cycling (order, wrap); rc7 only uses a scene",
    # -- values of a setting -------------------------------------------------
    "curve:perceptual": "LAB-01a: the perceptual brightness curve",
    "hold:toggle": "LAB-01c: the default hold action",
    "hold:none": "LAB-01c: a hold that does nothing",
    "hold:run": NEEDS_SCRIPT_SPY,
    "ramp:*": "LAB-01c: ramp direction alternate / up / down",
    "response:*": "LAB-01c: when a single press acts",
    "mode:color": "LAB-01a: hue and saturation",
    "mode:color_temp": "LAB-01a: Kelvin range of the light",
    "mode:cover_position": "LAB-01b: needs a cover target",
    "mode:fan_speed": "LAB-01b: needs a fan target",
    # -- what a press can do to a kind of entity -----------------------------
    "verb:automation.*": PRESS_VERBS,
    "verb:button.*": PRESS_VERBS,
    "verb:climate.*": PRESS_VERBS,
    "verb:cover.*": PRESS_VERBS,
    "verb:fan.*": PRESS_VERBS,
    "verb:humidifier.*": PRESS_VERBS,
    "verb:input_boolean.*": PRESS_VERBS,
    "verb:input_button.*": PRESS_VERBS,
    "verb:input_number.*": PRESS_VERBS,
    "verb:input_select.*": PRESS_VERBS,
    "verb:light.*": PRESS_VERBS,
    "verb:lock.*": PRESS_VERBS,
    "verb:media_player.*": PRESS_VERBS,
    "verb:remote.*": PRESS_VERBS,
    "verb:scene.*": PRESS_VERBS,
    "verb:script.*": PRESS_VERBS,
    "verb:select.*": PRESS_VERBS,
    "verb:siren.*": PRESS_VERBS,
    "verb:switch.*": PRESS_VERBS,
    "verb:vacuum.*": PRESS_VERBS,
    "verb:valve.*": PRESS_VERBS,
}
