# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0-rc.5] - 2026-07-18

### Changed
- Scroll-wheel bindings now react to every confirmed Matter `InitialPress`
  immediately, then subtract those eager notches from later cumulative counts.
  This removes the firmware's batching wait without applying a step twice.
- Switch `CurrentPosition = 0` no longer clears an active rotary cumulative
  sequence; it remains a release/stuck-state hint for physical buttons.
- Missing, malformed, zero-overflow and above-`MultiPressMax` rotary completion
  counts now end local accounting safely instead of leaking stale state into the
  next gesture.
- Bounded rotation modes no longer repeat an identical Home Assistant service
  call after brightness, color temperature, volume, cover position, climate
  temperature, fan speed or number value reaches its effective limit. The live
  test records the gesture as completed with an unchanged value; cyclic hue
  rotation continues to wrap normally.
- Hold-to-ramp pauses its recurring interval at a target limit while retaining
  release-direction handling and the lost-release watchdog.

## [0.6.0-rc.4] - 2026-07-18

### Fixed
- A controlled Matter Server restart no longer makes the integration abandon
  Home Assistant's supported core Matter client during the temporary
  config-entry unload. Runtime monitoring now allows a one-minute restart
  grace period and reattaches to the replacement core client when it returns.
  Initial incompatibility still falls back immediately, while a persistent
  runtime incompatibility still falls back after the grace period.

## [0.6.0-rc.3] - 2026-07-18

### Changed
- Live test now treats an unconfigured physical gesture as a successful
  hardware-recognition state instead of showing the internal fallback
  "calculated result not reported". It explains that the control does not
  operate a target yet and offers a direct action to configure that exact
  channel or button.
- The live-test introduction and status text now distinguish gesture
  recognition from a configured target action. The side summary is titled
  simply "Channels" or "Buttons" because it includes configured and
  unconfigured controls.
- Recent live events use a bounded, keyboard-focusable scroll region, so an
  event burst no longer keeps extending the page.
- Matter Server add-on 9.1.0 / matterjs-server 1.2.6 is accepted through its
  supported schema-11 compatibility profile while System Health distinguishes
  the server's schema 12 from the client compatibility schema.
- `node_updated`, `attribute_updated` and `server_shutdown` now have explicit
  passive handling. Switch `CurrentPosition` is used only to clear stale
  gesture state, never to manufacture a click.
- Button response now has three truthful policies: Instant initial press, Fast
  release and Multi-press aware. Instant is accepted only for an unambiguous
  single action with hold disabled, and completion is suppressed from executing
  that direct binding twice while public gesture events remain unchanged.
- Hold/release actions carry `observed_duration_ms` when one uninterrupted
  monotonic press observation exists. Live test labels it as integration-
  observed duration; reconnect or a release safety hint clears it rather than
  inventing a value.

### Fixed
- A Matter 1.6 multi-press completion with count `0` (overflow past
  `MultiPressMax`) is no longer misread as a single press. Positive counts
  above the endpoint's advertised maximum are ignored as invalid as well.

## [0.6.0-rc.2] - 2026-07-18

### Fixed
- The real E2489's two physical buttons carry Matter semantic `up` / `down`
  tags even though neither endpoint has a numeric wheel channel. RC.1 treated
  those tags as rotary evidence, so the already discovered device still showed
  the wheel icon, an empty three-channel view and no button-binding controls.
- Variant discovery now uses the stable live endpoint shape: exactly two Switch
  endpoints without numeric channel labels identify the dual button. Their
  semantic roles are normalized to buttons before the gesture engine, event
  entities, device triggers, config flow and panel consume them.
- Downloadable diagnostics now expose the sanitized device variant and each
  endpoint's `MultiPressMax`, making future hardware-shape regressions visible
  without leaking household identifiers.

## [0.6.0-rc.1] - 2026-07-17

### Added
- BILRESA devices are now classified from their Matter endpoint shape as either
  a scroll wheel or an E2489 dual button, so a button-only device is no longer
  presented as an empty wheel.
- Each physical dual-button control gets its own event entity and device
  triggers for single press, double press, hold and release. Rotation and
  triple press are never advertised for `MultiPressMax = 2`.
- Dual-button bindings are stored and dispatched by Matter endpoint, so both
  buttons on each device — and any number of dual-button devices — can keep
  independent single-press, double-press and hold targets without colliding on
  their shared `channel = None` signal.
