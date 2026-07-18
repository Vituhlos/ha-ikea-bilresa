# IKEA BILRESA hardware test checklist

Use this checklist for release candidates and device-facing changes. Keep the
template reusable; record dated results in the section at the end and summarize
them in `PROJECT_STATUS.md`.

## Test environment

Record before testing:

- Date and tester
- Home Assistant Core version
- Matter Server version and SDK version
- Matter Server implementation, API schema, and client version (for the current
  baseline: add-on 9.0.4, matterjs-server 1.1.7, schema 11, HA client 0.7.1)
- IKEA BILRESA firmware version
- Installation method/commit SHA
- Target entity models/integrations used
- Thread border router and any notable network conditions

Enable debug logging for `custom_components.ikea_bilresa` and retain relevant,
redacted logs for failures.

## Raw event capture (independent oracle)

For any item below that asserts what the device *actually sent* — notch counts,
press classification, timing, or the dual button's past-max behaviour — capture
the raw Switch-cluster stream at the Matter Server, one layer below Home
Assistant's filtering. This is the layer the integration itself consumes, so it
is a ground-truth oracle: it proves whether a decode mismatch is ours or the
device's, and it removes the recurring "the device's physical count was not
independently instrumented" limitation from earlier runs.

Method (adapted from StephanMeijer's public gist,
`https://gist.github.com/StephanMeijer/75a26615f9b692cf7ce7cf8d6716ade4`):

- Inside the **Matter Server add-on** container, patch
  `matter_server/server/device_controller.py` to log each Switch (cluster 59)
  node event as it arrives — `received_at` (ms), `endpoint_id`, `event_id`,
  `event_number`, device timestamp and raw `data`.
- Read it live with the add-on logs, filtered to the marker, e.g.
  `grep SWITCH_EVENT`.
- Cross-check the captured `event_id`/`data` sequence against the integration's
  decoded `ikea_bilresa_event`, event entity and (where applicable) device
  trigger for the same physical gesture.

Constraints — this is instrumentation, not a test, and does **not** replace the
checklists:

- It is a manual, host-side edit performed by the owner; it is **not** something
  the assistant can do remotely.
- The patch lives in the add-on's `site-packages` and is **wiped on any add-on
  update**. Treat it as temporary and remove it after the run; never rely on it
  as a permanent fixture.
- Raw lines contain node IDs and other household identifiers. **Redact** before
  pasting into this file, `PROJECT_STATUS.md`, issues or chat, per the repo's
  privacy rules.
- It captures what the device emits only. Binding outcomes, entity/trigger/event
  agreement, lifecycle, fallback and soak still require the checklist items.

## A. Discovery and lifecycle

- [ ] Integration connects to the configured Matter Server.
- [ ] Every physical BILRESA appears once with the correct name.
- [ ] All three channels appear as event entities.
- [ ] Channel selector LEDs and reported channel agree for channels 1–3.
- [ ] Restarting Home Assistant restores wheels and bindings.
- [ ] Matter Server restart marks entities unavailable, reconnects, and recovers.
- [ ] Hot-added wheel appears without reloading the integration.
- [ ] Removed wheel entities disappear without affecting other wheels.
- [ ] System Health reports connection/version/wheel/binding values correctly.
- [ ] System Health reports `core_matter_client` as the event source on a
      compatible Home Assistant version.
- [ ] Reloading the core Matter integration reattaches the event stream within
      five seconds and wheel actions resume.
- [ ] On a deliberately incompatible/mocked core client API, the integration
      falls back to `dedicated_websocket` and still receives wheel actions.
- [ ] The dedicated WebSocket accepts the matter.js schema-11 ServerInfo and
      rejects incompatible schema bounds with a clear error.
- [ ] Parent reconfigure rejects an unreachable URL and applies a valid URL
      without creating a second config entry.
- [ ] Downloaded diagnostics redact the Matter URL, node IDs, serials, wheel
      names, binding titles and all target entity IDs while retaining useful
      bounded counters.

## B. Raw BILRESA gestures

Repeat on all three channels:

