# IKEA BILRESA scroll wheel — device reference

This is the canonical, sanitized reference for facts observed in the owner's
Home Assistant environment on 2026-07-14/15 and rechecked on 2026-07-18. It
intentionally omits household
names, node IDs, device and config-entry IDs, serial numbers, network addresses,
entity IDs, automation names and account details. Do not add those values to a
committed fixture or diagnostic report.

These observations describe the device and protocol only. They do not mean the
current working tree or any post-v0.5.0 feature is hardware-verified.

## Hardware and environment baseline

- Two commissioned IKEA BILRESA scroll wheels, product E2490, Matter vendor ID
  4476 (`0x117C`), model `BILRESA scroll wheel`.
- Matter over Thread sleepy end device using one AAA battery; a device may be
  commissioned to multiple Matter fabrics.
- As of 2026-07-18, both commissioned wheels run firmware `1.9.15` on hardware
  `P2.0`. Earlier observations of one wheel on `1.8.7` remain historical
  compatibility evidence only.
- Home Assistant Core `2026.7.2` on HA OS `18.1`.
- Matter Server add-on `9.0.4`: matterjs-server `1.1.7`, matter.js `0.17.4`,
  WebSocket schema `11`, matter-python-client `0.7.1`.

Version and battery values are point-in-time facts. Repeat the compatibility
matrix in `HARDWARE_TEST.md` after a relevant upgrade.

## Matter node structure

The wheel exposes three selectable channels. Each channel uses three Matter
endpoints with the Switch cluster `0x003B` (59), Identify `0x0003` and
Descriptor `0x001D`:

| Endpoint | Channel | Role | FeatureMap | MultiPressMax |
|---|---:|---|---:|---:|
| 1 | 1 | scroll up | 22 | 18 |
| 2 | 1 | scroll down | 22 | 18 |
| 3 | 1 | button | 30 | 3 |
| 4 | 2 | scroll up | 22 | 18 |
| 5 | 2 | scroll down | 22 | 18 |
| 6 | 2 | button | 30 | 3 |
| 7 | 3 | scroll up | 22 | 18 |
| 8 | 3 | scroll down | 22 | 18 |
| 9 | 3 | button | 30 | 3 |

Switch FeatureMap bits are MomentarySwitch (bit 1),
MomentarySwitchRelease (bit 2), MomentarySwitchLongPress (bit 3) and
MomentarySwitchMultiPress (bit 4). Rotary endpoints expose `22` and button
endpoints expose `30`.

### Role and channel discovery

Descriptor `TagList` is attribute `ep/29/4`. Matter Server supplies each tag as
a mapping keyed by TLV field number:

```json
{"0": null, "1": 67, "2": 3, "3": "optional label"}
```

Switches namespace `0x43` (67) tag 3 means up, tag 4 means down and the
remaining button tags identify the button endpoint. A numeric label `1`, `2` or
`3` supplies the channel. This lets the integration discover roles without
hard-coded node IDs.

The Basic Information cluster `0x0028` reports IKEA as vendor, product E2490,
hardware and software versions. Firmware `1.9.15` exposes a serial number at
`0/40/15`, but the owner's `1.8.7` wheel omitted that optional attribute. Its
value must never be recorded in this repository. Device-registry linking must
therefore retain a serial-independent fallback.

## Switch cluster events

| Event ID | Name | Payload fields |
|---:|---|---|
| `0x00` | SwitchLatched | `newPosition` |
| `0x01` | InitialPress | `newPosition` |
| `0x02` | LongPress | `newPosition` |
| `0x03` | ShortRelease | `previousPosition` |
| `0x04` | LongRelease | `previousPosition` |
| `0x05` | MultiPressOngoing | `newPosition`, `currentNumberOfPressesCounted` |
| `0x06` | MultiPressComplete | `previousPosition`, `totalNumberOfPressesCounted` |

The camelCase field spelling above was observed from the live Matter Server.

### Observed gesture behavior

A fast rotary gesture typically produces:

