# Discovery decision

Status: **exempt / no supported implementation** (reviewed 2026-07-15).

The integration discovers every IKEA BILRESA node dynamically after it is
configured. The open question was whether Home Assistant could automatically
offer the integration merely because the core Matter integration is configured.

Home Assistant config-flow discovery is initiated by supported discovery
sources declared in the manifest, such as Zeroconf, SSDP, DHCP, USB, HomeKit,
Bluetooth, or Supervisor add-on discovery. BILRESA does not independently
advertise this custom integration through any of those sources; it is already
commissioned inside the core Matter fabric. Home Assistant has no supported
manifest source meaning "another integration is configured".

Starting a config flow as a side effect of Home Assistant startup would imitate
discovery, create unwanted prompts, and couple this integration to internal
config-entry timing. It is therefore intentionally not implemented.

Revisit this decision only if Home Assistant introduces a supported dependency
or Matter-device discovery source. Relevant documentation:

- <https://developers.home-assistant.io/docs/core/integration/config_flow/#discovery-steps>
- <https://developers.home-assistant.io/docs/creating_integration_manifest/>

This decision does not affect runtime wheel discovery: after one manual setup,
all existing and newly commissioned BILRESA wheels are discovered automatically.
