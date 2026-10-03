# Device registry plan: one device per wheel, compatible with HA 2027

Status: **proposal, not approved, nothing implemented** (2026-10-03).
Branch: `agent/dual-button-0.6`, on top of `v0.6.0-rc.13`.
`PROJECT_STATUS.md` remains the canonical handoff; this file is the design.

## Context

Home Assistant 2026.8 made every device owned by exactly one config entry.
`device_link.py` was written for the old model, where this integration added
its config entry to the core Matter device. Observed on the owner's Home
Assistant 2026.9.4 with `v0.6.0-rc.13`:

- every wheel and the dual button exist twice in the device registry (three
  physical devices, six registry devices), each pair carrying the same
  identifiers, one owned by Matter and one by `ikea_bilresa`;
- the log reports four deprecated registry calls from `device_link.py`
  (lines 111, 197, 202, 236) that stop working in 2027.8 and 2027.9;
- `ikea_bilresa` device triggers are offered only on the duplicate, never on
  the Matter device.

Owner's decision: our entities live on the **Matter device**, the integration
creates no duplicate, uses no API that Home Assistant has scheduled for
removal, and automations keep named BILRESA triggers.

## Verified facts the plan relies on

| Fact | Source |
|---|---|
| An entity attaches to another integration's device by setting `entity.device_entry` and no `device_info` | `helpers/entity_platform.py` 2026.9.4; developer blog 2026-07-21 |
| `DeviceRegistry.async_get_device_by_identifier(identifier, config_entry_id)` and `async_get_devices()` exist from 2026.8.0 | core source at tag `2026.8.0` |
| Rewriting an entity's `device_id` to a device of another config entry works | rc.13 does it; the entities sit there on 2026.9.4 |
| A live entity reloads `device_entry` when its registry entry changes | `helpers/entity.py` 2026.9.4 |
| Removing a device removes entities of the same config entry and only detaches entities of other config entries | `helpers/entity_registry.py` 2026.9.4 |
| A device trigger whose domain owns no config entry on the device fails validation | `device_automation/helpers.py` 2026.9.4 |
| Entity-targeted triggers are offered for the Matter device: `event.received` lists our gesture types there | live query on the owner's instance |
| Integrations provide such triggers through `trigger.py` + `triggers.yaml`; the entity filter accepts `integration:` | `helpers/trigger.py`, `websocket_api/automation.py`; a custom integration's triggers are listed on the owner's instance |
| Entity-targeted triggers are not behind a Labs flag | live `labs/list`; frontend 20260826.7 |
| Child devices cannot be used: the parent must belong to the same config entry | `helpers/device_registry.py` 2026.9.4 |
| The test suite pins Home Assistant 2026.7.2, which predates the registry change | `requirements-test.txt` |

## Design decisions

1. **Minimum Home Assistant 2026.8.0** in `hacs.json`. No second code path for
   older cores; HACS keeps those users on rc.13 or 0.5.0.
2. **Legacy device triggers are removed** (`device_trigger.py`). They cannot
   work on a device this integration does not own, and behaviour that depends
   on where the entities happen to sit would be worse than none.
3. **Named BILRESA triggers replace them**, built on the entity-targeted
   trigger platform (see Step 3). The built-in `event.received` keeps working
   on the same entities as a second route.
4. **A wheel with no resolvable Matter device keeps a standalone device**
   owned by this integration, carrying only our identifier plus manufacturer,
   model and name. That path already uses no deprecated API.
5. **Our `(ikea_bilresa, node)` identifier is removed from the Matter device.**
   We wrote it there; after Step 3 nothing reads it.

### What "compatible with HA 2027" can and cannot mean

No Home Assistant API carries a guarantee for a future release. What this plan
does guarantee:

- zero use of anything Home Assistant currently marks for removal;
- only documented extension points, and for the named triggers the same base
  class the core `event` integration uses (`StatelessEntityTriggerBase`);
- a test that fails if Home Assistant logs any deprecation report against
  `ikea_bilresa`;
- a scheduled CI job against the newest Home Assistant pre-release, so a future
  breaking change is seen months before it reaches a stable release.

## Step 0 — prerequisites

- The four step-placement help-text files were committed separately as
  `050d488`.
- Read `PROJECT_STATUS.md`, `docs/ROADMAP.md` and `docs/HARDWARE_TEST.md` in
  full, as `AGENTS.md` requires.

## Step 1 — test environment (no behaviour change)

