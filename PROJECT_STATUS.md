# Project status and agent handoff

Last updated: **2026-07-18 by Codex**

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

- Active publication branch: `agent/dual-button-0.6`, branched from the
  deployed `agent/stabilize-0.5-x` line after local B0/B1 commit `7446194`.
- `origin/main`: `f1e7583 docs: add DEVICE_REFERENCE — Matter/HA facts for the
  BILRESA wheel` before this stabilization snapshot is merged.
- Before Claude's reference commit, `main`/`origin/main` were at `662762a`.
- Icon implementation commit `f676bb7` is pushed on
  `agent/stabilize-0.5-x`, tagged and released as `v0.5.9-rc.11`, and installed
  through HACS. Its deployment record and README status are committed on the
  same branch; the working tree is expected to be clean at handoff.
- The owner authorized commit, push, a GitHub CI/PR workflow, an RC release and
  controlled Home Assistant deployment on 2026-07-15. Record their concrete
  results here after each gate; authorization is not proof that a gate passed.
- Latest stable release remains `v0.5.0`. The latest published and deployed
  prerelease is corrective `v0.6.0-rc.4`; its controlled Matter Server restart
  recovery and first physical post-restart single passed on the exact installed
  candidate. RC.3 fixed the count-zero overflow reproduced on RC.2 but failed
  the restart lifecycle gate. RC.1 exposed
  a separate real-device discovery defect and is explicitly marked known-bad
  for the E2489. Panel Phases 0-3
  were published as
  `v0.5.7-rc.11`; the functional editor/detail candidate was published as
  `v0.5.9-rc.1`, the first real-screenshot visual polish was published and
  deployed as `v0.5.9-rc.2`, the duplicate-back/channel-detail follow-up as
  `v0.5.9-rc.3`, and the selected icon identity as `v0.5.9-rc.11`. Draft PR #1
  remains open and `main` has not been merged.
- The `0.5.1`–`0.5.7` numbers are ordered work packages, not existing releases.
  Candidate naming is `v0.5.N-rc.K`; the third component advances gradually.

Claude's committed `docs/DEVICE_REFERENCE.md` originally contained
installation-specific identifiers. The working-tree version is now sanitized
while retaining protocol facts. The sensitive version remains in commit
history; do not publish another release until the owner decides whether and how
to clean history. Never paste those identifiers into issues, logs or chat.

## Panel visual rework after the RC.11 screenshots (Claude Code, 2026-07-17)

Status: **Implemented + Static + Python Unit + frontend Unit + harness-measured,
committed and published as `v0.5.9-rc.12`. Not yet deployed to Home Assistant,
not hardware-verified.** The manifest is `0.5.9-rc.12` so the panel module URL
cache-busts. Exact-revision CI/publication/deployment results are recorded at
the end of this section once each gate reports.

The owner opened the deployed `v0.5.9-rc.11` panel and reported it "still
doesn't sit right", naming one concrete defect: a tick appearing on the open
wheel in the rail and pushing a second row. That tick was the visible end of a
structural bug, and the audit it triggered found four more.

**The rail bug, because it explains two complaints at once.** `.rail-wheel`
declared `grid-template-columns: auto minmax(0, 1fr) auto` — three tracks — and
`_rail()` appended **four** children: glyph, status dot, copy, tick. So the dot
took the `1fr` track, every wheel name was pushed flush right with a gap beside
it, and the tick wrapped onto an implicit second row. The name misalignment was
the "something's off" the owner could feel but not name.
`test_rail_wheel_declares_a_column_for_every_child_it_renders` now parses the
declared tracks and counts the appended children, so the two cannot silently
disagree again.

The tick is deleted rather than given a fourth column: the tinted row already
said "open". But **measurement then showed the tint alone is not enough** — the
selected background is only **1.22:1** against the rail in both default themes,
since both come from `--secondary-background-color`. The rail now marks the open
wheel the way HA's own sidebar does: tint + accent glyph + medium weight. An
icon may take the accent where a word may not.

Also fixed, all from the same screenshots:

- **Empty channels carried a full channel's weight.** `repeat(3, 1fr)` plus
  `min-block-size: 100%` stretched every unconfigured channel to the tallest
  sibling — two blank rectangles beside one real card. This violated
  `PANEL_DESIGN.md`'s own "an unconfigured channel stays compact" rule.
- **The detail had no width ceiling** while the overview had one, so on the
  owner's ~1650 px window a fact's label and its value sat ~600 px apart. The
  detail is now capped at 1100 px; the 700 px collapse remains a *container*
  query on the pane, never a window query.
- **Card-in-card everywhere.** Diagnostics fact groups were bordered boxes with
  boxed headings inside a bordered page; they are now sections with hairline
  rows. Fewer boxes is what made the panel stop reading as a wireframe.
- **Duplicate heading storey.** Tab `Kanály` → heading `Chování kanálů`; tab
  `Diagnostika` → heading `Diagnostika`. The tab *is* the heading; the inner one
  is gone and only the explanatory line survives.
- **Italic as a state.** `Nenastaveno` was italic. HA never italicises state and
  it is a reliable generated-UI tell; it is dimmed instead. Note the dim must be
  `--secondary-text-color` (4.81:1), **not** `--disabled-text-color` (2.8:1,
  fails the AA gate this program measured).
- Robotic copy: the banner said *"Počet koleček s nedostupným cílem propojení:
  1"* — a log line. The backend knows which wheel and channel, so it now says
  so, and only counts when more than one wheel is affected. `Upravit cíl ·
  Světýlka` (an infinitive that reads as a button) became `Jas · Světýlka`.
  Absolute stamps became `Intl.RelativeTimeFormat`, with the exact time kept in
  `title`. Diagnostics deliberately keeps the absolute stamp: it is a surface
  for reading facts, not for glancing.
- `:active` on every button, hover moved inside `@media (hover: hover)` so touch
  users do not get stuck states, and the wheel card's hover stopped swinging its
  hairline to full ink.

**A scrollbar on the tab strip, found by the owner in this same session.** The
tab row grew a vertical scrollbar beside three short tabs. Root cause worth
recording, because it is a trap and not a typo: `.tabs` carries
`overflow-x: auto` as a real safety net (a long translation must not push the
page sideways), but per CSS Overflow, **when one axis is not `visible` the
other's `visible` computes to `auto`** — so the strip scrolls in *both* axes
whether or not that was asked for. The port then took the prototype's underline
at `inset-block-end: -1px` (harmless there: its tab strip had no `overflow-x`),
and that 1px overhang became 1px of scrollable height. Measured: `overflow-y`
computed to `auto` though it was never declared; `scrollHeight` 49 in a 48px box.

The same trap was clipping the tabs' focus ring: a tab fills the strip's height
exactly, so a ring at `outline-offset: 2px` is cut off top and bottom by that
container. Both are fixed together — the divider is painted inside as
`box-shadow: inset`, the underline sits at 0, and `.tab:focus-visible` is inset
at `-2px`. Verified with a real Tab keypress: `:focus-visible` matched, ring 2px
at `-2px`, and both axes measure 0 overflow.

Recorded because the deployed `border-block-end` + `overflow-x: auto` pair looks
completely innocent and will be re-introduced by anyone who does not know the
computed-value rule. `test_the_tab_strip_does_not_scroll_itself` holds it.

