"""Privacy-reviewed read models for the panel.

`PANEL_ROADMAP.md` Phase 1: pure, deterministic serializers over state that
already exists — the coordinator, config subentries, and the device/entity/area
registries. Nothing here mutates anything, subscribes to anything, or touches
Matter. Import it, call it, get a dict.

Three rules from the roadmap that shaped every function below:

- **Never serialize coordinator internals.** `BilresaCoordinator`, `BilresaWheel`
  and raw subentry dicts must not reach the frontend. Everything crossing the
  wire is built by hand here.
- **Never expose the Matter node ID.** The panel addresses a wheel by an opaque
  key; see `wheel_key`.
- **`unknown` is not `healthy`.** Where evidence is missing, say so.

The frontend contract these feed is drafted outside this repository. Keep the
two in step, or the panel will render fields nobody produces.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .binding_config import binding_revision, editor_data
from .const import (
    CLICK_NONE,
    CLICK_OFF,
    CLICK_ON,
    CLICK_TOGGLE,
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_HOLD_ACTION,
    CONF_HOLD_TARGET,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_SCENES,
    CONF_TARGET,
    CONF_TRIPLE_TARGET,
    DEFAULT_CLICK_ACTION,
    DEFAULT_HOLD_ACTION,
    DOMAIN,
    HOLD_RAMP,
    HOLD_TOGGLE,
    MODE_BRIGHTNESS,
    MODE_COLOR,
    MODE_COLOR_TEMP,
    MODE_COVER,
    MODE_FAN,
    MODE_NUMBER,
    MODE_TEMPERATURE,
    MODE_VOLUME,
    SUBENTRY_BINDING,
)
from .device_link import WheelAvailability, resolve_matter_device, wheel_availability
from .model import BilresaWheel
from .panel_strings import localize

CONTRACT_VERSION = 3

# Deliberately short: this is an addressing token, not a secret. Long enough not
# to collide across a household, short enough to read in a bug report.
_KEY_LENGTH = 12


def wheel_key(node_id: int) -> str:
    """Return a stable, opaque key for one wheel.

    The Matter node ID must not cross the wire (`PANEL_ROADMAP.md`), but the key
    must survive reloads and restarts or the panel loses its selection every time
    the integration reconnects. A hash of the node ID is both: deterministic
    without being the thing itself.

    This is not a security boundary. It stops the node ID leaking into
    screenshots, exported diagnostics and bug reports — which is the actual
    failure mode this project has already had once.
    """
    digest = sha256(f"{DOMAIN}:{node_id}".encode()).hexdigest()
    return digest[:_KEY_LENGTH]


@dataclass(slots=True)
class GestureSummary:
    """One physical gesture and the configured action it maps to."""

    gesture: str
    gesture_label: str
    action_label: str
    target_label: str | None = None
    target_missing: bool = False


@dataclass(slots=True)
class BindingEditor:
    """Editable binding data with an optimistic-concurrency token."""

    id: str
    revision: str
    data: dict[str, Any]


@dataclass(slots=True)
class ChannelSummary:
    """One channel of one wheel, as a human reads it."""

    channel: int
    profile: str | None = None
    behaviour: str | None = None
    target_label: str | None = None
    target_missing: bool = False
    actions: list[GestureSummary] = field(default_factory=list)
    binding: BindingEditor | None = None


@dataclass(slots=True)
class WheelOverview:
    """One physical wheel. No node ID, no serial, no product name."""

    key: str
    name: str
    area: str | None
    availability: WheelAvailability
    linked_to_matter: bool
    last_activity: str | None
    last_active_channel: int | None
    channels: list[ChannelSummary] = field(default_factory=list)


@dataclass(slots=True)
class OverviewSnapshot:
    """What the grid renders. `matter_connected` is integration-wide."""

    wheels: list[WheelOverview]
    matter_connected: bool
    event_source: str
    contract_version: int = CONTRACT_VERSION


def _entity_label(hass: HomeAssistant, entity_id: str | None) -> str | None:
    """Resolve an entity to the name the user gave it.

    Falls back to the entity_id only when nothing better exists. That is a
    deliberate leak of an identifier the user chose and can see in their own UI;
    it is not household-sensitive the way a node ID or serial is.
    """
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is not None and (name := state.attributes.get("friendly_name")):
        return str(name)
    entry = er.async_get(hass).async_get(entity_id)
    if entry is not None and (label := entry.name or entry.original_name):
        return str(label)
    return entity_id


def _target_missing(hass: HomeAssistant, entity_id: str | None) -> bool:
    """Whether a configured target can no longer be acted on.

    Detection only. The binding's own fail-closed behaviour is untouched — this
    must never be the thing that decides whether a command is sent.
    """
    if not entity_id:
        return False
    state = hass.states.get(entity_id)
    return state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)


def _as_int(value: Any) -> int | None:
    """Coerce a stored selector value to int, or None if it is not one.

    **Stored bindings hold `node_id` and `channel` as strings**, not ints: they
    come from config-flow selectors, and `"1"` is what lands in the subentry.
    Comparing them to `wheel.node_id`, which really is an int, silently matches
    nothing — every binding disappears and every channel reads "not configured".

    Do not "simplify" this to a direct comparison. It was written after the grid
    shipped claiming four configured channels were empty.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