- Dual-button hold-to-ramp supports fixed brighten/dim roles for a
  two-button "software DIRIGERA" pair, or the existing alternating direction,
  with the same release, reconnect, new-gesture and watchdog safety stops.
- The native config flow now builds a hardware-specific form after the device
  is selected. Dual buttons never show rotary, scene or triple-press options;
  wheel profiles and their existing rotary options are unchanged.
- A bundled `bilresa:dual-button` two-path glyph now identifies dual-button
  event entities through both supported Home Assistant custom-icon contracts.
- The existing BILRESA panel now includes every dual-button device alongside
  the wheels. Its unchanged detail workbench adapts the numbered channel spine
  from `1 / 2 / 3` to independently configurable buttons `1 / 2`, while
  omitting only rotation, triple-press and detent controls the hardware does
  not have. The existing Live test reports which button was pressed and the
  resulting action outcome. Matter endpoint ids remain server-side.

## [0.5.9-rc.12] - 2026-07-17

### Changed
- The panel's wheel detail now navigates by the wheel's three physical selector
  positions: a spine of three channels, one open at a time, with the open
  channel's gestures shown as a hairline-separated ledger. Comparing every
  channel of every wheel stays the job of the overview grid, which is why the
  grid is the landing layer.
- The switcher rail was misaligned and grew a stray second row: it declared
  three grid columns but rendered four children, so wheel names were pushed to
  the right edge and the open wheel's tick wrapped onto its own line. The tick
  is removed; the open wheel is now marked the way Home Assistant's own sidebar
  marks its active entry -- an accent icon and heavier text alongside the tint,
  because the tint alone measures only 1.22:1 against the rail.
- Unconfigured channels are compact invitations naming what they wait for,
  instead of blank boxes stretched to a configured channel's height.
- The wheel detail is capped at the overview's width so a wide window no longer
  drags a label and its value to opposite ends of the screen.
- Diagnostics fact groups are sections with hairline rows rather than nested
  bordered cards, and the tab already naming a view no longer repeats itself as
  an inner heading.
- Live test leads with the calculated result at hero scale and shows a detent
  strip scaled to the highest rotary count the hardware has been observed to
  emit.
- Times that are read at a glance (last activity) are now relative -- "2 hours
  ago" -- with the exact timestamp kept on hover. Diagnostics keeps the absolute
  stamp.
- Buttons acknowledge a press, hover states are gated to real pointers so touch
  users do not get stuck states, and an unavailable-target banner now names the
  affected wheel and channel instead of reporting a count.

### Fixed
- The view tab strip no longer shows a scrollbar or clips its own focus ring:
  `overflow-x: auto` silently makes the other axis scroll too, and an underline
  and a focus ring that overhung the strip were caught by it.

### Notes
- This is a visual and interaction rework only. Matter event decoding, binding
  storage, the WebSocket API and gesture processing are unchanged.

## [0.5.9-rc.11] - 2026-07-16

### Changed
- The approved optical V2 BILRESA glyph is now the integration's shared visual
  identity: a bundled `bilresa:scroll-wheel` provider supplies the Home
  Assistant sidebar icon, and the panel uses the same primary and secondary
  paths for wheel cards and the switcher rail.
- Channel actions now use distinct Material Symbols Rounded gestures for both
  rotation directions and single, double and triple press. Hold and release are
  rendered as one long-press sequence instead of inventing a separate release
  logo.

### Notes
- The icon provider and gesture paths are bundled with the integration. They do
  not depend on the Material Symbols custom integration being installed.

## [0.5.9-rc.10] - 2026-07-16

### Changed
- The wheel glyph is now a bespoke icon of the BILRESA itself -- the upright
  rounded body, the scroll wheel and the three channel dots -- drawn from the
  device's real shape, instead of a generic dial. Gesture icons unchanged.

## [0.5.9-rc.9] - 2026-07-16

### Changed
- The panel's icons are now the Material Symbols (MD3) rounded set, bundled
  directly into the integration rather than depending on the Material Symbols
  HACS integration being installed. So the panel has the MD3 look for everyone,
  with no runtime dependency and no blank icons. The wheel is a filled dial.

## [0.5.9-rc.8] - 2026-07-16

### Fixed
- Panel icons render again. rc.6/rc.7 switched to ha-icon to use Material
  Symbols, but ha-icon does not reliably upgrade inside a custom panel's shadow
  root, so every icon went blank. Reverted to inline SVG, which always renders.
  The wheel glyph is now a rotary dial (record-circle-outline) instead of the
  volume-knob icon.

