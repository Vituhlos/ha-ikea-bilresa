# Panel polish plan: make the editor a Home Assistant editor

Status: **approved by the owner 2026-10-04. Phase 0 answered, Phase 1
implemented (not released); Phases 2 to 5 not started.**
`PANEL_DESIGN.md` stays the product design; this file is the plan to close the
gap between that design and what the panel ships today. `PROJECT_STATUS.md`
remains the canonical handoff.

## Context

The owner said the settings panel is "not 100 % yet". A design review on
2026-10-04 looked at every view (overview, wheel detail, binding editor, Live
test, Diagnostics, dual button, 390 px width, dark) and he confirmed the
findings below match what bothered him.

How the review was done, and its limits: the panel's real JavaScript was
rendered locally with the repository's Czech labels and an overview snapshot
read from the owner's instance. Layout and copy are therefore real. Colours are
not: Home Assistant's default tokens stood in for the owner's theme. Saving was
not exercised. The Puppet screenshot tool cannot help here, because it renders
Lovelace dashboards only and rejects a custom panel path.

## Findings, most severe first

1. **The editor's controls are bare browser controls.** The entity picker is a
   plain `<select>` with no search, showing `Linka · light.linka`. The scene
   list is a native multi-select: several entries need Ctrl-click, it is close
   to unusable on a phone, and it cannot express order, although scene cycling
   depends on order. Numbers are bare inputs with no slider and the unit in a
   helper line. Every other Home Assistant settings page uses its own entity
   picker and selectors, so this is where the panel stops feeling native.
2. **A false alarm.** The overview shows "… has an unavailable binding target.
   Open the channel and fix the binding" for a bulb that is merely switched off
   at the wall. `_target_missing()` in `panel_models.py` treats `unavailable`
   and `unknown` like an entity that no longer exists. On the owner's instance
   the warning is permanent and there is nothing to fix.
3. **Editing opens below the summary instead of replacing it.** The gesture
   ledger stays on screen and the form repeats the same facts underneath; on a
   phone that is three screens of scrolling.
4. **The ledger is mostly empty rows.** Three of five rows usually read "No
   action". "Hold → release" with the value "Toggle · Linka — No action" is
   hard to parse.
5. **The "Channel behaviour" card mixes two things** (which channels are
   active, and the dial's step and acceleration) and never says what a dial is.
   The page ends up with two different "acceleration" fields, two different
   "per notch" steps and two Save buttons with different scopes. "Acceleration:
   0" is a bare number with no scale.
6. **Save, Cancel and Delete binding sit side by side.**
7. **Small things.** Labels and help are small grey text; the warning on a
   channel is a black exclamation mark with no colour; the wheel's subtitle
   wraps to three lines at 390 px.

8. **The header moves on scroll** (reported by the owner on 2026-10-04 from
   his own instance, theme Fluvy). The header is `position: sticky`, so this
   should not happen; the cause is not established. To be diagnosed and fixed
   in Phase 5.

Not measured: contrast ratios, keyboard order, screen reader output.

## What "fits Home Assistant's design" means here

`PANEL_DESIGN.md` already sets the rule: *selection and state use real Home
Assistant components, theme variables, typography, spacing, dividers and
standard Material Design Icons*, and the layout is rebuilt *from supported
HA/Lit primitives*. The panel follows the token half of that rule today and
not the component half. This plan closes the component half, and keeps the
rules that were decided with the owner on 2026-07-29:

- fields are grouped by what they belong to, never by how advanced they are;
- one row carries one gesture, in the ledger's order: rotation, short press,
  double, triple, hold;
- groups are separated by a hairline, never boxed.

## The one technical question that decides the approach

Verified in the Home Assistant frontend source (`20260826.7`) and the developer
documentation:

- Home Assistant publishes "Frontend component updates" every release and
  states: *"Custom card authors can use Home Assistant frontend components, but
  internal Home Assistant UI APIs may change."* Use is allowed; stability is
  not promised.
- `ha-form` with a selector schema is what custom card editors use. Selectors
  (`entity`, `number` with a slider and unit, `select`, `boolean`) are the same
  concept the config flow already uses on the Python side.
- **There is no supported way for a custom panel to load those components.**
  `window.loadCardHelpers` is defined only once the Lovelace panel has loaded.
  `ha-panel-custom` creates the panel element and loads nothing else. Whether
  `ha-form` and `ha-selector` are already registered when `/ikea-bilresa` is
  opened cold is therefore not known, and the usual workarounds reach into
  frontend internals.

Consequence, given the owner's other requirement (compatible with Home
Assistant 2027): **the panel may use Home Assistant's components but must not
depend on them.** Each control is rendered with the Home Assistant component
when it is available and with the panel's own control when it is not. If a
future frontend removes or renames a component, the panel degrades to today's
controls instead of breaking.