@callback
def _binding_by_channel(entry: Any, node_id: int) -> dict[int, Any]:
    """Index this wheel's binding subentries by channel."""
    bindings: dict[int, Any] = {}
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_BINDING:
            continue
        data = dict(subentry.data)
        if _as_int(data.get(CONF_NODE_ID)) != node_id:
            continue
        channel = _as_int(data.get(CONF_CHANNEL))
        if channel is not None:
            bindings[channel] = subentry
    return bindings


# The `panel_strings` key for each stored scroll mode.
#
# NOT keyed by CONF_BINDING_PROFILE: that is a config-flow-only field used to
# pick sensible defaults, and it is **never written to the subentry**. Reading it
# back returns None for every binding, which is how the first version of this
# grid reported four configured channels as "not configured".
_MODE_KEYS = {
    MODE_BRIGHTNESS: "mode_brightness",
    MODE_COLOR_TEMP: "mode_color_temp",
    MODE_COLOR: "mode_color",
    MODE_VOLUME: "mode_volume",
    MODE_COVER: "mode_cover_position",
    MODE_TEMPERATURE: "mode_temperature",
    MODE_FAN: "mode_fan_speed",
    MODE_NUMBER: "mode_number",
}


def _behaviour_label(data: dict[str, Any], language: str | None) -> str | None:
    """A short, human phrase for what this binding does, in the user's language.

    Scenes take precedence because scene cycling overrides the normal
    single-press action, which is what a user would notice first.

    Localized here rather than in the frontend: the roadmap requires English and
    Czech to stay aligned, and a second copy of these phrases in JavaScript is
    how they drift.
    """
    if scenes := data.get(CONF_SCENES):
        return localize(language, "mode_scenes", count=len(scenes))
    mode = data.get(CONF_MODE)
    if mode in _MODE_KEYS:
        return localize(language, _MODE_KEYS[mode])
    # A binding exists but its mode is unrecognised — say so rather than let it
    # read as unconfigured, which is a different and wrong thing.
    return str(mode) if mode else localize(language, "configured")


_CLICK_KEYS = {
    CLICK_TOGGLE: "action_toggle",
    CLICK_ON: "action_turn_on",
    CLICK_OFF: "action_turn_off",
    CLICK_NONE: "action_none",
}


def _gesture_summary(
    hass: HomeAssistant,
    language: str | None,
    gesture: str,
    action_key: str,
    target: str | None = None,
) -> GestureSummary:
    """Build one localized read-only gesture row."""
    return GestureSummary(
        gesture=gesture,
        gesture_label=localize(language, f"binding_gesture_{gesture}"),
        action_label=localize(language, action_key),
        target_label=_entity_label(hass, target),
        target_missing=_target_missing(hass, target),
    )


