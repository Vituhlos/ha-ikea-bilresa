# BILRESA panel implementation roadmap

Status: **Read-only phases released; Phase 4 and the `0.5.9` binding editor are
implemented with local Static + Python/frontend Unit gates**

This roadmap turns `PANEL_DESIGN.md` into small implementation packages with
explicit gates. It is the execution contract for the owner, Codex and Claude
Code. `PROJECT_STATUS.md` remains the canonical record of what has actually
been implemented and verified.

Version labels below are provisional work-package names. They are not releases,
tags or evidence that a gate passed.

Visual-direction status on 2026-07-15: **selected, then revised the same day.**

The target is the two-layer model in `PANEL_DESIGN.md`: a grid of wheel cards
as the landing layer, and a wheel detail containing a 256 px wheel rail, with
live test as a view inside an opened wheel. It was chosen by comparing four
layouts in a browser prototype against measured layout.

`images/panel/04-selected-combined-direction.png` is **superseded and is not
an implementation target** — it shows master-detail as the landing page. So are
the other three images. Build from `PANEL_DESIGN.md`, not from the images.

Generated decorative graphics remain excluded; the spike must use supported
Home Assistant/Lit components.

## Entry gate

Panel implementation starts only after both conditions are satisfied:

1. The applicable physical checks in `HARDWARE_TEST.md` have been run and
   recorded, so panel failures cannot be confused with an unverified runtime
   baseline. **Still open.** As of 2026-07-15 the `v0.5.7-rc.3` run has partial
   hardware evidence — raw direction/channel routing and a representative
   gesture set on both firmware versions — but binding outcomes, lifecycle,
   failure injection, fallback and soak checks remain open, so the RC run is
   IN PROGRESS. `PROJECT_STATUS.md` is authoritative for the current state and
   for the current single best next action, which is not this gate. The panel
   program has not started and must not consume the hardware window.
2. The owner selects a visually grounded panel direction. **Satisfied on
   2026-07-15.** Four layouts were compared in a browser prototype and the
   two-layer model was selected; desktop, laptop, tablet and narrow layouts
   were measured. Dark-theme and non-default-theme review remains a Phase 0
   deliverable before production frontend code.

The comparison covered one wheel, multiple wheels, an unconfigured channel, a
disconnected event source, an unavailable target and an active live gesture.
Do not begin production frontend code from prose alone.

Design work carried out outside this repository does not satisfy gate 1 and
does not count as any validation state in `PROJECT_STATUS.md`.

## Non-negotiable engineering rules

- Work on one package and one validation gate at a time.
- Keep Matter access passive and read-only; the browser never connects to
  Matter Server.
- Do not change event decoding, gesture timing, binding behavior or stored
  configuration during the read-only `0.5.8` package.
- The Python integration is the only source of truth. Browser storage may hold
  disposable UI preferences only.
- Panel load, unload or failure must not affect event processing or bindings.
- Existing Home Assistant config flows remain a supported fallback.
- Use authenticated Home Assistant WebSocket commands and subscriptions. Never
  add a separate token, port, daemon, app or add-on.
- Validate and authorize every future mutation on the Python side. Do not expose
  a generic arbitrary-service-call endpoint.
- Keep user-facing English and Czech text aligned.
- Never expose Matter Server URLs, node IDs, serials or installation-specific
  identifiers in rendered diagnostics, logs, fixtures or screenshots.
- Preserve the validation vocabulary: Implemented, Static, Unit, CI, HA UI,
  Hardware and Released are separate states.
- Do not commit, push, release or deploy without the owner's authorization for
  that concrete snapshot.

## Target repository structure

Exact names may change during the technical spike, but responsibilities should
remain separated:

```text
custom_components/ikea_bilresa/
  panel.py                 panel lifecycle and frontend asset registration
  panel_api.py             authenticated read/subscription WebSocket API
  panel_models.py          privacy-reviewed frontend view models
  frontend/                built, versioned JavaScript assets

frontend/
  package.json
  package-lock.json
  tsconfig.json
  vite.config.ts
  src/
    panel.ts               custom-element entry point
    api/                   typed WebSocket client and contracts
    components/            reusable Home Assistant-style components
    views/                 overview, wheel detail, live test, diagnostics
    localize/              English/Czech frontend strings
  test/

tests/
  test_panel.py
  test_panel_api.py
  test_panel_models.py
```

Preferred frontend baseline is TypeScript plus Lit, bundled locally with Vite.
The technical spike must verify this against the then-current Home Assistant
frontend API before it becomes a permanent dependency. Production assets must
not load code, fonts or libraries from a CDN.

