# Stabilization roadmap

This roadmap is the ordered implementation contract for the pre-1.0 `0.5.x`
release train. `PROJECT_STATUS.md` remains the live handoff and validation
record. A version number below is a work package, not a claim that a release or
tag exists.

Every package must keep these states separate: Implemented, Static, Unit, CI,
Hardware, and Released. No package may be tagged without the owner's explicit
request. Device-facing packages require the applicable checks in
`HARDWARE_TEST.md`.

| Work package | Scope | Current state | Exit gate still required |
|---|---|---|---|
| `0.5.1` | matter.js 1.1.7/schema-11 baseline, redacted protocol fixtures, lost-release watchdog | Implemented + Static + Unit + CI | Complete hardware RC |
| `0.5.2` | URL-aware core-client reuse and runtime dedicated-WebSocket fallback | Implemented + Static + Unit + CI | Both event sources on hardware |
| `0.5.3` | Linux HA test harness and broad integration coverage | 39 tests passed in CI; total coverage 51% | CI coverage above 95% |
| `0.5.4` | Redacted diagnostics and bounded runtime telemetry | Implemented + Static + Unit + CI | Live diagnostics privacy review |
| `0.5.5` | Measured fast-scroll optimization, only if telemetry demonstrates need | Evidence-based no-op documented | Hardware soak test without lost delta |
| `0.5.6` | Binding copy flow and mode presets | Implemented + Static + Unit + CI | Config-flow UI hardware check |
| `0.5.7` | Degraded-state System Health and actionable Repairs | Implemented + Static + Unit + CI | Live failure-injection checks in HA |

“Implemented” in this table does not close a package. The snapshot is
CI-verified but none of these packages is stable-released or hardware-verified.
The exact live validation record is in `PROJECT_STATUS.md`.

The remote is user-driven and may legitimately remain untouched for days.
Therefore absence of events alone must not create a Repair. System Health may
show the last event time, but Repairs are reserved for observable connection or
protocol failures that require user action.

## Versioning policy

During private pre-1.0 development, the third component advances for each small,
backwards-compatible and independently verifiable work package. Release
candidates use `v0.5.N-rc.K`. A larger configuration-model change or intentional
compatibility break requires a minor-version change instead.

If several sequential work packages are shipped in one snapshot, the version
uses the highest included package number. The current combined snapshot includes
`0.5.1` through `0.5.7`, so its candidate version is `v0.5.7-rc.1`, not
`v0.5.1-rc.1`.

## Cross-cutting compatibility rule

All Matter access stays behind an event-source abstraction. The preferred path
reuses Home Assistant's connected Matter client when it represents the same
server URL. The passive dedicated WebSocket remains the compatibility fallback.
Neither path may issue device-control commands.

The `0.5.5` measurement and no-accumulator decision is documented in
`SCROLL_PERFORMANCE.md`.

## Runtime behavior polish before the panel

`RUNTIME_POLISH_ROADMAP.md` is the ordered implementation contract for the
post-`rc.3` behavior findings: explicit button-response policy, unavailable
target safety, mode/domain validation, measured transitions, gesture-aware
trailing-scroll protection, velocity-based acceleration, predictable
resynchronization and Home Assistant-native event polish.

These items remain in the `0.5.7` release-candidate train until the runtime
baseline is stable. They take precedence over starting new panel runtime code;
panel design work may continue independently because it does not alter the
integration runtime.

## BILRESA dual button (E2489) program

Support for the button-only BILRESA variant is specified in its own
`ROADMAP_BUTTON.md`, kept separate from this wheel roadmap because it is a
different device class. It is scoped to a `0.6.x` minor train and does not change
or close any `0.5.1`-`0.5.7` wheel gate. The integration already half-discovers
the device today (see that file's "current defect"), so its first package is a
discovery-correctness fix, not a feature.

## Future BILRESA panel program

The optional first-party panel is specified in `PANEL_DESIGN.md` and governed
by the gated implementation plan in `PANEL_ROADMAP.md`. It does not change or
close any `0.5.1`-`0.5.7` stabilization gate.

Panel work begins only after the current physical release-candidate baseline is
recorded. Its first package is additive and read-only: no Matter protocol,
gesture, binding or stored-config changes. Binding writes and guided workflows
remain later packages with independent Unit, CI, HA UI and Hardware gates.
