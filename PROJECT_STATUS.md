# Project status and agent handoff

Last updated: **2026-07-16 by Codex**

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
- Working tree: dirty with the `v0.5.9-rc.3` panel visual follow-up described
  below. The latest deployed Home Assistant version remains `v0.5.9-rc.2`.
  Runtime commit `f0a4171` is the `v0.5.9-rc.2` tag target;
  `v0.5.9-rc.1` remains on `c3c5c2f`.
- The owner authorized commit, push, a GitHub CI/PR workflow, an RC release and
  controlled Home Assistant deployment on 2026-07-15. Record their concrete
  results here after each gate; authorization is not proof that a gate passed.
- Latest stable release remains `v0.5.0`. Panel Phases 0-3 were published as
  `v0.5.7-rc.11`; the functional editor/detail candidate was published as
  `v0.5.9-rc.1`, and the first real-screenshot visual polish is published and
  deployed as `v0.5.9-rc.2`. A second screenshot follow-up is implemented as a
  local `v0.5.9-rc.3` candidate. Draft PR #1 remains open and `main` has not
  been merged.
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

On 2026-07-16 the owner-authorized `v0.5.9-rc.1` deployment completed:

- the pre-restart Home Assistant configuration check was valid;
- HACS installed exactly `v0.5.9-rc.1` into
  `/config/custom_components/ikea_bilresa`;
- Home Assistant restarted and the `ikea_bilresa` entry returned to `loaded`;
- all four existing binding subentries remained present;
- live diagnostics confirmed stored `node_id` and `channel` values are strings,
  all four bindings contain `mode`, and none contains `binding_profile`;
- no matching `ikea_bilresa` system-log entry was present after restart.

This is deployment smoke evidence, not a physical-wheel Hardware result. The
frontend must be opened in a new browser tab before visual/manual validation
because an existing custom element cannot be redefined in a running tab.

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
- Explicit per-binding fast or multi-press-aware button response; this is
  deployed in `rc.4` but not hardware-verified.
- Gesture-aware trailing-scroll suppression, time-based acceleration,
  state-observed resynchronization and HA-native event polish; all are deployed
  in `rc.4` but not hardware-verified.

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

No production panel implementation has been started. The disposable Phase 0
delivery spike described below is implemented; it must not become the real
panel.

The documented delivery sequence is additive and provisional: a read-only panel
in planning package `0.5.8`, binding editing in `0.5.9`, workflow polish in
`0.5.10`, and carefully selected expansion afterward. A stored-configuration or
subentry-model migration still requires a minor version under `ROADMAP.md`.

The design direction above remains **design documentation only**. The separate
technical spike below changes frontend delivery and a read-only WebSocket API,
but does not implement the designed panel or change Matter, binding storage or
hardware behavior. The physical `v0.5.7` checklist remains open.

### Panel localization (Claude Code, 2026-07-16)

The panel shipped English-only to a Czech owner. It was recorded as an "open
Phase 0 decision", which described the gap without closing it.

New `panel_strings.py` holds every user-facing string in both languages **on
adjacent lines in one file**. Not `strings.json`: Home Assistant's translation
categories are fixed (`config`, `selector`, `system_health`, `issues`,
`device_automation`) and none describes a custom panel — HA has no category for
one, inventing a category risks hassfest, and the frontend would not fetch it.

Two JSON files in two directories is how English and Czech drift, which the
roadmap forbids. One file makes alignment structural, and
`tests/test_panel_strings.py` fails the build when a key, a placeholder or a
translation is missing on either side. 34 keys, all aligned.

Where each string is resolved:

- **behaviour labels** (`Plynulé stmívání`) are localized in `panel_models` and
  travel in the snapshot — they belong with the mode mapping;
- **UI chrome** travels in the panel's `config`, resolved once at registration.
  A language change therefore needs a reload; acceptable, since HA reloads the
  integration on a core config change.

**Known limitation, not hidden:** the language is `hass.config.language`, the
instance's, not the individual user's. Home Assistant exposes no per-user locale
to a WebSocket handler or to panel registration. A household reading two
languages gets one of them. Revisit if HA ever exposes a per-connection locale.

`test_the_frontend_does_not_hard_code_user_facing_english` keeps the second copy
from creeping back into JavaScript.

### Panel grid: two defects found on first sight (Claude Code, 2026-07-16)

`rc.9` deployed and the grid rendered — with **every channel of every wheel
reading "Not configured" while four bindings existed**. Two separate bugs, both
in `panel_models.py`, both invisible to sixteen green tests.

**1. Stored bindings hold `node_id` and `channel` as strings.** They come from
config-flow selectors; a live diagnostics dump shows `"channel": "1"`. The code
did `isinstance(channel, int)` and `data.get(CONF_NODE_ID) != node_id` against an
int `wheel.node_id`, so every binding was silently dropped. Fixed with `_as_int`
coercion.

**2. `CONF_BINDING_PROFILE` is never written to the subentry.** It is a
config-flow field for picking defaults. The stored field that describes behaviour
is `CONF_MODE` (`brightness`, `volume`, `cover_position`, …). Reading the profile
back returned `None` for every binding. Behaviour now maps from `CONF_MODE`, and
an unrecognised mode reports itself rather than reading as unconfigured — those
are different claims.

**Why the tests missed both: the fixtures were invented to match the code's
assumptions.** `const.py` was read for key *names* and the *types and presence*
were guessed. Sixteen tests agreed with the guess. The fixtures now use the shape
a real diagnostics dump showed, and `test_string_typed_subentry_still_matches_its_wheel`
copies one live binding verbatim. A fixture that agrees with the code proves
nothing about Home Assistant.