## [0.5.9-rc.7] - 2026-07-16

### Changed
- Panel icons now use Material Symbols (MD3) when that HACS integration is
  installed, and fall back to Material Design Icons otherwise, with no hard
  dependency. The wheel glyph is a concentric dial rather than the volume-knob
  icon. (rc.6 shipped the Material Symbols names with underscores; the set uses
  hyphens, so this corrects them.)

## [0.5.9-rc.6] - 2026-07-16 (superseded)

### Changed
- Panel icons now use Material Symbols (MD3) when that HACS integration is
  installed, and fall back to Material Design Icons otherwise. No hard
  dependency: users without Material Symbols still see MDI, so the panel stays
  portable. The wheel glyph is no longer the volume-knob icon.

## [0.5.9-rc.5] - 2026-07-16

### Changed
- The channel behaviour rows now carry a gesture icon (rotation, press, hold),
  continuing the visual pass toward the design mockup. Real Material Design
  Icons, keyed off the stable gesture type, in Home Assistant's entity-icon
  colour; no coloured text.

## [0.5.9-rc.4] - 2026-07-16

### Changed
- The panel's wheel cards and rail now carry the BILRESA wheel icon, the first
  step of a visual pass bringing the panel closer to the agreed design mockup.
  Icons are real Material Design Icons and carry Home Assistant's own entity-icon
  colour; no coloured text was introduced.

## [0.5.9-rc.3] - 2026-07-16

### Fixed
- The wheel detail no longer shows two "Back to all wheels" controls on desktop.
  The rail keeps the desktop back action; the in-pane back action is only shown
  when the rail collapses on mobile.

### Changed
- Channel detail is now a compact card grid instead of a table-like full-width
  gesture matrix. Each channel shows its behavior and target first, then a short
  scan-friendly gesture list, with edit/add actions in the card footer.

### Notes
- This is a frontend polish release based on real Home Assistant screenshots.
  Matter event decoding, binding storage, WebSocket contracts and dispatch
  behavior are unchanged from `0.5.9-rc.2`.

## [0.5.9-rc.2] - 2026-07-16

### Changed
- Refined the BILRESA panel visual hierarchy from the first real Home Assistant
  screenshots: the overview is centered and wider, the desktop back action lives
  inside the wheel rail, channel detail reads as one continuous surface, Live
  test makes the calculated result dominant, explicit target-changing tests are
  collapsed by default, and Diagnostics now hides internal contract data behind
  technical details.

### Notes
- This is a frontend and copy polish release. Matter event decoding, binding
  storage, WebSocket contracts and dispatch behavior are unchanged from
  `0.5.9-rc.1`.

## [0.5.9-rc.1] - 2026-07-16

### Added
- The panel now opens a full wheel detail with the measured 256 px
  wheel switcher, channel behavior cards, an opt-in Live test and a simple
  privacy-safe diagnostics view. The rail drops below 620 px and the detail
  columns respond to the pane's own width.
- Channel detail shows the stored behavior for rotation, short/double/triple
  press, hold and release, including their separate targets and unavailable
  target warnings. The panel contract is now version 3.
- Administrators can create, edit and delete binding subentries directly from
  the panel. The write API is limited to bindings, shares validation with the
  native config flow and requires an optimistic-concurrency revision for update
  and deletion.
- Live test correlates each gesture with the binding's structured calculated
  result and reports whether Home Assistant accepted, rejected or skipped the
  exact service action.
- Explicit panel test controls run rotation, single/double/triple press,
  hold and release through the real binding runtime without requiring physical
  access to a wheel.
- A dependency-free Node frontend test gate verifies that live activity is
  filtered to the opened wheel, bounded to eight entries and unsubscribed even
  when a subscription finishes after the user leaves the view.

### Notes
- `accepted` means Home Assistant validated and scheduled the service call. It
  does not claim that the physical target device changed.
- Matter decoding and device batching are unchanged. Binding dispatch remains
  non-blocking; the new reporting observes the existing call rather than waiting
  for a target-device round trip.
- Physical BILRESA verification is intentionally deferred. Panel-driven tests
  cover the binding and Home Assistant service path, not Matter radio delivery.

## [0.5.7-rc.11] - 2026-07-16

### Added
- **The panel speaks Czech.** It follows the language configured in Home
  Assistant's own settings.

