# Documentation

**English** · **Čeština**

## Guides for users

The same six guides exist in English and in Czech.

| Guide | English | Čeština |
|---|---|---|
| Getting started | [Getting started](en/getting-started.md) | [Začínáme](cs/getting-started.md) |
| The BILRESA panel | [The BILRESA panel](en/panel.md) | [Panel BILRESA](cs/panel.md) |
| Control bindings | [Control bindings](en/bindings.md) | [Ovládací propojení](cs/bindings.md) |
| Events, entities and automations | [Events, entities and automations](en/events-and-automations.md) | [Události, entity a automatizace](cs/events-and-automations.md) |
| Troubleshooting | [Troubleshooting](en/troubleshooting.md) | [Řešení potíží](cs/troubleshooting.md) |
| How it works, limits and roadmap | [How it works, limits and roadmap](en/how-it-works.md) | [Jak to funguje, omezení a plán](cs/how-it-works.md) |

The [README](../README.md) is the short overview ([česky](../README.cs.md)), and
the [CHANGELOG](../CHANGELOG.md) lists every release.

## Notes for developers and testers

These are written in English and are working documents: some are plans or
proposals and keep the wording they were written in, and say so at their top.
The live state of the project is in [PROJECT_STATUS.md](../PROJECT_STATUS.md).

| Document | What it is |
|---|---|
| [Development workflow](DEVELOPMENT.md) | How to run the checks, review and release. |
| [Hardware test checklist](HARDWARE_TEST.md) | What has and has not been checked on real devices. |
| [Scroll wheel device reference](DEVICE_REFERENCE.md) | What the wheel sends over Matter. |
| [Dual button device reference](DEVICE_REFERENCE_BUTTON.md) | What the dual button (E2489) sends. |
| [Matter.js Server compatibility](MATTERJS_COMPATIBILITY.md) | Behaviour with the Matter.js Server. |
| [Scroll performance decision](SCROLL_PERFORMANCE.md) | The evidence behind how scrolling is handled (batches and deltas). |
| [Discovery decision](DISCOVERY.md) | Why Home Assistant cannot offer the integration automatically. |
| [Discovering a target's usable range](TARGET_RANGE_DISCOVERY.md) | A proposal, not implemented, for reading a target's usable range. |
| [Advanced BILRESA controls](ADVANCED_GESTURES.md) | An ordered implementation contract for gestures beyond the basics. |
| [Device registry plan](DEVICE_REGISTRY_PLAN.md) | One device per wheel, compatible with Home Assistant 2027. |
| [BILRESA panel product design](PANEL_DESIGN.md) | Design of the panel. |
| [Panel implementation roadmap](PANEL_ROADMAP.md) | How the panel was built. |
| [Panel polish plan](PANEL_POLISH_PLAN.md) | Making the editor a Home Assistant editor. |
| [Stabilization roadmap](ROADMAP.md) | The original `0.5.x` plan (historical). |
| [Dual button roadmap](ROADMAP_BUTTON.md) | The work packages for the dual button. |
| [Runtime behaviour polish roadmap](RUNTIME_POLISH_ROADMAP.md) | The behaviour fixes before the panel. |
| [Latency roadmap](LATENCY_ROADMAP.md) | Latency, telemetry and Matter recovery. |
| [v0.6.0 checklist](V0.6.0_CHECKLIST.md) | The readiness checklist of `v0.6.0`. |
| [Project status history](archive/PROJECT_STATUS_HISTORY_2026-10-25.md) | The handoff log up to 2026-10-25. |
