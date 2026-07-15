# Project status and agent handoff

Last updated: **2026-07-15 by Codex**

This is the canonical live state for the owner, Codex and Claude Code. Read it
with `AGENTS.md`, `docs/DEVELOPMENT.md`, `docs/ROADMAP.md`, and the device-facing
references before making changes.

## Validation vocabulary

| Label | Meaning |
|---|---|
| **Implemented** | Code exists; verification is not implied. |
| **Static** | JSON/syntax/format/lint/type/diff checks passed. |
| **Unit** | Automated tests passed locally or in CI. |
| **CI** | GitHub Actions passed for the exact revision. |
| **Hardware** | Observed on a physical BILRESA with versions recorded. |
| **Released** | Included in an owner-approved tag/release. |

Never collapse these states or infer Hardware from Static, Unit, CI, MCP, or
earlier device-reference observations.

## Repository state

- Active publication branch: `agent/stabilize-0.5-x`, created from `main` at
  `f1e7583`.
- `origin/main`: `f1e7583 docs: add DEVICE_REFERENCE — Matter/HA facts for the
  BILRESA wheel` before this stabilization snapshot is merged.
- Before Claude's reference commit, `main`/`origin/main` were at `662762a`.
- Working tree: clean after the final CI-status commit described below. Preserve
  any later changes and always verify with `git status --short`.
- The owner authorized commit, push, a GitHub CI/PR workflow, an RC release and
  controlled Home Assistant deployment on 2026-07-15. Record their concrete
  results here after each gate; authorization is not proof that a gate passed.
- Latest stable release remains `v0.5.0`. Prerelease `v0.5.7-rc.3` was published
  from CI-verified commit `6db5b5b`; it contains all seven work packages, the
  overview cleanup and serial-independent Matter device linking. Draft PR #1
  remains open and `main` has not been merged.
- The `0.5.1`–`0.5.7` numbers are ordered work packages, not existing releases.
  Candidate naming is `v0.5.N-rc.K`; the third component advances gradually.

Claude's committed `docs/DEVICE_REFERENCE.md` originally contained
installation-specific identifiers. The working-tree version is now sanitized
while retaining protocol facts. The sensitive version remains in commit
history; do not publish another release until the owner decides whether and how
to clean history. Never paste those identifiers into issues, logs or chat.

## Home Assistant MCP observation

Read-only MCP checks succeeded earlier in this task:

- native remote server available; 78 tools listed;
- `ha_get_system_health` succeeded;
- Home Assistant Core 2026.7.2, HA OS 18.1, Matter Server add-on 9.0.4,
  matterjs-server 1.1.7, matter.js 0.17.4, schema 11, ha-mcp 7.12.3;
- core Matter and `ikea_bilresa` config entries were loaded;
- exact-name log searches returned no current Matter/BILRESA entries.

During that earlier read-only phase no Home Assistant state was changed. The
running custom integration was an older deployed copy and did not validate the
working tree. MCP does not replace physical BILRESA input.

After owner authorization, HACS explicitly installed `v0.5.7-rc.1` and Home
Assistant was restarted with a valid preflight config check. Non-hardware smoke
checks after restart established:

- HACS installed version `v0.5.7-rc.1`;
- `ikea_bilresa` config entry state `loaded`;
- parent reconfigure and binding subentry schema are available;
- event source `core_matter_client`, two discovered wheels, two bindings, and no
  event-source fallback;
- diagnostics contract available, with all 14 sampled URL/node/name/title/
  serial/target fields redacted and bounded recent-event metadata present;
- no matching `ikea_bilresa` system-log or error-log entries after restart.

These checks are Home Assistant smoke/diagnostic evidence, not Hardware.

## `0.5.x` stabilization train

All seven packages now have an implementation baseline. Their exit gates remain
open as shown below.

