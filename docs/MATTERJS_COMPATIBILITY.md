# Matter.js Server compatibility

## Runtime baseline and audited target

The owner's current environment uses Home Assistant Core 2026.7.2, Matter
Server add-on 9.0.4, matterjs-server 1.1.7, matter.js 0.17.4, WebSocket schema
11, and matter-python-client 0.7.1. `DEVICE_REFERENCE.md` contains the canonical
BILRESA endpoint and event facts captured from that environment.

Matter Server add-on 9.1.0 was statically audited on 2026-07-18 against its
official add-on changelog and the matterjs-server 1.2.6 tag. It uses WebSocket
server schema 12 but deliberately keeps schema 11 as the minimum supported
client schema. The matching official Python client also still advertises
schema 11. IKEA BILRESA therefore gains no device behavior from claiming client
schema 12; doing so unconditionally would only reject older schema-11 servers.

The integration consequently implements a **schema-11 compatibility profile**:
it accepts schema-11 servers and newer servers whose
`min_supported_schema_version` is at most 11. System Health reports the server
schema and client compatibility schema separately.

matterjs-server intentionally provides a Python Matter Server-compatible
WebSocket interface. The integration relies only on this passive subset:

- the initial `ServerInfo` message and its schema bounds;
- `start_listening` and its initial node list;
- `node_added`, `node_updated`, `node_removed`, `attribute_updated`,
  `node_event`, and `server_shutdown` events;
- node attribute paths in `<endpoint>/<cluster>/<attribute>` form;
- `MatterNodeEvent` fields `node_id`, `endpoint_id`, `cluster_id`, `event_id`,
  `event_number`, `priority`, `timestamp`, `timestamp_type`, and `data`.

## Matter Server 9.1.0 compatibility decisions

- `node_updated` is a full node snapshot and may be coalesced per node. It
  refreshes BILRESA metadata but is never interpreted as a physical gesture.
- `attribute_updated` uses
  `[node_id, "endpoint/cluster/attribute", value]`. Switch
  `CurrentPosition` (`*/59/0`) is consumed only as a release/stuck-state safety
  hint. Attribute updates may be coalesced under backpressure, so clicks,
  chords, sequences and press counts remain derived exclusively from ordered
  `node_event` messages.
- `node_event` messages use the ordered server queue. A severely stalled
  consumer can still be disconnected or lose old queued entries at the
  server's safety cap; the integration callback therefore remains synchronous,
  bounded and non-blocking.
- Matter 1.6 permits `MultiPressComplete.TotalNumberOfPressesCounted == 0` when
  `MultiPressMax` is exceeded. Zero and counts above the endpoint's advertised
  maximum are ignored; they are never converted to a single press.
- Schema-12 Thread diagnostics and WebRTC callbacks are request-scoped. This
  passive listener does not request those APIs. Unknown future event types are
  ignored safely.
- Time synchronization and experimental ICD battery-saving support are owned by
  Matter Server. The integration sends no device commands and requires no
  special code path for either feature.

These decisions have static and unit-test evidence. A real add-on 9.1.0
upgrade, reconnect and physical BILRESA gesture run are still required before
claiming Hardware compatibility.

## Controlled 9.1.0 restart finding

A controlled restart of the installed Matter Server add-on on 2026-07-18
exposed a lifecycle defect in `v0.6.0-rc.3`. Home Assistant temporarily
unloaded its core Matter config entry while the server restarted. RC.3 indexed
the resulting empty loaded-entry list and, after only two five-second monitor
checks, permanently selected the dedicated compatibility WebSocket for that
integration load. The BILRESA config entry was reloaded afterward and returned
to the supported core Matter client with all devices and bindings restored.

Released `v0.6.0-rc.4` treats an absent loaded Matter entry as a temporary
runtime outage. It keeps the core source preferred for twelve
five-second checks and reattaches when Home Assistant supplies the replacement
client. Initial setup with a genuinely unsupported client still falls back
immediately; persistent runtime incompatibility still falls back after the
one-minute grace period. Automated coverage reproduces the temporary empty
entry and verifies reattachment without fallback.

The exact released candidate was installed through HACS on 2026-07-18. A
controlled Matter Server 9.1.0 restart then produced one disconnect and one
reattach to the replacement core client, with two connection snapshots, zero
fallbacks, all three BILRESA devices and all six bindings restored. The source
remained `core_matter_client` after the full grace window and no matching
integration error was logged. The first physical E2489 single afterward
advanced both event surfaces once, dispatched one binding action, toggled only
its intended target once, and left the other button and observed targets
unchanged. This lifecycle path is therefore Hardware-verified on RC.4.

## Compatibility still requiring evidence

These items are mandatory gates, not completed validation:

1. Capture sanitized runtime fixtures from both the core-client subscription
   and dedicated-WebSocket paths on add-on 9.1.0.
2. Verify `MultiPressOngoing`, `MultiPressComplete`, long-press, and long-release
   ordering on physical BILRESA firmware 1.9.15.
3. Exercise both event sources against add-on 9.1.0 without duplicate delivery.
4. Verify fallback after initial incompatibility and verify core-client
   reattachment after a core Matter reload or Matter Server restart.
5. Verify that a configured URL different from the core Matter entry never
   reuses the wrong client.
6. Validate reconnect, node add/remove, and server shutdown behavior.
7. Repeat the compatibility matrix after relevant HA Core, Matter add-on, or
   BILRESA firmware upgrades.

The integration now validates schema bounds, accepts the schema-12/schema-11
minimum contract, restricts core-client reuse to the same configured URL,
handles node/attribute updates and server shutdown, and implements
initial/runtime fallback. Those are implemented safeguards, not evidence that
items 1–7 have passed.

Passing static checks or fake-client tests does not satisfy these gates.
