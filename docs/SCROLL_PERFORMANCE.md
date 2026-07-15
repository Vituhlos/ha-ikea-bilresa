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
