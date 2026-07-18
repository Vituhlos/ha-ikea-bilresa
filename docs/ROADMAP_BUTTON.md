# BILRESA dual button support — work package roadmap

This is the ordered implementation contract for adding **BILRESA dual button**
(IKEA product **E2489**) support to the `ikea_bilresa` integration. It is kept
separate from the scroll-wheel `ROADMAP.md` on purpose: the dual button is a
different device class (buttons only, no rotary channels), and mixing the two
would blur which gates apply to which hardware.

Read this together with `PROJECT_STATUS.md`, `docs/DEVICE_REFERENCE.md`,
`docs/HARDWARE_TEST.md` and `docs/ADVANCED_GESTURES.md`. The validation
vocabulary (Implemented / Static / Unit / CI / Hardware / Released) and the rule
that these states are never collapsed both apply here unchanged.

This document is the implementation contract; the current phase-by-phase
validation state is recorded in `PROJECT_STATUS.md`.

## Why this is its own version train

Adding a second physical device class touches discovery, the entity model, the
binding shape and the panel. Per the versioning policy in `ROADMAP.md`, a
device/config-model expansion of this size is a **minor bump**, not another
`0.5.x` package. This work is therefore scoped to a **`0.6.x`** train and must
not be folded into a `0.5.x` release candidate. The `0.5.x` stabilization gates
(hardware RC for the wheel) stay open and independent.

## Device facts (current knowledge, confirm before building)

Observed for the owner's unit "Tlačítko Obývák" via read-only Home Assistant MCP
on 2026-07-17. These are **HA-surface** facts; the raw Matter facts marked
*(confirm)* must be captured from the Matter Server before Phase B1 (see the
instrumentation note under Phase B4).

- IKEA of Sweden, model `BILRESA dual button`, product **E2489**, Matter vendor
  ID 4476 (`0x117C`), firmware `1.8.5`, hardware `P2.0`.
- Matter over Thread sleepy end device, 2× AAA battery.
- **Two** `GenericSwitch` endpoints (endpoint 1 and 2), Switch cluster `0x003B`.
- HA event entities expose event types `multi_press_1`, `multi_press_2`,
  `long_press`, `long_release` → per button: **single, double, long press**.
- Implied `MultiPressMax = 2` *(confirm)* — the wheel's buttons are 3. So the
  dual button has **no triple press**.
- Implied Switch `FeatureMap = 30` *(confirm)*: MomentarySwitch (bit1),
  MomentarySwitchRelease (bit2), MomentarySwitchLongPress (bit3),
  MomentarySwitchMultiPress (bit4) — same as the wheel's button endpoints.
- Descriptor `TagList`: **no numeric channel label**, but the real device does
  carry the semantic **up/down switch tags** for its two physical buttons.
  This was confirmed by the sanitized diagnostics from the first
  `v0.6.0-rc.1` deployment.

### Firmware quirk to design around

