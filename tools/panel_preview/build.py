"""Render the BILRESA panel without a Home Assistant instance.

Writes ``out/index.html``: the panel's real script, the repository's own labels
and field schema, and a synthetic home. Serve the folder and open it:

    python tools/panel_preview/build.py
    python -m http.server 8765 --bind 127.0.0.1 --directory tools/panel_preview/out

Query parameters: ``lang=cs`` (the viewing user's language, default ``en``),
``instance=cs`` (the Home Assistant instance's language, default ``lang``),
``dark=1``, ``narrow=1`` (no sidebar, phone layout),
``inset=16`` (a theme that pads the panel),
``theme=warm`` (a warm custom theme with large radii and a white header, the
kind the owner runs, instead of Home Assistant's default),
``open=<wheel key>`` with ``view=channels|buttons|live|diagnostics``, and
``edit=<n>`` to open the editor of channel or button ``n``.

What this shows and what it does not: layout, copy and the panel's own
fallback controls are real. Colours are Home Assistant's default tokens, not a
user's theme. Home Assistant's own components (``ha-selector``) are not
loaded, so the preview always shows the fallback path; the path that uses
them can only be checked in a real Home Assistant.

Everything in the fixture is invented. Never paste names or identifiers from a
real home into this file.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from custom_components.ikea_bilresa.panel_models import (  # noqa: E402
    CONTRACT_VERSION,
)
from custom_components.ikea_bilresa.panel_schema import panel_schema  # noqa: E402
from custom_components.ikea_bilresa.panel_strings import STRINGS  # noqa: E402

PANEL_JS = (
    REPO / "custom_components/ikea_bilresa/frontend/ikea_bilresa_panel.js"
).read_text(encoding="utf-8")
if "</script" in PANEL_JS:
    raise SystemExit("the panel script cannot be inlined: it contains </script")

# entity_id: (state, friendly name)
ENTITIES = {
    "light.counter": ("on", "Counter"),
    "light.ceiling": ("off", "Ceiling"),
    "light.ceiling_bulb": ("unavailable", "Ceiling bulb"),
    "light.reading_lamp": ("off", "Reading lamp"),
    "light.hall": ("off", "Hall"),
    "switch.fan": ("off", "Fan"),
    "script.good_night": ("off", "Good night"),
    "media_player.speaker": ("idle", "Speaker"),
    "scene.evening": ("unknown", "Evening"),
    "scene.movie": ("unknown", "Movie"),
    "scene.bright": ("unknown", "Bright"),
    "scene.night": ("unknown", "Night"),
}


def _name(entity_id: str | None) -> str | None:
    if entity_id is None:
        return None
    return ENTITIES.get(entity_id, (None, entity_id))[1]


def _state(entity_id: str | None) -> str:
    if entity_id is None:
        return "ok"
    if entity_id not in ENTITIES:
        return "missing"
    return "unavailable" if ENTITIES[entity_id][0] == "unavailable" else "ok"


def _action(labels: dict, gesture: str, action: str, target: str | None = None) -> dict:
    state = _state(target)
    return {
        "gesture": gesture,
        "gesture_label": labels[f"binding_gesture_{gesture}"],
        "action_label": labels[action],
        "target_label": _name(target),
        "target_state": state,
        "target_missing": state == "missing",
    }


def _worst(states: list[str]) -> str:
    order = ("ok", "unavailable", "missing")
    return max(states, key=order.index, default="ok")


def _press_label(target: str | None, action: str) -> str:
    """The ledger word for a press, as panel_models.py chooses it."""
    if not target:
        return "action_none"
    if target.startswith("scene.") or (target.startswith("script.") and action == "on"):
        return "action_run"
    if target.startswith("script.") and action == "off":
        return "action_stop"
    return {"on": "action_turn_on", "off": "action_turn_off"}.get(
        action, "action_toggle"
    )


def _channel(labels: dict, number: int, data: dict | None, *, enabled: bool = True):
    if data is None:
        return {
            "channel": number,
            "enabled": enabled,
            "configured": False,
            "profile": None,
            "behaviour": None,
            "target_label": None,
            "target_state": "ok",
            "target_missing": False,
            "actions": [],
            "binding": None,
        }
    target = data["target"]
    scenes = data.get("scenes") or []
    press = (
        {
            "gesture": "short_press",
            "gesture_label": labels["binding_gesture_short_press"],
            "action_label": labels["action_cycle_scenes"],
            "target_label": " / ".join(_name(scene) for scene in scenes),
            "target_state": "ok",
            "target_missing": False,
        }
        if scenes
        else _action(
            labels, "short_press", "action_toggle", data.get("click_target") or target
        )
    )
    actions = [
        _action(labels, "rotation", f"quantity_{data['mode']}", target),
        press,
        _action(
            labels,
            "double_press",
            _press_label(
                data.get("double_press_target"),
                data.get("double_press_action", "toggle"),
            ),
            data.get("double_press_target"),
        ),
        _action(
            labels,
            "triple_press",
            _press_label(
                data.get("triple_press_target"),
                data.get("triple_press_action", "toggle"),
            ),
            data.get("triple_press_target"),
        ),
        _action(
            labels,
            "hold",
            "action_ramp_alternate" if data["hold_action"] == "ramp" else "action_none",
            target if data["hold_action"] == "ramp" else None,
        ),
        _action(
            labels,
            "release",
            "action_stop_ramp" if data["hold_action"] == "ramp" else "action_none",
        ),
    ]
    state = _worst([item["target_state"] for item in actions])
    return {
        "channel": number,
        "enabled": enabled,
        "configured": True,
        "profile": data["mode"],
        "behaviour": labels[f"mode_{data['mode']}"],
        "target_label": _name(target),
        "target_state": state,
        "target_missing": state == "missing",
        "actions": actions,
        "binding": {"id": f"binding-{number}", "revision": "r1", "data": data},
    }


def _binding(target: str, mode: str = "brightness", **extra) -> dict:
    return {
        "target": target,
        "mode": mode,
        "step": 3,
        "step_curve": "linear",
        "acceleration": 0,
        "min_brightness": 1,
        "max_brightness": 100,
        "transition": 1,
        "click_action": "toggle",
        "button_response": "multi_press",
        "hold_action": "none",
        **extra,
    }


def _snapshot(labels: dict) -> dict:
    button_actions = [
        _action(labels, "short_press", "action_toggle", "light.ceiling"),
        _action(labels, "double_press", "action_toggle", "light.attic"),
        _action(labels, "hold", "action_none"),
        _action(labels, "release", "action_none"),
    ]
    return {
        "contract_version": CONTRACT_VERSION,
        "matter_connected": True,
        "event_source": "core_matter_client",
        "wheels": [
            {
                "key": "wheel-living",
                "variant": "wheel",
                "name": "Living room wheel",
                "area": "Living room",
                "availability": "connected",
                "linked_to_matter": True,
                "last_activity": "2026-01-01T18:00:00+00:00",
                "last_active_channel": 1,
                "last_active_button": None,
                "channels": [
                    _channel(
                        labels,
                        1,
                        _binding("light.counter", hold_action="ramp"),
                    ),
                    _channel(
                        labels,
                        2,
                        _binding(
                            "light.ceiling_bulb",
                            click_target="light.ceiling",
                            double_press_target="script.good_night",
                            double_press_action="on",
                            triple_press_target="scene.movie",
                            triple_press_action="on",
                        ),
                    ),
                    _channel(
                        labels,
                        3,
                        _binding(
                            "light.reading_lamp",
                            scenes=["scene.evening", "scene.movie", "scene.bright"],
                        ),
                    ),
                ],
                "buttons": [],
                "settings": {
                    "subentry_id": "settings-1",
                    "revision": "r1",
                    "step": 2,
                    "acceleration": 0,
                },
            },
            {
                "key": "wheel-bedroom",
                "variant": "wheel",
                "name": "Bedroom wheel",
                "area": "Bedroom",
                "availability": "connected",
                "linked_to_matter": True,
                "last_activity": None,
                "last_active_channel": None,
                "last_active_button": None,
                "channels": [
                    _channel(labels, 1, _binding("media_player.speaker", "volume")),
                    _channel(labels, 2, None),
                    _channel(labels, 3, None, enabled=False),
                ],
                "buttons": [],
                "settings": None,
            },
            {
                "key": "button-hall",
                "variant": "dual_button",
                "name": "Hall button",
                "area": "Hall",
                "availability": "connected",
                "linked_to_matter": True,
                "last_activity": "2026-01-01T17:00:00+00:00",
                "last_active_channel": None,
                "last_active_button": 2,
                "channels": [],
                "buttons": [
                    {
                        "button": 1,
                        "configured": True,
                        "behaviour": labels["button_actions"],
                        "target_label": labels["multiple_targets"].format(count=2),
                        "target_state": "missing",
                        "target_missing": True,
                        "actions": button_actions,
                        "binding": {
                            "id": "binding-b1",
                            "revision": "r1",
                            "data": {
                                "click_action": "toggle",
                                "button_response": "multi_press",
                                "click_target": "light.ceiling",
                                "double_press_target": "light.attic",
                                "hold_action": "none",
                                "ramp_direction": "alternate",
                            },
                        },
                    },
                    {
                        "button": 2,
                        "configured": False,
                        "behaviour": None,
                        "target_label": None,
                        "target_state": "ok",
                        "target_missing": False,
                        "actions": [],
                        "binding": None,
                    },
                ],
                "settings": None,
            },
        ],
    }


# Inter, the typeface of the warm theme; the default theme ignores it.
FONT = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap"

PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BILRESA panel preview</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="__FONT__" rel="stylesheet">
<style>
  html, body { margin: 0; }
  body {
    font-family: Roboto, "Segoe UI", system-ui, sans-serif;
    display: flex;
    align-items: flex-start;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    /* Home Assistant's default theme tokens, light. */
    --primary-color: #03a9f4;
    --primary-text-color: #141414;
    --secondary-text-color: #5e5e5e;
    --text-primary-color: #ffffff;
    --primary-background-color: #fafafa;
    --card-background-color: #ffffff;
    --ha-card-background: #ffffff;
    --divider-color: rgba(0, 0, 0, 0.12);
    --error-color: #db4437;
    --success-color: #43a047;
    --state-icon-color: #44739e;
    --app-header-background-color: #03a9f4;
    --app-header-text-color: #ffffff;
    --ha-card-border-radius: 12px;
    --ha-card-border-width: 1px;
    --ha-card-border-color: rgba(0, 0, 0, 0.12);
  }
  body.dark {
    --primary-text-color: #e1e1e1;
    --secondary-text-color: #9b9b9b;
    --primary-background-color: #111111;
    --card-background-color: #1c1c1c;
    --ha-card-background: #1c1c1c;
    --divider-color: rgba(225, 225, 225, 0.12);
    --ha-card-border-color: rgba(225, 225, 225, 0.12);
    --app-header-background-color: #101e24;
    --app-header-text-color: #e1e1e1;
  }
  /* A warm custom theme: white header, beige page, brown accent, 20 px cards,
     Inter. Close to the community theme the owner uses, not a copy of it. */
  body.warm {
    font-family: Inter, system-ui, sans-serif;
    --ha-font-family-body: Inter, system-ui, sans-serif;
    --primary-color: #856529;
    --primary-text-color: #33270b;
    --secondary-text-color: #716345;
    --text-primary-color: #fafaf9;
    --primary-background-color: #eeebe5;
    --secondary-background-color: #e7e2d8;
    --card-background-color: #ffffff;
    --ha-card-background: #ffffff;
    --divider-color: #e4ddcf;
    --error-color: #7c2f2c;
    --success-color: #245a1e;
    --state-icon-color: #716345;
    --app-header-background-color: #ffffff;
    --app-header-text-color: #33270b;
    --ha-card-border-radius: 20px;
    --ha-card-border-color: #e4ddcf;
    --ha-border-radius-md: 12px;
    --ha-border-radius-lg: 12px;
  }
  body.warm.dark {
    --primary-color: #cebb9c;
    --primary-text-color: #ede7dc;
    --secondary-text-color: #b9ae99;
    --text-primary-color: #12100d;
    --primary-background-color: #120e06;
    --secondary-background-color: #19140a;
    --card-background-color: #1d1913;
    --ha-card-background: #1d1913;
    --divider-color: #35322a;
    --error-color: #f9cfcb;
    --success-color: #cae3c6;
    --state-icon-color: #b9ae99;
    --app-header-background-color: #1d1913;
    --app-header-text-color: #ede7dc;
    --ha-card-border-color: #35322a;
  }
  #sidebar {
    position: sticky;
    top: 0;
    flex: 0 0 256px;
    height: 100vh;
    box-sizing: border-box;
    padding: 16px;
    border-right: 1px solid var(--divider-color);
    background: var(--card-background-color);
    color: var(--secondary-text-color);
    font-size: 14px;
  }
  /* Stands in for ha-panel-custom: the element a theme may pad. */
  #frame { flex: 1 1 auto; min-width: 0; background: var(--primary-background-color); }
</style>
</head>
<body>
<aside id="sidebar">Home Assistant</aside>
<div id="frame"></div>
<script>
const LABELS = __LABELS__;
const SNAPSHOTS = __SNAPSHOTS__;
const SCHEMA = __SCHEMA__;
const STATES = __STATES__;
</script>
<script type="module">
__PANEL_JS__
</script>
<script type="module">
const params = new URLSearchParams(location.search);
const lang = params.get("lang") === "cs" ? "cs" : "en";
// The instance language; `lang` is the viewing user's.
const instance = params.get("instance") === "cs" ? "cs" : lang;
document.documentElement.lang = lang;
if (params.get("dark")) document.body.classList.add("dark");
if (params.get("theme") === "warm") document.body.classList.add("warm");
const narrow = Boolean(params.get("narrow"));
if (narrow) document.getElementById("sidebar").remove();
const frame = document.getElementById("frame");
if (params.get("inset")) frame.style.padding = `${Number(params.get("inset"))}px`;
const calls = [];
window.__calls = calls;
const hass = {
  language: lang,
  dockedSidebar: narrow ? "always_hidden" : "docked",
  states: STATES,
  callWS: async (message) => {
    calls.push(message);
    if (message.type === "ikea_bilresa/overview") {
      return structuredClone(SNAPSHOTS[message.language || instance]);
    }
    return { ok: true };
  },
  connection: {
    subscribeMessage: async (callback, message) => {
      calls.push(message);
      window.__push = callback;
      return () => undefined;
    },
  },
};
const panel = document.createElement("ikea-bilresa-panel");
panel.panel = {
  config: {
    language: instance,
    labels: LABELS[instance],
    labels_by_language: LABELS,
    schema: SCHEMA,
  },
};
panel.narrow = narrow;
if (params.get("open")) {
  panel._open = params.get("open");
  panel._view = params.get("view") || "channels";
}
frame.appendChild(panel);
panel.hass = hass;
window.__panel = panel;
const edit = Number(params.get("edit"));
if (edit && params.get("open")) {
  const started = Date.now();
  const timer = setInterval(() => {
    const wheel = panel._snapshot?.wheels.find((item) => item.key === panel._open);
    if (wheel) {
      clearInterval(timer);
      const controls = panel._controlsFor(wheel);
      const control = controls.find(
        (item) => panel._controlNumber(wheel, item) === edit,
      );
      if (wheel.variant === "dual_button") panel._openButton = edit;
      else panel._openChannel = edit;
      if (control) panel._startEditor(wheel, control);
    } else if (Date.now() - started > 3000) {
      clearInterval(timer);
    }
  }, 30);
}
</script>
</body>
</html>
"""


def main() -> None:
    states = {
        entity_id: {
            "entity_id": entity_id,
            "state": state,
            "attributes": {"friendly_name": name},
        }
        for entity_id, (state, name) in ENTITIES.items()
    }
    html = (
        PAGE.replace("__LABELS__", json.dumps(STRINGS, ensure_ascii=False))
        .replace(
            "__SNAPSHOTS__",
            json.dumps(
                {language: _snapshot(labels) for language, labels in STRINGS.items()},
                ensure_ascii=False,
            ),
        )
        .replace("__SCHEMA__", json.dumps(panel_schema()))
        .replace("__STATES__", json.dumps(states, ensure_ascii=False))
        .replace("__FONT__", FONT)
        .replace("__PANEL_JS__", PANEL_JS)
    )
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    print(f"written {out / 'index.html'} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
