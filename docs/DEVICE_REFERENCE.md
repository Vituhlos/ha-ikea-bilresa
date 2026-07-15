# IKEA BILRESA scroll wheel — device & Home Assistant reference

Everything concrete we learned about the **IKEA BILRESA scroll wheel** as it
appears in this Home Assistant setup, pulled live from HA (device registry,
Matter node diagnostics, state machine, logs) and from upstream research. This
is the canonical reference so future work doesn't have to rediscover it.

> Captured 2026‑07‑14/15 from the owner's live system. Values like battery %,
> firmware and node availability are point‑in‑time; the structural facts
> (endpoints, clusters, event model) are stable for this hardware/firmware.

---

## 1. The physical devices

Two BILRESA wheels are commissioned (plus one spare, not paired). Both are
**Matter over Thread**, IKEA product **E2490**, `manufacturer = "IKEA of Sweden"`,
`model = "BILRESA scroll wheel"`, Matter **vendor id 4476 (0x117C)**.

| | Wheel "Nelča" | Wheel "Kitchen" |
|---|---|---|
| Matter **node_id** | **12** | **2** |
| HA device name | `BILRESA scroll wheel (Nelča)` | `Ovladač Linka/Lustr` (user‑named) |
| HA `device_id` | `bea15ec39b9a4d6bed084095a3885467` | `db19d5beb1839341242d10734dd540a9` |
| Area | `pokoj_nelca` | (kitchen) |
| Serial | `1035970000A0DDEC` | — |
| Firmware (sw) | `1.9.15` | `1.9.15` |
| Hardware (hw) | `P2.0` | `P2.0` |

Nelča device extra facts (from `ha_get_device`):
- Thread **sleepy end device**, network `MyHome1203563120`, IPv6
  `fdfe:a1f8:2d16:0:b6c6:256e:6c7a:dad9`.
- Battery **AAA**, ~**60 %** at capture time.
- Matter fabrics: **Apple Keychain** (Apple Home) + **Home Assistant** (label
  "Domov"). It is paired to *both* Apple Home and HA.
- Matter node identifiers used by the core Matter integration for the HA device:
  - `("matter", "serial_1035970000A0DDEC")`
  - `("matter", "deviceid_87B44E9F2FE3878A-000000000000000C-MatterNodeDevice")`
    (the `...000000000000000C...` segment is node id `0x0C = 12`.)

---

## 2. Matter node structure (node 12, from diagnostics)

The wheel exposes **3 channels** (a physical 3‑position selector picks the
active one). Each channel is **3 Matter endpoints**, all exposing the **Switch
cluster `0x003B` (59)** plus Identify (`0x0003`) and Descriptor (`0x001D`).

| Endpoint | Channel | Role | Switch FeatureMap | MultiPressMax |
|---|---|---|---|---|
| 1 | 1 | scroll **up** (rotary) | `22` = MS+MSR+MSM | **18** |
| 2 | 1 | scroll **down** (rotary) | `22` | 18 |
| 3 | 1 | **button** | `30` = MS+MSR+MSL+MSM | 3 |
| 4 | 2 | scroll up | 22 | 18 |
| 5 | 2 | scroll down | 22 | 18 |
| 6 | 2 | button | 30 | 3 |
| 7 | 3 | scroll up | 22 | 18 |
| 8 | 3 | scroll down | 22 | 18 |
| 9 | 3 | button | 30 | 3 |

**FeatureMap bits** (Switch cluster attr `0xFFFC` / 65532):
`bit0 LatchingSwitch, bit1 MomentarySwitch (MS), bit2 MomentarySwitchRelease
(MSR), bit3 MomentarySwitchLongPress (MSL), bit4 MomentarySwitchMultiPress
(MSM)`. So `22 = 0b10110 = MS|MSR|MSM`; `30 = 0b11110 = MS|MSR|MSL|MSM`.
Rotary endpoints have `NumberOfPositions = 2` and `MultiPressMax = 18`; button
endpoints add long‑press and have `MultiPressMax = 3`.