| Package | Implemented behavior | Current validation |
|---|---|---|
| `0.5.1` | Matter Server 9.0.4 / matterjs-server 1.1.7 / schema-11 contract fixture and validation; hold-to-ramp lost-release watchdog plus stop on new gesture, connection transition and unload | Implemented + Static + Unit + CI; Hardware pending |
| `0.5.2` | Reuse core Matter client only for matching server URL; monitor replacement/unavailability; one-way initial/runtime fallback to dedicated passive WebSocket; fallback telemetry | Implemented + Static + Unit + CI; Hardware pending |
| `0.5.3` | Python 3.14 Linux HA test dependencies, pytest coverage reporting, and expanded binding/config-flow/coordinator/diagnostics/System Health/Matter tests | Harness + Static + Unit + CI; 39 tests passed, coverage 51%; >95% gate open |
| `0.5.4` | Stronger diagnostics redaction and bounded counters/recent event metadata without node IDs or entity IDs | Implemented + Static + Unit + CI; live diagnostics privacy review pending |
| `0.5.5` | Evidence-based decision to retain immediate delta dispatch and avoid a latency-only accumulator; explicit measurement/revisit criteria | Documented; hardware soak gate pending |
| `0.5.6` | Two-stage binding creation with light/media/cover/climate/scenes/custom profiles and copy-from-existing defaults; English/Czech UI | Implemented + Static + Unit + CI; HA UI/hardware check pending |
| `0.5.7` | Degraded-state-safe System Health with source/last event/fallback detail; existing delayed connection Repair retained; failure tests authored | Implemented + Static + Unit + CI; live failure injection/Hardware pending |

The lack of user activity alone deliberately does not create a Repair: a remote
may legitimately be untouched for days. Repairs are reserved for an observable
connection/protocol failure.

## Other active working-tree behavior

- Scene cycling with ordered scene selector.
- Hold-to-ramp with alternating software-selected direction.
- Parent Matter Server URL reconfigure flow.
- System Health registration.
- Discovery exemption decision in `docs/DISCOVERY.md`.
- Internal evidence-only `quality_scale.yaml`.
- English/Czech documentation and translations.
- Shared handoff entry points: `AGENTS.md`, `CLAUDE.md`, this file, and `docs/`.
- Explicit per-binding fast or multi-press-aware button response; this
  post-`rc.3` change is not deployed or hardware-verified.
- Gesture-aware trailing-scroll suppression, time-based acceleration,
  state-observed resynchronization and HA-native event polish; all are
  post-`rc.3`, undeployed and not hardware-verified.

## Integration-overview cleanup (current working tree)

The post-`v0.5.7-rc.1` working tree now implements a focused Home Assistant UI
model cleanup intended for `v0.5.7-rc.2`:

- the redundant Matter Server connection binary sensor and its
  `DeviceEntryType.SERVICE` device are retired, leaving only physical BILRESA
  devices in the integration overview;
- config-entry migration `1.1 -> 1.2` removes the obsolete entity and service
  device registry records on upgrade, without touching physical Matter devices;
- the same integration-wide connection state remains in System Health, config
  entry state, delayed Repairs and redacted diagnostics;
- automatically generated binding titles use the compact, language-neutral
  `Wheel name · CH N` form; generated legacy titles are migrated while custom
  titles are preserved;
- the displayed integration name is shortened to `IKEA BILRESA`, and the
  manifest version is aligned to `0.5.7-rc.2`;
- brand/icon assets are deliberately unchanged because the owner is handling
  them separately.

Files involved: `custom_components/ikea_bilresa/__init__.py`, deleted
`binary_sensor.py`, `config_flow.py`, new `presentation.py`, manifest and
English/Czech strings, `hacs.json`, both READMEs, `CHANGELOG.md`, and regression
tests in `tests/test_init.py`, `tests/test_presentation.py`, and
`tests/test_config_flow.py`.

Validation for this uncommitted working tree:

```text
JSON parsing (manifest/strings/en/cs)               passed
python -m compileall -q custom_components tests     passed
mypy custom_components/ikea_bilresa                 passed (14 source files)
initial Ruff check                                  import formatting only
ruff check --fix + ruff format on affected files    completed
final ruff format --check (26 files)                 passed
final ruff check                                     passed
final mypy (14 source files)                         passed
presentation-helper behavioral smoke                passed
git diff --check                                     passed (CRLF warnings only)
python -m pytest -q                                 11 collection errors:
  ModuleNotFoundError: No module named 'homeassistant'
```

The pytest result is **Unit not run**, matching the existing Windows/Python
3.13 environment limitation. CI has not run for this working tree. The updated
overview and registry migration have not yet been exercised in a running Home
Assistant. No hardware behavior changed and no post-v0.5.0 work is
hardware-verified.

Publication and deployment results recorded later on 2026-07-15:

- implementation commit `cc3a20f` (`fix: clean up integration overview`) was
  pushed to `agent/stabilize-0.5-x` and updated draft PR #1;