Also fixed: the panel drew its own menu button on desktop, next to Home
Assistant's own sidebar control — two hamburgers. HA's `ha-menu-button` shows
itself only when `kioskMode === false && (narrow || dockedSidebar ===
"always_hidden")`; the panel now follows the same rule. `narrow` also re-renders
the header, since HA re-sets it on every resize across the breakpoint and a
stored-but-unrendered value leaves a desktop header on a phone. Kiosk mode is not
checked: it lives in a private frontend store, and a stray button under kiosk
beats a trapped user without one.

Status: **Implemented + Static. Unit not run locally. Not released** — needs an
`rc.10` to reach a browser.

### Panel `0.5.8` Phase 3 frontend shell and overview grid (Claude Code, 2026-07-16)

Status: **Released and running as part of `v0.5.7-rc.11`, per owner report.**
The original Phase 3 visual exit gate was not recorded independently; the local
Phase 4 browser checks below supersede the placeholder view but do not establish
HA UI or Hardware.

The Phase 0 stub is replaced by the real overview: the grid of wheel cards from
`PANEL_DESIGN.md`'s two-layer model, reading `ikea_bilresa/overview` and its
subscription. Loading, empty, ready, degraded and fatal states all exist. A card
opens a Phase 4 placeholder — navigation is Phase 3's deliverable, the detail is
not.

**How the styling was decided, because "make it look like HA" is not a method.**
The tokens were read out of the Home Assistant frontend source, not remembered:

- `--ha-space-1`..`20` (4–80px in 4px steps). HA's own agent skill for frontend
  styling — `.agents/skills/ha-frontend-styling/SKILL.md` in `home-assistant/frontend`,
  a better source than anything local — forbids hard-coded pixels in spacing and
  raw hex in component styles. Every gap and pad here is a token.
- `--ha-font-size-*` (xs 10 … 5xl 40), `--ha-font-weight-*`, `--ha-line-height-*`.
- `ha-card` now defaults to **`box-shadow: none` with a 1px
  `--ha-card-border-color` border**. The earlier prototype used shadows; that is
  no longer HA's look.
- Every token has a fallback: a theme predating the rename must still render.

**The `frontend-design` skill was loaded and deliberately not followed.** It
calls for a bold distinctive aesthetic — unusual fonts, gradients, asymmetry,
"unforgettable". That is precisely what `PANEL_DESIGN.md` rejects and what got
the original mockups thrown out. Here, not looking AI-generated means being
indistinguishable from Home Assistant, so HA's design system is the answer and
inventing one is the failure mode.

Decisions worth keeping:

- **No invented icons.** `mdi:knob`, which `event.py` uses for the wheel, is
  absent rather than approximated — an invented path is not "standard MDI".
  Resolving real icons needs `ha-svg-icon` or `@mdi/js`; open Phase 3 item.
- **Shadow DOM**, per HA's scoping guidance. Custom properties inherit through
  it; `hass-toggle-menu` needs `composed` to get out.
- **Skeletons, not a spinner**: the grid's shape is known before its data.
- Accent on the dot, the stripe and the border; never on a word. Same measured
  reason as everywhere else in this program.

**Deviation from the roadmap, on purpose:** it wants TypeScript + Lit + Vite with
a CI bundle-reproducibility check. This is a dependency-free custom element
instead. Reasons: the overview re-renders only on a low-rate subscription, so
Lit's diffing buys little; a whole JS toolchain plus a committed bundle is a
large, unverifiable addition while `pytest` cannot even run locally; and the
Phase 0 spike proved plain module delivery works, which a Vite bundle would have
to re-prove. **This is a decision to revisit at Phase 4, not a settled one** —
the wheel detail with its rail, tabs and live stream is where templating starts
paying for itself.

```text
python -m compileall -q custom_components tests     passed
ruff format --check / ruff check                    passed
mypy custom_components/ikea_bilresa                 passed (18 source files)
node --check <panel asset>                          passed
git diff --check                                    passed
python -m pytest -q                                 Unit not run
```

Owed before Phase 3 closes: the visual comparison in every required state, dark
and one non-default theme, Czech/English expansion, keyboard-only and
screen-reader passes, 320px, and a contrast pass against the real thing rather
than against a prototype.

### Panel `0.5.9` binding editor and correlated action results (Codex, 2026-07-16)

Status: **Implemented + Static + Python Unit + frontend Unit + CI + Released +
deployed backend smoke. Visual HA UI and Hardware pending.**

This candidate turns the Phase 4 detail into a functional administrator surface:

- binding create/update/delete uses a narrow WebSocket API that cannot mutate
  wheels, Matter devices, entities or unrelated config entries;
- native config flow and panel share `binding_config.py` normalization and
  semantic validation;
- updates and deletion require a deterministic revision token, so a stale tab
  receives a conflict instead of overwriting a newer subentry;
- the panel editor exposes rotation mode/target, step, transition, acceleration,
  brightness limits, short/double/triple press, response policy, hold action and
  scene cycling;
- GAP-2 is closed by structured per-action results such as brightness
  `before/after/unit`;
- GAP-3 is closed by an action correlation ID and dispatch states
  `pending/accepted/failed/skipped/not_configured/completed`;
- `accepted` means Home Assistant validated and scheduled the non-blocking
  service action. It is deliberately not described as physical-device success;
- panel test buttons run rotate, single/double/triple press, hold and release
  through the same `LightBinding` runtime without a physical wheel;
- physical Matter delivery remains a separate deferred Hardware gate.

Read-only Home Assistant MCP inspection before publication confirmed the loaded
`v0.5.7-rc.11` entry and four real binding subentries. All four store
`node_id`/`channel` as strings, contain `mode` and omit `binding_profile`, matching
the candidate's model and validator.

Validation:

```text
ruff format --check custom_components tests         passed
ruff check custom_components tests                  passed
mypy custom_components/ikea_bilresa                 passed (20 source files)
python -m compileall -q custom_components tests     passed
node --check <panel asset>                          passed
node --test tests/panel_frontend.test.mjs           passed (5 tests)
pytest on Python 3.14 + HA 2026.7.2                  passed (196 tests)
git diff --check                                    passed
```

