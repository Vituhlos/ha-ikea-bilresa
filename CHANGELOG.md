# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.5.7-rc.5...HEAD
[0.5.7-rc.5]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.5.7-rc.4...v0.5.7-rc.5
[0.5.7-rc.4]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.5.0...v0.5.7-rc.4
[0.5.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.5.0
[0.4.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.4.0
[0.3.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.3.0
[0.2.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.2.0
[0.1.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.1.0