- GitHub Actions run `29406230111` passed for exact commit `cc3a20f`: hassfest,
  HACS validation, Ruff and mypy passed; 45 tests passed in 0.75 s and total
  coverage was 53%;
- prerelease `v0.5.7-rc.2` was published from exact commit `cc3a20f`;
- HACS installed exactly `v0.5.7-rc.2`; the pre-restart Home Assistant config
  check returned valid with no errors, and Home Assistant restarted normally;
- post-restart read-only MCP checks found the integration loaded, connected via
  `core_matter_client`, with two physical devices, six `ikea_bilresa` event
  entities and two binding subentries;
- both generated binding titles migrated to the `Wheel name · CH 1` format;
  the obsolete service device and connection entity were absent;
- exact-domain system-log search returned no entries; the raw error log only
  contained Home Assistant's standard warning that a custom integration is not
  tested by Home Assistant Core.

This establishes Implemented + Static + Unit + CI + Released and a successful
non-hardware Home Assistant deployment smoke test for the overview cleanup. It
does not establish Hardware or complete visual review in the owner's browser.

## Future BILRESA panel concept

`docs/PANEL_DESIGN.md` now records the agreed product direction for an optional
first-party BILRESA panel inside Home Assistant. The native integration page
remains the installation and registry surface; the future panel would present
physical wheels, channel behavior, a guided binding editor, safe live hardware
event visualization and redacted diagnostics.

`docs/PANEL_ROADMAP.md` is the execution contract for that concept. It splits
the work into a visually selected and technically proven read-only `0.5.8`, an
administrator-only binding editor in `0.5.9`, workflow polish in `0.5.10`, and
individually evaluated later capabilities. Every phase has explicit privacy,
permission, frontend, CI, HA UI and physical-hardware gates.

The owner selected the panel's desktop direction on 2026-07-15 and **revised it
the same day**. The earlier record in this file — master-detail as the landing
structure, targeting `04-selected-combined-direction.png` — is superseded and
must not be built from.

The current direction is a two-layer model: a grid of wheel cards as the
landing layer, and a wheel detail containing a 256 px wheel rail with Channels,
Live test and Diagnostics as views of the opened wheel. The rail is a switcher
inside the detail, never the landing page.

All four images under `docs/images/panel/` are now superseded and are **not**
implementation targets; `04-selected-combined-direction.png` in particular
shows the rejected master-detail landing, an `Add control binding` action on a
read-only surface, and a sidebar labelled `Wheel Workspace`/`WHEELY`. Build
from `docs/PANEL_DESIGN.md` only. AI-generated decorative bars, coloured icon
circles and progress artwork are not implementation requirements.

The revision came from a browser prototype held **outside this repository**, at
`bilresa-panel-lab/compare.html` alongside the repo checkout. It is not a build
dependency, is not referenced by any code, and nothing in this repository needs
it to check out, test or run. It compared four layouts — grid, grid with a chip
switcher, grid to master-detail, and master-detail as landing — on measured
layout rather than prose. What it established:

- a rail landing page shows the channels of exactly one wheel at any wheel
  count, whereas the grid shows every channel of every wheel (6 for two wheels,
  15 for five); the panel's stated product intent requires the latter;
- a 300 px rail collapsed the detail to a single column on a 1024 px laptop; at
  256 px — Home Assistant's own sidebar width — the detail keeps two columns;
- the two-column detail must break on pane width, not window width;
- no horizontal page scroll and no element escaping the frame at 1280, 1024,
  900, 380 or 320 px, at one, two and five wheels, in normal and degraded state.

Explicitly **not** established by the prototype, and not claimable from it:
dark and non-default themes (defined in variables but never visually reviewed),
Czech/English text expansion, keyboard navigation, focus order, screen-reader
labels, WCAG 2.2 AA contrast, reduced motion, and anything about what Home
Assistant will actually register or serve. Prototype layout evidence is not
Implemented, Static, Unit, CI, HA UI or Hardware.

No panel code has been started. The technical spike remains open.

The documented delivery sequence is additive and provisional: a read-only panel
in planning package `0.5.8`, binding editing in `0.5.9`, workflow polish in
`0.5.10`, and carefully selected expansion afterward. A stored-configuration or
subentry-model migration still requires a minor version under `ROADMAP.md`.

This is **design documentation only**. No frontend, WebSocket API, runtime
behavior, binding storage, Home Assistant deployment or hardware behavior was
changed or verified. The physical `v0.5.7` checklist remains the release gate;
see `Single best next action` below for the current priority, which is not the
panel.

