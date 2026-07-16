# BILRESA panel product design

Status: **implemented through the `0.5.9-rc.1` candidate; HA UI deployment
validation pending and physical-wheel validation deferred**

This document defines the intended product and technical direction for a
future first-party BILRESA panel inside Home Assistant. It is the handoff for
the owner, Codex and Claude Code. The existing Home Assistant integration page
remains the installation and registry surface; the panel would become the
human-oriented product surface.

No panel work should delay the physical release-candidate validation in
`HARDWARE_TEST.md`. The first implementation must be additive and must not
change Matter event decoding, binding behavior or stored configuration.

## Selected visual direction

Selected on 2026-07-15 and revised the same day, after a browser prototype
replaced the generated mockups as the source of truth.

The panel has **two layers**. Earlier revisions of this document described the
top level three different ways; the following is the only valid reading.

1. **Overview — the landing layer.** A responsive grid with one card per
   physical wheel. Each card carries the wheel's name, area, status, last
   activity and all three channel summaries. This layer answers the first
   question in `Product intent`: what does each wheel control.
2. **Wheel detail — opened from a card.** A 256 px wheel rail on the left and
   the opened wheel on the right, with `Channels`, `Live test` and
   `Diagnostics` as views of that wheel. The rail is a *switcher*, not the
   overview: it makes moving between wheels one click without returning to the
   grid.

The live test is therefore a view inside an opened wheel, never the landing
page.

### Why the rail is not the landing layer

An earlier direction used the master-detail rail as the panel's landing
structure. A browser prototype measured against real layout ruled that out:
the rail only has room for a name, an area and a status dot, so a rail landing
page shows the channels of exactly one wheel no matter how many are installed.
The grid shows every channel of every wheel at once — six for two wheels,
fifteen for five. `Product intent` requires the latter, so the rail cannot be
the landing layer. Nesting it *inside* the detail keeps its one-click
switching without paying that cost.

Prototype measurements at a 1280 px viewport, two wheels:

| Layer | Rail | Detail pane | Channels visible |
|---|---|---|---|
| Grid overview | none | full width | 3 per wheel, every wheel |
| Wheel detail | 256 px | 1024 px, two columns | 3, opened wheel only |

The rail is **256 px** because that is Home Assistant's own sidebar width, and
because it keeps the detail pane above its 700 px two-column threshold on a
1024 px laptop. A 300 px rail measurably collapsed the detail to one column
there. Do not widen it without re-measuring that breakpoint.

Below 620 px the rail is dropped and the panel becomes a plain grid-to-detail
drill-down.

### Implementation constraints for both layers

- selection and state use real Home Assistant components, theme variables,
  typography, spacing, dividers and standard Material Design Icons, subject to
  the contrast rule below;
- generated decorative artifacts such as blue vertical selection bars,
  coloured circular icon buttons, custom progress arcs, gradients or invented
  graphics are not implementation requirements and should be removed.

### Colour, contrast, and a conflict this document used to hide

The constraint above — use Home Assistant's theme variables — and the WCAG 2.2
AA contrast gate in `PANEL_ROADMAP.md` Phase 3 **cannot both be satisfied
literally.** Taken at face value they send an implementer to the Phase 3 exit
gate with a finished frontend that fails it.

Home Assistant's own default accent tokens, measured on Home Assistant's own
card backgrounds (`#ffffff` light, `#1c1c1c` dark). AA needs **4.5:1** for
normal text and **3:1** for icons and other non-text:

| HA token | Light card | Dark card |
|---|---|---|
| `--primary-color` `#03a9f4` | **2.63** — fails text *and* icons | 6.48 |
| `--success-color` `#43a047` | **3.30** — fails text | 5.16 |
| `--warning-color` `#ffa600` | **1.96** — fails everything | 8.69 |
| `--error-color` `#db4437` | **4.29** — fails text | **3.97** — fails text |
| `--secondary-text-color` | 4.81 | 6.13 |
| `--primary-text-color` | 16.1 | 13.03 |

Not one accent colour in the default **light** theme passes AA for text. The
dark theme is the safer of the two — the opposite of the usual assumption — and
still fails on `--error-color`.

**The rule that resolves it: accent carries state, never text.** Keep the
theme's colour on the tab underline, the status dot, the icon — surfaces where
3:1 is the bar, or where the element is decorative and the meaning is carried
elsewhere. Put the words themselves on `--primary-text-color`. A green tick
beside black text reads as success and passes; green text does not pass.

