# Latency, telemetry and Matter recovery roadmap

This is the implementation contract for the next responsiveness and resilience
work after the current panel Phase 0 dirty tree is secured. It is deliberately
separate from `PANEL_ROADMAP.md`: the integration owns gesture semantics,
measurements and recovery; the optional panel only presents a stable read-only
view of those facts.

No item below is implemented merely because it is documented here. Keep
Implemented, Static, Unit, CI, Hardware and Released separate in
`PROJECT_STATUS.md`. Do not mix these packages with the current undeployed
companion-app header fix.

## Product goals

1. Make direct single-press control feel immediate when the configured gesture
   is unambiguous.
2. Measure the whole observable pipeline instead of inferring latency from one
   Home Assistant timestamp.
3. Preserve exact multi-press, hold, public event and automation behavior.
4. Recover automatically after a Matter Server or core Matter reload.
5. Expose bounded, anonymous read-only metrics that a future Latency Lab can
   display without opening another Matter connection.

## Non-goals and truth boundaries

- The integration remains a passive Matter event consumer and issues no Matter
  device-control commands.
- Home Assistant services remain the target-control path. Do not add direct
  Shelly RPC or vendor-specific shortcuts.
- A Home Assistant target state change is an acknowledgement visible to HA,
  not proof of the instant when a relay or lamp physically changed.
- A Matter event timestamp is useful only when its `timestamp_type` and clock
  relationship are understood. Unsupported or incomparable timestamps remain
  `unknown`; never manufacture a duration.
- An `event_number` gap is a discontinuity, not automatically a lost BILRESA
  action. Other Matter events, reconnect boundaries and server backpressure can
  also explain a gap.
- No persistent recorder history, unbounded arrays, household identifiers,
  entity IDs, node IDs, serials or target names belong in latency telemetry.

## L0 - protect the current panel handoff

Before backend work starts:

- preserve Claude Code's dirty `PROJECT_STATUS.md`, panel stub and
  `PANEL_DESIGN.md` changes;
- validate and deploy the companion-app header fix as its own candidate only
  after owner authorization;
- verify on a real phone that the menu button exits the custom panel;
- run the explicit missing-panel-asset degradation test when the owner accepts
  that destructive-but-recoverable check;
- do not combine the header fix with latency runtime behavior.

Exit gate: the dirty Phase 0 work has an exact recorded revision and the tree is
safe for the next coherent package.

## L1 - measurement foundation

Add one internal latency context that follows an actionable gesture through the
existing pipeline. Capture monotonic host timestamps at these boundaries where
available:

1. core-client or dedicated-WebSocket callback entry;
2. coordinator decode and dispatcher emission;
3. binding action selection;
4. Home Assistant service dispatch;
5. first matching target-state acknowledgement.

Also retain the Matter event's `timestamp`, `timestamp_type` and `event_number`
inside the short-lived private context. Normalize device-to-host latency only
when the timestamp contract is proven for the active server/device. Otherwise
report the device-side segment as unavailable while still reporting host-side
segments accurately.

Telemetry design:

- bounded rolling samples, initially at most 128 completed actions per binding
  and 256 stream observations globally;
- compute count, median, p95 and maximum on diagnostics/API read, not on every
  Matter callback;
- separate press, rotation and hold measurements;
- count duplicates, regressions and discontinuities without labelling every gap
  as packet loss;
- reset sequence expectations across reconnect/reload boundaries;
- correlate only state changes that belong to the active command window;
- keep the existing DEBUG trace available during development, then disable the
  temporary logger override after aggregate telemetry is verified.

Tests and gates:

- deterministic monotonic-clock tests for every stage and missing stage;
- timestamp-type tests including unsupported and unsynchronized clocks;
- bounded-memory and privacy/redaction tests;
- duplicate, out-of-order, discontinuity and reconnect tests;
- both event sources produce the same metric schema;
- Static + Unit + CI, then a short physical sample on the current channel-2
  light path without claiming physical relay timing.

## L2 - explicit Instant response policy

Extend the existing per-binding response selector from two policies to three:

- **Instant press:** execute the single action once on `InitialPress`;
- **Fast release:** keep the current exactly-once `ShortRelease` behavior;
- **Multi-press aware:** keep exact completion-based single/double/triple
  binding behavior on `MultiPressComplete`.

Safety contract:

- existing bindings keep their stored policy; no migration silently changes
  behavior;
- Instant is opt-in until physical evidence justifies any profile default;
- Instant is rejected with double- or triple-press targets;
- before implementation, decide and test the long-press contract explicitly.
  `InitialPress` cannot know whether the gesture will become a hold, so Instant
  must either be rejected for a distinct hold action or define a deliberate,
  non-duplicating press-then-hold composition. Do not guess;