### Panel direction revision on 2026-07-15 (Claude Code)

Claude Code revised the panel direction with the owner and rewrote the affected
documentation. Files changed: `docs/PANEL_DESIGN.md`, `docs/PANEL_ROADMAP.md`
and this handoff. No code, no images and no runtime file was touched.

This revision was made **concurrently with Codex's uncommitted low-latency and
hardware work in the same tree.** Claude Code touched only the three files
listed above; every other modified file in `git status` belongs to Codex. If
Codex held any of these three files in memory from before 17:05 and writes them
back, this revision will be silently lost — re-read before writing.

Documentation validation on 2026-07-15:

```text
git diff --check    passed (CRLF conversion warnings only)
panel-doc trailing-whitespace/final-newline check    passed
```

No static code checks, automated tests, CI, Home Assistant deployment or
hardware test was run because this change adds design documentation only.
Files in this documentation change are `docs/PANEL_DESIGN.md`,
`docs/PANEL_ROADMAP.md`, `docs/ROADMAP.md`, `docs/images/panel/*.png`, and
`PROJECT_STATUS.md`.

## Runtime behavior polish roadmap

`docs/RUNTIME_POLISH_ROADMAP.md` records the owner-approved runtime hardening
program discovered during the 2026-07-15 physical run. It is deliberately
separate from the revised two-layer panel program and orders eight packages by
safety and user impact:

1. explicit fast versus multi-press-aware button response;
2. unavailable/unknown target safety;
3. mode/target domain validation;
4. measured transition presets;
5. gesture-aware trailing-scroll protection;
6. velocity-based acceleration;
7. predictable off/on and external-state resynchronization;
8. Home Assistant-native event polish.

R1 now replaces the provisional automatic ShortRelease heuristic with an
explicit per-binding policy. New profiles select fast response; existing and
copied bindings without the field remain completion-aware. The native HA form
contains English/Czech trade-off text and rejects a fast policy combined with a
double/triple target. Runtime polish stays in the `0.5.7` candidate train; the
separate read-only panel remains planned for `0.5.8` after runtime
stabilization.

R1 is currently **Implemented + Static + Unit + CI**. Regression
tests are authored for single/double/triple completion, hold, lost completion,
reconnect, unload, old-binding compatibility and config-flow conflicts, but
HA UI and Hardware remain pending. The local Windows environment still cannot
run Unit because it lacks Home Assistant; the Unit result comes from the exact
Linux CI revision recorded below.

R2 is also **Implemented + Static + Unit + CI**. A shared target
availability guard covers brightness, colour temperature, colour, volume,
cover, climate, fan, number/input_number and button/scene targets. Missing,
`unknown` or `unavailable` targets receive no service call; an active ramp
stops, log messages are transition-deduplicated, and recovery clears the stale
tracked value. Parameterized unavailable-state, ramp, recovery and button tests
passed in CI. HA UI and Hardware remain pending.

R3 is **Implemented + Static + Unit + CI**. Config flow and
runtime use one compatibility map for light, media_player, cover, climate, fan,
number and input_number targets. The form returns a localized field error and
preserves its input; an incompatible legacy binding logs once and issues no
scroll service. Mapping and helper-level flow tests are authored. Full
create/edit/copy HA UI execution and Hardware remain pending.

R4 transition A/B tuning is explicitly **deferred for future physical work** at
the owner's request. No transition default or profile value changed.

R5 is **Implemented + Static + Unit + CI**. The coordinator exposes private per-channel raw
gesture metadata; bindings record scroll generations and the button's preceding
boundary. Only the preceding generation is suppressed, a deliberate new
`InitialPress` passes immediately, and a two-second timeout is only a lost-event
fallback. Authored tests cover trailing, new and missing-boundary sequences.
Timestamped live fixtures and both-firmware Hardware remain pending.

R6 is **Implemented + Static + Unit + CI**. Acceleration now uses decoded notches over a
bounded monotonic-time window, not one Matter batch size. It resets on idle,
direction changes, gesture boundaries and reconnect, caps the multiplier, and
preserves every delta when acceleration is zero. The default remains disabled.
Deterministic tests passed in CI; slow/medium/fast Hardware samples on both
firmware versions remain pending.

