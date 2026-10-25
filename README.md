# IKEA BILRESA for Home Assistant

**English** · [Čeština](README.cs.md)

[![release](https://img.shields.io/github/v/release/Vituhlos/ha-ikea-bilresa)](https://github.com/Vituhlos/ha-ikea-bilresa/releases)
[![CI](https://github.com/Vituhlos/ha-ikea-bilresa/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Vituhlos/ha-ikea-bilresa/actions/workflows/ci.yml)
[![stars](https://img.shields.io/github/stars/Vituhlos/ha-ikea-bilresa)](https://github.com/Vituhlos/ha-ikea-bilresa/stargazers)
[![license](https://img.shields.io/github/license/Vituhlos/ha-ikea-bilresa)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/use/custom_repositories/)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.8.0%2B-41BDF5)

Responsive, GUI-configurable control for the **IKEA BILRESA scroll wheel and
dual button** (Matter over Thread). The wheel processes real-time
`MultiPressOngoing` events to react during rotation — not only after you stop.
The physical remote still reports scroll input in batches, so this is
responsive stepped control rather than truly analog-continuous scrolling. The
dual button gains independent event entities, control bindings, automation
triggers and the same BILRESA panel.

If this integration saves you time, you can support its development. It is entirely optional.

<a href="https://buymeacoffee.com/Vituhlos"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" height="40"></a>

> **Status:** latest stable release **v0.6.1**, which is 0.6.0 plus a fix: the
> panel now speaks the language each user chose in their profile. The 0.6 line
> adds the BILRESA dual button, the BILRESA panel, more binding targets and
> automation triggers for every gesture. It needs Home Assistant 2026.8 or newer
> and replaces the old device triggers; read the upgrade notes in
> [CHANGELOG.md](CHANGELOG.md) and take a backup before upgrading from 0.5.x.
>
> **Testing status:** the pre-release `v0.7.0-rc.3` carries a redesigned panel
> layout and binding editor that are not in the stable release, together with the fixes of
> `v0.6.2-rc.2` (Zigbee2MQTT light groups, the `short_release` event, disabled
> channels). It is a test candidate, not hardware-validated. Hardware validation is incomplete for some
> device/gesture combinations; see [docs/HARDWARE_TEST.md](docs/HARDWARE_TEST.md)
> for the current checklist.

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
  - [Immediate short-release actions](#immediate-short-release-actions)
- [Multiple wheels](#multiple-wheels)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Limitations](#limitations)
- [Community tools](#community-tools)
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
- 🧭 **Automatic discovery of any number of BILRESA devices** — wheels and dual
  buttons are distinguished from their Matter endpoint shape; nothing is
  hard-coded to a product name or installation.
- 🎛️ **Clean events** — `rotate_up` / `rotate_down` (with a `notches` count),
  `press` / `double_press` / `triple_press`, `hold`, `release` for a wheel;
  button 1/2 expose `press`, `double_press`, `hold`, `release`.
- 🔘 **Independent dual-button bindings** — each button can toggle a different
  target, or a shared light can use fixed brighten/dim hold directions.
- 🪶 **No extra dependencies** — a tiny `aiohttp` WebSocket client, nothing to
  install or break on upgrades.
- 🛡️ **Safe & passive** — it only *listens*; it never sends commands to devices,
  so it cannot interfere with the core Matter integration.

## How it works

```
BILRESA wheel / dual button ──Matter/Thread──▶ Matter Server ──WS──▶ this integration
                                                                    ├▶ event entities
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

The E2489 dual button exposes two button-only endpoints with no channel labels.
Each becomes a separate Button 1/2 event entity and supports single press,
double press, hold and release (`MultiPressMax = 2`).

## Requirements

- Home Assistant **2026.8** or newer.
- The **Matter Server** add-on (or an external Matter Server), with your BILRESA
  wheel(s) already commissioned to Matter and working.
- The core **Matter** integration configured (used to auto-detect the server
  URL; the BILRESA can be paired to Home Assistant and/or Apple Home).
- A Thread network that the Matter integration can reach, because the BILRESA
  is a Matter-over-Thread device.

### Compatibility

The integration works with BILRESA devices that Home Assistant already sees
through its **Matter** integration. What matters is how the *remote* reaches
Home Assistant, which is separate from what it *controls*.

| How it is used | Status | Evidence |
|---|---|---|
| Wheel (E2490) and dual button (E2489) paired to a Matter Server and Home Assistant's core Matter integration | **Supported** | The integration subscribes to the core Matter client's event stream (`matter` is a dependency in `manifest.json`). Recorded hardware runs on firmware 1.9.15 used this path ([HARDWARE_TEST.md](docs/HARDWARE_TEST.md), [DEVICE_REFERENCE.md](docs/DEVICE_REFERENCE.md)); validation of some gestures is still open. |
| Read-only WebSocket to the Matter Server, the fallback when the core client API is unavailable | **Supported in code, not verified on hardware** | The checklist items for the fallback in [HARDWARE_TEST.md](docs/HARDWARE_TEST.md) are open. |
| Remote paired through **ZHA** | **Unsupported** | The integration has no ZHA code path; it reads Matter events only. |
| Remote paired through **Zigbee2MQTT** | **Unsupported** | There is no MQTT or Zigbee2MQTT code path. |
| Lights or other entities on **ZHA or Zigbee2MQTT** as the *targets* of a binding | **Supported by design, not verified for groups** | A target is any Home Assistant entity of a supported domain, whichever integration provides it. Fixes for Zigbee2MQTT light groups are in the test candidates; the reporter's confirmation is pending ([issue #9](https://github.com/Vituhlos/ha-ikea-bilresa/issues/9)). |
| The remote also paired to another Matter controller (for example Apple Home) | **Not verified** | A Matter device can be commissioned to several fabrics ([DEVICE_REFERENCE.md](docs/DEVICE_REFERENCE.md)); it has not been tested with this integration. |

"Supported" means shown by the code and recorded runs, not that every gesture
and configuration is validated.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Vituhlos&repository=ha-ikea-bilresa&category=integration)

Or add it manually:

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/Vituhlos/ha-ikea-bilresa`, category **Integration**.
2. Install **IKEA BILRESA**.
3. **Restart Home Assistant.**

The integration is not in the default HACS store yet — the custom-repository
step above is required. Upgrading from 0.5.x has breaking changes; read the
[CHANGELOG.md](CHANGELOG.md) and take a backup first.

### Manual

Copy `custom_components/ikea_bilresa/` into your Home Assistant
`config/custom_components/` folder and restart.

## Setup

**Settings → Devices & Services → Add Integration → IKEA BILRESA.**
Confirm the pre-filled Matter Server URL (change it only if you run the Matter
Server elsewhere). The integration discovers all supported BILRESA devices
automatically. A wheel gets an event entity per channel; a dual button gets one
per physical button.

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
- the **button response**: instant initial press, fast short release, or exact
  single/double/triple recognition for multi-press bindings,
- an optional ordered list of **scenes** to cycle on single presses (this takes
  precedence over the normal single-press action),
- the **hold action**: toggle an entity, continuously ramp the scroll target,
  or do nothing. Hold-to-ramp starts upward and alternates direction after each
  completed hold because the BILRESA long-press event carries no direction.

For the lowest direct-control latency, select **Instant initial press**. Because
the initial event cannot yet know whether the gesture will become a double
press or hold, Instant is accepted only when those separate actions are
disabled. **Fast release** runs after the first short release and remains safe
for a normal hold; multi-press aware waits for the BILRESA completion event.
Existing bindings without this setting retain the completion-aware behavior
until explicitly changed. A disabled channel runs no binding in any of these
modes. Public event entities and triggers keep exact
single/double/triple classification in every mode.

The integration then dims that light in real time. Add as many bindings as you
like — one per wheel channel — so this scales to any number of wheels with no
YAML. A binding sends no command while its target is missing, unknown or
unavailable; hold-to-ramp stops safely and the next action resynchronizes from
the recovered entity's real state. Rotate-up from an off light starts at the
configured minimum (or one usable step when the minimum is zero). External HA
changes rebase the next wheel action, while direction reversal during a
transition continues from the last requested value.

For a dual button, the same flow first selects Button 1 or Button 2 and then
shows only supported actions: independent single/double-press targets and
hold/release. There are no rotary, scene or triple-press fields. A hold ramp can
alternate direction or stay fixed to brighten/dim, so two buttons can form a
software DIRIGERA-style pair for one light.

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

### Triggers

The integration provides one automation trigger per gesture. In the automation
editor, pick the wheel (or one of its `Channel` entities) as the target and
choose the trigger:

| Trigger | Fires when |
|---------|------------|
| `ikea_bilresa.rotated_up` | a channel is scrolled up |
| `ikea_bilresa.rotated_down` | a channel is scrolled down |
| `ikea_bilresa.pressed` | a button is pressed once |
| `ikea_bilresa.double_pressed` | a button is pressed twice |
| `ikea_bilresa.triple_pressed` | a wheel button is pressed 3 times |
| `ikea_bilresa.held` | a button is held down |
| `ikea_bilresa.released` | a button is released after being held down |

```yaml
triggers:
  - trigger: ikea_bilresa.rotated_up
    target:
      entity_id: event.bilresa_scroll_wheel_channel_1
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

A target that names the whole device covers every channel of that wheel. The
dual button has no rotation and no triple press, so those two triggers never
fire for it.

> **Upgrading from 0.5.x or an earlier 0.6.0 pre-release:** the former *device
> triggers* ("Channel 1 scrolled up" on the device page) were removed. Since
> Home Assistant 2026.8 a device belongs to a single integration, and a device
> trigger only works on a device its own integration owns. Automations that
> still use one are listed under **Settings → System → Repairs**; replace the
> trigger with the matching one above.

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
`release` / `short_release`), `direction` (`up` / `down`), `notches`, `presses`.

```yaml
triggers:
  - trigger: event
    event_type: ikea_bilresa_event
    event_data:
      type: rotate
```

### Immediate short-release actions

For an automation that should react as soon as a short button press is released,
listen to `ikea_bilresa_event` with `type: short_release`, filtered by your wheel's
`node_id` and `channel`. Do not filter on `presses: 1`: the final click count is
not yet known at release time.

```yaml
triggers:
  - trigger: event
    event_type: ikea_bilresa_event
    event_data:
      node_id: 12  # Replace with your wheel's Matter node ID.
      channel: 1
      type: short_release
```

This bus-only event is emitted for each short release, including releases within
a double or triple click. Completed `press` events still follow with the final
count. Replace the automation's completed single-press trigger rather than
adding a second trigger for the same action, or it will run twice. A separate
double-click action can override the early action, but the interim effect will
be visible. Long holds do not emit this event. Existing event entities,
`ikea_bilresa.*` triggers and direct light bindings keep their completed-gesture
behavior; a direct binding that should react on release uses its own
**Button response → Fast release** setting instead. A disabled channel emits no
`short_release` either.

The E2489 dual button has no channel (`channel` is empty), so filter its two
buttons by `endpoint_id` instead. Pressing it more than twice in a row still
emits a `short_release` for each reported release, but no completed `press`
follows (the device ends the sequence with a zero count).

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
- **Connected, but no events when you turn or press** — go in this order:
  1. In **Settings → Devices & Services → Matter**, open the BILRESA device. Do
     its `event.*` entities update when you turn the wheel or press? If not, the
     cause is below this integration (battery, Thread network or border router,
     pairing); fix that first.
  2. Open the BILRESA panel, choose the device and open **Live test**. Turn one
     notch and press once. If rows appear, events reach the integration. If the
     core entities update but the Live test stays empty, go on to step 3.
  3. Open **Diagnostics** in the panel: it shows whether Matter is connected,
     which event source is in use (the core Matter client or the dedicated
     WebSocket) and when the last event arrived. Enable debug logging as above.
  4. Check the channel: the wheel has a 3-position selector and only the
     selected channel sends. A channel switched off in the panel emits nothing
     (its switch is on its card).
  5. Still silent? Open a [bug report](https://github.com/Vituhlos/ha-ikea-bilresa/issues/new/choose) with the Home Assistant Core
     version, the Matter Server version, the device model and firmware, whether
     it is also paired to another controller, what Live test and Diagnostics
     show, and the integration's downloaded diagnostics (**Settings → Devices &
     Services → IKEA BILRESA → ⋮ → Download diagnostics**; it redacts known
     identifiers, but look through it before attaching it).
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
- [x] **Automation triggers** and a **smooth-dimming blueprint**. *(next)*
- [x] Scene cycling, hold-to-ramp and System Health information. *(next)*
- [x] Parent Matter Server URL reconfiguration. *(next)*
- [x] Discovery feasibility reviewed — no supported dependency-discovery source;
      decision documented in [docs/DISCOVERY.md](docs/DISCOVERY.md). *(next)*
- [x] Internal `quality_scale.yaml` with only evidenced `done`/`exempt` rules.
- [x] Reuse the core Matter client event stream, with a compatibility fallback
      to the dedicated passive WebSocket. *(next)*
- [x] Plan the small-patch `0.5.1`–`0.5.7` stabilization train; implementation
      exists in the working tree, but each package keeps its own validation gate.
- [ ] Complete the remaining hardware validation and close the test-coverage
      gaps; see [docs/HARDWARE_TEST.md](docs/HARDWARE_TEST.md) and
      [PROJECT_STATUS.md](PROJECT_STATUS.md) for the current evidence.
- [ ] **Ecosystem publication:** submit the brand icon to
      `home-assistant/brands` and the integration to the default HACS store
      after the remaining validation gates are met. The stable GitHub release
      and custom-repository installation are already available.

## Limitations

- The wheel has a built-in ~500 ms–1 s anti-flood delay between notch batches, so
  this gets *close* to the DIRIGERA feel but is not truly analog-continuous. A
  matching `transition` on the light bridges the batches for a smooth ramp.
- Target lights round-trip through Home Assistant (rather than a direct
  Matter/Zigbee bind), adding small, usually imperceptible LAN latency.

## Community tools

These are made by other people. They are not part of this integration, which neither
depends on them nor sends them any data, and the integration does not maintain or
endorse them; check each project's own terms.

- **[Somrig Inlay Sheet Builder](https://bilresa.marcel1.com/)** — a web tool by a community member for
  designing inlay sheets (labels) for the switches. According to its author it can also
  produce 3D-printable cover models.

## Contributing

Issues and pull requests are welcome — [CONTRIBUTING.md](CONTRIBUTING.md)
explains how to report a bug or propose a feature (there are issue forms for
both), how to run the checks, and when hardware validation is required.
Security reports are covered by [SECURITY.md](SECURITY.md).

For developers and agents: the current implementation state, validation level
and prioritized backlog live in [PROJECT_STATUS.md](PROJECT_STATUS.md), the
canonical workflow is [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), and the
release trains are [docs/ROADMAP.md](docs/ROADMAP.md) and
[docs/ROADMAP_BUTTON.md](docs/ROADMAP_BUTTON.md).

## License

[MIT](LICENSE) © 2026 Vituhlos
