# IKEA BILRESA dual button (E2489) — device reference

Sanitized reference for the button-only BILRESA variant, companion to
`DEVICE_REFERENCE.md` (the scroll wheel). It omits household names, node IDs,
serial numbers, network addresses and entity IDs — never add those to a
committed fixture or report.

These are device/protocol facts. They do not mean any working-tree feature is
hardware-verified; see `HARDWARE_TEST.md` Section F.

## Hardware and environment baseline

- IKEA BILRESA dual button, product **E2489**, Matter vendor ID 4476 (`0x117C`),
  model string `BILRESA dual button`.
- Matter over Thread sleepy end device, 2× AAA battery.
- Firmware `1.9.15`, hardware `P2.0` (observed 2026-07-17; an earlier read showed
  `1.8.5`, so firmware moves — re-confirm after upgrades).
- Firmware `1.9.15` exposes the Basic Information serial number (`0/40/15`), so
  the device links to its core Matter device by serial as well as by operational
  identifier.

## Matter node structure

Home Assistant's core Matter integration exposes exactly **two** Switch (`0x003B`)
endpoints — one per physical button — plus per-button switch-position sensors and
a single Identify button. There is **no third switch endpoint**: any physical
pairing/reset control is not a Matter switch and produces no Home Assistant event.

| Endpoint | Role | FeatureMap | MultiPressMax |
|---|---|---:|---:|
| button A | physical button; semantic tag `up` | 30 *(confirm)* | 2 |
| button B | physical button; semantic tag `down` | 30 *(confirm)* | 2 |

- Endpoints carry **no numeric channel label**, but do carry the semantic
  **up/down switch tags**. The first `v0.6.0-rc.1` deployment proved that these
  tags describe the two physical button faces; treating them as rotary roles
  misclassified the device as an empty wheel. `model.py` therefore classifies
  the exact pair of channel-less switch endpoints as `dual_button` and
  normalizes both roles to `button`. The official Matter Switches namespace
  defines tag `0x0003` as `Up` and `0x0004` as `Down`; these are semantic
  function tags, not evidence that the physical control rotates:
  [connectedhomeip Namespace-Switches.xml](https://github.com/project-chip/connectedhomeip/blob/master/data_model/1.6/namespaces/Namespace-Switches.xml).
- Sanitized raw `TagList` facts captured from core Matter diagnostics:
  button A has Common Position tag `2` plus Switches `On`, `Up`, and Custom
  label `button 1`; button B has Common Position tag `3` plus Switches `Off`,
  `Down`, and Custom label `button 2`. The committed regression fixture keeps
  only these protocol fields with a synthetic node id.
- `MultiPressMax = 2`: the device never reports a press count above 2. This is the
  hard difference from the wheel's buttons (max 3) — the dual button has **no
  triple press**.

## Observed gestures

Captured live via HA history on firmware `1.9.15`, both buttons. This is the
**filtered** core-Matter surface (the derived `multi_press_N` events), not the raw
Switch stream — the raw `initial_press` / `short_release` / `multi_press_ongoing`
/ `multi_press_complete` sequence still needs a matter-server capture
(`HARDWARE_TEST.md`, "Raw event capture").

| Gesture | HA event_type | count field |
|---|---|---|
| single press | `multi_press_1` | `totalNumberOfPressesCounted` = 1 |
| double press | `multi_press_2` | `totalNumberOfPressesCounted` = 2 |
| hold | `long_press` | `newPosition` |
| release | `long_release` | `previousPosition` |

- **No `multi_press_3` / count 3 was ever produced**, including on deliberate
  fast triple presses — consistent with `MultiPressMax = 2`.
- Example hold: `long_press` → `long_release` about 0.5–1.2 s apart, matching the
  physical hold duration.
- Rapid repeated taps outside the multi-press window complete as a stream of
  separate `multi_press_1` events rather than a higher count.

### Raw Matter Server 9.1.0 stream (2026-07-18)

Captured from Matter Server add-on `9.1.0`, matterjs-server `1.2.6`,
matter.js `0.17.6-alpha.0-20260715-3585d95fe`, server schema `12`, minimum
client schema `11`, firmware `1.9.15`. Both physical endpoints produced the
same gesture grammar:

| Physical gesture | Ordered Switch events |
|---|---|
| single | `InitialPress` → `ShortRelease` → `MultiPressComplete(1)` |
| double | `InitialPress` → `ShortRelease` → `InitialPress` → `MultiPressOngoing(2)` → `ShortRelease` → `MultiPressComplete(2)` |
| hold/release | `InitialPress` → `LongPress` → `LongRelease` |
| three rapid physical taps | two reported press/release phases with `MultiPressOngoing(2)`, then `MultiPressComplete(0)` |

The observed long-press threshold was about `716–722 ms` from `InitialPress`.
One release followed about `0.68 s` later on button 1 and `1.63 s` later on
button 2; both CurrentPosition sensors returned to zero.

The three-tap capture confirms the Matter 1.6 overflow contract on the real
E2489: exceeding `MultiPressMax = 2` can complete with count zero. The installed
`v0.6.0-rc.2` incorrectly converted that zero to a single press and toggled the
configured target. A subsequent normal single press completed as count one,
showing that the device and integration were not left stuck.

The exact overflow was repeated after installing `v0.6.0-rc.3`. Matter Server
again reported `MultiPressComplete(0)`, while RC.3 dispatched zero actions,
left both the public custom event entity and the core Matter event entity
unchanged, did not change the configured target, and logged no integration
error. An immediate deliberate normal single then completed with count one,
advanced both event entities once and changed only its configured target once.
This Hardware-verifies both the G0 safeguard for a zero completion count and
clean recovery of the same endpoint afterward.

## How the integration consumes it

- `model.py` classifies the exact two channel-less switch endpoints as the
  `dual_button` variant, normalizes their semantic up/down tags to physical
  button roles, and parses `Switch.MultiPressMax` (`ep/59/2`) per endpoint.
- `event.py` builds one `BilresaButtonEvent` per button, advertising
  `press`, `double_press`, `hold`, `release` — capped by MultiPressMax, so no
  `triple_press` is offered here. Both endpoints report `channel = None` and share
  one dispatcher signal; each entity filters by endpoint id.
- Binding subentries use `node_id + endpoint` rather than the absent channel.
  Runtime keys tag endpoint and channel addresses separately, so both buttons
  on every physical dual button can keep independent targets even when several
  devices expose the same endpoint numbers.
- The corrected gesture engine acts on valid `MultiPressComplete`,
  `LongPress`, and `LongRelease` events. It ignores zero and above-max
  completion counts and uses CurrentPosition only to clear stale safety state;
  it never synthesizes a click from that attribute. This is implemented and
  unit-tested, released in `v0.6.0-rc.3`, and Hardware-verified for the real
  E2489 zero-count overflow. An above-max count remains deterministic test
  evidence only because this device signals physical overflow as zero.