R7 is **Implemented + Static + Unit + CI**. Rotate-up from off starts at the configured
floor or one usable step; target-state observation invalidates external changes
outside a bounded own-command echo window; direction reversal retains the last
requested target; unavailable/reconnect clears tracking. Tests are authored;
HA UI and Hardware remain pending.

R8 is **Implemented + Static + Unit + CI**. Channel event entities declare
`EventDeviceClass.BUTTON`; declared event types, unique IDs and device triggers
are unchanged. The legacy domain event preserves its payload and adds registry
`device_id` when a matching BILRESA device exists. Tests are authored; Unit,
CI and hassfest/HACS passed. Live automation compatibility remains pending.

Commit preparation on 2026-07-15:

- Claude Code's two-layer panel revision is preserved in `863bded`;
- R1-R3/R5-R8 runtime, translations and authored tests are committed in
  `1982188` (`feat: harden binding runtime behavior`);
- English/Czech README terminology was corrected from the historical
  light-only flow to the current Control binding / Ovládací propojení flow;
- the README status now distinguishes CI-verified `v0.5.7-rc.3` from the newer
  runtime polish, which is now CI-verified but remains undeployed and
  hardware-unverified;
- documentation was committed in `2480b34`; the first combined CI run exposed
  only brittle test assumptions, not a production-code failure;
- deterministic time cleanup and instance-level event device-class verification
  were committed in `7bc523b` (`test: make runtime behavior checks deterministic`).

Exact-revision GitHub Actions run `29430829523` passed for commit `7bc523b`:

```text
Validate manifest (hassfest) passed
Validate HACS               passed
Lint (ruff)                 passed
Type check (mypy)           passed
Unit tests                  112 passed in 1.13 s
Total coverage              68%
```

This establishes Unit + CI for R1-R3/R5-R8 at that revision. It does not
establish HA UI, deployment or Hardware for the new runtime behavior. R4 remains
explicitly deferred.

## Important files added or expanded

- Runtime: `binding.py`, `config_flow.py`, `coordinator.py`, `matter_core.py`,
  `matter_ws.py`, `diagnostics.py`, `system_health.py`, `const.py`.
- Tests: `tests/test_binding.py`, `test_config_flow.py`, `test_coordinator.py`,
  `test_diagnostics.py`, `test_matter_core.py`, `test_matter_ws.py`,
  `test_system_health.py`, and `tests/fixtures/matterjs_1_1_7.json`.
- Process/reference: `docs/ROADMAP.md`, `docs/DEVICE_REFERENCE.md`,
  `docs/MATTERJS_COMPATIBILITY.md`, `docs/SCROLL_PERFORMANCE.md`,
  `docs/HARDWARE_TEST.md`, and `docs/DEVELOPMENT.md`.

Use `git status --short` for the complete file list; do not assume an untracked
file is disposable.

## Validation recorded on 2026-07-15

Static gate after the complete seven-package implementation:

```text
python -m json.tool manifest/strings/en/cs JSON  passed
python -m compileall -q custom_components tests passed
ruff format --check custom_components tests     passed
ruff check custom_components tests              passed
mypy custom_components/ikea_bilresa             passed (14 source files)
git diff --check                                passed (CRLF conversion warnings only)
```

`ruff format custom_components tests` changed no files. `ruff check --fix`
performed one mechanical lint fix in tests, after which the static gate passed.

Automated tests:

```text
Python 3.13.12
python -m pytest -q
9 collection errors: ModuleNotFoundError: No module named 'homeassistant'
```

This is **Unit not run**, not a pass. Home Assistant 2026.7.2 and the configured
test harness require the Python 3.14 Linux CI environment; the earlier Windows
installation attempt was additionally blocked by `lru-dict` requiring MSVC.
Do not weaken or stub the production HA dependency merely to turn this local
environment green.

Not run for the current working tree:

- Home Assistant UI/config-flow and failure-injection checks;
- physical IKEA BILRESA release-candidate checklist.

GitHub Actions runs `29404200175`, `29404377898`, and final RC run
`29404628773` passed on Python 3.14.6. The final run validates commit `fa6d38d`:

```text
Validate manifest (hassfest) passed
Validate HACS               passed
Lint (ruff)                 passed
Type check (mypy)           passed
Unit tests                  39 passed in 0.92s
Total coverage              51%
```

The green test job establishes Unit + CI for the RC snapshot. It does not satisfy
the `0.5.3` coverage-above-95% exit gate and does not establish Hardware.

## Hardware status