Generated frontend assets should be committed only if Home Assistant/HACS needs
them at installation time. CI must then rebuild them and fail when the committed
bundle differs from the source.

## Data boundaries

Define a versioned panel contract before building UI components. Keep three
models distinct:

1. **Overview model**: wheel display key, user-visible name, area, availability,
   last activity, last active channel and channel binding summaries.
2. **Live activity model**: bounded ephemeral actions such as direction, delta,
   presses, hold state, calculated result and dispatch outcome.
3. **Diagnostic model**: privacy-reviewed connection/source/schema/watchdog
   information compatible with the existing redaction policy.

The panel contract must not serialize coordinator internals directly. Introduce
explicit dataclasses or typed dictionaries and test their complete output. Use
an opaque panel key rather than exposing the Matter node ID. Device and entity
registry identifiers may be used only where required for authenticated Home
Assistant navigation and must not enter exported diagnostics.

The initial API should remain minimal:

- one command to fetch the current overview snapshot;
- one subscription for overview/connection changes;
- one opt-in subscription for live activity while the live-test view is open;
- no write command in `0.5.8`.

Subscriptions must unsubscribe on view close, panel disconnect, config-entry
unload and Home Assistant shutdown. Coalesce bursts and bound queues so rapid
rotation cannot create unbounded browser or backend memory growth.

## Package `0.5.8` - read-only panel

### Phase 0 - visual direction and technical spike

Deliverables:

- ~~exactly three visual directions based on real Home Assistant references~~
  — done 2026-07-15; four layouts compared in a browser prototype;
- ~~owner-selected desktop target~~ — done 2026-07-15, two-layer model;
- owner-reviewed dark theme, at least one non-default theme, and Czech/English
  text expansion, none of which the prototype has verified;
- proof that a custom integration can register, serve, cache-bust and unregister
  one local panel asset on the supported Home Assistant version;
- proof of a read-only authenticated WebSocket request and subscription;
- documented decisions for panel visibility, localization and asset packaging;
- no production UI or runtime behavior change.

Spike checks:

- install through the same HACS path as the integration, with no manual
  `configuration.yaml` or Lovelace resource entry;
- load, reload, unload and restart without duplicate panels or stale resources;
- verify desktop browser and HA companion-app WebView loading;
- verify that an unavailable panel asset does not break integration setup.

Exit gate: the owner selects the visual direction and the spike proves a safe
packaging path. Abandon or revise the architecture if either fails.

### Phase 1 - backend read model

Implement privacy-reviewed pure serializers over existing coordinator,
config-entry/subentry and registry state.

Deliverables:

- overview, channel summary, connection and diagnostics view models;
- opaque wheel key mapping;
- user-assigned device name and area resolution;
- human-readable binding/profile summaries;
- last-active-channel tracking based only on observed events;
- unavailable-target detection without changing binding execution;
- complete Python tests for normal, empty, degraded and malformed state.

Do not expose `BilresaCoordinator`, `BilresaWheel`, raw subentry dictionaries or
telemetry dictionaries directly to the frontend.

Exit gate: serializers are deterministic, bounded and privacy-reviewed; no
Matter or binding behavior changes; Python Static and Unit gates pass.

### Phase 2 - authenticated read-only API

Deliverables:

- snapshot WebSocket command;
- overview/connection subscription;
- live-activity subscription activated only by the live-test view;
- explicit voluptuous schemas and typed response payloads;
- subscription cleanup and backpressure/coalescing;
- config-entry lifecycle integration;
- tests for authentication, unload, reconnect, multiple clients and malformed
  commands.

Read access must follow Home Assistant permissions. If per-device permission
checks cannot be implemented safely in the first package, restrict the panel to
administrators and document that decision rather than returning excess data.

Exit gate: API tests pass, payload redaction is reviewed and a disconnected
frontend has no effect on Matter listening or binding dispatch.

### Phase 3 - frontend shell and overview

Deliverables:

- locally bundled custom element and panel lifecycle;
- Home Assistant theme variables, locale and narrow-layout support;
- loading, empty, ready, degraded and fatal-error states;
- summary header and a width-constrained grid with one card per physical wheel;
- three channel summaries per wheel, visible on the overview without drilling
  into a wheel;
- navigation from overview to wheel detail;
- retry/reconnect behavior without a full HA reload;
- no binding mutation controls, and no `Add control binding` action on any
  read-only surface — deep-link to the native config flow instead.

Frontend quality floor:

- semantic HTML and keyboard navigation;
- visible focus and WCAG 2.2 AA contrast;
- screen-reader names for status and navigation;
- reduced-motion support;
- usable at 320 CSS pixels wide;
- light/dark and common custom-theme resilience;
- Czech text expansion without truncation;
- no unsafe HTML rendering of device or area names.

