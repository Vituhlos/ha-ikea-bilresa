# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- (planned) A smooth-dimming **blueprint** built on the clean scroll events.
- (planned) Per-binding acceleration and min/max brightness; button
  double/triple/hold actions in the GUI binding.

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

[Unreleased]: https://github.com/Vituhlos/ha-ikea-bilresa/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.3.0
[0.2.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.2.0
[0.1.0]: https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.1.0