Two consequences that are easy to miss:

- `--secondary-text-color` clears AA by **0.31** on a light card. Any tinted
  surface underneath it — a selection highlight, a hover state, a banner —
  pushes it under. Secondary text may sit only on an untinted
  `--card-background-color`; on a selected or tinted row it must be promoted.
- Warnings have no usable token. `--warning-color` is 1.96:1 on a light card,
  which fails even the 3:1 icon bar, and Home Assistant ships no readable
  variant. The panel needs its own warning ink. **Where it derives from is an
  open Phase 0 decision** — a hard-coded hex will break under a custom theme,
  and `PANEL_ROADMAP.md` requires at least one non-default theme to pass.

This rule was not reasoned out; it was measured. The prototype went from 14
contrast failures to zero across both themes, four layouts, six widths and the
degraded state — 17,968 elements checked, tightest passing element at 4.61.
Any implementation that reintroduces accent-coloured text will fail the gate
again, so re-run a contrast pass rather than trusting review by eye.

### Reference images are superseded

`images/panel/04-selected-combined-direction.png` is **no longer a valid
implementation target**. It shows master-detail as the landing page, which
this document now rejects; its sidebar is labelled `Wheel Workspace` and
`WHEELY`, which is internal jargon and not a Czech word; and it places an
`Add control binding` action on a surface that is read-only until `0.5.9`.
Do not implement from it.

The images below are retained only as a record of the exploration that led
here. **None of them is an implementation target.** They use generic demo
names and contain no installation-specific identifiers.

- [Native overview](images/panel/01-native-overview.png) — superseded
- [Wheel workspace](images/panel/02-wheel-workspace.png) — superseded
- [Live-test device detail](images/panel/03-live-test-detail.png) — superseded;
  its information hierarchy is explicitly reversed below, see `Live test`
- [Selected combined direction](images/panel/04-selected-combined-direction.png)
  — superseded

The current visual target is a browser prototype held outside this repository.
It is not a build dependency and is not required to check out or run the
integration; `PROJECT_STATUS.md` records where it lives and what it proves.
The technical spike must still rebuild the layout from supported HA/Lit
primitives and validate it in a real Home Assistant page — the prototype is
evidence about layout, not about what Home Assistant will serve.

## Product intent

The panel is not merely a visual replacement for the integration overview. It
should answer three user questions exceptionally well:

1. What does each physical wheel currently control?
2. How do I configure or change that behavior?
3. Is the wheel connected and are its gestures being understood correctly?

It must not become a second Home Assistant. Home Assistant remains responsible
for users, authentication, devices, entities, areas, services, scenes and
automations.

### The panel owns its app header, and must draw a way out

A custom panel is handed the whole viewport. Home Assistant draws no app header
for it, and **a panel without one traps the user.** On a narrow screen the
sidebar is collapsed and its only door is the header's menu button; in the
companion app a panel that omits it can only be escaped with a system back
gesture.

Every layer of the panel — overview, wheel detail, every tab, every error and
loading state — must therefore render a header carrying a menu button that
fires Home Assistant's `hass-toggle-menu` event (bubbling and composed, as
`ha-menu-button` does). The wheel detail's back affordance goes to the grid; it
is not a substitute for the way out to Home Assistant.

This is easy to miss and expensive to miss: on a desktop the sidebar is already
on screen, so nothing looks wrong. The Phase 0 spike shipped without a header
and trapped the owner on the first try in the companion app. Verify this on a
real phone, not at a narrow desktop window.

**The header must also clear the notch.** Home Assistant's frontend sets
`viewport-fit=cover`, so the companion app's WebView runs under the status bar.
A header with a plain fixed height puts its menu button behind an iPhone's notch
or Dynamic Island — the door is drawn, and still unusable. Take
`env(safe-area-inset-top)` as padding *added to* the bar's height (a
`content-box` bar, or the inset eats the bar rather than clearing it), and
`env(safe-area-inset-left/right)` for landscape, where the notch takes a side.
`env()` resolves to `0px` where there are no insets, so this is free elsewhere.
The insets apply to every layer that touches an edge, not only the header.

The spike got this wrong twice in a row — first no header, then a header under
the notch — and both times a narrow desktop window looked perfect. Neither a
window resize nor any test in this repository can catch it. Only a physical
notched phone can.

## Relationship to the native integration page