The normal Home Assistant pytest plugin imports Unix-only `fcntl` on Windows.
The local suite therefore ran with plugin auto-loading disabled and
`pytest_asyncio.plugin` loaded explicitly; the repository's own 196 tests all
passed. Exact-revision Linux CI remains the authoritative plugin/hassfest/HACS
gate.

Publication and deployment:

- runtime commit `c3c5c2f965041efad8cd08b7b252cddea468a687`;
- GitHub Actions run `29482215403` passed Unit tests, mypy, Ruff, hassfest, HACS
  validation and frontend checks;
- prerelease `v0.5.9-rc.1` was published from that exact commit;
- HACS installed that exact version after a valid config check;
- Home Assistant restarted, the integration loaded, four stored bindings were
  preserved and no matching system-log error was present.

The callable browser-control surface was unavailable in this task, so no visual
claim is made for the freshly loaded custom element. Open a new tab and perform
the manual panel checks below before promoting the RC.

### Post-RC.1 panel visual correction (Codex, 2026-07-16)

Status: **Implemented + Static + Unit + CI + Released + deployed to Home
Assistant as `v0.5.9-rc.2`. Browser visual comparison pending.**

Owner screenshots from the real Home Assistant page established that the RC.1
data model and functions work, but the composition did not reach the selected
visual direction:

- the desktop back action sat between the 256 px rail and wheel heading,
  creating a false third column;
- the overview occupied a small left-aligned strip on a wide screen;
- three equally weighted channel cards read like a generic administration form;
- the idle live-test result was visually minor while synthetic test buttons
  dominated the page;
- diagnostics exposed `Panel contract` in the default view and repeated its
  heading.

The working-tree correction:

- moves desktop `Back to all wheels` into the rail while keeping the in-pane
  back action below 620 px;
- centers the overview in a 1120 px maximum frame with two comfortable
  `auto-fit` columns;
- removes misleading per-channel chevrons from overview cards;
- renders channels as one continuous surface with numbered summaries and a
  responsive gesture grid;
- makes the human-readable calculated result the live-test hero, with configured
  channels and recent activity in a secondary column;
- collapses target-changing panel tests by default;
- leads diagnostics with one health statement and moves internal contract data
  under collapsed technical details.

No Matter, binding storage, WebSocket schema or dispatch behavior changes are
part of this correction.

Local validation for the `0.5.9-rc.2` candidate passed on Windows/Python 3.14:

```text
ruff format custom_components tests                         no changes
ruff format --check custom_components tests                 passed (38 files)
ruff check custom_components tests                          passed
mypy custom_components/ikea_bilresa                         passed (20 files)
python -m compileall -q custom_components tests             passed
node --check custom_components/.../ikea_bilresa_panel.js    passed
node --test tests/panel_frontend.test.mjs                   6 passed
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3.14 -m pytest -q
  -p pytest_asyncio.plugin                                  200 passed
manifest/strings/en/cs JSON parsing                         passed
git diff --check                                            passed (CRLF warnings only)
```

The focused design QA record is `design-qa.md`. Browser-rendered visual QA
remains blocked until the deployed custom element is opened in a fresh Home
Assistant tab and screenshots are captured.

Publication and deployment results for `v0.5.9-rc.2`:

- runtime commit `f0a4171` (`Refine BILRESA panel visual hierarchy`) was pushed
  to `agent/stabilize-0.5-x`;
- exact-revision GitHub Actions run `29485117546` passed frontend checks, HACS
  validation, hassfest, Ruff, mypy and Unit tests;
- prerelease `v0.5.9-rc.2` was published from exact commit `f0a4171`:
  https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.5.9-rc.2;
- pre-deployment Home Assistant config check was valid;
- HACS installed exactly `v0.5.9-rc.2`;
- Home Assistant restarted and the integration returned to `loaded`;
- System Health reported Matter connected via `core_matter_client`, no fallback
  reason, two discovered wheels and four configured bindings;
- HACS still reported installed version `v0.5.9-rc.2` after restart;
- config-entry diagnostics still showed four binding subentries. Stored
  `channel` values remained strings, `mode` was present, and no
  `binding_profile` field was present;
- system-log search for `ikea_bilresa` returned no entries. Raw log search
  showed only Home Assistant's standard custom-integration loader warning, and
  no `custom_components.ikea_bilresa` error lines.

### RC.2 screenshot follow-up for detail polish (Codex, 2026-07-16)

Status: **Implemented + Static + Unit locally as the `0.5.9-rc.3` candidate.
Not yet committed, CI-verified, released or deployed. Browser visual comparison
pending.**

Owner screenshots from the deployed `v0.5.9-rc.2` panel showed two remaining
detail-screen issues:

- desktop still showed two "Back to all wheels" controls because the in-pane
  mobile back button had both `display: none` and a later `display: inline-flex`
  in the same CSS rule;
- channel detail still felt bulky and hard to scan because each configured
  channel rendered a wide table-like 3 x 2 gesture matrix.

The working-tree correction:

- keeps desktop back navigation only in the 256 px rail and shows the in-pane
  back button only below the mobile rail-collapse breakpoint;
- replaces the channel gesture matrix with compact per-channel cards and a
  vertical gesture list;
- moves edit/add binding actions into each channel card footer so the card
  reads content-first instead of form-first.

No Matter, binding storage, WebSocket schema or dispatch behavior changes are
part of this correction.

Local validation for the `0.5.9-rc.3` candidate passed on Windows/Python 3.14:

```text
ruff format custom_components tests                         no changes
ruff format --check custom_components tests                 passed (38 files)
ruff check custom_components tests                          passed
mypy custom_components/ikea_bilresa                         passed (20 files)
python -m compileall -q custom_components tests             passed
node --check custom_components/.../ikea_bilresa_panel.js    passed
node --test tests/panel_frontend.test.mjs                   6 passed
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3.14 -m pytest -q
  -p pytest_asyncio.plugin                                  201 passed
manifest/strings/en/cs JSON parsing                         passed
git diff --check                                            passed (CRLF warnings only)
```