`v0.5.7-rc.3` now has partial physical hardware evidence on both installed
BILRESA wheels. Raw direction/channel routing and a representative gesture set
are verified as recorded below and in `docs/HARDWARE_TEST.md`. This is not a
complete Hardware PASS for the release candidate: binding outcomes, lifecycle,
failure injection, dedicated-WebSocket fallback and soak checks remain open.

The complete pending run is in `docs/HARDWARE_TEST.md`. It must cover both event
sources, cumulative counts, every channel, binding targets, scene cycling,
hold safety, copy/profile UI, diagnostics privacy, reconnect/reload/fallback and
soak behavior with exact HA/Matter/BILRESA versions recorded.

### Hardware run started 2026-07-15

The owner is now home and authorized the physical `v0.5.7-rc.2` checklist. A
read-only baseline was recorded in `docs/HARDWARE_TEST.md`; physical gesture
steps have not yet been observed, so Hardware remains open.

The two current physical wheels use different firmware. The `1.9.15` wheel
exposes Basic Information Serial Number `0/40/15` and its three custom event
entities merge with the user-named core Matter device. The `1.8.7` wheel omits
that attribute; its event entities appear on a separate default-named custom
device because `event.py` currently relies on the serial identifier for the
cross-integration registry merge. Coordinator diagnostics still discover both
wheels and all three channels. This is a confirmed presentation/linking defect,
not yet a gesture-processing failure.

No HA configuration or registry mutation was made. The next physical step is a
single slow clockwise notch on channel 1 of the `1.8.7` wheel to map its
standalone event entities and start the raw-gesture checklist.

### Serial-independent Matter device linking (`v0.5.7-rc.3`)

The post-`v0.5.7-rc.2` fix addresses the mixed-firmware
device-registry defect without changing Matter event decoding or issuing Matter
commands:

- new `device_link.py` reproduces Home Assistant Core 2026.7.2's canonical
  unbridged Matter identifier from the compressed fabric ID and node ID;
- resolution is restricted to a core Matter config entry using the same server
  URL, accepts serial and operational identifiers only when they resolve
  unambiguously, and never uses device name, area, entity ID or discovery order;
- firmware `1.8.7` can therefore link without Basic Information Serial Number;
- existing custom event entities are reassigned to the canonical core Matter
  device and an otherwise empty legacy standalone device is retired;
- linked event entities use link-only `DeviceInfo`, leaving core Matter's user
  name and hardware metadata authoritative;
- the custom node identifier remains on the merged device for existing device
  trigger lookup;
- coordinator node updates now refresh wheel metadata, allowing a newly
  reported serial after firmware update to take effect without a full reload;
- the binding selector uses the same resolver and can show the core Matter
  device's user name even when serial is absent.

Files involved: new `custom_components/ikea_bilresa/device_link.py`,
`event.py`, `coordinator.py`, `config_flow.py`, new
`tests/test_device_link.py`, expanded `tests/test_coordinator.py`, `CHANGELOG.md`,
`docs/DEVICE_REFERENCE.md`, `docs/HARDWARE_TEST.md`, and this handoff.

Validation for this fix candidate:

```text
python -m compileall -q custom_components tests     passed
ruff format custom_components tests                 completed (1 file changed)
ruff check custom_components tests                  passed
mypy custom_components/ikea_bilresa                 passed (15 source files)
```

The new tests cover the exact operational identifier, missing serial, server
URL isolation, conflicting serial/operational matches, legacy-device
reconciliation, and metadata refresh. The full static gate passed, including
JSON parsing, compileall, Ruff format and lint, mypy and `git diff --check`.
Local `python -m pytest -q` stopped during collection with 12
`ModuleNotFoundError: No module named 'homeassistant'` errors in the known
Windows/Python 3.13 environment. This is **Unit not run**, not a failure of an
executed test. CI and Home Assistant deployment have not run for this working
tree. Hardware is still pending; implementation and MCP observations are not
Hardware evidence.

Known migration assumption: when two registry devices already exist, the core
Matter device is retained as canonical and the otherwise empty custom duplicate
is removed. Home Assistant has no public general-purpose device-ID merge API;
existing automations that explicitly stored the duplicate custom device ID must
be reviewed during the controlled HA test. Core Matter device identity and all
entity IDs are preserved.

A read-only MCP recheck after implementation still reported firmware `1.8.7`
for the affected wheel and `1.9.15` for the other wheel. No HA state was changed.