The native integration page is generated by Home Assistant from config entries,
subentries and registry objects. The integration cannot control its card layout,
the `Hubs` grouping, search field or the wording used for devices that are not
assigned to a subentry.

The native page therefore remains the technical administration surface for:

- installing, reloading and removing the integration;
- Home Assistant device and entity registry access;
- native config-entry and subentry operations;
- standard diagnostics and System Health.

The custom panel should present physical wheels, channels, behavior and live
feedback without exposing Matter endpoints or config-entry terminology.

## Information architecture

```text
BILRESA panel
  Overview of physical wheels        <- grid of wheel cards, landing layer
    Wheel detail                     <- 256px wheel rail + opened wheel
      Channels and behavior
        Binding editor
      Live test
      Diagnostics
```

The wheel rail exists only at the `Wheel detail` level. It never replaces the
overview.

The panel should follow Home Assistant's visual language, themes, responsive
layout and accessibility conventions. It should feel like a focused native Home
Assistant page rather than an embedded third-party application.

## Main overview

The top-level summary should remain small and actionable:

- number of connected and unavailable wheels;
- Matter event-source connection state;
- one concise actionable warning when degraded;
- an `Add control binding` action for administrators.

Below it, show a responsive grid with one primary card for each physical
BILRESA wheel. Constrain the grid's maximum width rather than letting cards
stretch across an arbitrarily wide window: at 1280 px with two wheels the
prototype left a dangling empty third column, which reads as a failed load.
The production overview therefore uses a centered 1120 px maximum content
width and `auto-fit` columns with a 400 px comfortable minimum: two wheels fill
the desktop composition, while narrower panes collapse naturally without
keeping phantom tracks.
Each card should contain:

- user-assigned device name and area;
- connected, degraded or unavailable status;
- time of the last received activity;
- last active channel, clearly labelled as last observed rather than a live
  selector position;
- three channel rows with a human-readable behavior and target summary.

Example channel summary:

| Channel | Behavior | Target |
|---|---|---|
| 1 | Smooth dimming | Bedroom lights |
| 2 | Scene cycling | Evening / Reading / Movie |
| 3 | Not configured | Add binding |

The overview must not show config entries, subentries, Matter node IDs,
endpoint IDs or raw event names.

## Wheel detail

The detail is reached by opening a card from the overview. It is a two-part
layout: a 256 px wheel rail on the left, and the opened wheel on the right.

The rail lists every physical wheel with its name, area and status, marks the
open one, and switches to another wheel in one click. It deliberately does not
show channel summaries — there is no room, and that is the overview's job. A
back affordance returns to the grid.

On desktop the back affordance belongs at the top of the rail, above the wheel
switcher. Placing it between the rail and the wheel heading creates a false
third column and makes two navigation systems compete. Below 620 px the rail is
absent, so the same back action moves above the wheel heading inside the detail
pane.

Below 620 px the rail is dropped; the detail becomes a full-width page reached
by drill-down, and the back affordance is the only way back to the grid.

The opened wheel has three primary destinations: channels and behavior, live
test, and diagnostics. These may be tabs or another responsive Home
Assistant-native navigation pattern selected during visual prototyping.

The detail's own content collapses from two columns to one below a 700 px
*pane* width. Note that this threshold applies to the pane, not the window:
with the rail present the pane is roughly 256 px narrower than the viewport,
and a naive window-width breakpoint will keep two columns in a pane far too
narrow for them.

### Channels and behavior

Show a separate card for each of the three channels. A configured card should
summarize the behavior of:

- rotation left;
- rotation right;
- short press;
- double and triple press where configured;
- hold and release;
- selected Home Assistant targets.

Technical endpoint and cluster information belongs only in expanded diagnostics.

The production layout presents all three channels as compact, independently
scannable cards. Each channel has a numbered heading, a one-line
behavior/target summary and a short vertical gesture list. Avoid table-like
3 x 2 gesture matrices on desktop; they make the wheel feel like an
administration grid rather than a control surface. An unconfigured channel stays
compact instead of occupying the same visual weight as a fully configured one.
Editing expands inside that channel without moving the user to a separate
administration page.

### Guided binding editor

The editor should use progressive disclosure. The user first chooses a behavior
profile, then sees only fields relevant to that profile.

Initial profile concepts:

- **Smooth light**: rotation changes brightness and press toggles the target.
- **Scenes**: rotation cycles an ordered scene list and press activates the
  selected scene.