def _gesture_summaries(
    hass: HomeAssistant, data: dict[str, Any], language: str | None
) -> list[GestureSummary]:
    """Describe binding behavior without importing or executing binding.py.

    The defaults mirror ``BindingRuntime.__init__``. This is presentation only:
    it never decides whether an action runs and never calls a service.
    """
    target = data.get(CONF_TARGET)
    click_target = data.get(CONF_CLICK_TARGET) or target
    double_target = data.get(CONF_DOUBLE_TARGET)
    triple_target = data.get(CONF_TRIPLE_TARGET)
    hold_target = data.get(CONF_HOLD_TARGET)
    hold_action = data.get(CONF_HOLD_ACTION, DEFAULT_HOLD_ACTION)
    scenes = list(data.get(CONF_SCENES) or [])

    summaries = [
        _gesture_summary(
            hass,
            language,
            "rotation",
            "action_adjust",
            target,
        )
    ]

    if scenes:
        scene_labels = [
            label for scene in scenes if (label := _entity_label(hass, scene))
        ]
        summaries.append(
            GestureSummary(
                gesture="short_press",
                gesture_label=localize(language, "binding_gesture_short_press"),
                action_label=localize(language, "action_cycle_scenes"),
                target_label=" / ".join(scene_labels) or None,
                target_missing=any(_target_missing(hass, scene) for scene in scenes),
            )
        )
    else:
        click_action = data.get(CONF_CLICK_ACTION, DEFAULT_CLICK_ACTION)
        summaries.append(
            _gesture_summary(
                hass,
                language,
                "short_press",
                _CLICK_KEYS.get(click_action, "action_toggle"),
                None if click_action == CLICK_NONE else click_target,
            )
        )

    summaries.extend(
        (
            _gesture_summary(
                hass,
                language,
                "double_press",
                "action_toggle" if double_target else "action_none",
                double_target,
            ),
            _gesture_summary(
                hass,
                language,
                "triple_press",
                "action_toggle" if triple_target else "action_none",
                triple_target,
            ),
        )
    )

    if hold_action == HOLD_RAMP:
        summaries.append(
            _gesture_summary(hass, language, "hold", "action_ramp", target)
        )
        summaries.append(
            _gesture_summary(hass, language, "release", "action_stop_ramp", target)
        )
    elif hold_action == HOLD_TOGGLE and hold_target:
        summaries.append(
            _gesture_summary(hass, language, "hold", "action_toggle", hold_target)
        )
        summaries.append(_gesture_summary(hass, language, "release", "action_none"))
    else:
        # HOLD_NONE and a toggle without a target both execute nothing.
        summaries.append(_gesture_summary(hass, language, "hold", "action_none"))
        summaries.append(_gesture_summary(hass, language, "release", "action_none"))
    return summaries


@callback
def _channel_summaries(
    hass: HomeAssistant,
    wheel: BilresaWheel,
    bindings: dict[int, Any],
    language: str | None,
) -> list[ChannelSummary]:
    """One summary per channel the device itself reports.

    Channels come from the wheel's own Matter descriptors, never from a hard-coded
    three: `model.py` derives them per device, and a future BILRESA may differ.
    An unconfigured channel is a real state the grid must show, so every channel
    appears whether or not a binding exists.
    """
    channels = sorted(
        {ep.channel for ep in wheel.endpoints.values() if ep.channel is not None}
    )
    summaries: list[ChannelSummary] = []
    for channel in channels:
        subentry = bindings.get(channel)
        if subentry is None:
            summaries.append(ChannelSummary(channel=channel))
            continue
        data = dict(subentry.data)
        target = data.get(CONF_TARGET)
        # The click target defaults to the scroll target, mirroring binding.py.
        click_target = data.get(CONF_CLICK_TARGET) or target
        actions = _gesture_summaries(hass, data, language)
        summaries.append(
            ChannelSummary(
                channel=channel,
                # The stored scroll mode. CONF_BINDING_PROFILE is not persisted.
                profile=data.get(CONF_MODE),
                behaviour=_behaviour_label(data, language),
                target_label=_entity_label(hass, target),
                target_missing=(
                    _target_missing(hass, target)
                    or _target_missing(hass, click_target)
                    or any(action.target_missing for action in actions)
                ),
                actions=actions,
                binding=(
                    BindingEditor(
                        id=subentry.subentry_id,
                        revision=binding_revision(subentry),
                        data=editor_data(data),
                    )
                    if hasattr(subentry, "subentry_id") and hasattr(subentry, "title")
                    else None
                ),
            )
        )
    return summaries