```text
initial_press
multi_press_ongoing  count=6
multi_press_ongoing  count=12
multi_press_ongoing  count=16
multi_press_ongoing  count=18
short_release
multi_press_complete count=18
```

- Counts are cumulative within a gesture and may jump by several notches. Use
  the difference from the preceding count, crediting any first notch already
  emitted from the gesture's InitialPress.
- Firmware 1.9.15 batches fast rotation in the device. Ongoing events were
  observed roughly every 0.5–1 second, often advancing by 6–8 counts.
- One notch may contain only InitialPress, ShortRelease and
  MultiPressComplete with count 1.
- Matter's Switch contract generates InitialPress for every detected press and,
  when both events coincide, orders MultiPressOngoing directly after it. The
  owner's BILRESA raw stream follows that ordering but may report a cumulative
  jump larger than the number of InitialPress events seen since the previous
  report. Each received InitialPress is therefore an immediately safe lower
  bound; the cumulative count supplies the remaining notches.
  This ordering is specified in the public
  [Matter 1.2 Application Cluster Specification](https://csa-iot.org/wp-content/uploads/2023/10/Matter-1.2-Application-Cluster-Specification.pdf),
  Switch cluster multi-press sequence.
- Button single/double/triple presses complete with count 1/2/3.
- A hold is InitialPress, LongPress and LongRelease with no multi-press
  completion. The event carries no ramp direction.
- Waiting for MultiPressComplete adds the device's multi-press classification
  delay. An explicitly fast binding may react once on the first ShortRelease
  and suppress its later binding completion; a binding with double/triple
  targets must use the completion-aware response policy and wait for the final
  count. Public events remain completion-based in either mode.
- The highest observed rotary count was 18.

These are earlier device-reference observations. Re-test ordering and timing
against the current release candidate before marking a feature Hardware.

## Home Assistant and Matter Server behavior

The core Matter integration creates event entities for all nine endpoints but,
in the observed baseline, exposed MultiPressComplete rather than the ongoing
events needed for responsive scrolling. Entity IDs are installation-specific
and intentionally not recorded here.

The custom integration consumes a passive Matter event stream. It prefers the
loaded core Matter client's `subscribe_events` API when that config entry uses
the same server URL. Its fallback opens a separate read-only WebSocket and sends
only `start_listening`; neither source sends device-control commands.

The compatible WebSocket contract is:

1. Server sends `ServerInfo` including schema bounds.
2. Client sends `start_listening` with a message ID and empty arguments.
3. Command result supplies the initial node list.
4. Streamed messages contain `event` and `data`.

Relevant event names are `node_added`, `node_updated`, `node_removed`,
`node_event` and `server_shutdown`. A node event includes `node_id`,
`endpoint_id`, `cluster_id`, `event_id`, `event_number`, `priority`, `timestamp`,
`timestamp_type` and `data`. Node attributes use
`<endpoint>/<cluster>/<attribute>` paths.

## Practical implementation rules

- Filter node events to Switch cluster 59 and map endpoint to channel and role
  using Descriptor TagList.
- Emit every confirmed scroll notch from InitialPress, then subtract those
  eager credits from cumulative counts so no notch is applied twice.
- Convert ongoing and complete cumulative counts to remaining deltas and reset
  after completion or a decreased count.
- Reject non-integer, negative and above-`MultiPressMax` counts. A completion
  with a missing, invalid or Matter-overflow zero count still ends local
  accounting so stale credit cannot affect the next gesture.
- Ignore ShortRelease for scroll delta generation. CurrentPosition returning to
  zero is not the end of the cumulative rotary sequence and must not clear its
  count or eager credit.
- Preserve MultiPressComplete so a single notch and a final unsent delta are not
  lost.
- Use a target transition near the measured device batch interval to smooth
  visible changes; do not add latency-only software accumulation without the
  evidence required by `SCROLL_PERFORMANCE.md`.
- Treat a missing LongRelease as possible. Hold-to-ramp must stop on a watchdog,
  connection change, new gesture and unload.

See `MATTERJS_COMPATIBILITY.md` for remaining compatibility evidence and
`HARDWARE_TEST.md` for the release-candidate procedure.