The owner explicitly requested preparation, publication and controlled Home
Assistant deployment of `v0.5.7-rc.3` on 2026-07-15. Publication uses the
sanitized current tree; rewriting the older sensitive documentation commit
remains a separate deferred decision and was not part of this RC operation.

Publication and deployment results:

- panel design documentation was preserved separately in commit `bbda9de`;
- runtime fix and manifest `0.5.7-rc.3` were committed as `6db5b5b` and pushed
  to `agent/stabilize-0.5-x`, updating draft PR #1;
- GitHub Actions run `29422785785` passed for exact commit `6db5b5b`: hassfest,
  HACS validation, Ruff and mypy passed; 51 tests passed in 1.07 s on Python
  3.14.6 and total coverage was 56%;
- prerelease `v0.5.7-rc.3` was published from exact commit `6db5b5b`;
- before deployment, a read-only consumer scan found no references to the
  legacy duplicate device ID in automations, scripts, scenes or helpers; both
  storage dashboards were loaded separately and contained no reference;
- HACS installed exactly `v0.5.7-rc.3`; the pre-restart config check was valid
  with no errors and Home Assistant restarted normally;
- after restart the config entry was loaded through `core_matter_client`, with
  two wheels, three bindings, fallback count zero and no fallback reason;
- exactly two unique BILRESA devices were present in the custom integration:
  `Kolečko Nelča` on firmware `1.8.7` and `Kolečko Obývák` on `1.9.15`; both had
  Matter plus `ikea_bilresa` sources and exactly three custom event entities;
- the legacy standalone device was absent, proving the registry fallback and
  migration in the running HA instance while serial remained absent;
- exact-domain system-log and error-log searches returned no entries.

This establishes Implemented + Static + Unit + CI + Released and a successful
Home Assistant deployment/registry smoke test.

### Physical gesture smoke on `v0.5.7-rc.3`

The owner then operated both installed wheels while Codex observed their event
entities and diagnostics through read-only Home Assistant MCP calls:

- firmware `1.8.7` (`Kolečko Nelča`) passed clockwise/counter-clockwise routing
  and a single press on all three channels;
- its channel 1 additionally passed a batched fast clockwise rotation, single,
  double and triple press, and one `hold` followed by exactly one `release`;
- the first deliberately slower triple-press attempt was closed by the device
  as separate presses; a retry with all three presses inside the device's
  multi-press window produced `triple_press` with `presses: 3`;
- firmware `1.9.15` (`Kolečko Obývák`) passed clockwise/counter-clockwise
  routing and a single press on all three channels;
- no event crossed into a non-selected channel, the source remained
  `core_matter_client`, fallback count remained zero, and exact error-log
  searches returned zero matching `ikea_bilresa` and Matter errors.

This is Hardware evidence for the listed raw gestures, both firmware versions
and all six channel routes. It is not evidence for unobserved binding target
results or the remaining lifecycle/failure/soak checklist. The overall RC run
therefore remains **IN PROGRESS**.

### Explicit low-latency single-press candidate after `v0.5.7-rc.3`

During the physical run the owner reported visible button-to-light latency on
the firmware `1.9.15` wheel's channel 2. Read-only HA history showed that the
two separate public `press` events were followed by the configured light state
in 114 ms and 424 ms. The binding service path is therefore reasonably fast;
the remaining perceived delay occurs before the public action because the
existing engine waits for the device's `MultiPressComplete` classification.

The working tree now implements an explicit per-binding low-latency path
supported by the observed BILRESA event order:

- the coordinator sends button event names over a new internal per-channel
  dispatcher signal; raw hints are never fired on `ikea_bilresa_event`;
- a binding set to fast response executes its single-press action once on the
  first `ShortRelease`;
- subsequent releases in that gesture and its later completion cannot execute
  the binding again;
- bindings set to multi-press recognition keep the existing completion-aware
  single/double/triple behavior;
- the native HA form defaults new profiles to fast response, preserves old or
  copied bindings without the field as multi-press-aware, explains the trade-off
  in English and Czech, and rejects fast response with a double/triple target;
- public event entities, device triggers and the event bus remain based on the
  exact `MultiPressComplete` count;
- connection changes/unload clear the internal guard, and a stale guard can
  recover on a clearly later gesture.

Files involved: `binding.py`, `config_flow.py`, `coordinator.py`, `const.py`,
strings/translations, expanded binding/config-flow/coordinator tests,
`CHANGELOG.md`, English/Czech READMEs, `docs/DEVICE_REFERENCE.md`,
`docs/HARDWARE_TEST.md`, and this handoff.

