# Scroll performance decision

## Current evidence

Physical observations recorded in `DEVICE_REFERENCE.md` show that BILRESA
firmware 1.9.15 batches fast rotary activity in the device and emits cumulative
`MultiPressOngoing` counts roughly every 0.5–1 second. The gesture engine already
turns those cumulative values into exact deltas and the binding applies the
whole delta immediately.

## Decision for 0.5.5

Do not add a 50–100 ms software accumulator, debounce or rate limiter. Such a
layer cannot recover device-side events earlier, would add latency to a single
notch and could obscure a lost final delta. Target transitions are the supported
way to smooth the visible change between device batches.

This work package is therefore an evidence-based no-op in runtime code. It adds
the measurement criteria below and protects the existing low-latency path.

## Revisit criteria

Only introduce aggregation if timestamped hardware telemetry demonstrates all
of the following:

1. Matter events arrive materially faster than target service calls can be
   processed.
2. Direct dispatch causes measurable backlog, rate limiting or lost deltas.
3. A candidate algorithm preserves every cumulative delta, single-notch latency
   and the final `MultiPressComplete` value in a repeatable soak test.

Record event arrival, decoded delta, dispatched target value and service-call
completion using sanitized identifiers. Test both the reused core-client source
and the dedicated passive WebSocket. Never include node IDs, entity IDs, serial
numbers or household URLs in committed fixtures or reports.

## 2026-07-15 physical brightness measurement

On `v0.5.7-rc.3`, firmware `1.9.15`, channel 1 and a live brightness binding
using `step=3`, acceleration `0` and transition `1.0 s`, three physical gestures
produced:

| Gesture | Decoded updates | Total delta | Stream duration | First recorded target update |
|---|---:|---:|---:|---:|
| Slow down | 3 | 9 | 1.032 s | 1.166 s |
| Slow up | 5 | 13 | 2.051 s | 1.125 s |
| Faster down | 6 | 18 | 2.095 s | 1.098 s |

The target finished at 46% brightness after starting at 100%. No BILRESA or
Matter error was logged. The roughly one-second target-state updates align with
the configured one-second transition, while decoded actions continued to arrive
in the device's roughly one-second batches. This shows no software dispatch
backlog and does not satisfy the accumulator revisit criteria.

Home Assistant history records target-state updates, not the first visible
photon change. A future comparison may test a 0.3-0.5 second transition for a
more immediate feel, but the global default must not change from this recording
alone; visual smoothness and onset latency still need owner observation.

## Next step: measured transition tuning (raw SWITCH_EVENT capture)

This is the concrete procedure for the "future comparison" noted above, and the
way to satisfy the revisit criteria with real numbers instead of guessing. It
reuses the raw-capture instrumentation already documented in
`HARDWARE_TEST.md` ("Raw event capture (independent oracle)") — the StephanMeijer
gist's matter-server `SWITCH_EVENT` logging. That log is a per-event timestamp
recorder: one line per notch, with the exact time the device emitted it.

