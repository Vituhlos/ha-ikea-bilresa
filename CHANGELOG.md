# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Runtime **hot add / remove of wheels** — a newly commissioned BILRESA appears
  (and a removed one disappears) without restarting Home Assistant.
- **Matter Server connection** binary sensor; wheel entities become unavailable
  while the connection is down.
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

### Changed
- Editing a light binding now updates in place instead of reloading the config
  entry — no reconnect.

### Fixed
- A button press now briefly suppresses trailing scroll events, so pressing to
  turn a light off while dimming isn't immediately undone by the wheel's
  trailing rotation batch.

### Planned
- Submission to the HACS default store and a brand icon.

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

[Unreleased]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.5.0
[0.4.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.4.0
[0.3.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.3.0
[0.2.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.2.0
[0.1.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.1.0