Validation for this uncommitted candidate:

```text
python -m compileall -q custom_components tests     passed
ruff format --check custom_components tests         passed (28 files)
ruff check custom_components tests                  passed
mypy custom_components/ikea_bilresa                 passed (15 source files)
git diff --check                                    passed (CRLF warnings only)
python -m pytest -q                                 12 collection errors:
  ModuleNotFoundError: No module named 'homeassistant'
```

The final R1 static run also parsed manifest/strings/en/cs JSON successfully.
The authored R1 tests cover explicit policy defaults and validation plus
single/double/triple completion suppression, hold, lost completion recovery,
reconnect and unload. They were collected only as far as the missing
Home Assistant import permits; this is not a Unit pass.

After R2 the same complete static gate passed again with 28 formatted files and
15 mypy-checked source modules. A fresh pytest attempt again stopped during
collection with the same 12 missing-Home-Assistant errors; R2 therefore remains
Unit not run.

After R3 the combined R1-R3 static gate passed again: all four JSON files,
compileall, Ruff format/lint, mypy over 15 source modules and `git diff --check`.
No Unit, CI, HA UI or Hardware claim follows from that static result.

After R5-R8 and the explicit R4 deferral, the complete dirty-tree static gate
passed again:

```text
manifest/strings/en/cs JSON parsing                 passed
python -m compileall -q custom_components tests     passed
ruff format --check custom_components tests         passed (29 files)
ruff check custom_components tests                  passed
mypy custom_components/ikea_bilresa                 passed (15 source files)
git diff --check                                    passed (CRLF warnings only)
python -m pytest -q                                 13 collection errors:
  ModuleNotFoundError: No module named 'homeassistant'
```

The added R5-R8 tests did not execute in the local Windows/Python 3.13
environment, so the local result remains **Unit not run**. They subsequently
passed in the exact-revision Linux CI run recorded above. The currently
installed `v0.5.7-rc.3` does not contain this implementation, so today's latency
evidence justifies the change but does not Hardware-verify it.

The owner also ran a physical channel-1 brightness batch on the installed
`v0.5.7-rc.3` using the firmware `1.9.15` wheel. With step 3%, acceleration 0
and transition 1.0 s, slow down/up and faster down gestures produced 3/5/6
decoded updates, total deltas 9/13/18 and stream durations
1.032/2.051/2.095 s. First recorded target-state updates followed after
1.166/1.125/1.098 s; final brightness was 46% from a 100% baseline. No matching
BILRESA or Matter error was present.

This Hardware-verifies the installed RC's rotation-to-brightness data path for
that binding. The approximately one-second recorded state completion matches
its configured one-second transition and does not demonstrate a software
dispatch backlog. HA history cannot measure first visible light onset, so a
shorter transition remains a later A/B test, not a justified default change.

## Known risks and decisions

- The seven packages are stacked in one dirty tree; release them only in small,
  owner-tested patch snapshots rather than pretending all gates passed at once.
- Core Matter runtime-data structure is not a public custom-integration API.
  URL matching, feature detection and passive fallback reduce but do not remove
  upgrade risk.
- Dedicated WebSocket incompatibility after setup currently reconnects with
  backoff and logs the schema error; config/reconfigure reject incompatibility
  before saving. Verify the operator experience through failure injection.
- Hold ramp direction is a product choice because BILRESA LongPress carries no
  direction.
- Device-side 0.5–1 second batching sets the responsiveness floor. Do not add an
  accumulator unless `docs/SCROLL_PERFORMANCE.md` revisit criteria are met.
- Brand icon, brands PR and default HACS publication remain the final phase.

## Single best next action

Prepare the next `v0.5.7` release candidate from the CI-green runtime snapshot,
then perform focused HA UI and physical checks for R1-R3/R5-R8. R4 remains
deferred; none of the new runtime polish is Hardware-verified yet.

## Next-agent handoff

1. Read the required instruction/reference files; do not rely on chat history.
2. Re-check HEAD, branch, status and full relevant diff.
3. Preserve every dirty and untracked file.
4. Unit + CI are established only for exact commit `7bc523b`; do not infer HA
   deployment or Hardware from them.
5. The current authorization covers this stabilization PR, an RC release and a
   controlled HA deployment. It does not authorize unrelated repository or HA
   changes.