Exit gate: TypeScript, lint, component tests and production build pass; visual
comparison passes against the selected target in all required states.

### Phase 4 - wheel detail and live test

Candidate status on 2026-07-16: **Implemented + Static + Python/frontend Unit;
CI, HA UI and Hardware pending.** The detail, rail, channel action rows, opt-in
live subscription and simple wheel diagnostics exist. The later `0.5.9`
candidate closes GAP-2/GAP-3 with structured binding results and per-action
Home Assistant dispatch status. The public action event still carries the
calculated delta rather than the original cumulative Matter count.

The simple wheel-status diagnostics requested with the detail are included here
from the existing overview contract. Phase 5 still owns expanded technical
details, the standard diagnostics link, release documentation and RC gates.

Deliverables:

- the 256 px wheel rail, switching wheels in one click, dropped below 620 px;
- a back affordance to the grid overview from every detail width;
- the two-column detail collapsing on *pane* width, not window width — with the
  rail present the pane is ~256 px narrower than the viewport, and a window
  breakpoint will keep two columns in a pane too narrow for them;
- channel and behavior detail;
- safe listen-only live mode;
- direction, cumulative count, calculated delta, channel, press and hold state;
- calculated-result and dispatch-outcome feedback where existing runtime
  evidence can support it, presented **result-first**: the outcome is the
  hero, the gesture is a caption (see `PANEL_DESIGN.md`, `Live test`);
- automatic subscription stop when leaving live mode;
- bounded activity presentation with clear `last active channel` wording.

The UI must not synthesize gestures, call Matter control commands or promise
responsiveness below the device's observed batching floor.

Exit gate: component/API tests pass and a physical BILRESA confirms all three
channels, slow/fast rotation, single/double/triple press, hold/release,
lost-release watchdog and both event sources without added action latency.

### Phase 5 - read-only diagnostics and `0.5.8` release candidate

Deliverables:

- simple connected/degraded/disconnected explanation;
- core-client versus passive-fallback state;
- bounded technical details and recovery guidance;
- link to standard Home Assistant diagnostics;
- English/Czech documentation and changelog;
- frontend development and release commands added to `DEVELOPMENT.md`;
- final screenshots only after the UI is verified.

Exit gate:

- Python and frontend Static + Unit gates pass;
- CI rebuilds and verifies the frontend bundle;
- HACS upgrade and cache-busting test passes;
- HA UI checks pass on desktop, mobile, light and dark themes;
- hardware/live-display checklist passes on the exact candidate;
- the owner explicitly authorizes commit, push, deployment and release.

## Package `0.5.9` - binding editor

Owner override on 2026-07-16: implementation proceeded before the deferred
physical-wheel gate so the integration and panel can be completed first.

Status: **Phases 1-3 implemented with local Static + Python/frontend Unit;
CI and HA UI deployment pending.**

### Phase 1 - mutation contract

- design explicit create, update and delete binding commands;
- reuse one shared Python validation layer with native config flows;
- require administrator authorization;
- validate wheel/channel uniqueness and supported targets;
- return field-level validation errors without partial writes;
- define optimistic-concurrency or revision checking to prevent overwriting a
  binding changed in another browser or native config flow;
- preserve subentries as the source of stored binding configuration.

### Phase 2 - editor UX

- profile-first progressive disclosure;
- wheel, channel, target and behavior selection;
- review-before-save for material changes;
- unsaved-change warning;
- unavailable/removed-target warnings;
- success, conflict and retry states;
- native subentry reconfigure flow retained as recovery fallback.

### Phase 3 - destructive and recovery paths

- explicit confirmation for binding deletion;
- never delete a wheel, device, entity or Matter node from this panel;
- recover cleanly from integration reload during editing;
- verify that a failed write leaves the previous binding active;
- test simultaneous editors and stale revisions.

Exit gate: full Python/frontend tests, permission tests, CI, HA UI testing and
physical verification that edited bindings perform exactly as the native flow.

## Package `0.5.10` - guided workflows and polish

- refine light, scenes, media, cover, climate, custom and events-only profiles;
- copy a channel and copy settings between wheels;
- temporary channel disablement if it can be represented without ambiguous
  stored state;
- target conflict and availability guidance;
- improved first-run, empty, degraded and recovery experiences;
- comprehensive accessibility and companion-app polish;
- performance and bundle-size review.

Every profile remains a presentation over the existing binding model. If a
requested workflow requires a stored-config migration or behavior change, split
it into a separately versioned package with its own tests and hardware gate.

