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
- [ ] Single/double/triple/hold targets affect only their configured entities.

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

When a run is completed, append a dated section containing the environment,
checked/failed items, relevant redacted logs, fixes made, commit SHA, and final
verdict: `PASS`, `PASS WITH LIMITATIONS`, or `FAIL`.