## Phase 0 — spike (no code shipped)

Needs the owner to sign in once to his instance in the in-app browser; nothing
is changed there.

1. Open `/ikea-bilresa` cold and list which `ha-*` elements are registered.
2. Create `ha-form` with a small selector schema inside the panel's shadow root
   and confirm it renders, emits `value-changed`, and follows the theme.
3. If it is not registered on a cold load, test each loading route and note
   which ones touch internals.
4. Repeat after navigating from a dashboard, since that changes what is loaded.

Exit: a written answer in `PROJECT_STATUS.md` to "which components are there on
a cold load, and how reliably can the missing ones be loaded". Phase 2's scope
is fixed only after that.

### Result (2026-10-04, Home Assistant 2026.9.4, owner's instance)

Steps 1 and 2 were run on a cold load of `/ikea-bilresa`. Step 3 was not
needed. Step 4 was not run.

- **Registered on the cold load:** `ha-form`, `ha-selector`,
  `ha-entity-picker`, `ha-generic-picker`, `ha-picker-field`, `ha-slider`,
  `ha-control-slider`, `ha-select`, `ha-input`, `ha-button`, `ha-icon`,
  `ha-svg-icon`, `ha-icon-button`, `ha-card`, `ha-alert`, `ha-switch`,
  `ha-checkbox`, `ha-formfield`, `ha-expansion-panel`, `ha-settings-row`,
  `ha-sortable`, `ha-list`, `ha-list-item`, `ha-md-list-item`,
  `ha-state-icon`, `ha-domain-icon`, `ha-tab-group`, `hass-tabs-subpage`,
  `ha-top-app-bar-fixed`, `ha-menu-button`, `ha-dialog`, `ha-spinner`,
  `ha-tooltip`, `ha-dropdown`, `ha-code-editor`, `ha-yaml-editor`.
- **Not registered:** `ha-selector-entity`, `-number`, `-select`,
  `-boolean` (these loaded on demand as soon as an `ha-form` using them was
  rendered), `ha-entities-picker`, `ha-target-picker`, `ha-combo-box`,
  `ha-textfield`, `ha-md-list`, `hass-subpage`, `ha-header-bar`,
  `ha-md-dialog`, `ha-wa-dialog`, `ha-radio-group`,
  `ha-button-toggle-group`, `ha-fab`, `ha-button-menu`,
  `ha-labeled-slider`. `window.loadCardHelpers` was undefined.
- **`ha-form` works inside the panel:** a form with entity, number (slider),
  select and boolean selectors rendered, followed the theme and emitted
  `value-changed`.

What this does and does not settle:

- Phase 2 can be built on `ha-form` with a selector schema; no loading
  workaround that reaches into frontend internals is needed on this instance.
- Scene ordering has no ready component: `ha-entities-picker` is absent. The
  ordered list stays the panel's own control (`ha-sortable` is available for
  drag and drop; move up/down buttons remain the fallback).
- **A clean Home Assistant is unproven.** This instance loads several
  third-party frontend modules, and one of them may be what registered
  `ha-form`. The fallback path is therefore still required, and Phase 2 must
  be checked once on an instance without custom frontend modules before the
  dual path is trusted.

## Phase 1 — tell "unavailable" from "gone" (backend, independent of Phase 0)

- `panel_models.py`: replace the boolean with a three-way state per target:
  `ok`, `unavailable` (the entity exists and is currently unavailable or
  unknown), `missing` (no such entity). Keep `target_missing` in the snapshot,
  true only for `missing`, so an older cached panel keeps working; bump
  `contract_version`.
- Overview banner and the "fix the binding" copy apply to `missing` only.
- `unavailable` is shown where the target is named, as a neutral state, not as
  an error and not in the banner.