### How the role is decoded (works for any BILRESA, no hard‑coding)

Each endpoint's **Descriptor `TagList` (cluster `0x001D`, attribute `0x0004` /
`ep/29/4`)** carries semantic tags. The Matter Server delivers each tag as a
dict keyed by TLV field number:

```
{ "0": <MfgCode|null>, "1": <NamespaceID>, "2": <Tag>, "3": <Label?> }
```

- **Switches namespace `0x43` (67)** gives the role — tag `3 = Up`, `4 = Down`,
  `2 = Toggle`, `5 = Next`, `6 = Previous`, `8 = Custom` (label `"rotary"` or
  `"button"`).
- A tag with a **numeric label** (`"1"/"2"/"3"`) gives the **channel number**.

Observed raw taglists:
- EP1 (ch1 up): `[{"1":8,"2":6,"3":"1"}, {"1":67,"2":3}, {"1":67,"2":8,"3":"rotary"}]`
- EP2 (ch1 down): `[{"1":8,"2":6,"3":"1"}, {"1":67,"2":4}, {"1":67,"2":8,"3":"rotary"}]`
- EP3 (ch1 button): `[{"1":8,"2":6,"3":"1"}, {"1":67,"2":2}, {"1":67,"2":6}, {"1":67,"2":5}, {"1":67,"2":8,"3":"button"}]`
- (EP4–9 identical pattern with label `"2"`/`"3"`.)

Rule used: `Switches tag 3 → scroll_up`, `tag 4 → scroll_down`, otherwise
`button`; channel = the digit label.

### Root endpoint 0 (Basic Information, cluster `0x0028`/40)

`VendorName "IKEA of Sweden"`, `VendorID 4476`, `ProductName "BILRESA scroll
wheel"`, `ProductID 32768`, `0/40/11 "20250916"`, `0/40/12 "E2490"`,
`0/40/13 "www.ikea.com"`, `HardwareVersionString "P2.0"`, `SoftwareVersionString
"1.9.15"`, `SerialNumber "1035970000A0DDEC"`. Also PowerSource (`0x002F`/47,
AAA battery), Thread Network Diagnostics (`0x0035`/53), General Diagnostics,
OTA. `SerialNumber` is `0/40/15`.

---

## 3. Switch cluster events (`0x003B`) — the core of everything

| event_id | Name | Data fields |
|---|---|---|
| `0x00` | SwitchLatched | `NewPosition` |
| `0x01` | **InitialPress** | `NewPosition` |
| `0x02` | **LongPress** | `NewPosition` |
| `0x03` | **ShortRelease** | `PreviousPosition` |
| `0x04` | **LongRelease** | `PreviousPosition` |
| `0x05` | **MultiPressOngoing** | `NewPosition`, `CurrentNumberOfPressesCounted` |
| `0x06` | **MultiPressComplete** | `PreviousPosition`, `TotalNumberOfPressesCounted` |

**Data key names as delivered by the Matter Server (camelCase — confirmed live):**
`newPosition`, `previousPosition`, `currentNumberOfPressesCounted`,
`totalNumberOfPressesCounted`.

### Real observed event anatomy (from live debug logs)

One scroll "gesture" on a rotary endpoint produces, in order:

```
initial_press                                   # start (noise)
multi_press_ongoing  count = 6                  # CUMULATIVE within the gesture…
multi_press_ongoing  count = 12                 # …and it LEAPS (not +1)
multi_press_ongoing  count = 16
multi_press_ongoing  count = 18
short_release                                   # (interleaved / noise)
multi_press_complete count = 18                 # final total; resets the gesture
```

Key facts we verified on the hardware:
- **`count` is cumulative within a gesture** and jumps by several notches at a
  time. To move a target by the right amount you must use the **delta between
  consecutive events** (`Δ = new − last`), not treat each event as one notch.
