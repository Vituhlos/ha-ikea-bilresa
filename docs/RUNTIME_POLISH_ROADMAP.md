# Runtime behavior polish roadmap

This is the implementation contract for making BILRESA control behavior
predictable, responsive and safe before the optional custom panel program. It
is deliberately separate from `PANEL_ROADMAP.md`: runtime behavior must remain
correct without a panel, and panel design/development may continue independently.

The work stays in the `0.5.7` release-candidate train until the runtime baseline
is stable. Individual items are reviewable work packages, not promises that a
tag exists. Keep Implemented, Static, Unit, CI, Hardware and Released separate
in `PROJECT_STATUS.md`.

## Ordering principles

1. Prevent surprising or unsafe actions before optimizing feel.
2. Preserve existing public event entities and automation contracts.
3. Prefer measured behavior over timers and guessed defaults.
4. Keep Matter access passive and read-only.
5. Do not add batching, debounce or command queues without telemetry proving
   that direct dispatch is the bottleneck.
6. Every changed behavior needs regression tests and the smallest relevant
   physical check; a full laboratory matrix is not required for each patch.

## R1 - Explicit button response policy

**Priority:** first; intended for the next `v0.5.7` release candidate.

Replace the provisional automatic low-latency heuristic with an explicit
per-binding response policy:

- **Fast single press (recommended for direct light control):** execute the
  binding once on the first button `ShortRelease`, collapse further releases in
  that physical gesture, and suppress the later binding completion;
- **Multi-press aware:** wait for `MultiPressComplete` and preserve exact
  single/double/triple binding actions;
- public event entities, device triggers and `ikea_bilresa_event` always retain
  exact completion-based single/double/triple classification in both modes;
- a fast binding must clearly document that an external double/triple
  automation may still fire after its immediate single binding action;
- existing stored bindings default to the backwards-compatible multi-press
  policy unless the owner explicitly selects fast response;
- new binding profiles may recommend fast response, but the trade-off must be
  visible in English and Czech before saving.

Exit gates:

- tests for single, double, triple, hold, lost completion, reconnect and unload;
- config-flow validation and English/Czech copy;
- CI on the exact candidate revision;
- one physical A/B measurement on the current channel-2 light toggle, verifying
  exactly one target action and improved release-to-target latency.

Current state (2026-07-15): **Implemented + Static** in the dirty working tree.
The automatic heuristic has been replaced by an explicit native HA selector
with English/Czech trade-off text and conflict validation. Existing bindings
default to multi-press recognition; new profiles default to fast response.
Regression tests are authored, but Unit is not run locally because Home
Assistant is unavailable in the Windows environment. CI, HA UI and Hardware
remain pending; see `PROJECT_STATUS.md`.

## R2 - Unavailable and unknown target safety

All binding modes must refuse to calculate or issue a command when their target
is missing, `unknown` or `unavailable`. Recovery must resynchronize from the
real target state rather than a fabricated fallback.

Behavior:

- no service call to an unavailable target;
- no runaway hold ramp while the target is unavailable;
- stop an active ramp when the target becomes unavailable;
- log at most one useful transition and one recovery transition, never one line
  per wheel event;
- resume cleanly when the target returns.

Exit gates:

- parameterized tests across brightness, colour temperature, colour, volume,
  cover, climate, fan, number and input_number modes;
- no recurring log output during a simulated unavailable interval;
- a small live check using one temporarily unavailable or mocked target.

Current state (2026-07-15): **Implemented + Static** in the dirty working tree.
A shared availability guard now covers all eight scroll modes and button/scene
targets, stops an active ramp, deduplicates unavailable/recovery logs and clears
the tracked value on recovery. Parameterized and recovery/ramp tests are
authored. Unit is not run locally; CI, HA UI and Hardware remain pending.

## R3 - Mode and target compatibility validation

Reject invalid binding configurations before they are saved:

| Mode | Allowed target domains |
|---|---|
| Brightness, colour temperature, colour | `light` |
| Volume | `media_player` |
| Cover position | `cover` |
| Target temperature | `climate` |
| Fan speed | `fan` |
| Number | `number`, `input_number` |

The runtime must also fail closed for an incompatible legacy subentry instead
of sending a service to the wrong domain. The config flow returns a localized,
actionable field error and preserves the user's other input.

Exit gates:

- create, edit, copy and profile-flow tests for valid and invalid combinations;
- English/Czech validation text;
- live UI smoke of one rejected mismatch and one valid save.

Current state (2026-07-15): **Implemented + Static** in the dirty working tree.
The config flow and runtime share one mode/domain compatibility map. The form
returns a localized target-field error while preserving input; an incompatible
legacy binding logs once and issues no scroll command. Mapping and helper-level
flow tests are authored. Full create/edit/copy flow execution, Unit, CI, HA UI
and Hardware remain pending.

## R4 - Measured transition presets

**Deferred by owner on 2026-07-15.** Keep this as future physical tuning. No
default or profile transition changes may be inferred from static checks or HA
history; resume only when the owner wants to compare visible behavior at the
wheel and light.

Use physical A/B evidence to tune perceived brightness response without making
device-side batching more visible. The 2026-07-15 baseline used transition
`1.0 s`; first recorded target-state updates followed decoded actions after
roughly `1.1 s`.

