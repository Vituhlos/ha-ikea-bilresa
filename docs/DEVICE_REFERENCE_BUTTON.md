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
| button A | button | 30 *(confirm)* | 2 |
| button B | button | 30 *(confirm)* | 2 |

- Endpoints carry **no numeric channel label and no up/down switch tag** — this
  shape (button-only, no rotary) is what `model.py` uses to classify the device as
  the `dual_button` variant rather than a wheel.
- `MultiPressMax = 2`: the device never reports a press count above 2. This is the
  hard difference from the wheel's buttons (max 3) — the dual button has **no
  triple press**.

## Observed gestures (Home Assistant filtered surface, 2026-07-17)

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

## How the integration consumes it

- `model.py` classifies the node as the `dual_button` variant from endpoint shape
  and parses `Switch.MultiPressMax` (`ep/59/2`) per endpoint.
- `event.py` builds one `BilresaButtonEvent` per button, advertising
  `press`, `double_press`, `hold`, `release` — capped by MultiPressMax, so no
  `triple_press` is offered here. Both endpoints report `channel = None` and share
  one dispatcher signal; each entity filters by endpoint id.
- Binding subentries use `node_id + endpoint` rather than the absent channel.
  Runtime keys tag endpoint and channel addresses separately, so both buttons
  on every physical dual button can keep independent targets even when several
  devices expose the same endpoint numbers.
- The gesture engine's button path is stateless (acts on
  `MultiPressComplete` / `LongPress` / `LongRelease` only), so a press beyond the
  device maximum simply yields no event and cannot get stuck.