- The device has a **built‑in ~0.5–1 s anti‑flood delay**: during fast
  scrolling `multi_press_ongoing` arrives roughly **once per second**, each time
  the count leaping by ~6–8. So it is *not* truly analogue‑continuous; a
  matching `transition` on the target bridges the batches into a smooth ramp.
- A **single notch** = `initial_press` + `short_release` + `multi_press_complete
  count=1` (no ongoing).
- **Button:** single = complete `count=1`; double = complete `count=2`; triple =
  complete `count=3`; **hold** = `initial_press` + `long_press` + `long_release`
  (no complete). `MultiPressMax` for the button is 3.
- Highest count seen live: **18** (the new ceiling; the old core code capped at 8).

Example real log lines (Nelča, node 12, channel 2, `custom_components.ikea_bilresa`):
```
ch2 scroll_up   -> multi_press_ongoing (count=8)  raw={'newPosition':1,'currentNumberOfPressesCounted':8}
ch2 scroll_up   -> multi_press_complete (count=18) raw={'previousPosition':1,'totalNumberOfPressesCounted':18}
ch2 button      -> long_press  raw={'newPosition':1}
ch2 button      -> long_release raw={'previousPosition':1}
ch2 button      -> multi_press_complete (count=2) raw={'previousPosition':1,'totalNumberOfPressesCounted':2}
```

---

## 4. How the built‑in Home Assistant Matter integration exposes it

For each of the 9 switch endpoints the core Matter integration creates an
`event` entity:

- Nelča: `event.pokoj_nelca_bilresa_scroll_wheel_nelca_tlacitko_1` … `_9`
- Kitchen: `event.bilresa_scroll_wheel_tlacitko_1` … `_9`

Their `event_types` are `["multi_press_1", … , "multi_press_8"]` and attributes
include `event_type`, `previousPosition`, `totalNumberOfPressesCounted`,
`device_class: button`.

**The limitation:** core HA only surfaces **`MultiPressComplete`** — it waits
until you *stop* scrolling, then fires one batched "N presses", **capped at 8**,
and it **drops `MultiPressOngoing` entirely**. That is why plain Matter dimming
feels laggy/jumpy and fast scrolls beyond 8 notches are lost. Upstream:
- Issue: <https://github.com/home-assistant/core/issues/159035>
- PR (draft): <https://github.com/home-assistant/core/pull/159045> — adds
  `multi_press_ongoing` and raises the ceiling to 18.

There are also `sensor.bilresa_scroll_wheel_aktualni_poloha_spinace_1..9_2`
sensors = the Switch cluster `CurrentPosition` attribute, plus Thread
diagnostics, battery (`sensor…nelca_baterie`), firmware `update` entity, an
Identify `button`, and `sensor…duvod_spusteni` (boot reason).

**This integration** (`ikea_bilresa`) bypasses the limitation by opening its own
read‑only connection to the Matter Server and listening for the ongoing events.

---

## 5. Environment (this HA install)

- **Home Assistant OS 18.1**, Supervisor `2026.06.2`, **core `2026.7.2`**,
  Python `3.14.6`, amd64 / KVM.
- **Matter Server add‑on `9.0.4`** (slug `core_matter_server`), hostname
  `core-matter-server`, WS port **5580**, path `/ws`
  → **`ws://core-matter-server:5580/ws`**. Server identifies as
  `matter-server/1.1.7 (matter.js/0.17.4)`, **schema_version 11**, fabric_id 2.
- Core Matter integration config entry id: `01KJJG07W7W18V5CFSYCWJ789H`.
- Other relevant add‑ons: `Home-Assistant-Matter-Hub 2.0.49`, `ESPHome Device
  Builder`, `Samba`, `File editor`, `Advanced SSH & Web Terminal`, `HACS 2.0.5`,
  `Home Assistant MCP Server 7.12.3`.