- [ ] Slow clockwise rotation reports the correct direction and notch count.
- [ ] Slow counter-clockwise rotation reports the correct direction/count.
- [ ] Fast rotation produces cumulative deltas without loss or double counting.
- [ ] A new gesture resets the cumulative count correctly.
- [ ] Single, double, and triple press are distinguished.
- [ ] Long press emits `hold`; releasing it emits `release` exactly once.
- [ ] Event entity, device trigger, and `ikea_bilresa_event` agree.

## C. Binding behavior

- [ ] Brightness moves smoothly, respects min/max, and can switch off only when
      minimum brightness is zero.
- [ ] Button press followed by trailing scroll does not turn the target back on.
- [ ] Colour temperature clamps to the light's supported Kelvin range.
- [ ] Hue wraps correctly and preserves saturation.
- [ ] Media-player volume clamps to 0–100%.
- [ ] Cover position clamps to 0–100%.
- [ ] Climate target respects min/max and target step.
- [ ] Fan percentage clamps to 0–100%.
- [ ] `number` and `input_number` respect min/max/step.
- [ ] Unavailable/unknown targets do not cause errors or runaway commands.
- [ ] Binding setup rejects one incompatible mode/target pair, preserves the
      other form values, and then saves one compatible pair successfully.
- [ ] A trailing scroll from before a button action is ignored, while a new
      deliberate rotation immediately after the press is accepted.
- [ ] With acceleration enabled, collect slow/medium/fast samples on firmware
      `1.8.7` and `1.9.15`; with acceleration zero, no decoded delta is lost.
- [ ] Rotate-up from off starts at the documented floor; an external HA
      brightness change becomes the next scroll baseline; reconnect has no jump.
- [ ] Existing event-entity and device-trigger automations still fire, and the
      compatibility domain event contains the matching registry `device_id`.
- [ ] Single/double/triple/hold targets affect only their configured entities.
- [ ] A binding explicitly set to fast response runs one single-press action on
      `ShortRelease` and does not repeat it on `MultiPressComplete`.
- [ ] A binding set to multi-press recognition preserves completion-aware
      behavior and does not fire the single action early.
- [ ] The config flow rejects fast response while a double/triple target is
      configured, without losing the other entered values.

## D. Convenience features

- [ ] Scene cycling follows the configured order and wraps to the first scene.
- [ ] Scene cycling overrides the normal single-press action only when scenes
      are configured.
- [ ] Hold-to-ramp begins on `hold` and stops immediately on `release`.
- [ ] A deliberately missing `release` is stopped by the 30-second watchdog.
- [ ] Disconnecting Matter or starting another gesture stops an active ramp.
- [ ] The first ramp goes upward; the next completed hold goes downward.
- [ ] Reconfiguring/unloading during a hold cancels the timer cleanly.
- [ ] Hold action `toggle` preserves the legacy behavior.
- [ ] Hold action `none` performs no service call.
- [ ] Each binding profile preselects the expected mode without saving the
      flow-only profile field into the subentry.
- [ ] Copying a binding prepopulates its options, can be edited independently,
      and does not modify the source binding.

## E. Soak and failure checks

- [ ] Rapid alternating rotation for at least one minute remains responsive.
- [ ] Repeated presses during/after scrolling do not produce stuck timers.
- [ ] Three channels with separate bindings do not leak actions across channels.
- [ ] Two wheels used concurrently do not leak actions across Matter nodes.
- [ ] Logs contain no recurring exceptions, task warnings, or reconnect spam.

## F. BILRESA dual button (E2489)

Separate device class from the scroll wheel: two buttons, no rotary channels.
See `docs/ROADMAP_BUTTON.md`. Sections A–E above are wheel-shaped; use this
section for the dual button and capture the raw stream (above) for every
"device actually sent" claim.

