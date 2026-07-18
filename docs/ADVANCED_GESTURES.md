# Advanced BILRESA controls

This document turns the post-B3 product ideas into an ordered implementation
contract. It applies to any number of BILRESA scroll wheels and dual buttons;
all runtime state is always keyed by Matter node and physical endpoint.

Read this together with `ROADMAP_BUTTON.md`, `LATENCY_ROADMAP.md`,
`MATTERJS_COMPATIBILITY.md` and `HARDWARE_TEST.md`. Implemented, Unit, CI,
Hardware and Released remain separate claims.

## Product boundary

The integration owns reliable physical primitives and convenient direct
bindings. Home Assistant remains the automation engine.

- Ordered Matter `node_event` messages are the only source of clicks, holds,
  chords, sequences and rotation.
- Switch `CurrentPosition` is a release/stuck-state safety hint only.
- No Matter device commands are sent.
- Complex conditions and household-wide flows execute through HA scripts,
  scenes and automations rather than a second automation language in the
  integration.
- Existing bindings keep their behavior after upgrades. Every new ambiguous
  gesture is opt-in.

## G0 — Matter 1.6 / Matter Server 9.1 compatibility

Status: Implemented + Unit locally; Hardware and Released pending.

- Accept server schema 12 through its supported client-schema-11 profile.
- Handle `node_updated`, `attribute_updated` and `server_shutdown`.
- Use `CurrentPosition` only to clear stale state.
- Ignore Matter 1.6 multi-press overflow (`count == 0`) and counts above the
  endpoint's advertised `MultiPressMax`.
- Keep callbacks bounded so server-side backpressure does not delay gestures.

Exit gate: add-on 9.1.0 reconnect plus physical single/double/hold/release and
idle-resume run recorded in B4.

## G1 — response and observed hold duration

Status: Instant response and observed duration Implemented + Unit locally; hold
tiers pending; Hardware and Released pending.

- Add an opt-in **Instant press** response beside Fast release and Multi-press
  aware. Instant executes once on `InitialPress` and is rejected when a distinct
  double/triple or hold action would make the result ambiguous.
- Preserve exact public completion semantics: event entities, device triggers
  and `ikea_bilresa_event` still report the completed gesture, even when a
  direct binding reacted earlier.
- Track host-monotonic press start and release boundaries per node/endpoint.
  Expose `observed_duration_ms` only when both boundaries belong to the same
  uninterrupted connection. It describes integration-observed duration, not a
  laboratory measurement of finger contact.
- Offer hold tiers as opt-in triggers (for example short hold / long hold) with
  user-visible thresholds and exactly-one outcome. A lost release, reconnect or
  timeout clears the gesture without executing a delayed action.

Exit gate: deterministic ordering/exactly-once tests, then physical A/B latency
and lost-release checks.

## G2 — physical combinations

### Dual-button chord

- Recognize both physical buttons being down inside a small configurable window.
- Emit one chord primitive and suppress the two component click/hold actions for
  that gesture.
- Never infer a chord from two adjacent completed clicks or from coalesced
  `CurrentPosition` reports.
- Keep chord disabled until simultaneous presses are captured from the owner's
  E2489 in B4.

### Wheel button + rotation modifier

- While a wheel channel's physical button is held, rotation may select a second
  configured function, such as brightness versus colour temperature.
- The modifier is local to one node/channel and cannot leak to another wheel.
- Lost release, reconnect and a watchdog always return to the base layer.
- Normal rotation remains unchanged unless the modifier is explicitly enabled.

Exit gate: raw event-order capture on every installed BILRESA firmware followed
by no-leak tests with multiple devices.

## G3 — scripts, scenes, sequences and profiles

- Every press, hold tier, chord and modifier outcome can run an HA script or
  scene as well as a direct entity action.
- Common sequences such as tap-then-hold are supplied as reusable HA
  blueprints/device-trigger recipes. The integration exposes stable primitives
  and bounded timing metadata; it does not embed arbitrary condition trees.
- Named profiles/layers group existing bindings. Profile selection is exposed
  as an HA-native select state so dashboards, automations and the BILRESA panel
  observe the same active layer.
- Profile changes are atomic per device. A gesture that began in one profile
  finishes or is cancelled there; it never changes meaning halfway through.
- The panel keeps the existing wheel/dual-button workbench and adds profile and
  advanced-gesture sections progressively. It does not introduce a second
  visual design.

Exit gate: storage migration, restore-state, multi-device isolation,
script/scene acceptance reporting, EN/CS and accessibility tests.

## G4 — additional continuous controls

- Add light saturation as a separate explicit wheel mode; do not silently
  change the existing colour/hue mode.
- Add cover tilt only when the selected cover advertises tilt support. Position
  and tilt remain separate modes with correct min/max clamping.
- Keep unsupported modes out of selectors rather than accepting a configuration
  that can never work.
- Evaluate any further continuous domain from actual HA capabilities and Matter
  event evidence, not from product-name assumptions.

Exit gate: domain capability tests plus one safe physical target per new mode.

## Release order

G0 belongs in the next compatibility RC. G1 can follow after its focused
hardware pass. G2 stays experimental/opt-in until B4 proves the physical event
ordering. G3 and G4 are separate feature packages so a failure in an advanced
profile or target mode cannot destabilize the basic buttons and wheel.
