# IKEA BILRESA (smooth scroll) for Home Assistant

A Home Assistant custom integration that makes the **IKEA BILRESA scroll wheel**
(Matter over Thread) feel smooth again — the way it does on IKEA's own DIRIGERA
hub — by reacting to the wheel's **real-time `MultiPressOngoing` events** that the
built-in Matter integration currently drops.

> ⚠️ **Status: work in progress (v0.1, phase 1).** Right now the integration
> connects to your Matter Server, auto-discovers BILRESA wheels, and emits a
> Home Assistant event for every switch action (including the ongoing scroll
> events). `event` entities and a smooth-dimming blueprint are next. See the
> [Roadmap](#roadmap).

## Why this exists

The BILRESA presents itself over Matter as a **Generic Switch** with multi-press
events. Home Assistant's Matter integration only surfaces `MultiPressComplete`
— i.e. it waits until you *stop* scrolling and then delivers one batched
"N presses" event, capped at 8. The result is laggy, jumpy dimming, and fast
scrolls beyond 8 notches get lost.

The device **also** emits `MultiPressOngoing` events — one per notch, in real
time — which is exactly what makes the DIRIGERA hub feel continuous. This
integration opens its own read-only WebSocket connection to the Matter Server
and listens for those ongoing events, so you can react per-notch as it happens.

Related upstream work: [core#159035 (issue)](https://github.com/home-assistant/core/issues/159035)
· [core#159045 (PR)](https://github.com/home-assistant/core/pull/159045).

## How it works

- **Passive listener.** It connects to the Matter Server WebSocket
  (`ws://core-matter-server:5580/ws` by default, auto-detected from your Matter
  config entry) and only *listens*. It never sends commands to devices, so it
  cannot interfere with the core Matter integration that shares the same server.
- **No extra dependencies.** The WebSocket client is a small `aiohttp` wrapper —
  nothing to install, nothing to break on upgrades.
- **Generic & self-describing.** Wheels, channels and directions are discovered
  from the node's own Matter descriptors (Switches semantic-tag namespace
  `0x43`, Position namespace for the channel number), so it adapts to any
  BILRESA regardless of endpoint numbering, and to multiple wheels at once.

### What a BILRESA scroll wheel exposes (decoded from Matter)

Each wheel has **3 channels**; each channel is 3 Matter Switch endpoints
(cluster `0x003B`):

| Role | Capabilities |
|------|--------------|
| Scroll ↑ / ↓ (rotary) | MomentarySwitch + Release + **MultiPress**, `MultiPressMax = 18` |
| Button (press) | + **LongPress**, `MultiPressMax = 3` |

Switch cluster events used: `InitialPress` (0x01), `LongPress` (0x02),
`ShortRelease` (0x03), `LongRelease` (0x04), **`MultiPressOngoing` (0x05)**,
`MultiPressComplete` (0x06).

## Installation

### HACS (custom repository)

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/Vituhlos/ha-ikea-bilresa`, category **Integration**.
2. Install **IKEA BILRESA (smooth scroll)**.
3. Restart Home Assistant.
4. **Settings → Devices & Services → Add Integration →** *IKEA BILRESA* and
   confirm the pre-filled Matter Server URL.

### Manual

Copy `custom_components/ikea_bilresa/` into your HA `config/custom_components/`
folder, restart, then add the integration as above.

## Usage (v0.1)

Every wheel action fires an `ikea_bilresa_event` on the Home Assistant event
bus. Watch it under **Developer Tools → Events** (`ikea_bilresa_event`) while
you turn the wheel, or trigger automations on it:

```yaml
triggers:
  - trigger: event
    event_type: ikea_bilresa_event
    event_data:
      channel: 1
      role: scroll_up
conditions:
  - "{{ trigger.event.data.event_type in ['initial_press', 'multi_press_ongoing'] }}"
actions:
  - action: light.turn_on
    target:
      entity_id: light.svetylka_svetylka
    data:
      brightness_step_pct: 6
      transition: 0.4
```

Event payload fields: `node_id`, `wheel_name`, `endpoint_id`, `channel`,
`role` (`scroll_up` / `scroll_down` / `button`), `event_type`, `count`
(notches for multi-press events) and `raw` (the untouched Matter event data).

## Roadmap

- [x] **Phase 1** — Matter Server listener, wheel auto-discovery, real-time
      `ikea_bilresa_event` on the bus.
- [ ] **Phase 2** — `event` entities (with ongoing) attached to the existing
      device; a smooth-dimming blueprint (per-notch stepping + transition +
      velocity-based acceleration); config-flow polish; English/Czech
      translations.
- [ ] **Phase 3** — options for step size / acceleration; button single /
      double / triple / hold mapping; diagnostics.

## Limitations

- The wheel has a built-in ~500 ms anti-flood delay between notch bursts, so
  this gets *close* to the DIRIGERA feel but is not truly analog-continuous.
- Because the target lights round-trip through Home Assistant (rather than a
  direct Matter/Zigbee bind), there is a small, usually imperceptible LAN
  latency.

## License

[MIT](LICENSE)
