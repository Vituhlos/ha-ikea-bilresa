# IKEA BILRESA (smooth scroll) for Home Assistant

**English** · [Čeština](README.cs.md)

[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![release](https://img.shields.io/github/v/release/Vituhlos/ha-ikea-bilresa)](https://github.com/Vituhlos/ha-ikea-bilresa/releases)
[![license](https://img.shields.io/github/license/Vituhlos/ha-ikea-bilresa)](LICENSE)

Make the **IKEA BILRESA scroll wheel** (Matter over Thread) feel smooth again —
the way it does on IKEA's own DIRIGERA hub — by reacting to the wheel's
**real-time `MultiPressOngoing` events**, which Home Assistant's built-in Matter
integration currently drops.

> **Status:** latest stable release v0.5.0; prerelease v0.5.7-rc.3 passed its
> exact-revision Linux CI. Newer runtime polish has also passed static checks
> and exact-revision Linux Unit/CI; it is not released, deployed, or
> hardware-verified yet.

> **Development handoff:** current implementation state, validation level, and
> prioritized backlog live in [PROJECT_STATUS.md](PROJECT_STATUS.md). The shared
> workflow is documented in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).
> The ordered patch release train is in [docs/ROADMAP.md](docs/ROADMAP.md).

---

## Table of contents

- [Why this exists](#why-this-exists)
- [Features](#features)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Installation](#installation)
- [Setup](#setup)
- [Usage](#usage) — the manual
  - [Event entities](#event-entities)
  - [Event reference](#event-reference)
  - [Example automations](#example-automations)
  - [The `ikea_bilresa_event` bus event](#the-ikea_bilresa_event-bus-event)
- [Multiple wheels](#multiple-wheels)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Limitations](#limitations)
- [Contributing](#contributing)
- [License](#license)

## Why this exists

The BILRESA presents itself over Matter as a **Generic Switch** with multi-press
events. Home Assistant's Matter integration only surfaces `MultiPressComplete` —
it waits until you *stop* scrolling and then delivers a single batched "N
presses" event, capped at 8. The result is laggy, jumpy dimming, and fast
scrolls beyond 8 notches are lost entirely.

The device **also** emits `MultiPressOngoing` events — a running counter, in real
time, while you turn the wheel — which is exactly what makes the DIRIGERA hub
feel continuous. This integration subscribes to Home Assistant's existing Matter
client event stream, so Home Assistant can react per gesture as it happens. On
an older or incompatible client API it falls back to its own read-only
WebSocket.

Related upstream work:
[core#159035 (issue)](https://github.com/home-assistant/core/issues/159035) ·
[core#159045 (PR)](https://github.com/home-assistant/core/pull/159045).

## Features

- ⚡ **Real-time scrolling** — reacts to `MultiPressOngoing` while you turn the
  wheel, not only after you stop.
- 🔢 **Correct notch counting** — a gesture engine converts the wheel's
  cumulative, batched counter into per-event **notch deltas** (up to 18 per
  gesture), so brightness moves by the right amount.
- 🧭 **Automatic discovery of any number of wheels** — channels and directions
  are read from each wheel's own Matter descriptors; nothing is hard-coded.
- 🎛️ **Clean events** — `rotate_up` / `rotate_down` (with a `notches` count),
  `press` / `double_press` / `triple_press`, `hold`, `release`.
- 🪶 **No extra dependencies** — a tiny `aiohttp` WebSocket client, nothing to
  install or break on upgrades.
- 🛡️ **Safe & passive** — it only *listens*; it never sends commands to devices,
  so it cannot interfere with the core Matter integration.

## How it works

```
BILRESA wheel ──Matter/Thread──▶ Matter Server ──WS──▶ this integration ──▶ event entities
                                                                          └▶ ikea_bilresa_event
```

The integration normally reuses the core Matter integration's existing
`MatterClient` subscription. Its compatibility fallback connects to the Matter
Server WebSocket (`ws://core-matter-server:5580/ws` by default), issues a single
`start_listening`, and decodes `Switch` cluster events (cluster `0x003B`) for
every discovered BILRESA node.

Each wheel exposes **3 channels**, each of which is 3 Matter Switch endpoints:

| Role | Matter capabilities |
|------|---------------------|
| Scroll ↑ / ↓ (rotary) | MomentarySwitch + Release + MultiPress, `MultiPressMax = 18` |
| Button (press) | + LongPress, `MultiPressMax = 3` |

## Requirements

- Home Assistant **2026.6** or newer.
- The **Matter Server** add-on (or an external Matter Server), with your BILRESA
  wheel(s) already commissioned to Matter and working.
- The core **Matter** integration configured (used to auto-detect the server
  URL; the BILRESA can be paired to Home Assistant and/or Apple Home).

## Installation

### HACS (recommended)

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/Vituhlos/ha-ikea-bilresa`, category **Integration**.
2. Install **IKEA BILRESA**.
3. **Restart Home Assistant.**

### Manual

Copy `custom_components/ikea_bilresa/` into your Home Assistant
`config/custom_components/` folder and restart.

## Setup

**Settings → Devices & Services → Add Integration → IKEA BILRESA.**
Confirm the pre-filled Matter Server URL (change it only if you run the Matter
Server elsewhere). The integration discovers all BILRESA wheels automatically and
creates one device per wheel with an event entity per channel.

### GUI control bindings (turnkey control)

Prefer not to write automations? On the **IKEA BILRESA** entry
(Settings → Devices & Services) click **＋ Add → Control binding** and pick:

- a starting profile (light, media, cover, climate, scenes, or custom), or copy
  an existing binding as a starting point,
- the **Wheel** and **Channel** to use,
- the **target entity** controlled by scrolling,
- **Brightness change per notch** (%), **Minimum brightness** (%, `0` lets a
  downward scroll switch the light off) and **Transition** (s),
- the **single-press action** (toggle / on / off / nothing) and an optional
  **button target entity** — so a press can act on a *different* entity than the
  dimmed light (e.g. dim a bulb, but toggle its Shelly wall switch),
- the **button response**: fast single press for immediate direct control, or
  exact single/double/triple recognition for multi-press bindings,
- an optional ordered list of **scenes** to cycle on single presses (this takes
  precedence over the normal single-press action),
- the **hold action**: toggle an entity, continuously ramp the scroll target,
  or do nothing. Hold-to-ramp starts upward and alternates direction after each
  completed hold because the BILRESA long-press event carries no direction.

For responsive lighting, select **Fast single press** to run that binding's
single-press action as soon as the button is released. Select multi-press
recognition when the binding uses double/triple targets; it waits for the
BILRESA completion event. Existing bindings without this setting retain the
completion-aware behavior until explicitly changed. Public event entities and
device triggers keep exact single/double/triple classification in either mode.

The integration then dims that light in real time. Add as many bindings as you
like — one per wheel channel — so this scales to any number of wheels with no
YAML. A binding sends no command while its target is missing, unknown or
unavailable; hold-to-ramp stops safely and the next action resynchronizes from
the recovered entity's real state. Rotate-up from an off light starts at the
configured minimum (or one usable step when the minimum is zero). External HA
changes rebase the next wheel action, while direction reversal during a
transition continues from the last requested value.

Acceleration, when enabled, is based on decoded notches per elapsed time rather
than the size of one Matter batch. It resets after idle, direction changes,
gesture completion and reconnect; the default remains disabled until physical
tuning is complete. Post-press protection likewise follows gesture boundaries,
so an old trailing batch cannot undo a button action but a deliberate new
rotation is accepted immediately.

## Usage

This section documents the current integration behavior. Features ahead of the
latest release are identified in [PROJECT_STATUS.md](PROJECT_STATUS.md).

### Event entities

Each wheel channel becomes an `event` entity, e.g.
`event.bilresa_scroll_wheel_channel_1`. Its state is the timestamp of the
last action; the `event_type` attribute (and `notches` / `presses`) tells you
what happened. Use it as the primary automation trigger. These entities use
Home Assistant's button event device class; the compatibility domain event also
includes registry `device_id` when available.

### Event reference

| `event_type` | Meaning | Extra attribute |
|--------------|---------|-----------------|
| `rotate_up` | Scrolled up by *N* notches | `notches` |
| `rotate_down` | Scrolled down by *N* notches | `notches` |
| `press` | Single button press | `presses` = 1 |
| `double_press` | Double press | `presses` = 2 |
| `triple_press` | Triple press | `presses` = 3 |
| `hold` | Button long-pressed | — |
| `release` | Button released after a hold | — |

### Example automations

**Smooth dimming** — step brightness by the notch count, with a transition so
the light ramps between the wheel's ~1 s batches:

```yaml
alias: BILRESA – smooth dim up
triggers:
  - trigger: state
    entity_id: event.bilresa_scroll_wheel_channel_1
    attribute: event_type
    to: rotate_up
conditions:
  - "{{ trigger.to_state.attributes.event_type == 'rotate_up' }}"
actions:
  - action: light.turn_on
    target:
      entity_id: light.example
    data:
      brightness_step_pct: "{{ trigger.to_state.attributes.notches * 3 }}"
      transition: 1
mode: parallel
max: 20
```

Duplicate with `rotate_down` and a negative step for dimming down, and add a
`press` trigger calling `light.toggle` for the button.

### The `ikea_bilresa_event` bus event

Every action is also fired on the event bus as `ikea_bilresa_event` — handy for a
single automation that handles several wheels. Payload fields: `node_id`,
`wheel_name`, `channel`, `endpoint_id`, `type` (`rotate` / `press` / `hold` /
`release`), `direction` (`up` / `down`), `notches`, `presses`.

```yaml
triggers:
  - trigger: event
    event_type: ikea_bilresa_event
    event_data:
      type: rotate
```

## Multiple wheels

Everything is keyed by Matter node and endpoint, so **any number of wheels** work
at once with no configuration — each is discovered and gets its own device,
entities and events. The `node_id` / `wheel_name` / `channel` fields let you tell
them apart in automations.

## Troubleshooting

**Enable debug logging** (Settings → System → Logs, or):

```yaml
logger:
  logs:
    custom_components.ikea_bilresa: debug
```

- **No wheels discovered** — confirm the wheel works in the core Matter
  integration and that the Matter Server URL is correct. The log prints
  `Discovered BILRESA wheel: node …` on startup.
- **No events when scrolling** — check the wheel's battery and that the core
  Matter `event.*` entities update when you scroll.
- **Wrong channel** — the physical wheel has a 3-position channel selector; the
  active channel is what fires.

## Roadmap

- [x] Real-time listener, wheel auto-discovery, `ikea_bilresa_event`. *(0.1)*
- [x] Gesture engine, `event` entities, per-wheel devices, clean actions. *(0.2)*
- [x] **GUI light bindings** (config subentries) — map a wheel channel to a light
      and let the integration drive brightness directly, no YAML. *(0.3)*
- [x] Minimum-brightness floor and a separate button target entity. *(0.4)*
- [x] CI, unit tests and diagnostics. *(0.5)*
- [x] Hot add/remove of wheels, connection health/Repairs, in-place binding
      updates. *(next)*
- [x] Scroll modes (brightness / colour temperature / colour), acceleration,
      maximum brightness, double/triple/hold actions. *(next)*
- [x] **Device triggers** and a **smooth-dimming blueprint**. *(next)*
- [x] Scene cycling, hold-to-ramp and System Health information. *(next)*
- [x] Parent Matter Server URL reconfiguration. *(next)*
- [x] Discovery feasibility reviewed — no supported dependency-discovery source;
      decision documented in [docs/DISCOVERY.md](docs/DISCOVERY.md). *(next)*
- [x] Internal `quality_scale.yaml` with only evidenced `done`/`exempt` rules.
- [x] Reuse the core Matter client event stream, with a compatibility fallback
      to the dedicated passive WebSocket. *(next)*
- [x] Plan the small-patch `0.5.1`–`0.5.7` stabilization train; implementation
      exists in the working tree, but each package keeps its own validation gate.
- [ ] Complete hardware validation and automated coverage.
- [ ] **Final publication stage:** brand icon/`home-assistant/brands` PR and
      default HACS-store submission, only after the integration is finished.

## Limitations

- The wheel has a built-in ~500 ms–1 s anti-flood delay between notch batches, so
  this gets *close* to the DIRIGERA feel but is not truly analog-continuous. A
  matching `transition` on the light bridges the batches for a smooth ramp.
- Target lights round-trip through Home Assistant (rather than a direct
  Matter/Zigbee bind), adding small, usually imperceptible LAN latency.

## Contributing

Issues and pull requests are welcome. Please describe your wheel firmware and
Home Assistant / Matter Server versions when reporting a problem, and include a
debug log of the events if it concerns scrolling behaviour. Development and
hardware-validation procedures are in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
and [docs/HARDWARE_TEST.md](docs/HARDWARE_TEST.md).

## License

[MIT](LICENSE) © 2026 Vituhlos