- `requirements-test.txt`: `homeassistant` 2026.9.x with the matching
  `pytest-homeassistant-custom-component` (0.13.355 = 2026.8.1,
  0.13.360 = 2026.9.0b3, 0.13.368 = 2026.10.0b0; pick the exact pair).
- `tests/conftest.py`: enable custom integrations. Today's tests are mock-only;
  this class of defect is visible only against the real registries.
- `hacs.json`: `"homeassistant": "2026.8.0"`.
- `.github/workflows/ci.yml`: add a weekly scheduled job that installs the
  newest Home Assistant pre-release and runs pytest. It reports; it does not
  gate pull requests.
- Own commit. The existing 382 tests must pass unchanged.

## Step 2 — device linking

### `custom_components/ikea_bilresa/device_link.py`

- `resolve_matter_device()`: replace `async_get_device` and
  `device.config_entries` with `async_get_device_by_identifier(identifier,
  matter_entry_id)` for each URL-matched Matter entry
  (`_matching_matter_entry_ids` stays). Rules unchanged: serial and operational
  identifiers must not disagree, otherwise the wheel stays standalone.
- `reconcile_wheel_device()`, rewritten and idempotent. The order is binding:
  1. collect this node's entities from the entity registry (platform
     `ikea_bilresa`, our config entry, `unique_id` starting with
     `"{node_id}_"`), disabled ones included;
  2. if a Matter device resolved, `async_update_entity(device_id=...)` for
     those sitting elsewhere;
  3. find devices **owned by our config entry** for this node
     (`async_get_devices(identifiers=..., config_entry_id=ours)`) and remove
     only those with no entity left; otherwise warn and leave them, because
     removing a device also removes our entities still on it;
  4. drop our identifier from the Matter device through `new_identifiers`.
- New `DeviceLinkManager` in the same module:
  - keeps `node_id -> device_id` (the Matter device, or our standalone one);
  - listens to `EVENT_DEVICE_REGISTRY_UPDATED` for devices of the matched
    Matter entries and re-runs `reconcile`, guarded against its own writes;
  - covers a freshly commissioned wheel that this integration sees before
    Matter has created its device.
- `wheel_availability()` is unchanged.

### Entities: `entity.py`, `event.py`

- Replace `_set_device_info()`: linked means `self.device_entry = link.device`
  and `_attr_device_info = None`; standalone means a `DeviceInfo` with only our
  identifier and the hardware metadata. Same change in `BilresaChannelEntity`,
  `BilresaChannelEvent` and `BilresaButtonEvent`; `number.py` and `switch.py`
  only pass the parameter through.
- `_sync()` in `event.py` and `async_setup_channel_platform()` in `entity.py`:
  reconcile first, then construct entities.
- `unique_id` and entity names do not change, so every `entity_id` is kept.

### `coordinator.py`, `__init__.py`

- `coordinator.py:366`: take `device_id` for `ikea_bilresa_event` from the
  manager's map instead of a registry lookup on every notch.
- `__init__.py:58` (migration 1.1 to 1.2):
  `async_get_device_by_identifier((DOMAIN, entry.entry_id), entry.entry_id)`.
- `async_setup_entry`: create the manager before
  `async_forward_entry_setups`; unsubscribe on unload.

### Unchanged callers

`config_flow.py:377`, `panel_models.py:753` and `diagnostics.py:50` only call
`resolve_matter_device()` and read `link.device`.

## Step 3 — triggers

### Remove

`device_trigger.py`, `tests/test_device_trigger.py`, and the
`device_automation` section of `strings.json`, `translations/en.json` and
`translations/cs.json`.

### Add named triggers

- New `custom_components/ikea_bilresa/trigger.py` and `triggers.yaml`.
- Seven triggers, one per gesture and with no extra fields, matching the old
  device trigger types: `rotated_up`, `rotated_down`, `pressed`,
  `double_pressed`, `triple_pressed`, `held`, `released`.
- Each is a small subclass of `StatelessEntityTriggerBase` with
  `_domain_specs = {"event": DomainSpec()}`; `is_valid_state()` compares the
  entity's `event_type` attribute with the trigger's gesture.
- `entity_filter()` is overridden to keep only entities whose registry
  platform is `ikea_bilresa`. Without it, targeting the whole Matter device
  would also watch Matter's own nine event entities.
- `triggers.yaml` target: `entity: [{integration: ikea_bilresa, domain:
  [event]}]`, so the triggers are offered for any device, area or entity
  selection that contains our event entities, wherever those entities sit.
- Names and descriptions in `strings.json` and both translations; icons in a
  new `icons.json`.