### Fixed
- The panel no longer draws a second menu button beside Home Assistant's sidebar
  control on desktop. This shipped in rc.10 but could not take effect until a
  browser loaded the new panel module — the rc.10 fix that *was* visible
  (channels showing what they control) is served by Home Assistant, not the
  browser.

### Notes
- The panel's language is the instance's, from Settings → System → General, not
  each user's own. Home Assistant does not offer a custom panel a per-user
  language.
- No Matter event decoding, gesture timing, binding behaviour or stored
  configuration changed.

## [0.5.7-rc.10] - 2026-07-16

### Fixed
- **The panel's grid reported every configured channel as "Not configured".**
  Bindings store their wheel and channel as text, and the grid compared them as
  numbers, so it matched none of them. It also read the behaviour from a field
  that only exists while the binding is being created and is never saved.
  Channels now show what they actually do — "Smooth dimming", "Volume",
  "Cover position" — and the entity they control.
- The panel no longer draws its own menu button beside Home Assistant's sidebar
  control on desktop. It appears only when the sidebar is collapsed or hidden,
  matching Home Assistant's own behaviour, and now follows a window resize.

### Notes
- No Matter event decoding, gesture timing, binding behaviour or stored
  configuration changed. Bindings themselves always worked; only the panel's
  description of them was wrong.

## [0.5.7-rc.9] - 2026-07-16

### Added
- The panel's **overview grid**: one card per physical wheel with its name, area,
  status, last activity and all three channel summaries, over a new read-only
  WebSocket API. Built from Home Assistant's own design tokens.
- Read-only `ikea_bilresa/overview`, `.../overview/subscribe` and
  `.../activity/subscribe` WebSocket commands. Admin-only. No write path.

### Changed
- The Phase 0 spike's diagnostic table and its `.../spike/*` commands are gone.
  **An already-open panel tab from rc.8 will not work against this release**;
  reload the page. Those commands were never a contract.

### Fixed
- The panel header no longer sits under an iPhone's notch. Home Assistant's
  frontend runs the companion app's WebView under the status bar, and the header
  did not take the safe-area inset, so the menu button — the only way out of the
  panel — was covered.

### Notes
- The panel still cannot affect wheels, bindings or events, and this was now
  verified on a running Home Assistant rather than only asserted: with the panel
  asset removed, the integration sets up normally with a warning and no sidebar
  entry.
- No Matter event decoding, gesture timing, binding behaviour or stored
  configuration changed.

## [0.5.7-rc.8] - 2026-07-15

### Fixed
- Panel module registration is now idempotent when Home Assistant imports a
  cache-busted upgrade into a browser tab that still has the previous custom
  element registered. This prevents the sidebar panel from raising a duplicate
  `CustomElementRegistry` error after an integration upgrade or reload.

### Notes
- A full browser or companion-app page reload is still required to replace an
  already registered panel class with the new release's implementation; web
  platform custom elements cannot be redefined in place.
- No Matter event, gesture, binding or stored configuration behavior changed.

## [0.5.7-rc.7] - 2026-07-15

### Fixed
- The Phase 0 custom panel now owns a Home Assistant-style app header with a
  keyboard- and touch-accessible menu button, so companion-app users can reopen
  the sidebar and leave the panel.

### Notes
- The header uses Home Assistant theme tokens and a 48 px touch target with a
  dedicated keyboard focus indicator. No Matter, gesture, binding or stored
  configuration behavior changed.

## [0.5.7-rc.6] - 2026-07-15

### Added
- A **technical spike** for the future BILRESA panel, behind an admin-only
  sidebar entry. This is not the panel and not a feature: it renders a
  diagnostic table and exists to prove that the integration can serve, cache-bust
  and remove a frontend asset through HACS. It will be replaced wholesale.
- Two read-only WebSocket commands used only by that spike. They return three
  non-identifying scalars and have no write path.

### Notes
- The panel cannot affect wheels, bindings or events. If its asset is missing or
  registration fails, the integration sets up normally without a sidebar entry.
- No event decoding, gesture timing, binding behaviour or stored configuration
  changed in this release candidate.

## [0.5.7-rc.5] - 2026-07-15

### Added
- Per-wheel availability and core-Matter-link status in redacted diagnostics,
  derived read-only from the linked core Matter device.
- Privacy-safe DEBUG timing stages for fast single presses: `ShortRelease`,
  service dispatch, `MultiPressComplete`, and the first target-state change.
  Traces contain only a sequence number, channel, stage and elapsed time.

## [0.5.7-rc.4] - 2026-07-15