Record before testing: dual button firmware version (owner's unit was `1.8.5`),
hardware version, and the endpoint `MultiPressMax` read from diagnostics.

### F1. Discovery and presentation

- [x] The dual button is discovered from its node shape (two button endpoints,
      no channel label), not from the product string.
- [x] It is presented as a **buttons** device, not as a wheel with zero channels,
      and is excluded from any "wheel" count in System Health.
- [x] Each of the two buttons appears once as its own event entity.
- [x] Restarting Home Assistant restores the device and any button bindings.
- [x] Diagnostics redact node IDs, serials, names and target entity IDs.

### F2. Raw button gestures (capture the raw stream)

- [x] Single press on button 1 and button 2 each classify as one press.
- [x] Double press on each button classifies as a double press.
- [x] Long press emits `hold`; release emits `release` exactly once, per button.
- [x] Advertised event types match the endpoint's `MultiPressMax`: **no triple
      press** is offered for a `MultiPressMax = 2` device.
- [x] Pressing **more than max** (≥3 fast presses): capture the actual firmware
      completion contract and confirm the integration neither gets stuck nor
      emits a false action. **Real E2489 emits `MultiPressComplete(0)`; RC.3
      ignores it and accepts the next valid single exactly once.**
- [ ] Event entity, device trigger and `ikea_bilresa_event` agree for each
      gesture on each button.

### F3. Button binding behaviour

- [x] Single/double/hold targets affect only their configured entities.
- [ ] Hold action `toggle`/`none` behave as configured; a missing `release` is
      stopped by the watchdog.
- [ ] Paired hold-to-ramp (button 1 up / button 2 down on a shared target), if
      configured, begins on `hold` and stops on `release`.
- [ ] Unavailable/unknown targets cause no errors or runaway commands.

### F4. Reliability and no-leak

- [x] After ~15 min idle (matterjs-server #526), the next press is still
      delivered; note whether queued presses burst on resubscribe. **PASS on
      RC.3 after ~2 h 11 min: one completion, one action, no queued Switch
      burst, reconnect or fallback.**
- [x] The two buttons do not leak actions into each other. **PASS on RC.3:
      pressing endpoint 2 advanced only Button 2 and left Button 1 unchanged.**
- [x] A dual button and a scroll wheel used concurrently do not leak actions
      across Matter nodes. **PASS bounded adjacent-use check on RC.3: endpoint
      2 single followed by eight channel-3 rotate batches; only those two
      surfaces and their expected binding actions advanced.**
- [ ] Logs contain no recurring exceptions, task warnings, or reconnect spam.

## Recorded runs

No complete hardware run has been recorded yet.

### 2026-07-18 — E2489 B4 partial run on `v0.6.0-rc.2`

Tester: owner performing physical gestures, Codex observing Home Assistant,
recorder, integration diagnostics and sanitized Matter Server logs read-only.

Environment:

- Home Assistant Core `2026.7.2`, Home Assistant OS `18.1`, Python `3.14.6`;
- Matter Server add-on `9.1.0`, matterjs-server `1.2.6`,
  matter.js `0.17.6-alpha.0-20260715-3585d95fe`;
- WebSocket server schema `12`, minimum supported client schema `11`;
- installed custom integration `v0.6.0-rc.2`, event source
  `core_matter_client`, no fallback;
- one E2489 on firmware `1.9.15`, hardware `P2.0`, two Switch endpoints,
  `MultiPressMax = 2` on each;
- two wheels, one dual button and six configured bindings in the integration;
  household names, entity IDs, node IDs, serials and network identifiers omitted.

Observed results:

- **PASS F1:** System Health reported two wheels and one dual button; the E2489
  appeared as a buttons device with one custom event entity per physical
  button. Both bindings were restored and the diagnostic dump redacted node,
  serial and target identifiers.
- **PASS F2:** button 1 and button 2 each produced a single press, a double
  press, one hold and exactly one release. Core Matter and custom event
  entities agreed on endpoint and gesture. Both endpoints advertised only
  single/double/hold/release, never triple.
- **PASS F2 timing boundary:** deliberately slow pairs completed as two
  separate singles; fast pairs completed as doubles.
- **PASS F3:** separate single-press targets toggled only their configured
  lights. A configured button-1 hold target toggled exactly once. Button 2,
  configured with hold action `none`, still emitted hold/release and changed
  neither its single nor double target. A configured double target changed
  only on a completed double. A button-1 double with no double target changed
  nothing.
- **FAIL F2 overflow on the installed RC.2:** three rapid physical taps ended
  with the real device's Matter 1.6 `MultiPressComplete(0)`. RC.2's
  `decoded.get("count") or 1` converted zero to one, published a false single
  press and toggled the single-press target.
- **PASS recovery after the failure:** the endpoint position returned to zero;
  the next physical single press completed as count one and toggled its target
  normally. No recurring exception, task warning or reconnect spam appeared.
- **OPEN:** public `ikea_bilresa_event` and device-trigger agreement were not
  independently subscribed during this capture; only the two event-entity
  surfaces were compared.
- **OPEN:** installed-candidate overflow retest, approximately 15-minute
  idle-resume, dual-button/wheel concurrent no-leak, unavailable-target,
  watchdog/lost-release, integration/HA restore and controlled Matter Server
  reconnect remain.

The working tree already contains the G0 fix that rejects zero and counts above
the endpoint's advertised maximum, plus a deterministic regression test. That
implementation does not change this RC.2 result into a pass. It must be
published, installed and physically retested on the exact candidate.

Verdict: **FAIL on RC.2 overflow handling; otherwise the captured B4 gesture
and configured-binding subset passes. Overall B4 remains IN PROGRESS.**

### 2026-07-18 — `v0.6.0-rc.3` deployment and overflow retest

The owner authorized publication and deployment of the G0 compatibility
candidate. No physical button, wheel or controlled target was exercised during
the deployment baseline.

- exact release tag `v0.6.0-rc.3` resolves to candidate commit `e6e67eb`;
- all six GitHub Actions jobs passed for that revision;
- Home Assistant configuration validation passed before restart;
- HACS installed exactly `v0.6.0-rc.3` and Home Assistant restarted normally;
- post-restart diagnostics reported integration manifest `0.6.0-rc.3`, config
  entry `loaded`, Matter Server add-on `9.1.0` started, server schema `12`,
  minimum/client compatibility schema `11`, `core_matter_client`, no fallback,
  two wheels, one dual button and six restored bindings;
- the integration rediscovered both E2489 endpoints with
  `MultiPressMax = 2`;
- the post-start system log contained no matching `ikea_bilresa` entry.

Physical overflow follow-up:

- the owner made three rapid taps on the same E2489 side used for the RC.2
  failure;
- Matter Server logged the expected `MultiPressComplete(0)`;
- RC.3 received the ordered Switch sequence but diagnostics remained at
  `actions_dispatched = 0`;
- the public custom event entity and matching core Matter event entity did not
  advance or publish a false single;
- the configured target state did not change during the gesture;
- both integration and Home Assistant logs remained free of a matching error.
- an immediate normal single on the same endpoint completed as count one,
  advanced the custom and core event entities once, increased
  `actions_dispatched` from zero to one and changed only its configured target
  once; the other observed light remained unchanged.
- after approximately 2 hours 11 minutes without another valid Switch gesture
  on that endpoint, the next normal single completed as count one, advanced
  both event surfaces once and increased `actions_dispatched` from one to two;
  no queued Switch burst, reconnect, fallback or matching integration error
  appeared.
- the other E2489 endpoint then completed one single and only its Button 2
  surfaces advanced; its configured target toggled once while Button 1 stayed
  unchanged;
- the living-room wheel immediately followed on channel 3 with eight decoded
  rotate-up batches and exactly eight corresponding binding actions; wheel
  channels 1/2 and the observed dual-button targets stayed unchanged during
  the wheel activity;
- connection count remained one, fallback count remained zero and no matching
  integration error appeared.
- a controlled reload of only the IKEA BILRESA config entry returned `loaded`
  through `core_matter_client`, rediscovered two wheels and one dual button and
  restored all six bindings;
- the first physical single after that reload produced the expected
  InitialPress/ShortRelease/complete-one sequence, advanced both event surfaces
  once, dispatched one action and changed its intended target once; no old
  event replayed and no fallback or matching error appeared.

Verdict: **PASS deployment smoke and PASS real zero-count overflow safeguard.**
This confirms that RC.3 loads on Matter Server 9.1.0/schema 12 and correctly
ignores the real E2489 `MultiPressComplete(0)`. **PASS immediate recovery:** the
next valid single was neither lost nor duplicated. **PASS idle-resume:** a
single after ~2 hours 11 minutes was delivered once without a queued burst.
**PASS bounded no-leak:** the two dual-button endpoints and wheel channel 3
remained isolated during adjacent use. **PASS config-entry restore:** all
devices/bindings returned and the first post-reload single executed once.
Overall B4 remains **IN PROGRESS** for the Matter Server reconnect and targeted
failure-injection gates.

Controlled Matter Server restart follow-up:

- only the Matter Server add-on was restarted; no binding, target, integration
  option or automation was changed;
- the add-on returned to `started`, but RC.3 observed the temporarily unloaded
  core Matter config entry as `list index out of range`;
- after two five-second checks RC.3 selected `dedicated_websocket`, recorded one
  fallback and temporarily exposed the dual button as unavailable;
- all six stored bindings remained present, but this is a **FAIL** because the
  supported core Matter source did not recover in place;
- reloading only the IKEA BILRESA config entry restored `loaded`,
  `core_matter_client`, two wheels, one dual button, all six bindings and no
  active fallback.

Verdict amendment: **RC.3 FAILS the controlled Matter Server restart gate.**
RC.4 adds a one-minute runtime restart grace and has deterministic Unit
coverage for reattachment without fallback.

### 2026-07-18 — `v0.6.0-rc.4` restart recovery retest

- annotated tag and prerelease `v0.6.0-rc.4` resolve to exact release commit
  `90076cf`;
- exact-revision GitHub Actions run `29641472813` passed all six jobs;
- HACS installed exactly `v0.6.0-rc.4`, the pre-restart configuration check was
  valid and Home Assistant restarted normally;
- diagnostics confirmed manifest `0.6.0-rc.4`, Matter Server `9.1.0`, server
  schema 12, client compatibility schema 11, `core_matter_client`, two wheels,
  one dual button, six bindings and zero fallback;
- only the Matter Server app was then restarted. RC.4 recorded one disconnect,
  attached to the replacement core client, refreshed its node snapshot and
  stayed on `core_matter_client` for the full one-minute grace window;
- connection count advanced from one to two while fallback count remained zero;
  all three devices stayed represented and all six bindings remained present;
- no matching `ikea_bilresa` system-log entry appeared;
- the first physical Button 1 single afterward advanced both the custom and
  core Matter event entities once and dispatched exactly one binding action;
- its intended light changed from off to on once. Button 2 and the three other
  observed light targets remained unchanged.

Verdict: **PASS RC.4 controlled Matter Server restart recovery and PASS first
post-restart physical single without loss, duplication or cross-button leak.**
The unavailable-target and lost-release/watchdog failure-injection gates remain
open, so overall B4 remains **IN PROGRESS**.

### 2026-07-15 - `v0.5.7-rc.2` run in progress

Tester: owner with Codex read-only MCP observation.

Environment recorded at start:

- Home Assistant Core `2026.7.2`, Home Assistant OS `18.1`, Python `3.14.6`;
- Matter Server add-on `9.0.4`, matterjs-server `1.1.7`, matter.js `0.17.4`,
  WebSocket schema `11`;
- custom integration `0.5.7-rc.2`, installed through HACS;
- event source `core_matter_client`, connected, no fallback reason;
- two discovered wheels and three configured bindings;
- physical wheels have mixed firmware: one `1.9.15`, one `1.8.7`, both hardware
  `P2.0`;
- exact network, registry, serial, node, entity and target identifiers omitted.

Read-only baseline results:

- **PASS:** integration config entry loaded and Matter event source connected;
- **PASS:** coordinator discovered two BILRESA nodes, each with all three channel
  role groups in diagnostics;
- **PASS:** System Health reported `core_matter_client`, two wheels, three
  bindings, matter-server `1.1.7` / matter.js `0.17.4`, and no fallback;
- **PASS:** no current `ikea_bilresa` system-log or error-log entry;
- **FAIL:** both physical wheels do not appear once with their correct user
  names in the custom integration device presentation.

Compatibility finding behind the discovery failure:

- firmware `1.9.15` exposes Basic Information Serial Number attribute
  `0/40/15`; its custom event entities merge onto the corresponding core Matter
  device and inherit the user name;
- firmware `1.8.7` does not expose `0/40/15` in the live Matter diagnostics;
- the current custom integration links to the core Matter device only through
  `matter:serial_<serial>` when that attribute exists;
- therefore the `1.8.7` wheel's three event entities are created on a separate
  default-named BILRESA device instead of the user-named Matter device;
- both Matter devices themselves are available, so this is a device-registry
  linking/presentation defect, not evidence that gesture reception is broken.

No Home Assistant state, registry entry, integration option, logger level or
device was changed during this baseline. Gesture, binding, lifecycle, fallback
and soak checks remain pending. Final verdict remains **IN PROGRESS**.

An unreleased fix candidate was subsequently implemented in the working tree.
It resolves the exact core Matter operational identifier from the matching
server's compressed fabric ID and node ID when serial is absent, refuses
ambiguous matches, migrates the custom event entities from a legacy standalone
device, and refreshes wheel metadata after a firmware update. Static checks are
recorded in `PROJECT_STATUS.md`; CI, deployment, registry migration and physical
hardware verification remain pending. The recorded discovery failure above is
not converted to a pass by implementation alone.

A later read-only MCP recheck on 2026-07-15 still reported firmware `1.8.7` for
the affected wheel and `1.9.15` for the other wheel. No Home Assistant state was
changed by that check.

`v0.5.7-rc.3` deployment/registry smoke result:

- CI passed on exact commit `6db5b5b` with 51 tests and 56% total coverage;
- HACS installed exactly `v0.5.7-rc.3`, config preflight passed and HA restarted;
- integration loaded through `core_matter_client` with two wheels, three
  bindings and no event-source fallback;
- exactly two unique BILRESA devices appeared with the correct user names;
- firmware `1.8.7` remained installed on the affected wheel, proving that the
  serial-independent registry path—not a firmware update—removed the duplicate;
- each physical wheel had both Matter and `ikea_bilresa` sources and exactly
  three custom event entities;
- no matching `ikea_bilresa` system-log or error-log entry was present.

This passes the live HA registry/presentation portion of discovery. No wheel was
pressed or rotated during this deployment, so raw gestures, bindings, lifecycle,
fallback injection and soak checks remain pending and the overall verdict stays
**IN PROGRESS**, not Hardware PASS.

Physical gesture smoke continued later on 2026-07-15 against the same installed
`v0.5.7-rc.3` and environment:

- **PASS:** firmware `1.8.7` wheel, channel 1, slow clockwise mapped to
  `rotate_up` and slow counter-clockwise mapped to `rotate_down`;
- **PASS:** a faster clockwise movement on that channel produced six ordered
  `rotate_up` entity updates with deltas `3, 2, 3, 3, 3, 1` (15 total); the
  device's physical count was not independently instrumented, so this does not
  prove absolute no-loss accuracy;
- **PASS:** the same channel produced `press`/`presses: 1`,
  `double_press`/`presses: 2`, and `triple_press`/`presses: 3`;
- **OBSERVED:** a deliberately slower first triple-press attempt exceeded the
  device's multi-press window and completed as separate single presses; a fast
  retry completed correctly as one triple press;
- **PASS:** a roughly two-second hold produced one `hold` followed by exactly
  one `release`;
- **PASS:** firmware `1.8.7` channels 2 and 3 each produced clockwise,
  counter-clockwise and single-press events only on the selected channel;
- **PASS:** firmware `1.9.15` channels 1, 2 and 3 each produced clockwise,
  counter-clockwise and single-press events only on the selected channel;
- **PASS:** throughout the batch the event source remained
  `core_matter_client`, fallback count remained zero, and no matching
  `ikea_bilresa` or Matter error-log line appeared.

This provides Hardware evidence for both firmware versions, all six channel
routes, direction decoding and the representative channel-1 gesture set. Target
binding outcomes, event-entity/device-trigger/custom-event agreement, lifecycle,
fallback injection, UI flows and soak tests were not observed. Overall verdict
remains **IN PROGRESS**; the raw-gesture smoke subset is **PASS**.

A subsequent channel-2 binding observation on the firmware `1.9.15` wheel found
that two separate physical single presses toggled the configured light. Once
the public `press` event appeared, the target state followed after 114 ms and
424 ms respectively. The larger perceived delay therefore occurred before the
binding service call while the device/integration waited for
`MultiPressComplete` to classify single/double/triple. No household identifiers
are recorded here.

The working tree now contains an explicit low-latency candidate. A binding set
to fast response reacts once to `ShortRelease`; a binding set to multi-press
recognition waits for completion. The form rejects fast response with a
configured double/triple target, and public events retain completion-based
classification. This candidate has not been deployed or physically tested and
must not be marked Hardware until a later installed build confirms response
time and exactly-once behavior.

A channel-1 brightness measurement on the same firmware `1.9.15` wheel then
used the installed `v0.5.7-rc.3` binding with step 3%, zero acceleration and a
one-second transition. Slow down/up and faster down gestures produced 3/5/6
decoded updates, total deltas 9/13/18 and event-stream durations
1.032/2.051/2.095 seconds. The first recorded light-state updates followed the
first decoded events after 1.166/1.125/1.098 seconds. The light moved from 100%
to 46%, and no matching BILRESA or Matter error appeared. This passes the live
rotation-to-binding data path; visual onset/smoothness and absolute physical
notch accuracy were not independently measured.

When a run is completed, append a dated section containing the environment,
checked/failed items, relevant redacted logs, fixes made, commit SHA, and final
verdict: `PASS`, `PASS WITH LIMITATIONS`, or `FAIL`.

### 2026-07-15 - `v0.5.7-rc.4` deployment baseline

- Release commit `36f9c1c` passed exact-revision CI run `29431669462`:
  hassfest, HACS validation, Ruff, mypy and 112 tests passed with 68% total
  coverage.
- HACS installed exactly `v0.5.7-rc.4`; the Home Assistant configuration check
  was valid before restart.
- After restart, Home Assistant Core 2026.7.2 / Python 3.14.6 loaded the
  integration through `core_matter_client` with two discovered wheels, four
  bindings and no fallback reason.
- No integration system-log entry or error was present; only Home Assistant's
  standard custom-integration loader warning matched in the raw error log.
- An existing binding's reconfigure schema exposed Button response with the
  compatibility default `multi_press`. The deployment did not recreate or
  automatically change any binding, target or automation.

This is a deployment baseline only. No physical press or rotation was performed
against RC.4 yet, so every RC.4-specific Hardware item remains open.

### 2026-07-15 - `v0.5.7-rc.5` fast-response timing

- Release commit `4ad3fd8` passed exact-revision CI run `29434960588` with
  hassfest, HACS validation, Ruff, mypy, 122 tests and 69% total coverage.
- HACS installed exactly `v0.5.7-rc.5` after a valid configuration check; Home
  Assistant Core 2026.7.2 restarted with two wheels, three current bindings,
  `core_matter_client` and no fallback reason.
- The tested firmware `1.9.15` wheel's channel-2 binding was confirmed in Fast
  response mode. DEBUG was scoped only to
  `custom_components.ikea_bilresa.binding`.
- Five normal single presses produced the following elapsed-time ranges from
  receipt of raw `ShortRelease`: service dispatch 0.1-0.4 ms,
  `MultiPressComplete` 2.9-12.0 ms, and first target-state acknowledgement
  86.9-111.2 ms.
- Mean timing was approximately 0.2 ms to dispatch, 6.0 ms to completion and
  95.5 ms to target acknowledgement. Each trace completed as one press, no
  duplicate binding action was observed, and no integration/system error was
  present.

**PASS WITH LIMITATIONS:** the fast binding path dispatches exactly once and
immediately after `ShortRelease`, but completion follows only about 6 ms later
on this firmware. The remaining perceived delay is not in the binding dispatch
path. Physical release-to-Matter delivery and actual relay actuation are not
observable from HA timestamps, and firmware `1.8.7` has not yet been measured
with the same trace.