- Owner: HA email `vituhlos@gmail.com`, GitHub **@Vituhlos**. Integration repo:
  <https://github.com/Vituhlos/ha-ikea-bilresa>.

### python‑matter‑server WebSocket API (as used by this integration)

- On connect the server sends a **ServerInfo** message first.
- Client sends `{"message_id": id, "command": "start_listening", "args": {}}`;
  the server replies with `{"message_id": id, "result": [<all nodes>]}`, then
  streams events as `{"event": "<type>", "data": <payload>}`.
- **EventType** values: `node_added`, `node_updated`, `node_removed`,
  `node_event`, `attribute_updated`, `server_shutdown`, `server_info_updated`,
  `endpoint_added`, `endpoint_removed`.
- A **`node_event`** payload (`MatterNodeEvent`) has: `node_id`, `endpoint_id`,
  `cluster_id`, `event_id`, `event_number`, `priority`, `timestamp`,
  `timestamp_type`, `data`.
- Node objects carry `node_id` and an `attributes` dict keyed by
  `"<endpoint>/<cluster>/<attribute>"` (e.g. `"0/40/3"`, `"1/29/4"`).

---

## 6. Lights / entities the wheels were controlling (pre‑existing)

- **`light.svetylka_svetylka`** ("Svetylka Světýlka") — an **ESPHome** light,
  `supported_color_modes: ["brightness"]`, `supported_features: 40`
  (= `FLASH 8` + `TRANSITION 32`, i.e. it **does support transitions**).
  Controlled by the Nelča wheel.
- `light.linka`, `light.zarovka_lustr` / `light.lustr` — controlled by the
  kitchen wheel (the kitchen lustr is switched via a Shelly in the wall switch,
  brightness at the bulb).

### Pre‑existing automations (all were **disabled** during our testing)

| Automation entity_id | Alias / friendly | Wheel | Controls |
|---|---|---|---|
| `automation.ikea_bilresa_light_controller_v1_2_fixed_for_ha_2026_7` | "Světýlka Nelča – kolečko (jas, plynulé)" / "Jas svetylka Nelča" | Nelča (node 12) | `light.svetylka_svetylka` |
| `automation.bilresa_linka_jas_koleckem` | "BILRESA – Linka: jas kolečkem" | Kitchen (node 2) | `light.linka` |
| `automation.ikea_bilresa_light_controller` | "IKEA BILRESA - Light Controller" | Kitchen (node 2) | `light.linka` + `light.zarovka_lustr` |

The first two blueprint‑based ones use the blueprint
`Pech/ha-blueprint-ikea-bilresa-scrollwheel_fixed.yaml`
("IKEA BILRESA - Light Controller (v1.2 fixed for HA 2026.7)"), which reads the
9 core `event.*_tlacitko_*` entities and steps `brightness_step_pct`. To re‑enable
any of them: `automation.turn_on` on the entity_id.

---

## 7. Practical decode/notes for building on this

- Filter `node_event` where `cluster_id == 0x003B (59)`; map `endpoint_id` →
  (channel, role) via the taglist rule above; decode `event_id` via §3.
- For scroll, use the **delta** of `currentNumberOfPressesCounted`
  (`multi_press_ongoing`) / `totalNumberOfPressesCounted` (`multi_press_complete`)
  within a gesture; reset the running count on each `multi_press_complete` or
  when the count decreases (new gesture).
- Ignore `initial_press` / `short_release` for scrolling (they carry no delta).
- For a smooth ramp on a WiFi/ESPHome light, apply the step with a
  `transition ≈ 1 s` so the light interpolates between the ~1 s event batches.
- A truly analogue "DIRIGERA hub" feel is **not** achievable here: the device's
  own anti‑flood batching plus HA‑mediated control (the light is WiFi/ESPHome,
  not a direct Matter/Zigbee bind) put a floor on smoothness. Real‑time
  per‑batch reaction + transitions is the realistic ceiling.
