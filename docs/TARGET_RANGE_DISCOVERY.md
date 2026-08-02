# Discovering a target's usable range

Status: **proposal, nothing implemented.** Written 2026-08-02 after a hardware
run made the problem concrete. No version is promised; see `Scope` at the end.

## The problem, measured

A binding's `min_brightness` and `max_brightness` are percentages of the Home
Assistant range, and Home Assistant's range is 1-255 for every light. Real
devices are narrower, and they do not say so.

Two devices in this installation, both measured rather than assumed:

| Target | Configured minimum | Actual floor | Dead travel |
|---|---|---|---|
| `light.zarovka_lustr` (Matter bulb) | 1 % (3 units) | **26** units | bottom ~10 % |
| `light.linka` (Shelly Plus 0-10V) | 1 % | `range_map [10, 100]` | bottom ~10 % |

The bulb's floor was established on 2026-08-02 by two probes that bypass this
integration completely:

```text
light.turn_on brightness=18  -> entity reports 26
light.turn_on brightness=40  -> entity reports 41
```

So it tracks above the floor and clamps below it. The Shelly's figure comes
from its own RPC, recorded in `PROJECT_STATUS.md`.

The user-visible symptom is not an error. It is that the last stretch of the
scroll does nothing: the wheel keeps turning, the integration keeps calculating
correctly, and the light does not move. The same wheel feels different on two
channels for reasons nothing in the UI explains.

## What Home Assistant and Matter already give us

**Nothing usable, and this was checked rather than assumed.**

- The `light` entity model has no minimum-brightness attribute. `light/const.py`
  and `light/__init__.py` carry `ATTR_MIN_COLOR_TEMP_KELVIN` and nothing
  equivalent for brightness.
- Matter's `LevelControl` cluster does define `MinLevel` and `MaxLevel`, and
  Home Assistant's Matter integration reads them — but only under
  `device_type=(device_types.Speaker,)`, as a speaker setpoint's range. No light
  platform surfaces them. The bulb measured above exposes no such entity.
- Even where `MinLevel` is readable, it is a declaration. A manufacturer may
  report 1 while the firmware stops at 26. It is a hint, never evidence.

So the range has to be **learned from behaviour**, not read from a field.

## The hazard that shapes the whole design

**A clamped command and an undelivered command are indistinguishable from
here.** Both look like: we sent a value, the entity did not reach it.

This is not hypothetical. `PROJECT_STATUS.md` records seventeen seconds of
silence from `light.linka` during which fourteen dispatched commands never
landed, and a later session where the entity went `unavailable` twice while
nothing was being sent. A learner that read those as a floor would raise the
minimum permanently, silently, and wrongly — narrowing the usable range in
response to a network fault.

Any design here is therefore judged first on how it tells those two apart.

The distinguishing evidence is **a confirmed report at the same value from
several different commanded values**:

- silence is not a floor. A commanded value with no state report afterwards is
  no evidence of anything and must be discarded;
- one report is not a floor either. A single settle at 26 could be a coincidence
  of timing;
- *distinct* commanded values — 18, 12, 3 — all reported back as exactly 26,
  each with its own report, is a floor. Nothing else produces that pattern.

## Three approaches

### A. Passive learning from data the binding already holds

`LightBinding` already knows every value it dispatched and every state report
that followed; `RotationTrace` already records both, and the capture read on
2026-08-02 contains this exact evidence. Detection needs no new traffic, no
new Matter access and no interaction with the user's lights.

Cost: the inference above has to be right. Benefit: it costs nothing and it
observes the device under real use rather than under a synthetic sweep.

### B. Explicit calibration from the panel

An action that steps the target down and watches where it stops. Definitive and
easy to reason about, but it drives the user's lights on demand, so it must be
explicit, clearly labelled, and never automatic — the same rule
`PANEL_DESIGN.md` already sets for the Live test's synthetic gestures.

### C. Read `LevelControl.MinLevel` from the target's Matter node

Authoritative when it is truthful, but it only applies to Matter targets, it
requires reading a node this integration does not otherwise touch, and the
declaration may not match the firmware. At best a prior that still needs
confirming by A or B.

## Recommendation

**Detect with A. Confirm with B. Never write the minimum automatically.**

The panel states the observation and offers the change:

```text
Žárovka Lustr nepřijala nic pod 26 (10 %).
Spodní desetina otáčení je bez účinku.        [ Nastavit minimum na 11 % ]
```

Automatic application is rejected for the reason the hazard section gives: the
inference can be wrong, and a silent narrowing of a configured range in
response to a network fault is exactly the class of failure this project has
already spent three release candidates chasing. A suggestion that turns out to
be wrong costs the user one glance. An automatic write that is wrong costs them
a working dimmer and gives them nothing to look at.

There is also a cheaper first step worth shipping on its own: **report the
observation without offering anything.** Naming the dead travel already
explains the symptom, and it needs no config write at all.

## What an implementation must not do

- Must not treat an absent state report as evidence. Silence means unknown.
- Must not conclude anything from a single commanded value.
- Must not write `min_brightness` or `max_brightness` without an explicit
  action from the user.
- Must not probe a target on its own initiative, at setup, or on a schedule.
- Must not carry a learned floor across a target change — the value belongs to
  the entity, not to the binding.
- Must not let detection influence dispatch. The binding's behaviour is
  unchanged whether or not a floor is known; this is an observation layer.

## Open questions

- **Where does a learned floor live?** It is per-entity, not per-binding, and
  two channels may point at the same light. A binding-scoped store would learn
  the same fact twice and could disagree with itself.
- **Does it survive a restart?** Persisting it means storing a claim about a
  device that may have had its firmware changed since. Not persisting it means
  relearning on every restart, which is cheap for A and free for the user.
- **Ceilings too?** The Shelly's `range_map [10, 100]` is symmetric in
  principle. No maximum-side dead travel has been observed yet, so this
  proposal deliberately covers only the floor rather than inventing a symmetric
  design for an unmeasured case.
- **Non-brightness modes.** Cover position, fan speed, volume and number all
  have the same shape of problem and none has been measured. Nothing here
  should be generalized to them without evidence.

## Scope

Not `0.6.0`. That train is already carrying the channel dials, button switches
and per-wheel settings added on 2026-08-02, and its hardware checklist is
outstanding. This is `0.7` material at the earliest, and the observation-only
first step could ship ahead of the rest.