## Package `0.5.11+` - optional expansion

Evaluate individually rather than treating this as a guaranteed bundle:

- sanitized import/export;
- guided creation of standard Home Assistant automations;
- additional target types backed by real hardware testing;
- bounded troubleshooting observations;
- optional non-admin read-only access with verified permission filtering.

Do not build a parallel automation, scene, history, authentication or Matter
control system.

## CI and validation plan

### Python gate

Run the existing repository checks plus panel modules:

```powershell
python -m compileall -q custom_components tests
ruff format --check custom_components tests
ruff check custom_components tests
mypy custom_components/ikea_bilresa
python -m pytest -q
git diff --check
```

The Windows Home Assistant dependency limitation remains a recorded `Unit not
run` when applicable; GitHub Actions is the canonical Python 3.14 environment.

### Frontend gate

Finalize exact script names during the spike. The required capabilities are:

```text
npm ci
frontend format check
frontend lint
TypeScript type check
frontend unit/component tests
production bundle build
committed-bundle reproducibility check
```

Pin Node and package-manager versions in CI and commit the lockfile. Do not rely
on globally installed frontend tools.

### HA UI gate

- clean install and upgrade through HACS;
- integration setup, reload, unload, HA restart and browser refresh;
- no duplicate sidebar entry or stale bundle;
- reconnect after frontend WebSocket loss;
- desktop and companion-app mobile layouts;
- light, dark and at least one non-default theme;
- English and Czech;
- loading, empty, degraded, disconnected and unavailable-target states;
- keyboard-only and screen-reader smoke test.

### Hardware gate

Extend `HARDWARE_TEST.md` only when a concrete panel package exists. Test:

- both physical wheels and all three channels;
- one notch, slow rotation and fast batched rotation;
- single, double and triple press;
- hold, release and lost-release watchdog;
- core Matter client and passive WebSocket fallback;
- integration reload, HA restart and Matter reconnect;
- live panel closed versus open to prove no behavioral or latency regression;
- no raw private identifiers in screenshots, panel errors or diagnostics.

## Performance and reliability budgets

Initial budgets to validate during the spike:

- production panel bundle target below 200 KiB gzip unless measured evidence
  justifies more;
- no polling when a subscription can provide the state;
- no unbounded event arrays, queues, tasks or listeners;
- coalesce visual updates during rapid batches without changing backend action
  dispatch;
- panel rendering must not delay coordinator callbacks;
- no persistent recorder writes for live activity;
- clean subscription and custom-panel teardown on unload.

Hardware firmware batching remains the responsiveness floor. Measure panel
latency from the integration's received action to visible UI update separately
from device-to-Matter latency.

## Documentation required for every package

- update `PROJECT_STATUS.md` with files, exact commands, results and open gates;
- update this roadmap's package state without claiming future phases complete;
- update `CHANGELOG.md` for user-visible behavior;
- keep `README.md` and `README.cs.md` aligned when installation or usage changes;
- update `DEVELOPMENT.md` when tooling or build steps change;
- update `HARDWARE_TEST.md` for new physical checks;
- record architectural decisions that later agents cannot safely infer from
  code alone.

## Definition of done for the panel program

The panel program is complete only when:

- users can understand every wheel and channel without config-entry jargon;
- read-only state and live activity are accurate and bounded;
- administrators can safely manage bindings with the same validation and
  results as native flows;
- native flows remain a working fallback;
- the panel survives install, upgrade, reload, restart and frontend reconnect;
- desktop/mobile, themes, Czech/English and accessibility gates pass;
- Python and frontend Unit + CI gates pass for the exact revision;
- applicable behavior is observed on physical BILRESA hardware;
- failure of the panel cannot stop existing wheel actions;
- no separate add-on, daemon, credential or Matter control path is introduced.

## Open decisions owned by the technical spike

Resolve and record these before Phase 1:

- sidebar visibility by default versus an admin-only entry point;
- exact supported API for panel registration and asset serving;
- Lit/Vite versions and generated-bundle packaging;
- localization source and fallback behavior;
- stable opaque wheel key mapping;
- how much Home Assistant registry navigation is exposed;
- administrator-only versus permission-filtered read access;
- frontend test runner and visual-regression tooling;
- cache-busting behavior across HACS upgrades.

The panel is not the next action. `PROJECT_STATUS.md` holds the current single
best next action and is authoritative; as of 2026-07-15 that is the `v0.5.7`
low-latency release candidate and its latency verification, not this program.

The visual-direction step is done. When the `v0.5.7` hardware run closes,
`0.5.8` Phase 0 begins with the dark-theme and localization review plus the
smallest possible read-only technical spike.