### Added
- Runtime **hot add / remove of wheels** — a newly commissioned BILRESA appears
  (and a removed one disappears) without restarting Home Assistant.
- Wheel entities become unavailable while the Matter Server connection is down.
- A **repair issue** is raised when the Matter Server stays unreachable.
- **Connection test** when setting up the integration (a bad URL is rejected).
- Binding **scroll modes**: a rotation can control **brightness**, **colour
  temperature** or **colour** (`step` becomes a percentage of the mode's range).
- **Universal control target**: a binding can also scroll a **media player's
  volume**, a **cover's position**, a **climate target temperature**, a **fan's
  speed** or a **number's value** — not just lights.
- Binding options **Maximum brightness** and **Acceleration** (faster scrolling
  takes bigger steps).
- Binding **double-press / triple-press / hold** actions — each optionally
  toggles its own entity.
- **Device triggers** — build automations from the wheel's device page
  ("Channel 1 scrolled up", "Channel 2 held", …) without writing YAML.
- A **smooth-dimming blueprint** (`blueprints/automation/ikea_bilresa/`) for
  automation-based setups.
- **Strict typing**: a `py.typed` marker plus a **mypy** type-check job in CI.
- Optional **scene cycling**: each single press activates the next configured
  scene for that channel.
- Optional **hold-to-ramp**: holding the wheel button repeatedly steps the
  configured scroll target until release; the direction alternates per hold.
- **System Health** information for Matter Server connectivity and version,
  discovered wheels and configured bindings.
- **Parent reconfiguration** for changing and validating the Matter Server URL
  without removing the integration.
- Reuse of Home Assistant's existing core **MatterClient event stream**, with a
  feature-detected fallback to the dedicated passive WebSocket on incompatible
  Home Assistant versions.
- Strict matterjs-server **schema-11 compatibility validation** and a sanitized
  protocol fixture for the add-on 9.0.4 / server 1.1.7 baseline.
- Binding creation **profiles** and the option to copy an existing binding as a
  starting point.
- Bounded, privacy-redacted runtime telemetry in diagnostics, including event,
  fallback and connection counters without node or entity identifiers.
- Expanded Linux CI test harness and authored tests for Matter sources, hold
  safety, binding presets, diagnostics, telemetry and System Health failures.

### Changed
- Each binding now has an explicit **button response** policy. New profiles
  recommend a fast single press on `ShortRelease`; existing bindings retain the
  completion-aware default until changed. Multi-press targets require exact
  recognition, while public event entities and device triggers always retain
  exact single/double/triple classification.
- Binding setup now rejects a scroll mode paired with an incompatible entity
  domain, while legacy incompatible bindings fail closed at runtime.
- Acceleration now uses decoded notches over monotonic elapsed time instead of
  treating a large Matter batch as proof of fast rotation. It resets on idle,
  direction changes, gesture boundaries and reconnects; the default remains
  disabled pending physical tuning.
- Channel event entities now use Home Assistant's button event device class.
  The legacy domain event keeps its existing payload and adds `device_id` when
  the wheel has a matching registry device.
- Editing a light binding now updates in place instead of reloading the config
  entry — no reconnect.
- The integration name and generated binding titles are shorter and clearer in
  Home Assistant's integration overview.
- The declared minimum Home Assistant version is now 2026.6, matching the
  config-subentry and current reconfigure APIs used by the integration.
- Core Matter-client reuse is restricted to a matching configured server URL;
  repeated runtime incompatibility switches one-way to the passive WebSocket.
- Fast-scroll handling remains direct and delta-based: evidence shows an extra
  software accumulator would add latency without defeating device-side batching.

### Fixed
- Bindings now fail closed while any scroll or button target is missing,
  `unknown` or `unavailable`. Hold-to-ramp stops, repeated events do not spam
  commands or logs, and recovery discards stale tracked values before resuming.
- Post-press protection now suppresses only scroll updates belonging to the
  preceding gesture. A deliberate new rotation is accepted immediately, with
  a bounded timeout retained only for lost gesture boundaries.
- Target state changes from Home Assistant now invalidate stale binding state
  after a bounded own-command echo window. Rotate-up from off starts
  predictably at the configured floor/first step, while direction reversal
  continues from the last requested target instead of a transition midpoint.
- Hold-to-ramp now stops on a lost-release watchdog, connection transition, new
  gesture and unload, preventing a target from changing indefinitely.
- BILRESA wheels that omit the optional Matter serial-number attribute now link
  to the correct core Matter device through its fabric-scoped operational node
  identifier. Existing standalone duplicates are reconciled conservatively,
  and changed node metadata is refreshed after firmware updates.

### Removed
- The redundant Matter Server connection service device and binary sensor. The
  same integration-wide state remains available through System Health, config
  entry status, Repairs and diagnostics without appearing as a fake device.

### Planned
- Validate the CI-green post-`v0.5.7-rc.3` runtime polish in the Home Assistant
  UI and through applicable physical-device gates before publishing the next
  candidate or stable release.
- Submission to the HACS default store and a brand icon remain the final phase.

## [0.5.0] - 2026-07-14

### Added
- Config-entry **diagnostics** download (with sensitive fields redacted).
- Developer tooling for a professional repo: GitHub Actions CI running
  **hassfest**, **HACS validation** and **ruff**, unit tests for the gesture
  engine and node parsing, and ruff/pytest configuration.

## [0.4.0] - 2026-07-14

### Added
- Binding option **Minimum brightness**: scrolling down eases to this floor and
  stays on; set it to `0` to let a downward scroll switch the light off.
- Binding option **Button target entity**: a single press can act on a different
  entity than the dimmed light (e.g. dim a bulb but toggle its Shelly wall
  switch). Uses the universal `homeassistant` service, so it works on switches,
  lights, input booleans, etc.

### Fixed
- Dimming now tracks an absolute brightness target instead of issuing percentage
  steps, fixing the abrupt "hold near the bottom then snap off" behaviour and a
  mid-transition read race during fast scrolls.

## [0.3.0] - 2026-07-14

### Added
- **GUI light bindings** via config subentries. Add a binding in the UI that
  maps a wheel channel to a light; the integration then dims it directly
  (per-notch delta × step, with a transition for a smooth ramp) and runs a
  configurable action (`toggle` / `on` / `off` / none) on a single button press.
  Works for any number of wheels and bindings.
- Czech and English translations for the binding flow.

### Changed
- The config entry now supports subentries; adding, editing or removing a
  binding reloads the entry.

## [0.2.0] - 2026-07-14

### Added
- **Gesture engine** that converts the wheel's cumulative, batched
  `multi_press_ongoing` counter into per-event **notch deltas**, so a light can
  be moved by the correct amount in real time during a scroll.
- **`event` entities** — one per wheel channel — emitting clean event types:
  `rotate_up`, `rotate_down` (with a `notches` attribute), `press`,
  `double_press`, `triple_press`, `hold`, `release`.
- **Per-wheel devices**, attached to the existing core-Matter device when a
  serial number is available.
- High-level `ikea_bilresa_event` bus event now carries decoded actions
  (`type`, `direction`, `notches`, `presses`) instead of raw Matter payloads.

### Changed
- Reworked internals into a `BilresaCoordinator` + `GestureEngine` + event
  platform, replacing the phase-1 log-only listener.

## [0.1.0] - 2026-07-14

### Added
- Initial release: a passive **Matter Server WebSocket listener** (no extra
  dependencies) that auto-discovers IKEA BILRESA scroll wheels from their Matter
  descriptors and fires a raw `ikea_bilresa_event` for every switch action —
  including the real-time `multi_press_ongoing` scroll events that the core
  Matter integration drops.
- Single-instance config flow with automatic Matter Server URL detection.
- English and Czech translations.

[Unreleased]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.6.0-rc.5...HEAD
[0.6.0-rc.5]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.6.0-rc.4...v0.6.0-rc.5
[0.6.0-rc.4]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.6.0-rc.3...v0.6.0-rc.4
[0.6.0-rc.3]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.6.0-rc.2...v0.6.0-rc.3
[0.6.0-rc.2]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.6.0-rc.1...v0.6.0-rc.2
[0.6.0-rc.1]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.5.9-rc.12...v0.6.0-rc.1
[0.5.7-rc.8]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.5.7-rc.7...v0.5.7-rc.8
[0.5.7-rc.7]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.5.7-rc.6...v0.5.7-rc.7
[0.5.7-rc.6]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.5.7-rc.5...v0.5.7-rc.6
[0.5.7-rc.5]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.5.7-rc.4...v0.5.7-rc.5
[0.5.7-rc.4]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.5.0...v0.5.7-rc.4
[0.5.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.5.0
[0.4.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.4.0
[0.3.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.3.0
[0.2.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.2.0
[0.1.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.1.0