@callback
def _last_activity(
    hass: HomeAssistant, wheel: BilresaWheel
) -> tuple[str | None, int | None]:
    """Return (ISO timestamp, channel) of this wheel's most recent event.

    Read from this integration's own `event` entities, whose state IS the
    timestamp of the last event (`event.py`). The coordinator cannot answer this:
    its `_recent_events` deque carries no node ID, and endpoints are numbered per
    node, so two wheels both have an endpoint 1.

    `EventEntity` does not restore state, so this is `(None, None)` after every
    Home Assistant restart until the wheel is next touched. That is "no activity
    yet" and the UI must render it as such — never as a fault.
    """
    registry = er.async_get(hass)
    newest: tuple[str, int] | None = None
    for channel in sorted(
        {ep.channel for ep in wheel.endpoints.values() if ep.channel is not None}
    ):
        entity_id = registry.async_get_entity_id(
            "event", DOMAIN, f"{wheel.node_id}_ch{channel}"
        )
        if entity_id is None:
            continue
        state = hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            continue
        # States are ISO 8601 UTC timestamps, so lexical order is chronological.
        if newest is None or state.state > newest[0]:
            newest = (state.state, channel)
    return newest if newest is not None else (None, None)


@callback
def _wheel_name_and_area(
    hass: HomeAssistant, device: dr.DeviceEntry | None, wheel: BilresaWheel
) -> tuple[str, str | None]:
    """Resolve the user-visible name and area.

    NOT `wheel.name`: `model.py` sets it to the Matter *product* name, which is
    identical for every BILRESA in the household. Using it labels every wheel the
    same. The registry holds the name the user actually chose.
    """
    if device is None:
        return (wheel.name, None)
    name = device.name_by_user or device.name or wheel.name
    area = None
    if device.area_id:
        area_registry = ar.async_get(hass)
        if (area_entry := area_registry.async_get_area(device.area_id)) is not None:
            area = area_entry.name
    return (name, area)


@callback
def async_overview_snapshot(hass: HomeAssistant, entry: Any) -> dict[str, Any]:
    """Build the whole overview. Deterministic, bounded, no I/O.

    Bounded by construction: one entry per discovered wheel, one summary per
    channel the device reports. Nothing here grows with uptime or event volume.
    """
    coordinator = entry.runtime_data
    # The instance language, not the individual user's: Home Assistant exposes no
    # per-connection locale here. See panel_strings.
    language = getattr(hass.config, "language", None)
    wheels: list[WheelOverview] = []

    for node_id, wheel in sorted(coordinator.wheels.items()):
        link = resolve_matter_device(
            hass,
            matter_url=coordinator.url,
            server_info=coordinator.matter_server_info,
            wheel=wheel,
        )
        name, area = _wheel_name_and_area(hass, link.device, wheel)
        last_activity, last_channel = _last_activity(hass, wheel)
        wheels.append(
            WheelOverview(
                key=wheel_key(node_id),
                name=name,
                area=area,
                # Per-wheel reachability, not the server connection. See
                # device_link.wheel_availability.
                availability=wheel_availability(hass, link.device),
                linked_to_matter=link.device is not None,
                last_activity=last_activity,
                last_active_channel=last_channel,
                channels=_channel_summaries(
                    hass, wheel, _binding_by_channel(entry, node_id), language
                ),
            )
        )

    snapshot = OverviewSnapshot(
        wheels=wheels,
        matter_connected=bool(coordinator.connected),
        event_source=str(coordinator.event_source),
    )
    return asdict(snapshot)