- Known limit: triggers are offered per target, not per entity capability, so
  `rotated_up` and `triple_pressed` are also listed for the dual button. They
  never fire there.

### Translate the gestures on the event entities

`event.py`: add `_attr_translation_key` (`channel`, `button`) while keeping
`_attr_name`, so names do not change. Add
`entity.event.<key>.state_attributes.event_type.state.*` for all seven gestures
in English and Czech, the pattern core Matter uses. The built-in
`event.received` then shows readable gesture names too.

### Tell users whose automations break

After Home Assistant has started, scan automation `raw_config` for device
triggers with `domain: ikea_bilresa` and raise one Repairs issue listing the
affected automations and the replacement trigger. The issue clears when none
remain. Lives beside the existing `ISSUE_CANNOT_CONNECT`; English and Czech.

## Step 4 — documentation and handoff

- `CHANGELOG.md`: a Breaking section (minimum Home Assistant, removed device
  triggers, `device_id` in the bus event now names the Matter device), Added
  (named triggers) and Fixed (duplicate devices).
- `README.md` and `README.cs.md`: the device trigger lines and an automation
  example using a named trigger.
- `docs/HARDWARE_TEST.md` (lines 96 and 185), `docs/V0.6.0_CHECKLIST.md`
  (item 8 is resolved by this work), `docs/DEVICE_REFERENCE.md`.
- `PROJECT_STATUS.md`: the handoff `AGENTS.md` requires.
- `blueprints/automation/ikea_bilresa/smooth_dimming.yaml` needs no change; it
  uses a state trigger on the event entity.

## Tests

Rewrite `tests/test_device_link.py`; add `tests/test_device_link_registry.py`
and `tests/test_trigger.py`, all against real registries:

1. linked: entities land on the Matter device and no own device is created;
2. migration from the rc.13 state (a duplicate holding the switches, events on
   the Matter device, our identifier on both): one device, every `entity_id`
   unchanged, the duplicate gone;
3. migration from the 0.5.0 state (standalone device);
4. a duplicate holding a foreign or unknown entity is not removed;
5. no Matter entry, a different URL, or conflicting identifiers: standalone;
6. the Matter device appears later: the listener moves the entities;
7. the Matter device disappears: entities survive without a device, no
   exception;
8. a second `reconcile` changes nothing;
9. `device_id` in the bus event;
10. each named trigger fires for its gesture and for no other;
11. a named trigger aimed at the whole Matter device ignores Matter's own
    event entities;
12. `get_triggers_for_target` on the Matter device returns the seven triggers;
13. the Repairs issue appears and clears;
14. English and Czech translations stay in step, new keys included;
15. **2027 guard:** during tests 1 to 12 Home Assistant logs no deprecation
    report against `ikea_bilresa`; plus a static test that the sources contain
    none of `async_get_device(`, `add_config_entry_id`, `merge_identifiers`,
    `primary_config_entry`, `via_device=`.

## Verification

- **Gate A and B** from `docs/DEVELOPMENT.md`. The local `.venv` (Python
  3.14.6) has neither `homeassistant` nor `pytest`; if they cannot be
  installed on Windows this is "Unit not run" and CI decides.
- **Gate C:** CI (hassfest, HACS, Ruff, mypy, pytest).
- **On Home Assistant**, only after the owner approves a deployment, and after
  a full backup, because removing the duplicate devices cannot be undone:
  1. the integration shows three devices, not six, and no linked device;
  2. every entity keeps its `entity_id` and sits on the Matter device;
  3. the system log holds no `helpers.frame` report about `ikea_bilresa`;
  4. the trigger query for each device returns the named triggers and
     `event.received`;
  5. the panel reports `linked_to_matter` and availability as before, and all
     bindings are preserved;
  6. **Hardware (owner):** rotation, press, double press and hold reach the
     binding, the event entity, a named trigger and the bus event. Record it
     in `docs/HARDWARE_TEST.md`.

## Risks and what this plan does not cover

- Automations built on the legacy device triggers stop working. The Repairs
  issue and the changelog reduce the surprise; they do not remove it.
- If the Matter integration is removed while this one keeps running, our
  entities have no device until this integration is reloaded.
- Writing `new_identifiers` on a device we do not own (only to remove our own
  entry) must pass the real-registry test; if it causes any problem the step
  is dropped, since nothing depends on it.
- The trigger platform is newer than the device registry API. The scheduled
  pre-release job is the early warning for it.
- Out of scope: the release itself (`manifest.json` version, an rc.14 tag),
  pull requests #5, #6 and #8, and issue #4.