### Panel `0.5.8` Phase 4 wheel detail, live test and diagnostics (Codex, 2026-07-16)

Status: **Superseded by the `0.5.9-rc.1` candidate above.** The read-only detail
and measured layout remain its foundation.

The working tree is based on `0c0e11f`. It implements the read-only wheel detail
without touching `binding.py`, the dispatch path, stored configuration or any
Matter listener:

- exact 256 px wheel rail, hidden below 620 px, with one-click wheel switching,
  readable status words and a back affordance at every width;
- detail columns collapse from the measured **detail pane** width at 700 px,
  not from the browser window width;
- Channels, Live test and Diagnostics tabs with ARIA roles, roving keyboard
  focus, focus restoration and reduced-motion handling;
- channel action rows from a new contract-v2 read model. It mirrors persisted
  bindings correctly: `node_id` and `channel` remain strings and the stored mode
  is `CONF_MODE`; no nonexistent `binding_profile` field is assumed;
- opt-in activity subscription only while Live test is selected, filtered to
  the opened wheel, bounded to eight rows and reliably unsubscribed when the
  user leaves the view or disconnects;
- result-first live presentation that explicitly says the calculated result and
  dispatch outcome are unavailable when the API returns `null`;
- simple read-only wheel diagnostics from the existing overview contract,
  including availability, event source, link state and recovery guidance.

GAP-2 and GAP-3 were intentionally left open in this read-only phase and are
closed only by the separately versioned `0.5.9` candidate above. The public
activity event still does not contain the original cumulative Matter count.

Local browser QA used a temporary standalone harness and a new browser tab after
each frontend redefinition. The harness and browser artifacts were deleted.
Measured results: the rail was exactly 256 px at a 1024 px viewport; the detail
pane was 720 px; both detail columns were 352 px; 320 px and 380 px views hid the
rail, used one column and had zero horizontal overflow. Light mobile and dark
desktop states, live activity, diagnostics, tab semantics and heading hierarchy
were inspected. This is **not** evidence for HA UI, a non-default theme, the
iPhone notch/safe area, a screen reader or physical BILRESA hardware.

That intermediate Phase 4 validation record is superseded by the complete
`0.5.9-rc.1` validation block above.

Changed files:

- `.github/workflows/ci.yml`
- `CHANGELOG.md`
- `custom_components/ikea_bilresa/frontend/ikea_bilresa_panel.js`
- `custom_components/ikea_bilresa/panel_models.py`
- `custom_components/ikea_bilresa/panel_strings.py`
- `docs/DEVELOPMENT.md`
- `docs/PANEL_DESIGN.md`
- `docs/PANEL_ROADMAP.md`
- `PROJECT_STATUS.md`
- `tests/panel_frontend.test.mjs`
- `tests/test_panel.py`
- `tests/test_panel_models.py`
- `tests/test_panel_strings.py`

### Panel `0.5.8` Phase 2 authenticated read-only API (Claude Code, 2026-07-16)

Status: **Implemented + Static. Unit not run locally. CI has not run. Not
deployed.** Phase 2's exit gate also wants a reviewed payload redaction and proof
that a disconnected frontend cannot affect Matter listening or binding dispatch;
the design gives the latter by construction (see below), but neither has been
observed in a running Home Assistant.

`panel_api.py` rewritten. The Phase 0 spike's two `.../spike/...` commands are
**deleted, not extended**, exactly as that package said they would be. Three
commands replace them, all admin-only, all read-only:

- `ikea_bilresa/overview` — one snapshot from `panel_models`;
- `ikea_bilresa/overview/subscribe` — pushes a fresh snapshot on
  `SIGNAL_CONNECTION` and `SIGNAL_WHEELS_UPDATED`;
- `ikea_bilresa/activity/subscribe` — live gestures, opt-in, live-test view only.

This gives `panel_models.async_overview_snapshot` its caller; it is no longer
dead code. `tests/test_panel_api.py` rewritten: 13 tests covering unload,
cleanup, multiple clients, malformed events, redaction, and that no write command
exists.

Decisions and their reasons:

- **Live activity listens to the public `ikea_bilresa_event` bus event**, not the
  coordinator. A bus listener runs *after* the action has been dispatched, so the
  panel being open cannot change gesture timing or binding latency — the concern
  that shaped `rc.4`/`rc.5`. No coordinator change was needed, and the earlier
  worry about a "someone is watching" flag turned out to be unnecessary.
- **The bus payload carries `node_id`, `wheel_name` and `endpoint_id`; all three
  are stripped.** The wheel is addressed by its opaque key. Tested.
- **`result` and `dispatched` are sent as `null`** — GAP-2 and GAP-3, still open.
  The live-test view can show the gesture and nothing about whether it landed,
  which is the opposite of what `PANEL_DESIGN.md` wants as its hero. Null is the
  honest answer; do not fill it with a guess.
- **No queue, so no backlog to bound.** Each event goes straight to the socket
  and is dropped. Rotation is rate-limited by the device's own 0.5–1 s batching.
  The roadmap asks for coalescing; there is nothing to coalesce because nothing
  accumulates.
- **The overview subscription must never be driven per gesture.** Rebuilding the
  whole snapshot per notch is exactly the unbounded work the roadmap warns about.
  That is what the activity subscription is for.
- **An unloaded integration returns an empty snapshot**, not an error: a browser
  can hold the sidebar open across an unload, and "nothing here" is renderable.

The Phase 0 stub JS now calls `ikea_bilresa/overview` instead of the deleted
spike commands, so it keeps working as a smoke check until Phase 3 replaces it.
**A deployed `rc.8` browser tab will break against this** — it still calls
`.../spike/info`. That is intended: those commands were never contract.

