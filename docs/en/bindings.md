# Control bindings

[README](../../README.md) · [All guides](../README.md) · **English** · [Čeština](../cs/bindings.md)

A control binding makes one wheel channel, or one button of a dual button, act on
an entity of your choice. The [panel](panel.md) and the native flow below write
the same bindings.

## GUI control bindings (turnkey control)

Prefer not to write automations? In the [panel](panel.md), or on the
**IKEA BILRESA** entry (Settings → Devices & Services) with **＋ Add → Control
binding**, pick:

- a starting profile (light, media, cover, climate, scenes, or custom), or copy
  an existing binding as a starting point,
- the **Wheel** and **Channel** to use,
- the **target entity** controlled by scrolling,
- **Brightness change per notch** (%), **Minimum brightness** (%, `0` lets a
  downward scroll switch the light off) and **Transition** (s),
- the **single-press action** (toggle / on / off / nothing) and an optional
  **button target entity** — so a press can act on a *different* entity than the
  dimmed light (e.g. dim a bulb, but toggle its Shelly wall switch). The target
  of a press, double press, triple press or hold may also be a **scene** or a
  **script** (see [Scenes and scripts](#scenes-and-scripts-as-targets) below),
  and each of these gestures has its own **action** on its target: toggle, turn
  on or turn off,
- the **button response**: instant initial press, fast short release, or exact
  single/double/triple recognition for multi-press bindings,
- an optional ordered list of **scenes** to cycle on single presses (this takes
  precedence over the normal single-press action),
- the **hold action**: toggle an entity, continuously ramp the scroll target,
  or do nothing. Hold-to-ramp starts upward and alternates direction after each
  completed hold because the BILRESA long-press event carries no direction.

For the lowest direct-control latency, select **Instant initial press**. Because
the initial event cannot yet know whether the gesture will become a double
press or hold, Instant is accepted only when those separate actions are
disabled. **Fast release** runs after the first short release and remains safe
for a normal hold; multi-press aware waits for the BILRESA completion event.
Existing bindings without this setting retain the completion-aware behavior
until explicitly changed. A disabled channel runs no binding in any of these
modes. Public event entities and triggers keep exact
single/double/triple classification in every mode.

The integration then dims that light in real time. Add as many bindings as you
like — one per wheel channel — so this scales to any number of wheels with no
YAML. A binding sends no command while its target is missing, unknown or
unavailable (a scene or a script that reports `unknown`, such as a scene never
activated, is still run); hold-to-ramp stops safely and the next action resynchronizes from
the recovered entity's real state. Rotate-up from an off light starts at the
configured minimum (or one usable step when the minimum is zero). External HA
changes rebase the next wheel action, while direction reversal during a
transition continues from the last requested value.

## Actions by kind of target

What a gesture can do depends on the target you pick: the action list in the
panel shows only what that kind of target can carry out. Toggle, turn on and turn
off exist for everything switchable (light, switch, fan, humidifier, remote,
climate, input boolean); the rest:

| Target | Actions |
|---|---|
| **media player** | play / pause, play, pause, stop, next track, previous track, volume up, volume down, mute / unmute, and toggle, turn on, turn off |
| **cover** | toggle, open, close, stop |
| **lock** | lock |
| **vacuum** | start, pause, stop, return to dock, locate |
| **fan** | speed up, slow down, and toggle, turn on, turn off |
| **button, input button** | press the button |
| **automation** | run the automation |
| **input select, select** | next, previous, first, last option |
| **input number** | increase, decrease (by the number's own step) |
| **valve** | close, stop |
| **siren** | turn off |
| script, scene | see below |

Mute / unmute asks the player for the opposite of what it reports when the
button is pressed; a player that does not say whether it is muted (for example
one that is off) is skipped. A target that is unavailable is skipped, and the
live activity says why.

**What is left out on purpose:** unlocking a lock, opening it, or toggling it;
turning a siren on; opening a valve; disarming an alarm. One stray press on a
remote that anyone can pick up must not open a door, sound a siren, let water
run or disarm an alarm; use a script or an automation, where you decide how. For
a garage door or a gate the panel warns beside *Open* and *Toggle* that it opens
when the button is pressed, with nobody watching.

A device that does not support a verb (a player without *next track*, say) makes
Home Assistant write an error to its log; the live activity still says the action
was accepted, because the call is sent without waiting for the device. A binding
saved before these actions existed keeps working as it was.

## Scenes and scripts as targets

Every press gesture (single, double, triple press and hold) takes one action on
one target. The action means different things for different targets:

| Target | Toggle | Turn on | Turn off |
|---|---|---|---|
| light, switch | toggles | turns on | turns off |
| **script** | runs it, or stops it if it runs | **runs it** | **stops it** |
| **scene** | runs it | runs it | not possible (refused when saving) |

The panel names the choices after the target (for a script: *Run script*, *Stop
script*, *Toggle script*) and pre-selects *Run* when you pick a script or a
scene. A binding saved before this choice existed has no action stored and keeps
toggling, as it always did.

**Run script** starts the script and tells it which gesture started it, in the
variables `gesture` (`short_press`, `double_press`, `triple_press` or `hold`),
`presses`, `channel`, `endpoint` and `device`, so one script can serve several
buttons. Toggle and Stop cannot pass variables. A script that is already
running follows its own [mode](https://www.home-assistant.io/docs/script/#script-modes)
(by default a second start is ignored with a warning).

```yaml
script:
  bilresa_lights:
    mode: restart
    sequence:
      - action: light.toggle
        target:
          entity_id: >-
            {{ 'light.example_b' if gesture == 'double_press' else 'light.example_a' }}
```

Replace `light.example_a` and `light.example_b` with your own lights. Select the
script as the target of a short press and of a double press with the action *Run
script*; it then toggles the first light for one and the second for the other. A scene that was never activated reports the state
`unknown` and is run all the same.

For a dual button, the same flow first selects Button 1 or Button 2 and then
shows only supported actions: independent single/double-press targets and
hold/release. There are no rotary, scene or triple-press fields. A hold ramp can
alternate direction or stay fixed to brighten/dim, so two buttons can form a
software DIRIGERA-style pair for one light.

Acceleration, when enabled, is based on decoded notches per elapsed time rather
than the size of one Matter batch. It resets after idle, direction changes,
gesture completion and reconnect; the default remains disabled until physical
tuning is complete. Post-press protection likewise follows gesture boundaries,
so an old trailing batch cannot undo a button action but a deliberate new
rotation is accepted immediately.
