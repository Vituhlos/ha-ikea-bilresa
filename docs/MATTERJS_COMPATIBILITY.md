# Matter.js Server compatibility

## Verified contract baseline

The owner's current environment uses Home Assistant Core 2026.7.2, Matter
Server add-on 9.0.4, matterjs-server 1.1.7, matter.js 0.17.4, WebSocket schema
11, and matter-python-client 0.7.1. `DEVICE_REFERENCE.md` contains the canonical
BILRESA endpoint and event facts captured from that environment.

matterjs-server intentionally provides a Python Matter Server-compatible
WebSocket interface. The integration relies only on this passive subset:

- the initial `ServerInfo` message and its schema bounds;
- `start_listening` and its initial node list;
- `node_added`, `node_updated`, `node_removed`, `node_event`, and
  `server_shutdown` events;
- node attribute paths in `<endpoint>/<cluster>/<attribute>` form;
- `MatterNodeEvent` fields `node_id`, `endpoint_id`, `cluster_id`, `event_id`,
  `event_number`, `priority`, `timestamp`, `timestamp_type`, and `data`.

## Compatibility still requiring evidence

These items are mandatory gates, not completed validation:

1. Capture sanitized schema-11 fixtures from both the core-client subscription
   and dedicated-WebSocket paths.
2. Verify `MultiPressOngoing`, `MultiPressComplete`, long-press, and long-release
   ordering on physical BILRESA firmware 1.9.15.
3. Exercise both event sources against add-on 9.0.4 without duplicate delivery.
4. Verify fallback after initial incompatibility and after a core Matter reload.
5. Verify that a configured URL different from the core Matter entry never
   reuses the wrong client.
6. Validate reconnect, node add/remove, and server shutdown behavior.
7. Repeat the compatibility matrix after relevant HA Core, Matter add-on, or
   BILRESA firmware upgrades.

The integration now validates schema 11, restricts core-client reuse to the
same configured URL, and implements initial/runtime fallback. Those are
implemented safeguards, not evidence that items 1–7 have passed.

Passing static checks or fake-client tests does not satisfy these gates.