```text
python -m compileall -q custom_components tests     passed
ruff format --check / ruff check                    passed
mypy custom_components/ikea_bilresa                 passed (18 source files)
node --check <panel asset>                          passed
git diff --check                                    passed
python -m pytest -q                                 Unit not run
  ModuleNotFoundError: No module named 'homeassistant' (Windows/3.13)
```

### Panel `0.5.8` Phase 1 backend read model (Claude Code, 2026-07-16)

Status: **Implemented + Static. Unit not run locally. CI has not run. Not
deployed and not called by anything yet.** Phase 1's exit gate wants
deterministic, bounded, privacy-reviewed serializers with no Matter or binding
behaviour change; that is what this is, but only CI has ever executed the tests.

New `panel_models.py` builds the overview snapshot the grid renders, plus
`tests/test_panel_models.py` (16 tests: normal, empty, degraded, malformed,
determinism, privacy). Pure functions over the coordinator, subentries and the
device/entity/area registries. No I/O, no subscriptions, no mutation, no Matter.

Decisions a later agent cannot infer from the code:

- **`wheel_key` is `sha256("ikea_bilresa:<node_id>")[:12]`.** The roadmap forbids
  the node ID on the wire, but the key must survive reloads or the panel loses
  its selection on every reconnect; a hash is both. It is **not** a security
  boundary — node IDs are small and brute-forceable. It exists so the node ID
  cannot leak into screenshots, exports and bug reports, which this project has
  already done once.
- **Last activity comes from this integration's own `event` entity states**, not
  the coordinator. `_recent_events` carries no node ID and endpoints are numbered
  per node, so two wheels both have an endpoint 1 — attribution is impossible
  there. Entity states are ISO-8601 UTC, so lexical max is chronological max.
- **`EventEntity` does not restore state**, so `last_activity` and
  `last_active_channel` are `None` after every restart until a wheel is touched.
  Tested. The UI must render that as "no activity yet", never as a fault.
- **Channels come from the device's own descriptors**, never a hard-coded three.
- **Behaviour labels are English placeholders on the Python side.** Localization
  is still an open Phase 0 decision, but it belongs here: the roadmap requires
  English and Czech to stay aligned, and two copies in the frontend is how they
  drift.
- **`target_missing` is detection only.** The binding's fail-closed behaviour is
  untouched; this must never decide whether a command is sent.

Not done, and deliberately: nothing calls `async_overview_snapshot` yet. Phase 2
(the authenticated API) is what gives it a caller. It is dead code until then —
unlike GAP-1, there was no honest existing consumer to wire it into, and
inventing one would have been worse.

```text
python -m compileall -q custom_components tests     passed
ruff format --check / ruff check                    passed
mypy custom_components/ikea_bilresa                 passed (18 source files)
git diff --check                                    passed
python -m pytest -q                                 Unit not run
  ModuleNotFoundError: No module named 'homeassistant' (Windows/3.13)
```

### Panel `0.5.8` Phase 0 technical spike (Claude Code, 2026-07-15)

Status: **Implemented + Static + Unit + CI + Released + deployed and observed in
the owner's Home Assistant.** The delivery path works. Phase 0's core question is
answered: a panel can be built, because it can be delivered.

Released as `v0.5.7-rc.6` from CI-verified commit `325b080` (hassfest, HACS,
ruff, mypy, 134 tests on Python 3.14.6), installed through HACS, HA restarted.

Observed live on 2026-07-15 against Home Assistant 2026.7.2:

- the integration set up normally: `loaded`, two wheels, three bindings,
  `core_matter_client`, no fallback, and **no `ikea_bilresa` log entries at all**;
- the sidebar entry appeared and the module loaded and executed;
- `hass`, `narrow` and `panel` were all injected; the panel config carried the
  cache-busted `module_url` `.../ikea_bilresa_panel.js?v=0.5.7-rc.6`;
- the authenticated read-only WebSocket request returned real coordinator data
  (`wheel_count: 2`);
- **a config-entry reload re-registered the panel and did NOT re-register the
  static path** — the guard holds. This was the one thing inferred from HA source
  and unverifiable locally, and it is now confirmed;
- the subscription pushed twice across that reload (disconnect + reconnect),
  proving the push path, not merely that subscribing does not raise.

**Defect found after RC.6: the spike trapped the owner in the companion app.** A
custom panel owns the whole viewport; Home
Assistant draws no app header. On a narrow screen the sidebar's only door is that
header's menu button, so a panel without one cannot be left except by a system
back gesture. Invisible on a desktop, where the sidebar is already on screen. The
stub now renders a header whose menu button fires `hass-toggle-menu` (bubbling
and composed, as `ha-menu-button` does), and `PANEL_DESIGN.md` now carries this
as a requirement for **every** layer and state of the real panel — the wheel
detail's back affordance goes to the grid and is not a substitute for the way out
to Home Assistant.

Codex then hardened the candidate for RC.7 without changing its navigation
contract: the app header is semantic, the menu is a native button with a 48 px
touch target, the static SVG is hidden from assistive technology, Home Assistant
theme tokens provide its colours, and keyboard focus has a distinct visible
indicator. A regression test preserves the header/event/accessibility contract.

Local RC.7 validation before publication:

```text
manifest/strings/en/cs JSON parsing                 passed
node --check ikea_bilresa_panel.js                  passed
python -m compileall -q custom_components tests     passed
ruff format --check custom_components tests         passed (33 files)
ruff check custom_components tests                  passed
mypy custom_components/ikea_bilresa                 passed (17 source files)
dependency-free DOM event contract                  passed
git diff --check                                    passed (CRLF warnings only)
python -m pytest -q                                 15 collection errors:
  ModuleNotFoundError: No module named 'homeassistant'
```

