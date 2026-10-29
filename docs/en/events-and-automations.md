# Events, entities and automations

[README](../../README.md) · [All guides](../README.md) · **English** · [Čeština](../cs/events-and-automations.md)

This guide documents the current integration behavior. Features ahead of the
latest release are identified in [PROJECT_STATUS.md](../../PROJECT_STATUS.md).

## Event entities

Each wheel channel becomes an `event` entity, e.g.
`event.bilresa_scroll_wheel_channel_1`. Its state is the timestamp of the
last action; the `event_type` attribute (and `notches` / `presses`) tells you
what happened. Use it as the primary automation trigger. These entities use
Home Assistant's button event device class; the compatibility domain event also
includes registry `device_id` when available.

## Dial and button entities

Besides the event entities, every wheel channel has two more, independent of any
binding:

| Entity | What it is |
|---|---|
| `number` *Dial* | A slider from 1 to 100. Turning the wheel moves it by the *Dial change per notch* set in the panel (with optional acceleration); the value is kept across restarts. Use it to read the wheel in automations and dashboards, or set it yourself. |
| `switch` *Button* | An on/off toggle that every single press of the channel's button flips. It only remembers on or off; nothing is commanded on the device. Double press, triple press and hold do not touch it, so they stay free for other uses. |

## Event reference

| `event_type` | Meaning | Extra attribute |
|--------------|---------|-----------------|
| `rotate_up` | Scrolled up by *N* notches | `notches` |
| `rotate_down` | Scrolled down by *N* notches | `notches` |
| `press` | Single button press | `presses` = 1 |
| `double_press` | Double press | `presses` = 2 |
| `triple_press` | Triple press | `presses` = 3 |
| `hold` | Button long-pressed | — |
| `release` | Button released after a hold | — |

## Triggers

The integration provides one automation trigger per gesture. In the automation
editor, pick the wheel (or one of its `Channel` entities) as the target and
choose the trigger:

| Trigger | Fires when |
|---------|------------|
| `ikea_bilresa.rotated_up` | a channel is scrolled up |
| `ikea_bilresa.rotated_down` | a channel is scrolled down |
| `ikea_bilresa.pressed` | a button is pressed once |
| `ikea_bilresa.double_pressed` | a button is pressed twice |
| `ikea_bilresa.triple_pressed` | a wheel button is pressed 3 times |
| `ikea_bilresa.held` | a button is held down |
| `ikea_bilresa.released` | a button is released after being held down |

```yaml
triggers:
  - trigger: ikea_bilresa.rotated_up
    target:
      entity_id: event.bilresa_scroll_wheel_channel_1
actions:
  - action: light.turn_on
    target:
      entity_id: light.example
    data:
      brightness_step_pct: "{{ trigger.to_state.attributes.notches * 3 }}"
      transition: 1
mode: parallel
max: 20
```

A target that names the whole device covers every channel of that wheel. The
dual button has no rotation and no triple press, so those two triggers never
fire for it.

> **Upgrading from 0.5.x or an earlier 0.6.0 pre-release:** the former *device
> triggers* ("Channel 1 scrolled up" on the device page) were removed. Since
> Home Assistant 2026.8 a device belongs to a single integration, and a device
> trigger only works on a device its own integration owns. Automations that
> still use one are listed under **Settings → System → Repairs**; replace the
> trigger with the matching one above.

## Example automations

**Smooth dimming** — step brightness by the notch count, with a transition so
the light ramps between the wheel's ~1 s batches:

```yaml
alias: BILRESA – smooth dim up
triggers:
  - trigger: state
    entity_id: event.bilresa_scroll_wheel_channel_1
    attribute: event_type
    to: rotate_up
conditions:
  - "{{ trigger.to_state.attributes.event_type == 'rotate_up' }}"
actions:
  - action: light.turn_on
    target:
      entity_id: light.example
    data:
      brightness_step_pct: "{{ trigger.to_state.attributes.notches * 3 }}"
      transition: 1
mode: parallel
max: 20
```

Duplicate with `rotate_down` and a negative step for dimming down, and add a
`press` trigger calling `light.toggle` for the button.

## Blueprint: smooth dimming

For an automation-based setup, a blueprint dims one light with one channel:
scrolling changes the brightness by the notch count (with a transition that
bridges the wheel's batched updates) and a single press toggles the light. Its
inputs are the channel's event entity, the light, the brightness step per notch
and the transition.

[![Open your Home Assistant instance and show the blueprint import dialog with this blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FVituhlos%2Fha-ikea-bilresa%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fikea_bilresa%2Fsmooth_dimming.yaml)

The turnkey [control bindings](bindings.md#gui-control-bindings-turnkey-control) need no
automation at all; use the blueprint when you want one.

## The `ikea_bilresa_event` bus event

Every action is also fired on the event bus as `ikea_bilresa_event` — handy for a
single automation that handles several wheels. Payload fields: `node_id`,
`wheel_name`, `channel`, `endpoint_id`, `type` (`rotate` / `press` / `hold` /
`release` / `short_release`), `direction` (`up` / `down`), `notches`, `presses`.

```yaml
triggers:
  - trigger: event
    event_type: ikea_bilresa_event
    event_data:
      type: rotate
```

## Immediate short-release actions

For an automation that should react as soon as a short button press is released,
listen to `ikea_bilresa_event` with `type: short_release`, filtered by your wheel's
`node_id` and `channel`. Do not filter on `presses: 1`: the final click count is
not yet known at release time.

```yaml
triggers:
  - trigger: event
    event_type: ikea_bilresa_event
    event_data:
      node_id: 12  # Replace with your wheel's Matter node ID.
      channel: 1
      type: short_release
```

This bus-only event is emitted for each short release, including releases within
a double or triple click. Completed `press` events still follow with the final
count. Replace the automation's completed single-press trigger rather than
adding a second trigger for the same action, or it will run twice. A separate
double-click action can override the early action, but the interim effect will
be visible. Long holds do not emit this event. Existing event entities,
`ikea_bilresa.*` triggers and direct light bindings keep their completed-gesture
behavior; a direct binding that should react on release uses its own
**Button response → Fast release** setting instead. A disabled channel emits no
`short_release` either.

The E2489 dual button has no channel (`channel` is empty), so filter its two
buttons by `endpoint_id` instead. Pressing it more than twice in a row still
emits a `short_release` for each reported release, but no completed `press`
follows (the device ends the sequence with a zero count).

## Multiple wheels

Everything is keyed by Matter node and endpoint, so **any number of wheels** work
at once with no configuration — each is discovered and gets its own device,
entities and events. The `node_id` / `wheel_name` / `channel` fields let you tell
them apart in automations.
