# IKEA BILRESA for Home Assistant

**English** · [Čeština](README.cs.md)

[![release](https://img.shields.io/github/v/release/Vituhlos/ha-ikea-bilresa)](https://github.com/Vituhlos/ha-ikea-bilresa/releases)
[![CI](https://github.com/Vituhlos/ha-ikea-bilresa/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Vituhlos/ha-ikea-bilresa/actions/workflows/ci.yml)
[![stars](https://img.shields.io/github/stars/Vituhlos/ha-ikea-bilresa)](https://github.com/Vituhlos/ha-ikea-bilresa/stargazers)
[![license](https://img.shields.io/github/license/Vituhlos/ha-ikea-bilresa)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/use/custom_repositories/)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.8.0%2B-41BDF5)

Responsive, GUI-configurable control for the **IKEA BILRESA scroll wheel and
dual button** (Matter over Thread) in Home Assistant.

The wheel reports real-time `MultiPressOngoing` events, so Home Assistant can
react while you turn it, not only after you stop. The remote still sends scroll
input in batches, so this is responsive stepped control rather than truly analog
scrolling.

> **Stable release:** the latest stable release is **v0.6.1**. The 0.6 line added the dual button, the BILRESA
> panel, more binding targets and an automation trigger for every gesture. It
> needs Home Assistant 2026.8 or newer and replaces the old device triggers:
> take a backup and read the upgrade notes in the [CHANGELOG](CHANGELOG.md)
> before upgrading from 0.5.x.
>
> **Test candidate:** the pre-release **v0.7.0-rc.5** has a redesigned panel and
> binding editor that the stable release does not have, an action for every
> gesture, the fix for the Matter freeze (GitHub #21), plus the fixes of
> `v0.6.2-rc.2` (Zigbee2MQTT light groups, the `short_release` event, disabled
> channels). It is not hardware-validated, and some device and gesture
> combinations still wait for validation; see the
> [hardware checklist](docs/HARDWARE_TEST.md).

If this integration saves you time, you can support its development. It is
entirely optional.

<a href="https://buymeacoffee.com/Vituhlos"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" height="40"></a>

## Highlights

| | |
|---|---|
| ⚡ **Real-time scrolling** | Reacts to `MultiPressOngoing` while you turn the wheel, not only after you stop. |
| 🖥️ **A panel in the sidebar** | Overview of your devices, an editor with one section per gesture, a live test and read-only diagnostics. English and Czech. |
| 🎚️ **Control bindings, no YAML** | Scrolling dims a light or moves a volume, cover, temperature or fan; a press, double press, triple press or hold toggles, turns on or off, or runs a **scene** or a **script**. |
| 🎛️ **Events and triggers** | Event entities, an automation trigger for every gesture, a bus event, and an immediate short-release for fast automations. |
| 📟 **Dial and button entities** | Every wheel channel also has a 1–100 dial and an on/off toggle for automations and dashboards. |
| 🧭 **Any number of devices** | Wheels (E2490) and dual buttons (E2489) are found automatically. |
| 🛡️ **Nothing written to Matter** | The integration listens to Matter events and never sends a Matter command to the remote or changes its pairing. |

## Quick start

1. **Check** that you have Home Assistant 2026.8 or newer, a Matter Server with
   your BILRESA already paired, and a Thread network the Matter integration can
   reach.
2. **Install** through HACS: add `https://github.com/Vituhlos/ha-ikea-bilresa` as
   a custom repository (category *Integration*), install **IKEA BILRESA** and
   restart Home Assistant.
   [![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Vituhlos&repository=ha-ikea-bilresa&category=integration)
3. **Add the integration** in **Settings → Devices & Services → Add Integration →
   IKEA BILRESA**, then open **IKEA BILRESA** in the sidebar, choose a device and
   press **Edit binding** on a channel (in the stable v0.6.1 a channel with no
   binding yet offers **Add a control binding** instead).

Details, and what to do when something does not work, are in the guides below.

## Works with

- ✅ A wheel (E2490) or dual button (E2489) paired to a Matter Server and to Home
  Assistant's core Matter integration.
- ❌ A remote paired through ZHA or Zigbee2MQTT. Lights and other entities on ZHA
  or Zigbee2MQTT can still be *targets* of a binding.

The full table, with the evidence for each case, is in
[Getting started](docs/en/getting-started.md#compatibility).

## Documentation

| Guide | It answers |
|---|---|
| [Getting started](docs/en/getting-started.md) | What do I need, which setups work, how do I install and set up? |
| [The BILRESA panel](docs/en/panel.md) | What does the panel show, and how do I edit a binding, the dial or a channel? |
| [Control bindings](docs/en/bindings.md) | How do I make a gesture do something, including running a scene or a script? |
| [Events, entities and automations](docs/en/events-and-automations.md) | Which events, entities and triggers exist, and how do I use them in automations? |
| [Troubleshooting](docs/en/troubleshooting.md) | Nothing happens, or a button is unreadable in my theme? |
| [How it works, limits and roadmap](docs/en/how-it-works.md) | Why does this exist, how does it work, what are its limits and what is planned? |

The [CHANGELOG](CHANGELOG.md) lists every release, and
[docs/HARDWARE_TEST.md](docs/HARDWARE_TEST.md) is the current hardware checklist.
All guides are also in Czech; see [all guides](docs/README.md).

## Community tools

These are made by other people. They are not part of this integration, which neither
depends on them nor sends them any data, and the integration does not maintain or
endorse them; check each project's own terms.

- **[Somrig Inlay Sheet Builder](https://bilresa.marcel1.com/)** — a web tool by a community member for
  designing inlay sheets (labels) for the switches. According to its author it can also
  produce 3D-printable cover models. The panel links to it from a device's page.

## Contributing

Issues and pull requests are welcome — [CONTRIBUTING.md](CONTRIBUTING.md)
explains how to report a bug or propose a feature (there are issue forms for
both), how to run the checks, and when hardware validation is required.
Security reports are covered by [SECURITY.md](SECURITY.md).

For developers and agents: the current implementation state, validation level
and prioritized backlog live in [PROJECT_STATUS.md](PROJECT_STATUS.md), the
canonical workflow is [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), and the
release trains are [docs/ROADMAP.md](docs/ROADMAP.md) and
[docs/ROADMAP_BUTTON.md](docs/ROADMAP_BUTTON.md).

## License

[MIT](LICENSE) © 2026 Vituhlos