The pytest result remains **Unit not run locally**, not a failure or pass. Linux
CI supplied the Unit gate. Exact commit `cae5aef` passed GitHub Actions run
`29438976760`: HACS validation, hassfest, Ruff, mypy and 135 tests on Python
3.14.6; total coverage was 70%. Prerelease `v0.5.7-rc.7` was published, HACS
installed it after a valid configuration check and Home Assistant restarted
normally. The loaded manifest and HACS both reported RC.7.

That deployment smoke test exposed a second frontend-lifecycle defect in an
already-open desktop tab: loading the cache-busted RC.7 module while RC.6's
`ikea-bilresa-panel` custom element remained registered raised
`CustomElementRegistry: the name ... has already been used`. The published RC.7
tag was not rewritten. RC.8 adds `customElements.get()` guarding around the
registration; a full page/WebView reload is still needed to replace an existing
class because the web platform does not permit custom-element redefinition.

RC.8 validation and deployment results:

```text
manifest/strings/en/cs JSON parsing                 passed
node --check ikea_bilresa_panel.js                  passed
double cache-busted ES-module import                passed; one definition
python -m compileall -q custom_components tests     passed
ruff format --check custom_components tests         passed (33 files)
ruff check custom_components tests                  passed
mypy custom_components/ikea_bilresa                 passed (17 source files)
git diff --check                                    passed (CRLF warnings only)
```

- exact commit `b50e17c` passed GitHub Actions run `29439486506`: HACS
  validation, hassfest, Ruff, mypy and 136 tests on Python 3.14.6; total
  coverage was 70%;
- prerelease `v0.5.7-rc.8` was published without altering RC.7;
- the Home Assistant configuration check was valid, HACS explicitly installed
  RC.8 and Home Assistant restarted normally;
- HACS and the running integration manifest both reported RC.8; the entry was
  `loaded` through `core_matter_client`, with two wheels, three bindings, zero
  fallbacks and no fallback reason;
- the post-restart exact-domain system-log search returned no BILRESA or panel
  error.

This establishes Implemented + Static + Unit + CI + Released and a successful
non-hardware HA deployment smoke test for the mobile header and registration
guard.

**The RC.8 header is NOT mobile-safe, despite the wording above and in the RC.8
release notes.** The owner opened RC.8 on an iPhone: the menu button sits under
the notch. The header was written with a plain `height: 56px` and no safe-area
insets, and the companion app's WebView runs under the status bar (Home
Assistant's frontend sets `viewport-fit=cover`), so the notch overlaps the
one control that lets a user leave the panel. This is the same class of defect as
the missing header itself: real on a phone, invisible everywhere it was tested.

Fixed in the working tree (Claude Code, 2026-07-16), Implemented + Static only:
the header now takes `env(safe-area-inset-top)` as `padding-block` with
`box-sizing: content-box`, so the inset is added to the 56px bar rather than
eaten out of it, plus `max(4px, env(safe-area-inset-left/right))` for landscape
where the notch takes a side. `env()` resolves to 0px without insets, so nothing
changes on a desktop. `tests/test_panel.py::test_panel_header_clears_the_notch`
locks the CSS in.

**A narrow desktop window cannot catch this** — it reports no insets. Neither
can any test in this repository: the assertions only prove the CSS is present,
not that it clears a real notch. Only a physical notched phone can.

Still owed before Phase 0 can be called closed:

- re-verify the companion app **on a real iPhone** with the safe-area fix, once
  it is released; RC.8 is known bad there;
- ~~the degradation test~~ — **run and passed on 2026-07-16.** The owner renamed
  `frontend/ikea_bilresa_panel.js` away and the config entry was reloaded against
  the deployed `rc.8`. The entry stayed `loaded` with two wheels, four bindings,
  `core_matter_client` and no fallback; the log carried exactly the intended
  `WARNING ... panel asset is missing at /config/... continuing without a panel`;
  no `ikea_bilresa` error appeared. This is the only real evidence that
  `async_setup_panel`'s `try/except` holds — the unit test for it invents the
  missing file and says nothing about a running Home Assistant.

For the real panel, not just this spike: every layer must respect the safe-area
insets, not only the header. `PANEL_DESIGN.md` records the header requirement;
the insets belong with it.

The owner authorized starting the panel program with the `v0.5.7` hardware gate
still open. The spike is deliberately additive: no event decoding, gesture
timing, binding behaviour or stored configuration is touched.

New files: `panel.py` (asset + sidebar lifecycle), `panel_api.py` (two read-only
WebSocket commands), `frontend/ikea_bilresa_panel.js` (a dependency-free stub
that reports what worked), `tests/test_panel.py`, `tests/test_panel_api.py`.
Changed: `__init__.py` (wire-up), `manifest.json` (frontend/http/panel_custom/
websocket_api dependencies).

The JS stub is not the panel and must not grow into one. The real panel is
TypeScript + Lit via Vite, laid out per the two-layer model in
`PANEL_DESIGN.md`. The stub exists to be deleted.

Three Home Assistant facts found while writing it, recorded because they are not
in the developer documentation and cost a deploy cycle each to rediscover:

- **Static paths cannot be unregistered.** `http.async_register_static_paths`
  adds aiohttp routes for the process lifetime with no removal API, so a
  config-entry reload must not re-register the path. Only the static path is
  guarded; the panel itself is removed and re-added normally.
- **`frontend.async_register_built_in_panel` and `frontend.async_remove_panel`
  are `@callback`, not coroutines**, despite the `async_` prefix.
  `panel_custom.async_register_panel` genuinely is a coroutine.
- The developer docs cover only `panel_custom` via `configuration.yaml`, not the
  integration-level API. These signatures were read from Home Assistant 2026.7.2
  source, not from documentation.

Decisions taken, all reversible and all recorded here because a later agent
cannot infer them from the code:

- sidebar entry is **admin-only** (`require_admin=True`), per the roadmap's rule
  to restrict rather than over-serve when per-device permission filtering is not
  yet possible;
- cache-busting is a `?v=<integration version>` query on the module URL,
  which is why the static path can keep `cache_headers=True`;