- **Media**: volume, play/pause and next/previous behavior.
- **Cover**: position adjustment and stop behavior.
- **Custom action**: advanced Home Assistant actions and targets.
- **Events only**: keep behavior in Home Assistant automations.

Relevant controls may include:

- target entity, device, area, group or scene list as supported by the profile;
- rotation sensitivity;
- inverted direction;
- smooth transition duration;
- short, double and triple press behavior;
- hold-to-ramp settings;
- an explicit disabled state for a channel.

The editor must validate targets before saving, warn about removed or
unavailable targets and present a review summary before a material change.

### Live test

Live test is a core feature, not hidden developer tooling. It should provide a
safe listen-only mode driven by physical BILRESA input and display:

- direction of rotation;
- received cumulative count and calculated delta;
- last active channel;
- single, double and triple press completion;
- hold start and release;
- the resulting action calculated by the integration;
- whether the configured target action was dispatched successfully.

**The visual hierarchy must lead with the result, not the gesture.** The
largest element on the view is the outcome — `brightness 42 -> 58%` — followed
by whether dispatch succeeded. The gesture that caused it is a small caption
underneath.

The reason is that the user already knows what they did: they are holding the
wheel and can feel the notches. Nobody opens live test out of curiosity; they
open it when something is not working, and the question they arrived with is
"did it reach the light". Rendering `rotate right +6 steps` as the hero and
the brightness change as fine print — as `03-live-test-detail.png` does —
answers the one question the user did not ask.

Example human-readable feedback, in priority order:

```text
brightness 42 -> 58%          <- hero
action dispatched             <- confirmation
Channel 1 · rotate right · +6 steps    <- caption
```

Entering live test must not itself control a Matter device or synthesize a
hardware gesture. Any future action-preview or target-test control must be
explicit, clearly labelled and protected against accidental actuation.

The production layout keeps the large outcome surface on the left and a compact
configured-channel/recent-activity column on the right. Panel-driven synthetic
tests are secondary, collapsed by default, and explicitly warn that they may
change real target entities.

### Diagnostics

The default diagnostic view should remain understandable:

- connected, degraded or disconnected;
- last received event time;
- event source: Home Assistant core Matter client or passive WebSocket fallback;
- one actionable recovery recommendation when required.

Expanded technical details may include:

- Home Assistant, Matter Server and supported WebSocket schema versions;
- active event source and fallback reason;
- node availability without exposing the node identifier;
- discovered endpoint roles and channels;
- bounded recent event metadata without private identifiers;
- hold watchdog state;
- a link to the standard redacted Home Assistant diagnostics download.

The default diagnostics view begins with one human-readable health statement.
Connection and recent activity remain visible; internal contract versions and
similar implementation details stay inside a collapsed `Technical details`
section. A full-width recovery card is shown only when there is an action to
take.

Recent raw activity should be bounded and kept in memory unless a separately
justified requirement proves persistence is necessary. Do not write every
rotation event to the Home Assistant recorder.

## Future product capabilities

The panel can later support:

- copying a channel configuration to another channel;
- copying settings between wheels;
- named behavior presets;
- warnings for missing, removed or unavailable targets;
- conflict and validation checks;
- temporary channel disablement;
- sanitized import and export without installation-specific identifiers;
- guided creation of ordinary Home Assistant automations;
- direct navigation to the relevant HA device, entities and automations;
- bounded quality observations such as last activity, typical batch size and
  incomplete gesture detection.

The panel must not implement a parallel scene engine, automation engine, user
system or long-term history database.

## Hardware and protocol constraints

The UI must describe only capabilities supported by evidence in
`DEVICE_REFERENCE.md`:

- BILRESA reports cumulative counts, not an absolute rotary angle;
- fast rotation is batched by firmware, observed at roughly 0.5-1 second
  intervals;
- the highest observed rotary gesture count is 18;
- a hold event contains no direction;
- the physical selector's current position is not known continuously, so the
  UI must say `last active channel`, not `current channel`;
- a missing long-release event is possible and the runtime watchdog remains
  authoritative.

The panel cannot remove the device-side batching floor or claim real-time
precision that the hardware does not provide.

## Technical architecture

The future panel should be a custom element registered inside Home Assistant.
It receives Home Assistant state and themes through the frontend `hass` object
and communicates only with the loaded Python integration.

```text
Matter Server
    |
Python IKEA BILRESA integration
    |-- Home Assistant devices and entities
    |-- binding configuration and gesture processing
    |-- redacted diagnostics and System Health
    `-- authenticated BILRESA WebSocket API
             |
        BILRESA panel