### Two ideas taken from Codex's Hallmark demo

The owner had Codex build a standalone Hallmark prototype at
`bilresa-panel-hallmark-demo/` (outside the integration; not a build dependency).
It independently reached most of the above. Two of its ideas were **not** in this
audit and are adopted:

1. **The channel spine.** Three detents, one channel open at a time, mirroring
   the wheel's three physical selector positions. The owner selected it on
   2026-07-17. It supersedes `PANEL_DESIGN.md`'s "separate card for each of the
   three channels"; that document is updated rather than quietly bypassed. It
   does not weaken the panel's first product question, because comparing every
   channel of every wheel is the **overview's** job — which is why the grid is
   the landing layer.
2. **The detent strip.** Eighteen marks under the live result, active ones
   showing the last batch. Eighteen because that is the highest rotary count
   `DEVICE_REFERENCE.md` has ever observed — a scale grounded in this hardware,
   not a round number that looked good. `test_the_detent_strip_is_scaled_to_
   observed_hardware` locks the count to that provenance.

The demo's own regressions were **not** carried over: `--disabled-text-color`
for "empty" (2.8:1), font weights 600/750 (HA's scale is 400/500), a hard-coded
white app header, and `aria-pressed` on what is really a view switcher (the
spine here is a `tablist` with arrow-key support, like the view tabs).

### Validation

```text
ruff format --check custom_components tests          passed (38 files)
ruff check custom_components tests                   passed
python -m compileall -q custom_components tests      passed
node --check ikea_bilresa_panel.js                   passed
node --test tests/panel_frontend.test.mjs            6 passed
pytest on Windows Python 3.14                        207 passed
git diff --check                                     passed (CRLF warnings only)
EN/CS panel string alignment                         196 keys each
```

`mypy` did **not** run: the local Python 3.14 has no mypy installed. CI remains
the authoritative mypy/hassfest/HACS gate and has not run for this tree.

**Browser evidence is from a local harness, not Home Assistant.** The real
`ikea_bilresa_panel.js` was rendered against a snapshot shaped like the owner's
deployment (two wheels, four bindings, one dead target) with the real Czech
strings exported from `panel_strings.py`. Measured at 1440 px, dark and light,
and at 320 px: rail exactly 256 px; rail button 3 children, 56 px, one row, no
tick; detail inner 1100 px; spine `tablist` with roving focus; gesture ledger
reading `Jas · Světýlka Světýlka` and one merged `Podržení → uvolnění` row;
live result 56 px with 18 detents and 6 active; `před 2 hodinami` with the exact
stamp in `title`; at 320 px no horizontal scroll and zero elements escaping the
frame. Console clean throughout.

This is **not** HA UI evidence: the harness supplies its own theme tokens and
its own `hass` stub, and it cannot prove what Home Assistant serves, how a real
user theme moves these tokens, or how the companion app renders any of it. A
screenshot of the harness is also not a screenshot of the panel. One honest
correction worth recording: an apparent dark-theme bug (the selected rail row
painting its light value) turned out to be a stale-paint artifact of toggling
the theme attribute in a live page; a clean load in dark mode was correct. It
was **not** "fixed" — nothing was wrong.

Files: `custom_components/ikea_bilresa/frontend/ikea_bilresa_panel.js`,
`custom_components/ikea_bilresa/panel_strings.py`, `tests/test_panel.py`,
`docs/PANEL_DESIGN.md`, and this handoff.

### Publication (2026-07-17)

- runtime commit `161b2bf` (`feat: rework panel visual hierarchy`) pushed to
  `agent/stabilize-0.5-x`, updating draft PR #1;
- exact-revision GitHub Actions run `29604008836` passed for `161b2bf`:
  Frontend checks, mypy, Validate HACS, hassfest, Lint (ruff) and 210 unit
  tests. This supplies the mypy gate the local Python 3.14 could not run;
- prerelease `v0.5.9-rc.12` published from exact commit `161b2bf`:
  https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.5.9-rc.12;
- the tag resolves to `161b2bf` and is marked prerelease.

### Deployment smoke (2026-07-17)

Owner-authorized HACS deployment of `v0.5.9-rc.12` completed:

- pre-restart config check `valid`;
- HACS installed exactly `v0.5.9-rc.12` into
  `/config/custom_components/ikea_bilresa` (verified on disk before restart);
- Home Assistant (Core 2026.7.2, HA OS 18.1, Python 3.14.6) restarted and the
  `ikea_bilresa` config entry returned to `loaded`;
- System Health reported Matter connected via `core_matter_client`, no fallback,
  three discovered wheels and **four configured bindings preserved**;
- exact-domain system-log search returned zero entries; the raw error log showed
  only Home Assistant's standard "custom integration not tested" loader warning,
  no `custom_components.ikea_bilresa` error lines.

This establishes **Implemented + Static + Unit + CI + Released + non-hardware HA
deployment smoke**. It does **not** establish visual/HA UI review or Hardware:
the deployment confirms the backend loads and bindings survive, but the panel
has not been rendered in a real Home Assistant page from this session — the
callable browser surface here is the local harness, not the authenticated HA
frontend.

Owed before this can be called done: open the deployed panel in a **completely
fresh** browser tab (an existing tab keeps the old custom element and the web
platform forbids redefining it) and confirm the spine, the corrected rail, the
lighter unconfigured channels, the result-led Live test and the non-scrolling
tab strip — plus the standing debts this work does not discharge (a non-default
theme, a screen-reader pass, and a physical notched phone).

## BILRESA dual button (E2489) planning docs (Claude Code, 2026-07-17)

Status: **Documentation only. No code, no Static/Unit/CI/Hardware claim.**

The owner added a physical **BILRESA dual button** (E2489, "Tlačítko Obývák",
Matter node observed via read-only MCP) and asked for a support plan. Recorded,
not implemented:

- new `docs/ROADMAP_BUTTON.md` — a `0.6.x` minor train (B0 variant-discovery fix
  → B1 button event entities + device triggers → B2 button binding profile → B3
  panel → B4 hardware + `DEVICE_REFERENCE_BUTTON.md`). Kept separate from the
  wheel roadmap at the owner's request; pointer added to `docs/ROADMAP.md`;
- key finding it documents: `model.parse_node` matches on the product substring
  `"bilresa"`, so the dual button is **already half-discovered** — both endpoints
  decode as `role=button, channel=None`, it enters `coordinator.wheels` and gets
  `ikea_bilresa` device identifiers, but `event.py` makes no entities (channel is
  None), so it is mis-presented as a wheel with zero channels. B0 fixes that
  before any feature;
- firmware quirk to design around (from core PR #159045 / issue #159452):
  pressing past `MultiPressMax` (=2) makes the firmware stop emitting events, so
  the button decode needs a timeout-terminal, not an indefinite wait;
- `docs/HARDWARE_TEST.md` gained a **raw SWITCH_EVENT capture** procedure (the
  StephanMeijer gist's matter-server instrumentation, as an independent oracle
  with explicit privacy/temporary-patch caveats) and a **Section F** dual-button
  checklist. No hardware run recorded.

Read-only MCP was used only to read the device; no Home Assistant state changed.
Dual-button facts marked *(confirm)* in the roadmap still need a raw capture.

### B0 — device-variant discovery (Claude Code, 2026-07-17)

Status: **Implemented + Static + local Unit. mypy not run locally (not
installed). CI has not run. Not deployed, no Hardware.**

The first `ROADMAP_BUTTON.md` package: stop mis-presenting the dual button as a
wheel with zero channels, before adding any feature. No entities, triggers or
bindings for the dual button yet — that is B1.

- `model.py`: `BilresaWheel` gains derived `variant` / `is_dual_button`
  **properties** (not stored fields), computed from endpoint shape — a device
  with rotary (up/down) endpoints is `wheel`, one with only button endpoints is
  `dual_button` (`VARIANT_*` in `const.py`). Derived, so it can never disagree
  with the endpoints, and no constructor/fixture anywhere needed changing.
  Discovery still matches on the `"bilresa"` product substring; the variant is
  the shape distinction, not a new product-code match.
- `system_health.py`: `discovered_wheels` now counts wheel-variant devices only,
  and a new `discovered_buttons` counts dual buttons — so the button no longer
  inflates the wheel count.
- `event.py`: `_sync` skips dual buttons, so no channelless wheel device is
  reconciled/built for them (they already produced zero entities; this also stops
  asserting a wheel link).
- `panel_models.py`: `async_overview_snapshot` skips dual buttons, so the grid
  no longer renders a zero-channel wheel card.
- `coordinator.py`: the discovery log says the variant instead of always "wheel".
- Tests: `test_model.py` (dual-button node fixture with the real shape — two
  button endpoints, no channel label — variant assertions), `test_system_health.py`
  (separate wheel/button counts) and `test_panel_models.py` (overview excludes the
  dual button).

Not done on purpose (deferred): a pre-existing merged `ikea_bilresa` identifier
on an already-discovered dual button is not un-merged here; registry migration
belongs with B1 when the device gets its real entities.

Local validation on Windows / Python 3.14:

```text
python -m compileall (changed files)                 passed
ruff format --check custom_components tests           passed (38 files)
ruff check custom_components tests                    passed
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3.14 -m pytest
  -p pytest_asyncio.plugin                            216 passed
mypy                                                  not run (not installed locally)
```

Files: `custom_components/ikea_bilresa/const.py`, `model.py`, `system_health.py`,
`event.py`, `panel_models.py`, `coordinator.py`, `tests/test_model.py`,
`tests/test_system_health.py`, `tests/test_panel_models.py`, and this handoff.
Owed before B0 closes: exact-revision CI (mypy/hassfest/HACS) and a deployed check
that the dual button no longer shows as a wheel in System Health or the panel.

### B1 (event entities) — dual button gestures in HA (Claude Code, 2026-07-17)

Status: **Implemented + Static + local Unit (222 pytest pass on py3.14, ruff
clean). mypy not run locally. CI has not run. Not deployed, no Hardware.**

This is the event-surface slice of B1: the dual button now produces real Home
Assistant event entities. Device triggers and button bindings are **not** in this
slice (see "deferred" below).

- `event.py`: `_sync` handles both variants — it reconciles the device for both,
  then builds channel entities for a wheel and **button** entities for a dual
  button. New `BilresaButtonEvent`: one entity per physical button, `unique_id`
  `{node}_ep{endpoint}`, name `Button N` (1-based in endpoint order), device
  model `BILRESA dual button` when unlinked.
- **Addressing:** both button endpoints report `channel = None`, so they share the
  one `signal_channel(node, None)` dispatcher signal. Each entity filters
  `action.endpoint_id` to keep only its own button's gestures — no coordinator
  hot-path change was needed (the actions were already being decoded and
  dispatched; only the entity to receive them was missing).
- **Advertised event types are capped by MultiPressMax:** `const.button_event_types`
  returns `press`, `double_press`, `hold`, `release` for the dual button (max 2)
  and adds `triple_press` only at max ≥ 3. No rotation. `model.py` now parses
  `Switch.MultiPressMax` (attribute `ep/59/2`) into `SwitchEndpoint.multi_press_max`.
  `_handle_action` also drops any press count not in the advertised list rather
  than raising.
- **The "past-max goes silent" quirk needs no new timeout here:** the engine's
  button path is stateless (it acts only on `MultiPressComplete`/`LongPress`/
  `LongRelease`, never accumulates), so an unclassified >max press simply produces
  no event — correct, and it cannot get stuck. The timeout concern remains
  relevant only to hold bindings (B2), which already have the ramp watchdog.
- Tests: `test_model.py` (MultiPressMax parsing), `test_event.py`
  (`button_event_types` cap, entity identity/types, endpoint filtering, dropped
  over-max press, hold/release mapping).

Local validation (Windows / Python 3.14): `compileall` passed, `ruff format
--check` passed (38 files), `ruff check` passed, full `pytest` **222 passed**.
mypy not run locally (not installed); CI is authoritative.

Deferred to later B1/B2 slices, on purpose:
- **Device triggers** for the buttons (the automation-UI dropdown). The event
  entities are usable in automations now; the device-trigger sugar is next.
- **Button binding profile** (click/double/hold targets, paired hold-to-ramp) —
  that is B2.
- **Un-merging the pre-existing `ikea_bilresa` identifier** off an already-linked
  dual button: reconcile is now called for it and is idempotent, so no migration
  is forced, but a dedicated registry migration for legacy state is still owed if
  one is found in the field.

Owed before this closes: exact-revision CI, and a deployed check that pressing the
physical dual button drives its new `Button 1/2` event entities (single/double/
hold/release), with no triple-press trigger advertised.

### B1b — device triggers for the dual button (Claude Code, 2026-07-17)

Status: **Implemented + Static + local Unit (226 pytest pass on py3.14, ruff
clean, JSON valid). mypy not run locally. CI has not run. Not deployed, no
Hardware.**

Device-page automation triggers now match the device variant.

- `device_trigger.py` is variant-aware. `async_get_triggers` looks up the
  discovered device from the loaded coordinator (duck-typed, no import cycle):
  a **dual button** offers `button_N` subtypes (one per physical button) with
  only the gestures `button_event_types(MultiPressMax)` allows — press,
  double_press, hold, release; **no rotation, no triple** at max 2. A wheel (or an
  unknown device) keeps the existing `channel_1..3` triggers unchanged.
- `async_attach_trigger` filters a button trigger on `endpoint_id` (buttons carry
  `channel = None` and are told apart by endpoint), and keeps the channel filter
  for wheels. `EVENT_BILRESA` already carries `endpoint_id`, so no coordinator
  change was needed.
- Strings: `button_1..4` subtypes added to `strings.json`, `translations/en.json`
  and `translations/cs.json` (Tlačítko N); the existing `{subtype} pressed` /
  `double-pressed` / `held` / `released` trigger-type strings already read
  correctly for buttons.
- **New `tests/test_device_trigger.py`** (there was none): dual button offers
  button subtypes without rotate/triple, wheel still offers channels, the
  `button_N → endpoint` mapping, and attach filters by endpoint not channel.

Local validation (Windows / Python 3.14): `compileall` passed, JSON parse of the
three string files passed, `ruff format --check` passed (39 files), `ruff check`
passed, full `pytest` **226 passed**. mypy/hassfest not run locally; CI is
authoritative (hassfest validates strings.json ↔ en.json alignment).

Still deferred to B2: the button binding profile (click/double/hold targets,
paired hold-to-ramp). The legacy-identifier registry migration is still owed if
found in the field.

Owed before B1b closes: exact-revision CI, and a deployed check that the dual
button's device page lists Button 1/Button 2 triggers (press/double/hold/release,
no triple, no rotation) and that one fires a test automation.

### B2 — dual-button binding profile and config flow (Codex, 2026-07-17)

Status: **Implemented + Static + local Unit. CI has not run. Not committed,
deployed, HA-UI-verified or Hardware-verified.**

B2 now treats each physical button as its own fully independent control binding,
including when several dual buttons expose the same endpoint numbers:

- **Stored/runtime address:** a wheel binding remains `node_id + channel`; a
  dual-button binding stores `node_id + endpoint`. Runtime keys are explicitly
  tagged `(node_id, "channel", channel)` or
  `(node_id, "endpoint", endpoint_id)`, so the two buttons on one device cannot
  collide and endpoint 1 on one physical dual button cannot collide with
  endpoint 1 on another. Both button bindings still subscribe to the existing
  shared `channel=None` action/raw signals and filter the action's `endpoint_id`
  before running.
- **Independent actions:** each endpoint has its own single-press action
  (`toggle` / `on` / `off` / `none`) and target, optional double-press toggle
  target, and hold action/target. Button 1 may therefore toggle one light while
  button 2 toggles another; every other dual button has its own independent pair.
- **No impossible UI:** creation selects the physical BILRESA first, then builds
  the schema from its parsed variant. A dual button never receives mode, step,
  acceleration, min/max brightness, transition, scene or triple-press fields.
  Its multi-press selector says single/double only. Wheel profiles retain their
  rotary and triple-press fields. Reconfigure may move a binding only between
  devices of the same variant, preventing a channel-shaped entry from being
  saved onto a button-shaped device.
- **Copy flow:** copy-from-existing still pre-fills actions, but the selected
  destination node is authoritative and unsupported source fields are omitted
  before storage. Copying a wheel profile to a button cannot smuggle mode,
  rotation, scene or triple-press fields into the button subentry.
- **Hold-to-ramp / software DIRIGERA:** button bindings reuse the existing
  brightness ramp, release/reconnect/new-gesture stops and 30-second watchdog.
  A new button-only direction can be `up`, `down` or `alternate`, so two endpoint
  bindings may share a light while button 1 always brightens and button 2 always
  dims. The historic wheel behavior remains `alternate`.
- **Icon:** `bilresa_icons.js` now contains the owner-supplied dual-button
  primary and 0.32 secondary paths as the self-contained
  `bilresa:dual-button` glyph. Both current and legacy Home Assistant icon
  contracts resolve it, and `BilresaButtonEvent` uses it. The wheel glyph is
  unchanged.
- **Documentation:** the endpoint address decision and fixed-direction paired
  ramp are recorded in `docs/ROADMAP_BUTTON.md` and
  `docs/DEVICE_REFERENCE_BUTTON.md`; `CHANGELOG.md` records the user-visible
  behavior.

Tests use the real device shape (two `ROLE_BUTTON` endpoints, `channel=None`,
`MultiPressMax=2`) and cover two endpoints on one device, the same endpoint ids
on a second device, independent click targets, endpoint-filtered fast response,
copy sanitization, hidden rotary/triple fields, wheel-schema preservation,
fixed up/down shared-target ramps, release/watchdog safety, titles and both icon
provider contracts.

Exact local validation on Windows / Python 3.14:

```text
manifest/strings/en/cs JSON parsing                  passed
EN/CS/string recursive key alignment                 passed (163 paths each)
python -m compileall -q custom_components tests      passed
ruff format --check custom_components tests          passed (39 files)
ruff check custom_components tests                   passed
mypy custom_components/ikea_bilresa                  passed (20 source files)
node --check panel + icon provider                    passed
node --test panel + icon frontend tests               passed (10 tests)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3.14 -m pytest
  -q -p pytest_asyncio.plugin                         passed (238 tests)
git diff --check                                     passed (CRLF warnings only)
```

Not run: hassfest, HACS validation and exact-revision GitHub CI. No Home
Assistant config-flow screen was opened and no physical press changed a target,
so neither HA UI nor Hardware is claimed. The existing identifier-registry
migration was not needed and remains a separate owed item. B3 panel rendering
was intentionally not touched by the B2 slice; its later implementation is
recorded directly below.

Known assumption: the config flow validates the selected endpoint against the
currently discovered device, and stores the Matter endpoint rather than a
derived button index. This is stable across multiple physical devices and does
not assume endpoints are globally unique.

Single best next action: after owner review of the combined B2+B3 tree, commit
it and run exact-revision CI; only then deploy a candidate for the real-HA panel
pass and execute `HARDWARE_TEST.md` F3 for independent button targets and the
fixed up/down shared-light ramp.

### B3 — existing panel adapted for the dual button (Codex, 2026-07-17)

Status: **Implemented + Static + local Unit + browser-harness visual checks.
Not committed, not run in exact-revision CI, not deployed to Home Assistant and
not Hardware-verified.**

B3 is an adaptation of the existing wheel panel, not a second panel or a new
visual direction:

- **Shared overview and rail:** every wheel and every dual-button device stays
  in the same landing grid and the same 256 px detail switcher. Multiple
  dual-button devices retain separate opaque device keys and each shows its own
  button 1/2 summaries.
- **The same workbench:** the dual-button detail literally reuses
  `.channel-workbench`, `.channel-spine`, `.channel-position` and
  `.channel-surface`. The wheel's vertical `1 / 2 / 3` selector becomes
  `1 / 2`; selecting a number opens one button in the same right-hand gesture
  ledger. An earlier two-stacked-card draft was rejected after owner review and
  removed; no button-only card system or parallel panel remains.
- **Independent binding editor:** button 1 and button 2 open the existing inline
  editor with only their supported short press, double press and hold/release
  fields. Saving sends the safe display button number; the server resolves and
  stores the Matter endpoint. Endpoint ids never enter the frontend snapshot or
  mutation response.
- **Adapted Live test:** the existing `Live test` tab remains. The WebSocket
  activity API maps a private endpoint to safe `button: 1|2` server-side, so the
  UI reports the physical button, short/double/hold/release gesture, dispatch
  state and structured binding result. Panel-triggered tests offer only single,
  double, hold and release. Rotation, triple press and the detent strip remain
  wheel-only.
- **Variant-aware diagnostics and copy:** last activity names a button for the
  dual device; device-level diagnostic wording no longer calls every BILRESA a
  wheel. EN and CS panel dictionaries remain exactly aligned.

The privacy/multi-device tests cover two dual-button devices with the same
endpoint numbers, independent targets, safe endpoint-to-button activity
mapping, binding mutations without leaked endpoint ids, and rejection of
channel-shaped or unsupported rotary/triple requests.

Browser harness checks used the production custom element and its production
CSS, first at the owner's 1521 px reference width and then at 320 px. The
desktop workbench matched the existing wheel composition with a vertical grey
spine and one right-hand action surface. Light and custom dark themes had no
document, host or main-pane horizontal overflow; both button positions were
present; every visible control measured at least 44 px; and real Tab traversal
showed a 2 px focus outline at every in-panel stop. The adapted Live test showed
`Tlačítko 2 · dvojitý stisk`, its structured target result, no detent strip and
only the four supported synthetic controls. This is harness evidence, **not** a
real-HA visual pass.

Exact local validation on Windows / Python 3.14 after B3:

```text
manifest/strings/en/cs JSON parsing                  passed
EN/CS/string recursive key alignment                 passed
python -m compileall -q custom_components tests      passed
ruff format --check custom_components tests          passed (39 files)
ruff check custom_components tests                   passed
mypy custom_components/ikea_bilresa                  passed (20 source files)
node --check panel + icon provider                    passed
node --test panel + icon frontend tests               passed (16 tests)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 py -3.14 -m pytest
  -q -p pytest_asyncio.plugin                         passed (246 tests)
git diff --check                                     passed (CRLF warnings only)
```

Still owed: exact-revision hassfest/HACS/Ruff/mypy/unit CI, a real Home
Assistant light/dark/custom-theme visual and screen-reader pass, and B4 physical
verification. No release, deployment or device control has been performed.

### `v0.6.0-rc.1` publication and controlled deployment

The owner explicitly authorized publication of B0-B3 as an RC and installation
through the existing custom HACS repository on 2026-07-17, specifically to make
the real-HA and physical checks in B4 possible.

Candidate preparation:

- branch: `agent/dual-button-0.6`, based on the currently deployed 0.5.x line;
- version/tag: `0.6.0-rc.1` / `v0.6.0-rc.1`;
- scope: B0 variant discovery, B1 event entities/device triggers, B2 independent
  bindings/config flow, and B3 adaptation of the existing panel and Live test;
- B4 remains open and this tag must be a **prerelease**, never stable;
- local Static, Python Unit, frontend Unit and browser-harness results are
  recorded in the B2/B3 sections above.

The historical repository warning about installation-specific identifiers in
an older, already-public commit remains recorded above. The owner has now
explicitly requested another repository release from this same public history;
the release must not copy any such identifiers into notes, logs or chat.

Concrete publication and deployment results:

- B0/B1 commit `7446194` and B2/B3/release commit `b0c139a` were pushed on
  `agent/dual-button-0.6`;
- draft PR `#2` targets `agent/stabilize-0.5-x`, keeping the `0.6.x` train
  separate from the wheel stabilization line;
- exact-revision CI run `29612854755` passed on full commit
  `b0c139ae45d60f925f18041758f60853830f81c3`: Ruff, frontend checks, mypy,
  246 Python tests, HACS validation and hassfest all succeeded;
- GitHub prerelease `v0.6.0-rc.1` was published, and its lightweight tag points
  directly to that exact CI-verified commit;
- the pre-deployment Home Assistant configuration check was valid; HACS
  installed the exact tag and reported `v0.6.0-rc.1` pending restart;
- Home Assistant restarted normally. The post-restart configuration check is
  valid, the BILRESA config entry is `loaded`, Matter is connected through
  `core_matter_client`, and HACS reports `v0.6.0-rc.1` installed;
- post-restart integration health reports three existing wheels, four existing
  bindings and the new `discovered_buttons` field. It currently reports zero
  discovered dual buttons, so discovery and all gesture/binding outcomes remain
  B4 Hardware work rather than a release claim;
- no BILRESA error was present after startup. The only matching log lines are
  Home Assistant's standard warning for an unreviewed custom integration.

This establishes publication plus install/startup smoke for the RC.1 package,
not functional Hardware evidence for B0-B3.

The owner's first real-panel check then disproved the RC.1 discovery fixture:

- the already commissioned E2489 remained visible with the wheel glyph;
- its detail still showed wheel copy and an empty three-channel surface;
- no button-binding controls were offered;
- sanitized live diagnostics showed exactly two endpoints with
  `channel = null`, but semantic roles `scroll_up` and `scroll_down`;
- System Health therefore reported three wheels and zero dual buttons.

This is not a browser-cache defect. The server sent `variant = wheel`.
The real E2489 uses Matter up/down semantic tags for its two physical buttons;
the invented RC.1 fixture incorrectly omitted those tags. Corrective
`v0.6.0-rc.2` classifies the exact pair of channel-less switch endpoints as a
dual button and normalizes both downstream roles to `button`. Until RC.2 passes
CI and the same real panel reports two buttons, B0 and B3 are not Hardware and
RC.1 is not a valid B4 test baseline.

Corrective RC.2 candidate preparation:

- `tests/fixtures/bilresa_dual_button_node.json` contains only the minimal,
  sanitized raw endpoint facts captured from core Matter diagnostics, with a
  synthetic node id and no serial, network, entity or household identifiers;
- the fixture includes the complete observed TagLists, FeatureMap `30` and
  `MultiPressMax = 2` for both endpoints;
- the same fixture now drives parser/decoder, panel-read-model and config-flow
  regression tests, so those layers cannot silently substitute an invented
  button shape again;
- the official connectedhomeip Switches namespace confirms tags `0x0003` /
  `0x0004` as semantic Up/Down functions, not physical rotation evidence;
- local validation on 2026-07-18: JSON parsing and compileall passed; Ruff
  format/check passed; mypy passed 20 source files; 251 Python tests and 16
  frontend tests passed; `git diff --check` passed with CRLF warnings only.

Corrective RC.2 publication and controlled deployment completed on 2026-07-18:

- corrective commit `fb290d3` (`fix: classify the real BILRESA dual button
  shape`) was pushed to `agent/dual-button-0.6`; draft PR #2 was updated;
- exact-revision GitHub Actions run `29633850027` passed all six jobs for full
  commit `fb290d3e2d0d38faa1a5a5222412ab5bd0cfc528`: Ruff, mypy, frontend,
  251 Python tests, HACS validation and hassfest;
- prerelease `v0.6.0-rc.2` was published from that exact commit:
  https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.6.0-rc.2;
  the RC.1 release notes were amended to identify its known E2489 defect, and
  the RC.1 tag was not moved;
- the pre-restart Home Assistant config check was valid; HACS installed exactly
  `v0.6.0-rc.2`; Home Assistant restarted and the config entry returned to
  `loaded` with the post-restart config check valid;
- System Health changed from **3 wheels / 0 buttons** on RC.1 to **2 wheels /
  1 dual button** on RC.2. Matter is connected through `core_matter_client`,
  no fallback is active, and all four existing wheel bindings were preserved;
- sanitized integration diagnostics report version `0.6.0-rc.2` and the real
  dual-button shape as `variant = dual_button`: two channel-less endpoints,
  both normalized to role `button`, each with `MultiPressMax = 2`;
- the Home Assistant device registry now contains two enabled
  `ikea_bilresa` event entities for that device, Button 1 and Button 2, with the
  HA button event device class;
- the live server-side `ikea_bilresa/overview` snapshot returns the existing
  panel contract (`contract_version = 4`) with the same device shell,
  `variant = dual_button`, `channels = []` and independent unconfigured button
  controls `1 / 2`. The frontend maps that variant to the dedicated dual-button
  glyph, the `Tlačítka / Živý test / Diagnostika` tabs, and `Přidat propojení`
  for each control;
- the config-subentry create schema lists the dual-button device alongside both
  wheels, so the native add-binding path can select it. No real binding was
  created and no target-changing panel test was run;
- the only matching startup log line is Home Assistant's standard warning for
  an unreviewed custom integration; no BILRESA runtime error was recorded.

This is **Implemented + Static + Unit + CI + Released + real-HA server-side
deployment smoke** for RC.2. It corrects the precise server-side failure shown
by the owner's RC.1 screenshots. It is deliberately not labelled Hardware:
the owner still needs to open a completely fresh panel tab and physically press
both buttons to verify gesture delivery and real target outcomes in B4.

### Post-RC.2 Live-test empty-state and history pass (2026-07-18)

Status: **Implemented + Static + local Python Unit + frontend Unit. Not
committed, not published, not deployed, no new Hardware claim.**

The owner's first correct dual-button screenshot proved physical single presses
were reaching the adapted Live test, but also exposed two product defects:

- an unconfigured press was presented as the internal fallback
  `Vypočtený výsledek se nehlásí`, making successful hardware recognition read
  like a runtime error;
- the recent-event card had no bounded visual height, so its event rows would
  keep extending the detail page instead of becoming a secondary history.

The live-result model now separates **recognized gesture** from **configured
target outcome**. A press with no binding leads with `Stisk rozpoznán`, explains
that it reached Home Assistant but the button does not control a target yet,
and offers `Nastavit tlačítko 1/2`, which opens the existing inline editor for
that exact physical button. Wheel channels use the same state model. A
not-configured control is neutral, not a failed dispatch.

The Live-test copy was reviewed as one state system rather than as isolated
phrases. The intro now promises gesture recognition first and target action
second; result/event labels are contextual; runtime jargon was removed from
ordinary empty states; and the side heading is `Tlačítka` / `Kanály`, because
the list includes configured and unconfigured controls.

The recent-event list remains bounded to eight records in memory and is now
also capped at 320 px on screen with vertical overflow, contained overscroll,
stable scrollbar space and a labelled keyboard-focusable ordered list. It keeps
native list semantics and a visible inset focus ring.

Files:

- `custom_components/ikea_bilresa/frontend/ikea_bilresa_panel.js`
- `custom_components/ikea_bilresa/panel_strings.py`
- `tests/panel_frontend.test.mjs`
- `tests/test_panel.py`
- `tests/test_panel_strings.py`
- `docs/PANEL_DESIGN.md`
- `CHANGELOG.md`
- `PROJECT_STATUS.md`

Validation:

```text
manifest/strings/en/cs JSON parsing                  passed
python -m compileall -q custom_components tests      passed
ruff format --check custom_components tests          passed (39 files)
ruff check custom_components tests                   passed
mypy custom_components/ikea_bilresa                  passed (20 source files)
node --check panel                                   passed
node --test panel + icon frontend tests               passed (19 tests)
isolated Windows Python 3.14 pytest                   passed (254 tests)
git diff --check                                     passed (CRLF warnings only)
```

The user-provided real-HA screenshot was inspected at its original resolution.
No post-change real-HA screenshot was captured: the available authenticated
screenshot service supports Lovelace dashboards, not this custom panel, and the
Product Design browser workflow was not requested. Visual HA verification
therefore remains pending and must not be inferred from code/tests.

## `0.5.9-rc.11` BILRESA icon identity (current working tree)

The owner selected the optical V2 product glyph and Material Symbols Rounded
gesture family on 2026-07-16. The current working tree implements that decision:

- a small globally loaded `bilresa_icons.js` provider registers
  `bilresa:scroll-wheel` through both the current `window.customIcons` contract
  and the backward-compatible `window.customIconsets` contract;
- the provider is registered before the sidebar panel entry and removed from
  the advertised extra-module list on unload; panel failure remains non-fatal;
- the sidebar icon changes from `mdi:knob` to `bilresa:scroll-wheel`;
- wheel cards and the switcher rail use the same approved V2 primary path,
  secondary path and `0 0 24 24` view box; the panel keeps the selected 0.32
  secondary opacity;
- channel actions use distinct Rounded paths for rotate left/right, single,
  double and triple press; rotation is a paired glyph because the read model
  exposes one combined left/right action;
- hold and release render as one long-press sequence with an end marker, rather
  than assigning release an unrelated standalone symbol;
- manifest/cache-busting version is `0.5.9-rc.11`; no external Material Symbols
  integration is required.

Local validation for this working tree:

```text
manifest/strings/en/cs JSON parsing                  passed
python -m compileall -q custom_components tests     passed
ruff format --check custom_components tests         passed
ruff check custom_components tests                  passed
mypy custom_components/ikea_bilresa                 passed (20 source files)
node --check panel + icon provider                   passed
Node frontend tests                                 9 passed
Python tests on Windows Python 3.14                 204 passed
git diff --check                                    passed (CRLF warnings only)
Playwright desktop/mobile/overview visual fixture   passed; clean console
```

Exact-revision publication and deployment results:

- commit `f676bb7` was pushed to `agent/stabilize-0.5-x` and updated draft PR
  #1;
- GitHub Actions run `29523574699` passed HACS validation, hassfest, Ruff, mypy,
  204 Python tests and the frontend syntax/unit checks;
- prerelease `v0.5.9-rc.11` was created from exact commit `f676bb7`;
- Home Assistant configuration checks passed before and after the HACS download;
- HACS installed exactly `v0.5.9-rc.11`, Home Assistant restarted, and the
  integration returned to `loaded` with all four binding subentries preserved;
- exact-domain system-log and error-log searches returned zero matches;
- the running HA instance served `bilresa_icons.js` and the panel bundle with
  HTTP 200; content checks confirmed the custom provider/V2 geometry, distinct
  triple-press path and hold/release sequence;
- automated capture of the real panel was unavailable because the optional
  Puppet screenshot-engine add-on is not installed. It was not installed solely
  for this check.

This establishes **Implemented + Static + Unit + CI + Released** and a
successful non-hardware Home Assistant deployment smoke test. Real-HA visual
review in a fresh browser tab and physical-wheel Hardware remain pending.

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

Status: **Implemented + Static + Unit + CI + Released + deployed to Home
Assistant as `v0.5.9-rc.3`. Browser visual comparison pending.**

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

Publication and deployment results for `v0.5.9-rc.3`:

- runtime commit `ecacb21` (`Polish BILRESA wheel detail layout`) was pushed to
  `agent/stabilize-0.5-x`;
- exact-revision GitHub Actions run `29486044677` passed frontend checks, HACS
  validation, hassfest, Ruff, mypy and Unit tests;
- prerelease `v0.5.9-rc.3` was published from exact commit `ecacb21`:
  https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.5.9-rc.3;
- pre-deployment Home Assistant config check was valid;
- HACS installed exactly `v0.5.9-rc.3`;
- Home Assistant restarted and the integration returned to `loaded`;
- System Health reported Matter connected via `core_matter_client`, no fallback
  reason, two discovered wheels and four configured bindings;
- HACS still reported installed version `v0.5.9-rc.3` after restart;
- config-entry diagnostics still showed four binding subentries. Stored
  `channel` values remained strings, `mode` was present, and no
  `binding_profile` field was present;
- system-log search for `ikea_bilresa` returned no entries. Raw log search
  showed only Home Assistant's standard custom-integration loader warning, and
  no `custom_components.ikea_bilresa` error lines.

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

### Matter Server 9.1.0 compatibility audit and G0 safeguards (2026-07-18)

Status: **Implemented + Static + Python Unit + frontend regression +
exact-revision CI + Released + real-HA deployment smoke. G0 overflow fix is not
yet Hardware-verified.**

The official Home Assistant add-on 9.1.0 changelog, matterjs-server 1.2.6 tag,
WebSocket API/schema changelog, Python client and Matter 1.6 Switch definition
were reviewed. Matter Server 9.1.0 uses server schema 12 with minimum supported
schema 11; its own Python client still advertises schema 11. The integration
therefore correctly remains a schema-11 compatibility client and accepts the
new server instead of claiming schema 12 and breaking older schema-11 servers.
System Health now reports both values separately.

The dedicated WebSocket path now handles `node_updated`,
`attribute_updated` and `server_shutdown` explicitly. The core-client adapter
restores node/path context for Switch `CurrentPosition` by comparing the
already-updated Matter node cache. CurrentPosition is deliberately only a
release/stuck-state hint because matterjs-server may coalesce attribute updates
under backpressure. Every user-visible gesture remains derived from ordered
`node_event` messages.

The Matter 1.6 overflow contract exposed a real bug:
`decoded.get("count") or 1` converted a valid zero completion count into a
single press. Zero, non-integer and positive counts above the endpoint's
advertised `MultiPressMax` are now ignored instead of executing a target.

The post-B3 feature ideas are specified in `docs/ADVANCED_GESTURES.md` as G1–G4:
Instant response and observed hold duration; opt-in dual-button chords and
wheel-button rotation modifiers; HA scripts/scenes/sequences and named
profiles; saturation and cover tilt. The contract keeps all state isolated by
node/endpoint, preserves the existing panel workbench and leaves complex logic
to Home Assistant rather than embedding a second automation engine.

The first bounded G1 slice is also implemented locally. Bindings and the
existing panel editor now distinguish three real response points:
`Instant initial press`, `Fast release` and `Multi-press aware`. Instant reacts
once on `InitialPress`; semantic validation rejects it when double/triple or
hold behavior would make that early action ambiguous. The later public
completion still reaches event entities, device triggers and the public event
bus, but the direct binding cannot execute twice. Existing stored bindings keep
their prior default.

G1 also records `observed_duration_ms` for hold/release actions when
`InitialPress` and the later boundary belong to one uninterrupted host-
monotonic observation. The public event entity, event bus, binding activity and
Live test carry the bounded value. The panel labels it as integration-observed
time (for example `zachyceno 2,25 s`), not physical contact duration. A
reconnect, reset or CurrentPosition release hint invalidates the measurement
instead of manufacturing a number.

Files added or materially changed by this package:

- `custom_components/ikea_bilresa/matter_ws.py`
- `custom_components/ikea_bilresa/matter_core.py`
- `custom_components/ikea_bilresa/coordinator.py`
- `custom_components/ikea_bilresa/engine.py`
- `custom_components/ikea_bilresa/const.py`
- `custom_components/ikea_bilresa/system_health.py`
- `custom_components/ikea_bilresa/binding.py`
- `custom_components/ikea_bilresa/binding_config.py`
- `custom_components/ikea_bilresa/event.py`
- `custom_components/ikea_bilresa/panel_api.py`
- config-flow, panel and EN/CS response copy
- `tests/fixtures/matterjs_1_2_6.json`
- protocol/core/coordinator/engine/System Health tests
- `docs/MATTERJS_COMPATIBILITY.md`
- `docs/ADVANCED_GESTURES.md`
- `docs/ROADMAP_BUTTON.md`
- `CHANGELOG.md`

Validation:

```text
isolated Windows Python 3.14 pytest                   passed (275 tests)
ruff format --check custom_components tests          passed (39 files)
ruff check custom_components tests                   passed
mypy custom_components/ikea_bilresa                  passed (20 source files)
python -m compileall -q custom_components tests      passed
node --check panel                                   passed
node --test panel + icon frontend tests              passed (20 tests)
git diff --check                                     passed (CRLF warnings only)
```

Publication and controlled deployment completed on 2026-07-18:

- candidate commit `e6e67eb` was pushed on `agent/dual-button-0.6`;
- GitHub Actions run `29636673855` passed hassfest, HACS validation, Ruff,
  mypy, frontend tests and Python unit tests;
- annotated tag and prerelease `v0.6.0-rc.3` resolve to exact candidate
  `e6e67eb`;
- the pre-restart Home Assistant configuration check was valid, HACS installed
  exactly `v0.6.0-rc.3`, and Home Assistant restarted normally;
- post-restart diagnostics reported integration manifest `0.6.0-rc.3`, config
  entry `loaded`, Matter Server add-on `9.1.0` started, server schema `12`,
  client compatibility schema `11`, event source `core_matter_client`, no
  fallback, two wheels, one dual button and all six stored bindings;
- no `ikea_bilresa` system-log entry appeared after startup.

No binding, automation, target or device configuration was changed during
deployment. This establishes a successful server-side deployment smoke on
Matter Server 9.1.0/schema 12.

The owner then repeated the exact three-rapid-tap overflow gesture on the
installed RC.3. Matter Server reported `MultiPressComplete(0)` on the E2489
endpoint. RC.3 dispatched zero actions, neither the public custom event entity
nor the core Matter event entity advanced, the configured target stayed
unchanged, and no `ikea_bilresa` error appeared. The G0 zero-count safeguard is
therefore **Hardware PASS** on the exact released candidate. Above-max rejection
remains Unit evidence because the real device represents this overflow as zero.
An immediate deliberate normal single then produced
`MultiPressComplete(1)`, advanced both event surfaces once, dispatched exactly
one binding action and changed only the configured target once. Recovery after
the ignored overflow is also **Hardware PASS**.

The next single arrived after approximately 2 hours 11 minutes without a valid
Switch gesture on that endpoint. Matter Server emitted exactly one completion
with count one; both event surfaces advanced once and the binding action count
increased by one. There was no queued Switch burst, reconnect, fallback or
matching integration error. The B4 idle-resume gate is therefore
**Hardware PASS**.

The owner then pressed the other E2489 side and immediately operated the living
room wheel. Only the second dual-button endpoint advanced and it toggled only
its configured target once; the first endpoint stayed unchanged. The wheel
then emitted eight real-time rotate-up batches on channel 3 and the integration
dispatched exactly eight corresponding wheel actions. Wheel channels 1/2 and
the observed dual-button targets did not change from the wheel activity. No
reconnect, fallback or matching error appeared. Cross-endpoint and cross-node
no-leak are therefore **Hardware PASS** for this bounded adjacent-use test. The
integration config entry was then reloaded without restarting Home Assistant.
It returned `loaded` through `core_matter_client` with two wheels, one dual
button and all six stored bindings. Its first post-reload physical single
produced exactly one completion, one public event, one binding action and one
intended target change; no old event replayed and no fallback or error
appeared. Config-entry restore is therefore **Hardware PASS**.

The subsequent controlled restart of only the Matter Server add-on exposed a
real RC.3 lifecycle defect. While Home Assistant temporarily had no loaded core
Matter config entry, `_get_loaded_client()` indexed an empty list and the
ten-second runtime-unavailable threshold caused a permanent switch to
`dedicated_websocket` for that integration load. Diagnostics recorded one
fallback with reason `list index out of range`, and the dual button was
temporarily unavailable. Reloading only the IKEA BILRESA config entry restored
`loaded`, `core_matter_client`, two wheels, one dual button and all six
bindings. RC.3 therefore **FAILS** the controlled Matter Server restart gate;
the successful config-entry reload does not turn that result into a pass.

The local `v0.6.0-rc.4` candidate explicitly represents the missing loaded
Matter entry as a temporary runtime condition, extends the runtime grace from
10 to 60 seconds, and reattaches to the replacement core client. Initial
unsupported-client fallback remains immediate and persistent runtime
incompatibility still falls back after the grace period. The exact regression
test keeps the Matter entry absent for five monitor checks, restores a new
client, and proves reattachment without fallback. Local validation passed 276
Python tests, 20 frontend tests, Ruff format/lint, mypy, compileall, panel
syntax and diff checks. Candidate commit `5a39f90` is pushed on
`agent/dual-button-0.6`; GitHub Actions run `29641407216` passed hassfest, HACS
validation, Ruff, mypy, frontend checks and Python unit tests on that exact
revision.

The release/deployment follow-up completed on 2026-07-18:

- release commit `90076cf` passed exact-revision GitHub Actions run
  `29641472813`;
- annotated tag and prerelease `v0.6.0-rc.4` resolve to `90076cf`;
- HACS installed exactly `v0.6.0-rc.4`; configuration validation passed and
  Home Assistant restarted normally;
- the loaded manifest reported `0.6.0-rc.4`, with Matter Server 9.1.0/schema 12,
  client compatibility schema 11, `core_matter_client`, two wheels, one dual
  button, six bindings and no fallback;
- a controlled restart of only the Matter Server app produced one disconnect
  and one successful core-client reattach. Connection count advanced to two,
  fallback count stayed zero through the full grace window, all devices and
  bindings returned, and no matching integration error appeared;
- the first physical Button 1 single afterward advanced the custom and core
  Matter event surfaces once, dispatched exactly one action and changed only
  its intended light from off to on. Button 2 and the other observed targets
  stayed unchanged.

RC.4 therefore has Static, Unit, exact-revision CI, Released, deployed and
Hardware evidence for the Matter Server restart recovery and first post-restart
single.

The owner then authorized the two remaining targeted B4 failure-injection
checks with a reversible safe dimmable target. Button 2 was temporarily changed
from hold-none to hold-ramp-up while its existing single/double targets were
preserved. A qualifying real hold produced `long_press` at `13:32:44.658`; the
30-second watchdog fired at `13:33:14.664`, and the later
`long_release` at `13:34:03.490` neither restarted the ramp nor emitted a stale
command. There was no cross-target change, reconnect or fallback. The exact
original Button 2 payload was restored, including its original
`73c03e349fe721d3` revision, and the safe target returned to its original off
state.

The already configured wheel channel-2 target was then naturally unavailable
while its power relay was off. Two physical detent batches were decoded and
skipped with one transition-deduplicated availability warning, no target
change, no recurring command, no integration error and no fallback. After
power recovery, a clean physical clockwise detent decoded as up and moved the
target from brightness 128 to 135, proving normal-path recovery and the
expected clockwise-to-brighten mapping. The target was restored to its original
100% brightness.

RC.4 therefore has **B4 Hardware PASS**. The run covers the real E2489 grammar,
both endpoints, independent binding outcomes, overflow safeguard, idle resume,
cross-endpoint/node isolation, config-entry reload, Matter Server restart,
lost-release watchdog, unavailable-target suppression and recovery. The
optional paired two-button hold-ramp profile was not configured and is not
claimed.

This follow-up changes documentation only. `git diff --check` passed and the 20
Node frontend tests passed. A fresh `python -m pytest -q` attempt did not reach
test execution because the current system Python lacks the `homeassistant`
package; all 18 collection modules reported that same missing dependency. This
is a local-environment limitation, not a Python-test pass. The installed code
remains the exact `v0.6.0-rc.4` release whose Python suite and six CI jobs
already passed; no runtime source or test file changed in this follow-up.

### B4 E2489 partial hardware run on Matter Server 9.1.0 (2026-07-18)

The owner authorized and performed a controlled physical gesture run against
the currently installed `v0.6.0-rc.2`; Codex observed Home Assistant state,
recorder history, redacted integration diagnostics and sanitized Matter Server
logs. No binding, integration option, logger level, automation or device
configuration was changed.

Both physical buttons passed single, double, long-press and long-release
delivery. Slow pairs remained separate singles and fast pairs completed as
doubles. Configured single, double, hold-toggle and hold-none outcomes affected
only their intended targets. Both CurrentPosition values returned to zero and
no matching integration error appeared.

The real E2489 then reproduced the exact G0 overflow case: three rapid physical
taps ended with `MultiPressComplete(0)`. Installed RC.2 converted zero to one,
published a false single press and toggled its configured target. A subsequent
normal single completed correctly, so the input was not left stuck. This is
direct Hardware evidence that the local `count <= 0` safeguard is necessary;
it is not Hardware evidence that the safeguard works until an exact candidate
is installed and the same test passes without a target action.

The raw grammar and sanitized environment were added to
`docs/DEVICE_REFERENCE_BUTTON.md`; the partial verdict and remaining gates are
recorded in `docs/HARDWARE_TEST.md`. Overall B4 remains **IN PROGRESS**.

## Single best next action

Review the remaining unchecked all-features hardware matrix independently from
the now-complete B4 package, then decide whether `v0.6.0-rc.4` needs a final
soak-only RC follow-up or is ready for the explicitly authorized stable-release
gate.

## Next-agent handoff

1. Read the required instruction/reference files; do not rely on chat history.
2. Start from RC.3 release commit `e6e67eb` plus its deployment-record
   follow-up on `agent/dual-button-0.6`; then re-check HEAD, branch and status.
3. Do not move the `v0.6.0-rc.1` tag away from runtime commit `b0c139a`.
4. RC.1 failed real E2489 discovery. RC.2 fixed discovery and supplied partial
   B4 Hardware evidence but failed three-tap overflow handling. RC.3 has Static,
   Python Unit, frontend Unit, exact-revision CI, Released and successful
   Matter Server 9.1.0/schema-12 deployment-smoke evidence; its zero-count
   overflow fix and immediate normal-single recovery passed the exact physical
   retest, and a later single passed after approximately 2 hours 11 minutes
   idle with no queued burst or reconnect. Adjacent use of the other dual-button
   endpoint and wheel channel 3 also passed cross-endpoint/node no-leak. A
   config-entry reload restored all devices/bindings and its first single
   exactly once. Its controlled Matter Server restart then failed because the
   temporary core-entry unload triggered a permanent dedicated-WebSocket
   fallback. RC.4 release commit `90076cf` fixes that lifecycle path and is
   locally validated, exact-revision CI-green, Released, deployed and Hardware
   PASS for the controlled restart plus first physical post-restart single.
5. The owner selected a safe dimmable target for the bounded watchdog check.
   The temporary binding and target state were restored exactly; do not repeat
   target-changing tests without fresh authorization.
6. The Live-test polish and G0 compatibility safeguards are included in RC.3.
   Do not promote RC.3 to stable. RC.4 is the current prerelease and now has
   complete B4 Hardware evidence, including restart recovery, watchdog,
   unavailable-target suppression and normal-path recovery.
