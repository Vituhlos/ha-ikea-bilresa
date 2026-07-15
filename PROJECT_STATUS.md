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
- Working tree: intentionally dirty. Preserve all changes.
- The owner authorized commit, push, a GitHub CI/PR workflow, an RC release and
  controlled Home Assistant deployment on 2026-07-15. Record their concrete
  results here after each gate; authorization is not proof that a gate passed.
- Latest stable release remains `v0.5.0`. Draft PR #1 publishes the
  stabilization snapshot and targets the prerelease `v0.5.1-rc.1` after CI.
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

No Home Assistant state was changed. The running custom integration appeared to
be an older deployed copy and does not validate this working tree. MCP does not
replace physical BILRESA input.

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

GitHub Actions run `29404200175` passed for commit `83bb24a` on Python 3.14.6:

```text
Validate manifest (hassfest) passed
Validate HACS               passed
Lint (ruff)                 passed
Type check (mypy)           passed
Unit tests                  39 passed in 0.92s
Total coverage              51%
```

The green test job establishes Unit + CI for that snapshot. It does not satisfy
the `0.5.3` coverage-above-95% exit gate and does not establish Hardware.

## Hardware status

**No post-v0.5.0 work and no active working-tree feature is hardware-verified.**
`docs/DEVICE_REFERENCE.md` contains earlier observations of the device's event
model; those observations are evidence for implementation, not a pass for this
release candidate.

The complete pending run is in `docs/HARDWARE_TEST.md`. It must cover both event
sources, cumulative counts, every channel, binding targets, scene cycling,
hold safety, copy/profile UI, diagnostics privacy, reconnect/reload/fallback and
soak behavior with exact HA/Matter/BILRESA versions recorded.

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

Push the stabilization snapshot, let GitHub Actions validate the exact revision,
and fix every CI regression. Only a passing revision may be merged and tagged as
the prerelease `v0.5.1-rc.1`; non-hardware HA diagnostics may then be run before
the complete physical checklist in `docs/HARDWARE_TEST.md`.

## Next-agent handoff

1. Read the required instruction/reference files; do not rely on chat history.
2. Re-check HEAD, branch, status and full relevant diff.
3. Preserve every dirty and untracked file.
4. Do not claim Unit, CI or Hardware from the current record.
5. The current authorization covers this stabilization PR, an RC release and a
   controlled HA deployment. It does not authorize unrelated repository or HA
   changes.