```

Architecture rules:

- The Python integration remains the single source of truth.
- The browser must not connect directly to Matter Server.
- All Matter access remains passive and read-only.
- Important configuration must never exist only in browser storage.
- Read operations use authenticated Home Assistant WebSocket subscriptions.
- Mutating WebSocket commands require explicit schemas, server-side validation
  and administrator authorization.
- Non-admin users may receive a read-only experience if product testing shows
  it is useful.
- Existing config flows remain a functional fallback and recovery path.
- Panel failure must not stop gesture processing or configured bindings.
- Frontend assets must be versioned to avoid stale browser caches after an
  integration upgrade.
- English and Czech UI strings must remain aligned.
- Desktop, tablet, narrow mobile layout, keyboard navigation, focus states,
  screen-reader labels, loading, empty, degraded and error states are required.

Home Assistant reference material:

- [Creating custom panels](https://developers.home-assistant.io/docs/frontend/custom-ui/creating-custom-panels/)
- [Frontend architecture](https://developers.home-assistant.io/docs/frontend/architecture/)
- [Extending the WebSocket API](https://developers.home-assistant.io/docs/frontend/extending/websocket-api)
- [Authentication permissions](https://developers.home-assistant.io/docs/auth_permissions/)

## Delivery sequence and provisional versions

The sequence deliberately starts read-only to avoid risking the existing
binding configuration.

### `0.5.8` - read-only panel

- overview cards for physical wheels;
- channel and current binding summaries;
- connection and event-source state;
- live hardware event visualization;
- read-only bounded diagnostics.

This phase validates frontend packaging, cache behavior, themes, responsive
layout and live subscriptions without creating a new write path.

### `0.5.9` - binding editor

- edit the existing binding model through the panel;
- administrator-only validated writes;
- target availability warnings;
- review and save states;
- native config flows retained as fallback.

### `0.5.10` - workflows and polish

- guided behavior profiles;
- copy channel and copy wheel actions;
- refined empty, loading, degraded and error states;
- accessibility and mobile polish.

### `0.5.11+` - carefully selected expansion

- additional proven target types;
- sanitized import/export;
- guided HA automation creation;
- extended bounded troubleshooting observations.

These version numbers are planning labels, not releases or promises. A larger
stored-config migration, subentry-model change or intentional compatibility
break requires a minor version such as `0.6.0` under `ROADMAP.md`.

## First implementation recommendation

The first implementation should be a read-only panel containing wheel cards,
channel summaries, connection status and live test. This provides visible value
without changing binding storage or behavior and proves the frontend delivery
architecture before any panel write access is introduced.

The direction-comparison step this section used to require has been done. Four
layouts — grid, grid with a chip switcher, grid to master-detail, and
master-detail as landing — were built as a browser prototype and compared on
measured layout rather than on prose or generated images. The result is the
two-layer model above.

The prototype has verified, by measurement in a real browser:

- one, two and five wheels;
- mixed configured, unconfigured and unavailable-target channels;
- disconnected event source and the degraded banner;
- desktop 1280, laptop 1024, tablet 900 and narrow 380/320 layouts, with no
  horizontal page scroll and no element escaping the frame at any width;
- the 256 px rail and the 700 px pane threshold quoted above;
- WCAG 2.2 AA contrast in the **default light and dark themes**, computed
  rather than eyeballed, across four layouts, six widths and the degraded
  state: zero failures in 17,968 elements checked.

The following remain **unverified** and are still owed before or during the
frontend packages. Do not record them as passed on the strength of the
prototype:

- **non-default themes** — contrast is clean only against the two default
  palettes; a user theme can move any token, and the roadmap requires at least
  one non-default theme to pass;
- **whether the dark theme looks right** — its contrast is computed, but no
  human has ever looked at it. Contrast is arithmetic, not design;
- Czech versus English text expansion;
- keyboard-only navigation, visible focus order and screen-reader labels;
- non-text contrast of *background-coloured* elements — status dots, the tab
  underline, borders and focus rings were outside the audit, which only walked
  text and icon foreground colours;
- reduced-motion behavior;
- every claim about what Home Assistant will actually register and serve.

Do not begin panel implementation merely from this prose specification. The
direction is now visually grounded, so the next step is the small technical
spike for panel registration, asset loading and a read-only WebSocket
subscription.