- `ShortRelease`, `LongPress`, `LongRelease` and `MultiPressComplete` cannot
  repeat the instant single action;
- lost completion, reconnect, unload and a clearly new gesture recover the
  guard safely;
- public event entities, device triggers and `ikea_bilresa_event` retain their
  current exact completion semantics in all policies;
- English and Czech copy explain the latency/gesture trade-off before save.

Tests and gates:

- single, rapid repeated single, double, triple, hold and lost-release
  sequences for both installed firmware event shapes;
- config create/reconfigure/copy validation and backwards-compatible defaults;
- exactly-once tests across reconnect and unload;
- Static + Unit + CI;
- focused Hardware A/B on one direct light binding: Instant versus Fast, with
  the L1 measurement foundation active.

## L3 - Matter source self-healing

Make temporary core Matter unavailability an expected lifecycle state rather
than an opaque exception:

- replace `list index out of range` with an explicit
  `Matter integration temporarily unavailable` reason when no loaded core
  Matter config entry exists;
- retain the current bounded switch to the passive dedicated WebSocket when the
  core source stays unavailable;
- while on fallback, probe the URL-matched core client at a conservative
  interval;
- switch back only after the core client is stable for multiple consecutive
  checks;
- perform an atomic handover: never run both streams as active dispatch sources
  and never duplicate an action;
- apply cooldown/backoff to prevent source flapping;
- expose fallback count, recovery count, current source, last transition reason
  and last transition time in bounded diagnostics;
- keep the integration operational if either source alone remains healthy.

Tests and gates:

- Matter Server restart, core config-entry reload and temporary empty-entry
  list;
- incompatible/replaced core client and dedicated-WebSocket reconnect;
- no overlap, duplicate delivery, task leak or reconnect loop;
- Static + Unit + CI;
- controlled live restart/reload showing fallback and automatic return without
  a manual BILRESA reload.

## L4 - stable read-only Latency Lab API contract

Claude Code owns the Latency Lab frontend. The backend first supplies a small,
versioned, read-only WebSocket contract through the panel API established by
Phase 0. The frontend must not parse logs, inspect private coordinator objects
or calculate protocol truth independently.

Suggested response shape (names provisional until implementation review):

```json
{
  "schema_version": 1,
  "measurement_state": "idle",
  "active_source": "core_matter_client",
  "sample_limit": 128,
  "samples": {
    "press": {
      "count": 0,
      "event_to_dispatch_ms": {"median": null, "p95": null, "max": null},
      "dispatch_to_state_ms": {"median": null, "p95": null, "max": null}
    }
  },
  "stream_health": {
    "duplicates": 0,
    "regressions": 0,
    "discontinuities": 0,
    "reconnects": 0,
    "fallbacks": 0,
    "recoveries": 0
  },
  "limitations": ["physical_actuation_not_observed"]
}
```

Contract requirements:

- administrator-only while the panel program remains admin-only;
- an explicit start/stop measurement session may clear ephemeral samples but
  must not alter bindings, devices or Matter state;
- automatic timeout and unsubscribe when the Lab closes;
- bounded update rate so rapid rotation cannot delay backend action dispatch or
  flood the browser;
- result-first explanations distinguish integration latency, target-state
  acknowledgement and unobservable physical latency;
- stable schema version and tests shared between Python and frontend fixtures;
- normal diagnostics remain useful without opening the panel.

Frontend exit gates remain in `PANEL_ROADMAP.md`: desktop/mobile, light/dark,
Czech/English, keyboard, screen reader, reconnect and real-device checks.

## Recommended delivery order

1. Finish L0 without mixing in runtime work.
2. Implement L1 and collect a small trustworthy baseline.
3. Implement L2 against those measurements; keep Instant opt-in.
4. Implement L3 as an independent lifecycle/reliability package.
5. Freeze the L4 API schema, then hand it to Claude Code for the Latency Lab.

L1 must precede L2 so Instant is evaluated with evidence. L3 may be developed
before or after L2 but should not share its commit. L4 waits for the metric
model to stabilize; otherwise frontend work will be repeatedly rewritten.

## Rough effort

- L1: large, approximately two to four focused coding/verification sessions;
- L2: medium, approximately one to two sessions plus a short physical A/B;
- L3: medium, approximately one to two sessions plus a controlled restart;
- L4 backend contract: medium, approximately one to two sessions;
- Latency Lab frontend: separately owned by Claude Code.

These are complexity estimates, not calendar promises. CI and physical evidence
remain separate gates and may expose additional work.
