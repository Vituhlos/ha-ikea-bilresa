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

## Recorded runs

No complete hardware run has been recorded yet.

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