Test `0.3 s`, `0.5 s` and `1.0 s` on the same light and binding. Record:

- visible onset judged by the owner;
- smoothness between roughly one-second BILRESA batches;
- HA state completion time;
- final brightness and errors.

Only change a profile/default after the A/B result. Keep the raw numeric option
for users who prefer a different feel. Do not infer visible onset from recorder
timestamps alone.

## R5 - Gesture-aware trailing-scroll protection

Replace the fixed post-press suppression window with gesture state wherever the
observed Matter sequence permits it:

- ignore only scroll updates belonging to the gesture that preceded a button
  action;
- do not discard a deliberate new rotation after the press;
- keep a bounded timeout only as a lost-event safety fallback;
- handle both firmware `1.8.7` and `1.9.15` event ordering;
- retain the rule that a trailing scroll must never turn a just-disabled target
  back on.

Exit gates:

- timestamped sequence fixtures from sanitized live telemetry;
- tests for press-after-scroll, new-scroll-after-press and missing completion;
- physical reproduction on at least the two installed firmware versions.

Current state (2026-07-15): **Implemented + Static** in the dirty working tree. Private
per-channel gesture metadata records scroll generations and the button's
preceding boundary. Only that generation is suppressed; a new `InitialPress`
passes immediately and a two-second timeout is only a lost-boundary fallback.
Sequence tests are authored. Unit/CI and both-firmware Hardware gates are
recorded separately in `PROJECT_STATUS.md`.

## R6 - Velocity-based acceleration

The current acceleration derives from a single decoded batch size. Batch size
also reflects firmware timing, so it is not a reliable speed measurement.

Replace it with a bounded velocity model based on decoded notches per elapsed
time:

- use monotonic timestamps and a short smoothing window;
- reset after an idle gap, direction change, reconnect or gesture completion;
- cap the multiplier and preserve exact unaccelerated delta accounting;
- keep acceleration disabled by default until both firmware versions pass;
- do not add a latency-only accumulator.

Exit gates:

- deterministic timestamp-driven unit tests;
- slow/medium/fast physical samples on both firmware versions;
- no overshoot at min/max and no dependence on arbitrary Matter batch splits.

Current state (2026-07-15): **Implemented + Static** in the dirty working tree. A bounded
monotonic-time velocity window replaces single-batch-size acceleration and
resets on idle, direction change, gesture boundary and reconnect. Acceleration
zero preserves every delta and remains the default. Deterministic tests are
authored; Unit/CI and both-firmware physical samples remain separate.

## R7 - Predictable off/on and resynchronization semantics

Define and document behavior when reality changes outside the binding:

- whether rotate-up from off starts at the configured minimum or restores the
  previous brightness;
- how an external automation or app change rebases the tracked target;
- what a direction reversal does to an in-flight transition;
- when the fixed resynchronization interval may be replaced by target-state
  observation without feeding the binding's own transitions back into itself;
- how reconnect/reload restores internal state without a visible jump.

Prefer one predictable default over many knobs. Add a user option only when two
behaviors are both common, safe and impossible to infer.

Current state (2026-07-15): **Implemented + Static** in the dirty working tree.
Rotate-up from off starts at the configured floor or one usable step; external
HA state changes invalidate tracking outside a bounded own-command echo window;
direction reversal uses the last requested value; unavailable/reconnect clears
state. State-observation tests are authored. Unit/CI/HA UI/Hardware are
tracked separately.

## R8 - Home Assistant-native event polish

Keep event entities as the primary automation surface and align them with the
current Home Assistant event model:

- evaluate `EventDeviceClass.BUTTON` for channel event entities;
- retain strict declared event types and lifecycle-safe subscriptions;
- keep existing device triggers compatible, but do not expand that API while
  Home Assistant is evaluating alternatives;
- review whether the legacy domain event needs registry `device_id`
  attribution without leaking identifiers into diagnostics or documentation;
- document event entities first in automation examples.

Exit gates:

- hassfest/HACS validation, entity lifecycle tests and automation compatibility
  tests;
- no entity-ID or unique-ID migration;
- existing automations continue to trigger after upgrade.

Current state (2026-07-15): **Implemented + Static** in the dirty working tree. Channel
entities declare `EventDeviceClass.BUTTON`; event types, unique IDs and device
triggers are unchanged; the compatibility domain event preserves all fields and
adds registry `device_id` when available. Regression tests are authored.
Unit/CI/HA automation compatibility remain separate gates.

## Release staging

Recommended staging, subject to evidence rather than calendar dates:

1. **Next RC:** R1, R2 and R3 as separate commits, then one combined CI and
   controlled HA deployment.
2. **Feel RC:** R5 after sanitized event-order capture; R4 remains explicitly
   deferred until the owner wants physical transition A/B tuning.
3. **Algorithm RC:** R6 only after measured velocity evidence.
4. **Final `0.5.7` stabilization:** R7 and R8, regression suite, soak and owner
   acceptance.
5. **Panel program:** resume the separately documented read-only `0.5.8` panel
   work without coupling it to runtime correctness.

## Explicit non-goals

- No Matter writes or device-control commands.
- No speculative command accumulator or rate limiter.
- No panel frontend work in this roadmap.
- No brand/default-HACS publication work.
- No stable release claim from static checks, MCP observation or design alone.