Confirmed in home-assistant/core PR #159045 discussion: pressing a button **more
times than `MultiPressMax`** makes the firmware **stop emitting events** — no
`MultiPressComplete` arrives and the interaction is lost (see also core issue
\#159452). The wheel wraps at 18; the dual button just goes silent past 2. The
button decode path must therefore treat "no completion" as a real terminal state
via a timeout, not wait forever.

## The current defect this work must fix first

`model.parse_node` matches any product whose name contains `"bilresa"`, so the
dual button is already claimed by the integration:

- both endpoints have `channel = None`, but their semantic tags initially decode
  as `ROLE_SCROLL_UP` / `ROLE_SCROLL_DOWN`;
- the node lands in `coordinator.wheels` and gets `("ikea_bilresa", "<node>")`
  device identifiers via `reconcile_wheel_device`;
- but `event.py` builds entities only for `channel is not None`, so the device
  gets **zero** custom entities;
- System Health and the panel then count it as a **wheel with no channels**.

The original invented no-tag fixture allowed this defect to survive B0-B3 and
the first RC deployment. The corrected contract classifies the exact two
channel-less switch endpoints as a dual button and normalizes their semantic
up/down roles to physical-button roles before any downstream consumer sees
them.

## Phases and exit gates

| Package | Scope | Exit gate |
|---|---|---|
| `0.6.0-B0` | Device-variant discovery | Static + Unit + CI; dual button no longer appears as an empty wheel |
| `0.6.0-B1` | Button event entities + device triggers | Static + Unit + CI; **Hardware**: real presses observed |
| `0.6.0-B2` | Button binding profile + config flow | Static + Unit + CI; HA UI + **Hardware** |
| `0.6.0-B3` | Panel presentation for the dual button | Static + Unit + CI; real-HA visual pass |
| `0.6.0-B4` | Hardware verification + reference capture | **Hardware** run recorded in `HARDWARE_TEST.md` |

### B0 — Device-variant discovery (no user-visible feature yet)

- Introduce an explicit device variant on the parsed model, e.g.
  `BilresaWheel.variant ∈ {"wheel", "dual_button"}`, decided from endpoint
  shape: exactly two switch endpoints with **no numeric channel labels** form a
  `dual_button`; the existing endpoints grouped by numeric channels stay
  `wheel`. Do not use up/down semantic tags as evidence of rotation by
  themselves.
- Keep discovery descriptor-driven; do **not** match on the product string
  `E2489`/`E2490`. "BILRESA" is an IKEA range, not a device — match on node shape
  (this is the same lesson recorded for the wheel).
- Represent buttons without a channel: address them by endpoint (or a derived
  1-based button index), since `channel` is `None` for this device.
- Until B1 ships, a `dual_button` variant must **not** be presented as a wheel:
  exclude it from the wheel-channel entity build and from any "wheel" counts in
  System Health, or present it as an explicit "buttons" device with no channels.
- Model/coordinator/System Health unit tests for the new variant. Fixtures must
  use the **real** dual-button node shape (two channel-less endpoints carrying
  the up/down semantic tags), not an invented one — the first RC failure and
  the wheel's panel-model bugs both came from fixtures that agreed with the code
  instead of the device.

### B1 — Button event entities and device triggers

- A per-button event entity (`event.py`) with button-appropriate event types:
  `press`, `double_press`, `hold`, `release`. **No** `rotate_up`/`rotate_down`
  and **no** `triple_press` for a `MultiPressMax = 2` device — advertise only
  what the endpoint's `MultiPressMax` supports, read from the attribute rather
  than assumed.
- Reuse the existing gesture engine for press-count and hold/release; add the
  timeout-terminal handling for the "past-max goes silent" quirk so a button
  never gets stuck mid-gesture.
- Device triggers (`device_trigger.py`) for the button gestures, so automations
  can be built from the device page — this is the exact gap HA core has open in
  issue #158789, and we can close it locally ahead of core.
- Naming/localization: button labels in `panel_strings.py`, EN/CS aligned, held
  by `test_panel_strings`.

### B2 — Button binding profile and config flow

Implementation decision (2026-07-17): wheel bindings keep their stored
`(node_id, channel)` address. A dual-button binding instead stores
`CONF_NODE_ID` plus `CONF_ENDPOINT` and is keyed at runtime as
`(node_id, "endpoint", endpoint_id)`. The action and raw-button dispatcher
signals remain shared at `signal_channel(node, None)` /
`signal_raw_button(node, None)`, but every button binding filters the action's
endpoint before it can run. The node component separates any number of physical
dual buttons; the endpoint component separates the two buttons on each device.
The channel and endpoint key spaces are explicitly tagged, so a wheel channel
number can never alias a button endpoint number.

- A button-only binding: `click_action` / `double_press_target` /
  `hold_action` / `hold_target`, **without** a scroll `mode`. Most fields already
  exist in `const.py`; the flow just omits rotary-only options for this variant.
- Optional "software DIRIGERA" convenience: because IKEA does **not** implement
  Matter bindings, offer a hold-ramp direction of `up`, `down`, or `alternate`.
  Two independent endpoint bindings can therefore share a light target while
  button 1 always ramps up and button 2 always ramps down. This reuses the
  wheel's release/reconnect/new-gesture stops and lost-release watchdog.
- Config-flow validation and copy-from-existing, mirroring the wheel binding,
  with the incompatible rotary options hidden rather than rejected after entry.

### B3 — Panel presentation

- The panel must render a `dual_button` device as **two buttons**, not three
  channels — no rotary controls or detent strip. Keep the existing `Live test`
  view, adapted to report button 1/2 short press, double press, hold, release
  and the resulting binding outcome. Reuse the existing
  detail shell **and the existing workbench composition**: the wheel's numbered
  `1 / 2 / 3` spine becomes a numbered `1 / 2` button spine, with one selected
  control rendered in the same right-hand action surface. Do not introduce a
  second panel design or stack separate button cards.
- The shared overview and detail rail list every wheel and every dual-button
  device. Button numbers are only safe display controls; the browser never
  receives Matter endpoint ids.
- All existing panel gates apply: dark + one non-default theme, EN/CS expansion,
  keyboard + screen-reader pass, 320 px, contrast against real HA.

### B4 — Hardware verification and reference capture

- Add a **dual-button** section to `HARDWARE_TEST.md` (discovery, per-button
  single/double/long, past-max quirk, binding outcomes, soak, two-device
  no-leak) and record a dated run.
- Capture the raw Matter facts into a new `docs/DEVICE_REFERENCE_BUTTON.md`
  (endpoints, FeatureMap, `MultiPressMax`, TagList, event sequences), sanitized
  the same way the wheel reference is — no node IDs, serials or entity IDs.
- Reliability caveat to test: matterjs-server issue #526 reports IKEA battery
  Matter devices (BILRESA included) going unresponsive after ~15 min idle, then
  bursting queued presses on resubscribe. Include an idle-then-press soak item.

## Non-goals

- The unofficial Zigbee/Touchlink mode of the E2489 is out of scope; this
  integration is a passive Matter listener.
- No device-control commands are ever issued, consistent with the wheel.