- the asset ships inside `custom_components/ikea_bilresa/frontend/`, so HACS
  delivers it with the integration — no `configuration.yaml`, no Lovelace
  resource;
- the two WebSocket commands are named `.../spike/...` on purpose. They return
  three scalars, expose no identifier and have no write path. They are to be
  deleted when the real contract lands, not extended.

`async_setup_panel` never raises: a panel that cannot be served must degrade to
"no panel", not to a failed integration setup. That is tested, but tests are not
evidence that it holds in a real Home Assistant.

```text
python -m json.tool manifest.json                   valid
python -m compileall -q custom_components tests     passed
ruff format --check custom_components tests         passed
ruff check custom_components tests                  passed
mypy custom_components/ikea_bilresa                 passed (17 source files)
git diff --check                                    passed
python -m pytest -q                                 Unit not run
  ModuleNotFoundError: No module named 'homeassistant' (Windows/3.13)
```

**The spike's exit gate was a deployment. Five of six steps have passed on real
Home Assistant; only the companion app is still owed.**

1. sidebar entry appears and opens — **passed** (`rc.6`);
2. every row of the stub's table populated, `wheels discovered: 2` — **passed**;
3. config-entry reload: panel re-registers, static path does **not**, no
   duplicate-route error — **passed**. This was the one behaviour inferred from
   HA source and unverifiable locally;
4. Home Assistant restart — **passed**;
5. companion app — **failed on `rc.8`**: the header sat under the iPhone notch.
   Fixed in `cf6454c`, released in `rc.9`, **not yet re-verified on a phone**;
6. asset removed, reload — **passed** (2026-07-16, on `rc.8`): entry stayed
   `loaded`, the intended warning appeared, no error. See the Phase 0 section.

The roadmap said that if 3, 4 or 6 failed, the packaging approach was wrong and
the architecture should be revised or abandoned rather than worked around. All
three passed. **The delivery path is proven; a panel can be built because it can
be delivered.** Step 5 is a bug in one header, not a verdict on the approach.

### Per-wheel availability, GAP-1 (Claude Code, 2026-07-15)

Drafting the panel contract against the real source found that **three fields
the panel design promises have no backend source at all.** The first is now
closed; the other two are open and block the Live test view as designed.

**GAP-1 — per-wheel availability — CLOSED.** Implemented + Static; Unit not
run.
Every "unavailable" in this integration meant the Matter Server or the core
client, never a node. `BilresaWheel` had no availability field, nothing
subscribed to per-node availability, and `BilresaChannelEvent.available` returns
`coordinator.connected` — the server connection. A wheel with a flat battery
therefore reported available for as long as the server was up.

New `device_link.wheel_availability(hass, device)` returns
`connected`/`unavailable`/`unknown` for one wheel by reading the states of the
linked core Matter device's own entities. Core Matter tracks per-node
reachability; this integration cannot. It is read-only and changes no behaviour.
Two deliberate choices: this integration's own entities are excluded (they live
on the same device after linking and their availability *is*
`coordinator.connected`, so reading them is circular), and `unknown` means "no
evidence", never "healthy".

`diagnostics.py` now calls it per wheel and reports `availability` plus
`linked_to_matter` — the latter because it is the reason availability can be
`unknown`. Diagnostics can therefore distinguish a flat battery from a dead
server for the first time. This also gives the function a caller instead of
leaving it as dead code, and makes GAP-1 verifiable in a running HA through
MCP diagnostics before any frontend exists.

`tests/test_diagnostics.py` previously asserted only the contents of the
`TO_REDACT` set and never executed the diagnostics function; redaction was
tested as a list of strings, not as behaviour. It now exercises the function and
asserts the new fields did not reopen the redaction policy.

**GAP-2 — live-test result string — RESOLVED in the `0.5.9-rc.1` candidate.**
Bindings publish structured calculated `before`, `after`, `unit` results on an
internal dispatcher signal. Reporting is unconditional constant work and never
checks whether a panel is watching.

**GAP-3 — per-action dispatch outcome — RESOLVED in the `0.5.9-rc.1`
candidate.** Every decoded or synthetic action has a correlation ID. The
non-blocking HA service coroutine reports accepted/failed for that exact action;
skipped and local-only completion states remain distinct.

Two corrections worth recording, because both are easy to get wrong again:

- Per-wheel *last activity* and *last active channel* are NOT missing. Each
  channel is an `EventEntity` (`event.py`) whose state is the timestamp of its
  last event, so both come from the HA state machine, not the coordinator. But
  `EventEntity` does not restore state, so both are empty after every HA restart
  until the wheel is next touched. The UI must render that as "no activity yet",
  never as a fault.
- `BilresaWheel.name` is the Matter *product* name and is identical for every
  wheel. The user-visible name must come from the device registry.

Related defect, **not fixed**: `event.py` reporting `available` from
`coordinator.connected` means a dead wheel looks alive in Home Assistant itself
— in dashboards and automations, not only in the panel. Fixing it is an entity
behaviour change and needs its own hardware gate.

Files: `custom_components/ikea_bilresa/device_link.py`,
`custom_components/ikea_bilresa/diagnostics.py`, `tests/test_device_link.py`,
`tests/test_diagnostics.py`.

**The out-of-repo lab is stale — do not read it as current.**
`bilresa-panel-lab/contract.ts` was the contract *draft*; `panel_models.py` is
the contract now, and the draft is wrong where they disagree: it never knew that
`node_id`/`channel` are stored as strings, and it keys behaviour off
`binding_profile`, which is never persisted. `compare.html` settled the grid vs
master-detail question and its styling predates HA's design tokens. Both did
their job and neither is maintained. The panel lives entirely in
`custom_components/ikea_bilresa/` — there is nothing to port in.