- The binding runtime is untouched: it already sends nothing to an unavailable
  target.
- English and Czech copy; tests in `test_panel_models.py` for all three states.

This is the only finding that misinforms the user, so it comes first.

**Implemented 2026-10-04** as described, with three decisions made on the
way:

- `unknown` counts as `ok`, not `unavailable`: a scene that was never
  activated and an idle media player report it and work.
- An entity with no state that the entity registry still knows (disabled, or
  its integration is not loaded) is `unavailable`, not `missing`.
- A channel or button row names the target its state belongs to instead of
  appending the state to its own label, which could blame the wrong entity.

## Phase 2 — the editor's controls

Scope depends on Phase 0. The intended end state:

- **Entity fields:** Home Assistant's entity selector (search, icon, area),
  filtered by the domains the mode supports. Fallback: the panel's own
  searchable list.
- **Scenes:** an ordered list with add, remove and reorder, since order is the
  feature. Fallback: the same list with move up/down buttons.
- **Numbers:** a slider with the unit beside the value, in the range the
  server validates. Fallback: number input with the unit as a suffix.
- **Choices:** Home Assistant's select. Fallback: `<select>`.
- **One schema, owned by the server.** The fields, ranges, units and
  visibility rules already exist in `binding_config.py` and `config_flow.py`.
  The panel asks the integration for the form description instead of keeping
  its own copy, so the config flow and the panel cannot drift apart.

## Phase 3 — edit in place

- "Edit binding" turns the ledger into the form; the read-only summary is not
  kept above it.
- The ledger lists configured gestures. Gestures with no action collapse into
  one "add an action" row that names what can be added.
- "Hold → release" becomes one row that states the hold action plainly; the
  release half is mentioned only when it does something.
- Field order and grouping keep the 2026-07-29 rules above.

## Phase 4 — the channel behaviour card

- Split it: "Active channels" on its own, and "Dial" on its own with one
  sentence saying what the dial is (the number entity each channel has) and
  where to find it.
- Name the two steps so they cannot be confused: the binding's step changes
  the target, the dial's step changes the dial.
- Give acceleration a scale and say what 0 means.
- One Save per card, labelled with what it saves.

## Phase 5 — actions and polish

- Move "Delete binding" away from Save and Cancel; keep its confirmation.
- Find out why the header moves on scroll in the owner's theme and fix it.
- Warning state uses the theme's warning colour and an icon, not a black mark.
- Wheel subtitle at 390 px: one line, with the rest on a second line by
  design, not by overflow.
- Measure contrast for secondary text in light and dark; keyboard and screen
  reader pass. This closes the part of `V0.6.0_CHECKLIST.md` item 4 that is
  still owed.

## Verification

- **A committed preview tool.** The local render used for this review becomes
  a small developer tool in the repository, fed by a synthetic fixture (no
  names or identifiers from any real home). It gives every view at desktop and
  phone width, light and dark, without a Home Assistant instance, and is what
  makes a visual change checkable before deployment.
- `tests/panel_frontend.test.mjs`: the fallback path for every control, so the
  panel is proven to work without Home Assistant's components.
- `tests/test_panel_models.py` and `tests/test_panel_api.py` for the snapshot
  and schema changes.
- **In real Home Assistant, by the owner or through his signed-in browser
  session:** light, dark and his own theme, desktop and phone. A local render
  cannot stand in for this.

## Risks

- Home Assistant's components are not a stable API. The fallback is the
  answer; it also has to stay tested, or it will rot.
- Two renderings of each control cost more than one. If Phase 0 shows the
  components cannot be loaded reliably, the plan falls back to building the
  panel's own controls well, styled with the tokens, and drops the dual path.
- A contract bump (Phase 1) means an old cached panel script may talk to a new
  backend for one page load; the compatibility field covers that.

## Out of scope

Behaviour profiles, new gestures, new target types, and the "short press"
versus "single press" wording, which waits for the owner's decision.

## Decisions needed from the owner

1. ~~Sign in to the instance in the in-app browser for Phase 0.~~ Done.
2. Which phases must be in the stable 0.6.0. Recommendation: Phase 0 and
   Phase 1 before it, Phases 2 to 5 after it, because rc.14 already carries a
   large change that has to reach stable first.
