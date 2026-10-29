# How it works, limits and roadmap

[README](../../README.md) · [All guides](../README.md) · **English** · [Čeština](../cs/how-it-works.md)

## Why this exists

The BILRESA presents itself over Matter as a **Generic Switch** with multi-press
events. Home Assistant's Matter integration only surfaces `MultiPressComplete` —
it waits until you *stop* scrolling and then delivers a single batched "N
presses" event, capped at 8. The result is laggy, jumpy dimming, and fast
scrolls beyond 8 notches are lost entirely.

The device **also** emits `MultiPressOngoing` events — a running counter, in real
time, while you turn the wheel — which is exactly what makes the DIRIGERA hub
feel continuous. This integration subscribes to Home Assistant's existing Matter
client event stream, so Home Assistant can react per gesture as it happens. On
an older or incompatible client API it falls back to its own read-only
WebSocket.

Related upstream work:
[core#159035 (issue)](https://github.com/home-assistant/core/issues/159035) ·
[core#159045 (PR)](https://github.com/home-assistant/core/pull/159045).

## How it works

```
BILRESA wheel / dual button ──Matter/Thread──▶ Matter Server ──▶ this integration
                                                                  ├▶ event, dial and button entities
                                                                  ├▶ ikea_bilresa_event and triggers
                                                                  └▶ control bindings ──▶ Home Assistant services
                                                                       (lights, scenes, scripts, …)
```

The integration normally reuses the core Matter integration's existing
`MatterClient` subscription. Its compatibility fallback connects to the Matter
Server WebSocket (`ws://core-matter-server:5580/ws` by default), issues a single
`start_listening`, and decodes `Switch` cluster events (cluster `0x003B`) for
every discovered BILRESA node.

Each wheel exposes **3 channels**, each of which is 3 Matter Switch endpoints:

| Role | Matter capabilities |
|------|---------------------|
| Scroll ↑ / ↓ (rotary) | MomentarySwitch + Release + MultiPress, `MultiPressMax = 18` |
| Button (press) | + LongPress, `MultiPressMax = 3` |

The E2489 dual button exposes two button-only endpoints with no channel labels.
Each becomes a separate Button 1/2 event entity and supports single press,
double press, hold and release (`MultiPressMax = 2`).

Control bindings run inside Home Assistant: a binding reads the recognised
gesture and calls Home Assistant services, such as `light.turn_on`,
`scene.turn_on` or `script.turn_on`, on the entity you chose. The integration
sends nothing over Matter.

## Limitations

- The wheel has a built-in ~500 ms–1 s anti-flood delay between notch batches, so
  this gets *close* to the DIRIGERA feel but is not truly analog-continuous. A
  matching `transition` on the light bridges the batches for a smooth ramp.
- Target lights round-trip through Home Assistant (rather than a direct
  Matter/Zigbee bind), adding small, usually imperceptible LAN latency.
- A gesture acts on one entity, or runs one scene or one script. For several
  things at once, point it at a script (or a scene) that does them; a script
  started with *Run script* also learns which gesture started it.
- The panel is for administrators; other users do not see it. The event
  entities, triggers and bindings do not depend on it.

## Roadmap

What each release contains is in the [CHANGELOG](../../CHANGELOG.md). This is where the
project is going; none of it is a promise or a date, and each item still needs
its checks in [docs/HARDWARE_TEST.md](../HARDWARE_TEST.md).

**Stable (v0.6.1).** Event entities, automation triggers, dial and button
entities, control bindings with several scroll modes, acceleration, scene
cycling and hold-to-ramp, the dual button, the BILRESA panel, reuse of Home
Assistant's Matter client with a read-only WebSocket fallback, English and
Czech.

**In pre-release, not hardware-validated** (up to `v0.7.0-rc.4`). The
redesigned panel and its binding editor, the `short_release` event, Zigbee2MQTT
light-group fixes, disabled channels that stay silent, and scenes and scripts as
gesture targets.

**Planned, roughly in this order.**

- An action of its own for every gesture, with scripts told which gesture
  started them: merged after `v0.7.0-rc.4`, not yet in a release.
- Hold with an action when it starts and another when it ends, for example to
  run a script that changes something while you hold and stop it on release.
- Full Home Assistant actions (any service, with data) for a gesture, instead of
  a single entity.
- A rotation mode that steps through a list of scenes.
- The remaining hardware validation, and then the brand icon in
  `home-assistant/brands` and the default HACS store.