```text
python -m compileall -q custom_components tests     passed
ruff format custom_components tests                 passed
ruff check custom_components tests                  passed
mypy custom_components/ikea_bilresa                 passed (15 source files)
git diff --check                                    passed (CRLF warnings only)
python -m pytest -q                                 Unit not run
  ModuleNotFoundError: No module named 'homeassistant' (Windows/3.13)
```

CI has not run. No Home Assistant deployment and no hardware check was performed
for this change. The panel program's entry gate 1 is still open; the owner
authorized this work anyway, and it does not claim any gate.

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

### `v0.5.7-rc.4` publication and Home Assistant deployment

The owner explicitly approved RC.4 publication and controlled deployment on
2026-07-15. Release commit `36f9c1c` changes only the manifest/release metadata;
the runtime implementation is inherited from the previously CI-verified
commits.

- exact-revision GitHub Actions run `29431669462` passed hassfest, HACS
  validation, Ruff, mypy and 112 tests on Python 3.14.6; total coverage was 68%;
- prerelease `v0.5.7-rc.4` was published from exact commit `36f9c1c`;
- the pre-deployment Home Assistant configuration check was valid with zero
  errors;
- HACS explicitly installed `v0.5.7-rc.4`, after which Home Assistant restarted
  normally;
- post-restart System Health reported Home Assistant Core 2026.7.2, Python
  3.14.6, the integration loaded and connected through `core_matter_client`, two
  discovered wheels, four configured bindings and no fallback reason;
- HACS still reported exactly `v0.5.7-rc.4` as installed after restart;
- the existing binding reconfigure schema exposed `button_response` with the
  compatibility default `multi_press`; no binding, target or automation was
  recreated or automatically changed;
- exact-domain system-log search returned no entries, and the raw error log had
  zero errors; its three matching warnings were Home Assistant's standard
  custom-integration loader warning only.

This establishes Released plus a successful non-hardware Home Assistant
deployment smoke test for RC.4. It does not establish Hardware for the fast
button path, trailing-scroll protection, time-based acceleration,
resynchronization or event compatibility.

### `v0.5.7-rc.5` fast-press timing result

The owner approved targeted instrumentation and deployment after RC.4 history
showed inconsistent perceived single-press latency. Commit `4ad3fd8` adds a
DEBUG-only, privacy-safe trace for `ShortRelease`, service dispatch,
`MultiPressComplete` and the first click-target state change. It logs only a
trace sequence, channel, stage, elapsed milliseconds and press count; no node,
entity or household identifiers are emitted. Outside DEBUG the trace is
inactive. Claude's preceding `cab14e0` per-wheel diagnostics commit was
preserved unchanged in the same pushed snapshot.

- exact-revision CI run `29434960588` passed hassfest, HACS validation, Ruff,
  mypy and 122 tests on Python 3.14.6; total coverage was 69%;
- prerelease `v0.5.7-rc.5` was published and HACS installed it after a valid
  configuration preflight; Home Assistant restarted normally;
- post-restart the integration was loaded through `core_matter_client`, with two
  wheels, three current bindings and no fallback reason; the tested firmware
  `1.9.15` channel-2 binding retained `button_response=fast`;
- DEBUG was enabled only for `custom_components.ikea_bilresa.binding`;
- the owner's final five normal single presses produced service dispatch in
  0.1-0.4 ms, completion in 2.9-12.0 ms, and target-state acknowledgement in
  86.9-111.2 ms after `ShortRelease`;
- averages were approximately 0.2 ms to dispatch, 6.0 ms to completion and
  95.5 ms to target acknowledgement; no integration/system error was present.

This Hardware-verifies exactly-once fast-path dispatch and the listed internal
timing stages for the firmware `1.9.15` wheel/channel/binding. It shows that the
completion-aware path adds only about 6 ms after `ShortRelease` on this device,
so fast mode cannot materially improve the remaining perceived delay here. The
unmeasured portions are physical release to Matter `ShortRelease` delivery and
actual Shelly relay actuation versus its later HA state acknowledgement. DEBUG
remains enabled for the binding module for short-term follow-up measurement; do
not leave it enabled indefinitely during heavy rotation testing.

## Known risks and decisions

### Planned latency, telemetry and recovery program

`docs/LATENCY_ROADMAP.md` is now the ordered implementation contract for the
owner-selected next responsiveness work. It records four independent backend
packages: a bounded measurement foundation, an opt-in `InitialPress` response
policy alongside the existing `ShortRelease` and completion-aware policies,
automatic return from the passive fallback to a stable URL-matched core Matter
client, and a versioned read-only API for Claude Code's future Latency Lab.

The Latency Lab frontend remains part of the panel program and is explicitly
owned by Claude Code. The Python integration owns timing truth, privacy,
aggregation and Matter lifecycle recovery; the frontend must not parse logs or
open a separate Matter connection.

This section is **Planning only**. None of L1-L4 is Implemented, Static, Unit,
CI, Hardware or Released. The Phase 0 companion-app header and registration
guard are secured separately in deployed RC.8; latency runtime work must not be
mixed into their real-phone verification.

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

Commit, push, wait for exact-revision CI, publish `v0.5.9-rc.3`, install it via
HACS and restart Home Assistant. Then open the panel in a new tab and capture
the same real-HA states, especially the wheel detail channels screen, plus
320/380 px mobile and one dark-theme pass. Physical-wheel validation remains
deliberately deferred by owner direction.

## Next-agent handoff

1. Read the required instruction/reference files; do not rely on chat history.
2. Start from the pushed `v0.5.9-rc.2` deployment-record commit `73c7137` plus
   the locally implemented `v0.5.9-rc.3` detail polish recorded above; then
   re-check HEAD, branch and status.
3. Do not move the `v0.5.9-rc.1` tag away from runtime commit `c3c5c2f`.
4. Static, Python Unit, frontend Unit, exact-revision CI, release and backend
   deployment smoke are established. Visual HA UI and Hardware remain pending.
5. Do not mutate real bindings or run target-changing panel tests unless the
   owner identifies a safe binding/target for that check.