The point is **not** to make scrolling smoother than the firmware allows. IKEA's
firmware does not do rotary encoding; it emits discrete notches batched at a
~500 ms MultiPress window (StephanMeijer's independent measurement, consistent
with `DEVICE_REFERENCE.md`'s 0.5-1 s). Transport is ~30-150 ms. So there is a
hard firmware ceiling; this procedure only tunes how reliably we hit it and how
the visible brightness change is smoothed between batches.

### The loop: measure → find the gap → change one knob → measure again

1. **Baseline.** Enable the raw `SWITCH_EVENT` capture and
   `custom_components.ikea_bilresa` debug logging, then do one deliberate slow
   and one faster rotation. Line up three timelines for the same gesture:
   - device emit time (raw capture),
   - our dispatch time (integration debug log),
   - target-state acknowledgement (HA history / light state).

   Example shape (illustrative, not recorded):

   ```text
   T+0 ms     device: MultiPressOngoing count=6
   T+40 ms    integration: set brightness -> 55%
   T+150 ms   light: acknowledged 55%
   ```

2. **Locate the gap.** The three timelines show where latency lives: in the
   device (the ~500 ms batch — not ours to fix), in our dispatch (fixable), or in
   the light's transition (a binding setting).

3. **Change exactly one knob** on the binding, nothing else. The leading
   candidate is `transition`: the default is `DEFAULT_TRANSITION = 1.0 s`, but the
   device batches at ~500 ms, so a 1.0 s transition can still be easing the
   previous batch when the next arrives — a "rubber-band" feel. Test ~0.3 s (what
   IKEA's own KAJPLATS reportedly uses). `acceleration` and the trailing-scroll
   suppression window are secondary candidates, each measured the same way.

4. **Re-measure identically and compare.** Either the change is clearly snappier
   and we adopt it, or nothing improves and the current default is now defended
   with numbers rather than assumed.

### Roles and constraints

- The owner runs the capture and turns the wheel — the physical-hardware step
  that cannot be done remotely. The assistant reads the **redacted** log,
  identifies the gap and proposes the single change; then repeat.
- The gist's numbers come from its author's unit/firmware; ours is mixed
  `1.8.7`/`1.9.15`. Use its **method** to measure our own hardware, do not
  hardcode its constants.
- Redact node IDs, entity IDs, serials and URLs from every captured line before
  it enters a report, per the repo's privacy rules. Remove the add-on patch after
  the run; it is wiped on any add-on update anyway.

### Outcome

A measurement-backed entry appended here: either "change the default transition
to X, with the before/after numbers", or "keep 1.0 s because the remaining lag is
in firmware and no binding knob moves it". Nothing changes in runtime code until
that entry exists. This does not touch the dual-button work in
`ROADMAP_BUTTON.md`; it is a wheel-behaviour item.

## 2026-07-18 raw-event timing and first-notch finding

A controlled run on Matter Server add-on 9.1.0 / matterjs-server 1.2.6 used its
native sanitized Switch-event logging and integration DEBUG timestamps. The
integration accounted for every cumulative notch without loss or duplication,
and raw-event completion to integration dispatch took approximately 4-10 ms.
The software dispatch path was therefore not the source of the perceived lag.

The device emitted `InitialPress` before the first cumulative count, but the
engine ignored it for rotation. The first actionable batch consequently arrived
roughly 0.5-0.6 seconds later. A representative sanitized fast sequence began
with counts `5 → 10 → 13 → 16 → 18`, completed, and continued in a new sequence
`3 → 7 → 11 → 14`; each cumulative report followed an InitialPress in the
observed stream. A 1.0 → 0.5 second target-transition comparison improved target
acknowledgement, while 0.3 seconds showed no repeatable further gain; neither
transition removed the initial wait.

The Matter Switch sequence explicitly generates InitialPress for every detected
press and orders a coincident MultiPressOngoing directly after it. The resulting
candidate therefore emits one eager notch on every rotary `InitialPress` and
credits all of them against cumulative ongoing/complete counts. Later counts
remain the source of truth for every remaining notch. `CurrentPosition = 0`
does not reset rotary accounting because it describes an individual release,
not completion of the cumulative multi-press series.

This is Implemented/Unit evidence only until an owner-authorized candidate is
released, deployed, and physically checked for single-notch latency, exact
fast-scroll totals, direction reversal, count wrap and both installed firmware
versions.

The same recorded fast stream also continued after the bound light had reached
its configured maximum. The candidate therefore avoids sending another
identical service payload once a bounded target is already at its effective
limit. Unit tests cover both limits for brightness, color temperature, volume,
cover position, climate temperature, fan speed and number value. Hue is
excluded because its intended behavior wraps through 360 degrees. This reduces
avoidable service traffic, but a deployed trace must still confirm that no
queue or later state movement remains at saturation. Hold-to-ramp additionally
pauses its recurring 200 ms interval when no further bounded change is possible;
release-direction accounting and the lost-release watchdog remain active.
