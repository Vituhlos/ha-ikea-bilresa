# Getting started

[README](../../README.md) · [All guides](../README.md) · **English** · [Čeština](../cs/getting-started.md)

## Requirements

- Home Assistant **2026.8** or newer.
- The **Matter Server** add-on (or an external Matter Server), with your BILRESA
  wheel(s) already commissioned to Matter and working.
- The core **Matter** integration configured (used to auto-detect the server
  URL; the BILRESA can be paired to Home Assistant and/or Apple Home).
- A Thread network that the Matter integration can reach, because the BILRESA
  is a Matter-over-Thread device.

### Compatibility

The integration works with BILRESA devices that Home Assistant already sees
through its **Matter** integration. What matters is how the *remote* reaches
Home Assistant, which is separate from what it *controls*.

| How it is used | Status | Evidence |
|---|---|---|
| Wheel (E2490) and dual button (E2489) paired to a Matter Server and Home Assistant's core Matter integration | **Supported** | The integration subscribes to the core Matter client's event stream (`matter` is a dependency in `manifest.json`). Recorded hardware runs on firmware 1.9.15 used this path ([HARDWARE_TEST.md](../HARDWARE_TEST.md), [DEVICE_REFERENCE.md](../DEVICE_REFERENCE.md)); validation of some gestures is still open. |
| Read-only WebSocket to the Matter Server, the fallback when the core client API is unavailable | **Supported in code, not verified on hardware** | The checklist items for the fallback in [HARDWARE_TEST.md](../HARDWARE_TEST.md) are open. |
| Remote paired through **ZHA** | **Unsupported** | The integration has no ZHA code path; it reads Matter events only. |
| Remote paired through **Zigbee2MQTT** | **Unsupported** | There is no MQTT or Zigbee2MQTT code path. |
| Lights or other entities on **ZHA or Zigbee2MQTT** as the *targets* of a binding | **Supported by design, not verified for groups** | A target is any Home Assistant entity of a supported domain, whichever integration provides it. Fixes for Zigbee2MQTT light groups are in the test candidates; the reporter's confirmation is pending ([issue #9](https://github.com/Vituhlos/ha-ikea-bilresa/issues/9)). |
| The remote also paired to another Matter controller (for example Apple Home) | **Not verified** | A Matter device can be commissioned to several fabrics ([DEVICE_REFERENCE.md](../DEVICE_REFERENCE.md)); it has not been tested with this integration. |

"Supported" means shown by the code and recorded runs, not that every gesture
and configuration is validated.

## Installation



### HACS (recommended)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Vituhlos&repository=ha-ikea-bilresa&category=integration)

Or add it manually:

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/Vituhlos/ha-ikea-bilresa`, category **Integration**.
2. Install **IKEA BILRESA**.
3. **Restart Home Assistant.**

The integration is not in the default HACS store yet — the custom-repository
step above is required. Upgrading from 0.5.x has breaking changes; read the
[CHANGELOG.md](../../CHANGELOG.md) and take a backup first.

### Manual

Copy `custom_components/ikea_bilresa/` into your Home Assistant
`config/custom_components/` folder and restart.

## Setup

**Settings → Devices & Services → Add Integration → IKEA BILRESA.**
Confirm the pre-filled Matter Server URL (change it only if you run the Matter
Server elsewhere). The integration discovers all supported BILRESA devices
automatically. A wheel gets an event entity per channel; a dual button gets one
per physical button.

## Next steps

- Open **IKEA BILRESA** in the sidebar and pick a device: the
  [panel guide](panel.md) shows what you can see and edit there.
- Make a gesture do something: [control bindings](bindings.md), including how to
  run a scene or a script.
- Use the gestures in your own automations:
  [events, entities and automations](events-and-automations.md).
- Nothing happens: [troubleshooting](troubleshooting.md).
