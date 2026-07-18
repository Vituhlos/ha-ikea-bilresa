"""Authenticated WebSocket API for the BILRESA panel.

`PANEL_ROADMAP.md` Phase 2. This replaces the Phase 0 spike's two throwaway
commands, which existed only to prove the transport and are now deleted rather
than extended, as that package said they would be.

All commands are admin-only. Overview and activity are read-only; binding
mutations use the same validation as the native config-subentry flow and require
optimistic-concurrency tokens for updates and deletion.

- `ikea_bilresa/overview` — one snapshot.
- `ikea_bilresa/overview/subscribe` — pushes a fresh snapshot when the wheel set
  or the connection changes.
- `ikea_bilresa/activity/subscribe` — live gestures, opt-in, for the live-test
  view only.

The mutation contract is deliberately narrow: it can create, update or delete a
binding subentry and nothing else. It cannot mutate wheels, Matter devices,
entities or arbitrary config entries.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
import voluptuous as vol

from .binding_config import (
    binding_revision,
    editor_data,
    validate_binding_data,
)
from .const import (
    ACTION_HOLD,
    ACTION_PRESS,
    ACTION_RELEASE,
    ACTION_ROTATE,
    CONF_CHANNEL,
    CONF_ENDPOINT,
    CONF_NODE_ID,
    DIRECTION_DOWN,
    DIRECTION_UP,
    DOMAIN,
    EVENT_BILRESA,
    ROLE_BUTTON,
    SIGNAL_BINDING_ACTIVITY,
    SIGNAL_BINDINGS_UPDATED,
    SIGNAL_CONNECTION,
    SIGNAL_WHEELS_UPDATED,
    SUBENTRY_BINDING,
)
from .engine import WheelAction
from .panel_models import CONTRACT_VERSION, async_overview_snapshot, wheel_key
from .presentation import generated_binding_title, generated_button_binding_title

TYPE_OVERVIEW = f"{DOMAIN}/overview"
TYPE_OVERVIEW_SUBSCRIBE = f"{DOMAIN}/overview/subscribe"
TYPE_ACTIVITY_SUBSCRIBE = f"{DOMAIN}/activity/subscribe"
TYPE_BINDING_SAVE = f"{DOMAIN}/binding/save"
TYPE_BINDING_DELETE = f"{DOMAIN}/binding/delete"
TYPE_BINDING_TEST = f"{DOMAIN}/binding/test"

_COMMANDS_REGISTERED = f"{DOMAIN}_ws_registered"


@callback
def _loaded_entry(hass: HomeAssistant) -> Any | None:
    """The single loaded config entry, or None.

    The panel must never assume the integration is up: a browser can hold the
    sidebar open across an unload, and `single_config_entry` means there is at
    most one.
    """
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    return entries[0] if entries else None


@callback
def _snapshot_or_empty(hass: HomeAssistant) -> dict[str, Any]:
    """A snapshot, or an honest empty one while the integration is unloaded.

    An unloaded integration is a state the grid can render — "nothing here" —
    not an error to throw at the browser.
    """
    entry = _loaded_entry(hass)
    if entry is None:
        return {
            "wheels": [],
            "matter_connected": False,
            "event_source": "unloaded",
            "contract_version": CONTRACT_VERSION,
        }
    return async_overview_snapshot(hass, entry)


@callback
def _node_for_key(entry: Any, key: str) -> int | None:
    """Resolve an opaque panel key without exposing the Matter node ID."""
    return next(
        (node_id for node_id in entry.runtime_data.wheels if wheel_key(node_id) == key),
        None,
    )


@callback
def _binding_for_id(entry: Any, binding_id: str) -> Any | None:
    """Return one binding subentry, rejecting IDs from other subentry types."""
    subentry = entry.subentries.get(binding_id)
    if subentry is None or subentry.subentry_type != SUBENTRY_BINDING:
        return None
    return subentry


@callback
def _binding_for_address(
    entry: Any,
    node_id: int,
    *,
    channel: int | None = None,
    endpoint: int | None = None,
) -> Any | None:
    """Return the existing binding for one channel or button endpoint."""
    address_key = CONF_ENDPOINT if endpoint is not None else CONF_CHANNEL
    address_value = endpoint if endpoint is not None else channel
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_BINDING:
            continue
        data = subentry.data
        if str(data.get(CONF_NODE_ID)) == str(node_id) and str(
            data.get(address_key)
        ) == str(address_value):
            return subentry
    return None


@callback
def _control_address(
    entry: Any, node_id: int, msg: dict[str, Any]
) -> tuple[int | None, int | None, str | None]:
    """Resolve a safe panel control number to its server-side binding address."""
    wheel = entry.runtime_data.wheels[node_id]
    if wheel.is_dual_button:
        if "button" not in msg or "channel" in msg:
            return (None, None, "control_mismatch")
        endpoints = sorted(
            endpoint.endpoint_id
            for endpoint in wheel.endpoints.values()
            if endpoint.role == ROLE_BUTTON
        )
        button = msg["button"]
        if button < 1 or button > len(endpoints):
            return (None, None, "control_missing")
        return (None, endpoints[button - 1], None)

    if "channel" not in msg or "button" in msg:
        return (None, None, "control_mismatch")
    channels = {
        endpoint.channel
        for endpoint in wheel.endpoints.values()
        if endpoint.channel is not None
    }
    channel = msg["channel"]
    if channel not in channels:
        return (None, None, "control_missing")
    return (channel, None, None)


@callback
def _button_index(entry: Any, node_id: int, endpoint_id: Any) -> int | None:
    """Map a private endpoint id to the dual button's safe display number."""
    if not isinstance(endpoint_id, int):
        return None
    wheels = getattr(entry.runtime_data, "wheels", {})
    wheel = wheels.get(node_id)
    if wheel is None or not wheel.is_dual_button:
        return None
    endpoints = sorted(
        endpoint.endpoint_id
        for endpoint in wheel.endpoints.values()
        if endpoint.role == ROLE_BUTTON
    )
    try:
        return endpoints.index(endpoint_id) + 1
    except ValueError:
        return None


@callback
def _binding_payload(subentry: Any) -> dict[str, Any]:
    """Serialize the editable part of a binding after a mutation."""
    return {
        "id": subentry.subentry_id,
        "revision": binding_revision(subentry),
        "data": editor_data(dict(subentry.data)),
    }


@callback
def _binding_title(
    hass: HomeAssistant,
    entry: Any,
    wheel: str,
    *,
    channel: int | None = None,
    button: int | None = None,
) -> str:
    """Use the same human title style as the native config flow."""
    snapshot = async_overview_snapshot(hass, entry)
    name = next(
        (item["name"] for item in snapshot["wheels"] if item["key"] == wheel),
        "BILRESA",
    )
    if button is not None:
        return generated_button_binding_title(name, str(button))
    assert channel is not None
    return generated_binding_title(name, str(channel))


@websocket_api.websocket_command({vol.Required("type"): TYPE_OVERVIEW})
@websocket_api.require_admin
@callback
def ws_overview(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the current overview snapshot."""
    connection.send_result(msg["id"], _snapshot_or_empty(hass))


@websocket_api.websocket_command({vol.Required("type"): TYPE_OVERVIEW_SUBSCRIBE})
@websocket_api.require_admin
@callback
def ws_overview_subscribe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Push a fresh snapshot when the wheel set or the connection changes.

    Both signals are low-rate by nature — a wheel appearing or the Matter
    connection flipping — so a full snapshot per signal needs no coalescing. Do
    not add per-gesture triggers here; that is what the activity subscription is
    for, and rebuilding the whole overview per notch would be exactly the
    unbounded work the roadmap warns about.

    Every unsubscribe is handed to `connection.subscriptions`, which Home
    Assistant unwinds on unsubscribe, socket loss and shutdown. Nothing here
    outlives its socket.
    """

    @callback
    def _push() -> None:
        connection.send_message(
            websocket_api.event_message(msg["id"], _snapshot_or_empty(hass))
        )

    unsubs = [
        async_dispatcher_connect(hass, SIGNAL_CONNECTION, _push),
        async_dispatcher_connect(hass, SIGNAL_WHEELS_UPDATED, _push),
        async_dispatcher_connect(hass, SIGNAL_BINDINGS_UPDATED, _push),
    ]

    @callback
    def _unsubscribe() -> None:
        for unsub in unsubs:
            unsub()

    connection.subscriptions[msg["id"]] = _unsubscribe
    connection.send_result(msg["id"], _snapshot_or_empty(hass))


@websocket_api.websocket_command({vol.Required("type"): TYPE_ACTIVITY_SUBSCRIBE})
@websocket_api.require_admin
@callback
def ws_activity_subscribe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Stream decoded gestures and correlated binding execution updates.

    The public bus event remains the source for the physical gesture. A separate
    internal dispatcher signal carries the binding's calculated result and
    whether Home Assistant accepted the exact service action. Neither listener
    changes behavior based on whether a panel is open.

    The bus payload carries `node_id`, `wheel_name` and `endpoint_id`. None of
    them may cross the wire — the wheel is addressed by its opaque key, as
    everywhere else.

    No queue is kept: each event is written straight to the socket and dropped.
    There is therefore no backlog to bound. Rotation is rate-limited by the
    device's own 0.5–1 s batching, so this cannot become a flood.
    """

    @callback
    def _send(data: dict[str, Any]) -> None:
        node_id = data.get("node_id")
        if not isinstance(node_id, int):
            return
        entry = _loaded_entry(hass)
        button = (
            _button_index(entry, node_id, data.get("endpoint_id"))
            if entry is not None
            else None
        )
        connection.send_message(
            websocket_api.event_message(
                msg["id"],
                {
                    "wheel": wheel_key(node_id),
                    "action_id": data.get("action_id"),
                    "channel": data.get("channel"),
                    "button": button,
                    "gesture": data.get("type"),
                    "direction": data.get("direction"),
                    "notches": data.get("notches"),
                    "presses": data.get("presses"),
                    "observed_duration_ms": data.get("observed_duration_ms"),
                    "source": data.get("source", "matter"),
                    "result": data.get("result"),
                    "dispatch_status": data.get("dispatch_status", "received"),
                    "dispatched": data.get("dispatched"),
                    "reason": data.get("reason"),
                },
            )
        )

    @callback
    def _forward_event(event: Event) -> None:
        _send(dict(event.data))

    @callback
    def _forward_binding(data: dict[str, Any]) -> None:
        _send(data)

    unsubs = [
        hass.bus.async_listen(EVENT_BILRESA, _forward_event),
        async_dispatcher_connect(hass, SIGNAL_BINDING_ACTIVITY, _forward_binding),
    ]

    @callback
    def _unsubscribe() -> None:
        for unsub in unsubs:
            unsub()

    connection.subscriptions[msg["id"]] = _unsubscribe
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): TYPE_BINDING_SAVE,
        vol.Required("wheel"): str,
        vol.Optional("channel"): vol.All(int, vol.Range(min=1)),
        vol.Optional("button"): vol.All(int, vol.Range(min=1)),
        vol.Required("data"): dict,
        vol.Optional("binding_id"): str,
        vol.Optional("expected_revision"): str,
    }
)
@websocket_api.require_admin
@callback
def ws_binding_save(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create or update one binding with validation and conflict detection."""
    entry = _loaded_entry(hass)
    if entry is None:
        connection.send_result(msg["id"], {"ok": False, "error": "unloaded"})
        return
    node_id = _node_for_key(entry, msg["wheel"])
    if node_id is None:
        connection.send_result(msg["id"], {"ok": False, "error": "wheel_missing"})
        return

    channel, endpoint, address_error = _control_address(entry, node_id, msg)
    if address_error is not None:
        connection.send_result(msg["id"], {"ok": False, "error": address_error})
        return
    button = msg.get("button") if endpoint is not None else None
    binding_id = msg.get("binding_id")
    existing = _binding_for_id(entry, binding_id) if binding_id else None
    occupied = _binding_for_address(entry, node_id, channel=channel, endpoint=endpoint)

    if binding_id and existing is None:
        connection.send_result(msg["id"], {"ok": False, "error": "binding_missing"})
        return
    if existing is not None:
        if occupied is not existing:
            connection.send_result(
                msg["id"],
                {"ok": False, "error": "binding_address_mismatch"},
            )
            return
        current_revision = binding_revision(existing)
        if msg.get("expected_revision") != current_revision:
            connection.send_result(
                msg["id"],
                {
                    "ok": False,
                    "error": "conflict",
                    "binding": _binding_payload(existing),
                },
            )
            return
    if occupied is not None and occupied is not existing:
        connection.send_result(
            msg["id"],
            {
                "ok": False,
                "error": (
                    "button_occupied" if endpoint is not None else "channel_occupied"
                ),
                "binding": _binding_payload(occupied),
            },
        )
        return

    normalized, errors = validate_binding_data(
        msg["data"], node_id=node_id, channel=channel, endpoint=endpoint
    )
    if normalized is None:
        connection.send_result(
            msg["id"], {"ok": False, "error": "validation", "fields": errors}
        )
        return

    title = _binding_title(
        hass,
        entry,
        msg["wheel"],
        channel=channel,
        button=button,
    )
    if existing is None:
        address_id = (
            f"endpoint:{endpoint}" if endpoint is not None else f"channel:{channel}"
        )
        new_subentry = ConfigSubentry(
            data=MappingProxyType(normalized),
            subentry_type=SUBENTRY_BINDING,
            title=title,
            unique_id=f"{node_id}:{address_id}",
        )
        hass.config_entries.async_add_subentry(entry, new_subentry)
        saved = new_subentry
    else:
        hass.config_entries.async_update_subentry(
            entry, existing, title=title, data=normalized
        )
        saved = entry.subentries[existing.subentry_id]

    async_dispatcher_send(hass, SIGNAL_BINDINGS_UPDATED)
    connection.send_result(msg["id"], {"ok": True, "binding": _binding_payload(saved)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): TYPE_BINDING_DELETE,
        vol.Required("binding_id"): str,
        vol.Required("expected_revision"): str,
    }
)
@websocket_api.require_admin
@callback
def ws_binding_delete(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete one binding only when the caller still has the latest revision."""
    entry = _loaded_entry(hass)
    if entry is None:
        connection.send_result(msg["id"], {"ok": False, "error": "unloaded"})
        return
    existing = _binding_for_id(entry, msg["binding_id"])
    if existing is None:
        connection.send_result(msg["id"], {"ok": False, "error": "binding_missing"})
        return
    current_revision = binding_revision(existing)
    if msg["expected_revision"] != current_revision:
        connection.send_result(
            msg["id"],
            {
                "ok": False,
                "error": "conflict",
                "binding": _binding_payload(existing),
            },
        )
        return
    hass.config_entries.async_remove_subentry(entry, existing.subentry_id)
    async_dispatcher_send(hass, SIGNAL_BINDINGS_UPDATED)
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): TYPE_BINDING_TEST,
        vol.Required("wheel"): str,
        vol.Optional("channel"): vol.All(int, vol.Range(min=1)),
        vol.Optional("button"): vol.All(int, vol.Range(min=1)),
        vol.Required("gesture"): vol.In(
            (ACTION_ROTATE, ACTION_PRESS, ACTION_HOLD, ACTION_RELEASE)
        ),
        vol.Optional("direction", default=DIRECTION_UP): vol.In(
            (DIRECTION_UP, DIRECTION_DOWN)
        ),
        vol.Optional("notches", default=1): vol.All(int, vol.Range(min=1, max=20)),
        vol.Optional("presses", default=1): vol.All(int, vol.Range(min=1, max=3)),
    }
)
@websocket_api.require_admin
@callback
def ws_binding_test(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Run an explicit panel test through the normal configured binding."""
    entry = _loaded_entry(hass)
    if entry is None:
        connection.send_result(msg["id"], {"ok": False, "error": "unloaded"})
        return
    node_id = _node_for_key(entry, msg["wheel"])
    if node_id is None:
        connection.send_result(msg["id"], {"ok": False, "error": "wheel_missing"})
        return
    wheel = entry.runtime_data.wheels[node_id]
    channel, endpoint, address_error = _control_address(entry, node_id, msg)
    if address_error is not None:
        connection.send_result(msg["id"], {"ok": False, "error": address_error})
        return
    if wheel.is_dual_button and (msg["gesture"] == ACTION_ROTATE or msg["presses"] > 2):
        connection.send_result(msg["id"], {"ok": False, "error": "gesture_unsupported"})
        return
    action = WheelAction(
        node_id=node_id,
        wheel_name=wheel.name,
        channel=channel,
        endpoint_id=endpoint or 0,
        type=msg["gesture"],
        direction=msg["direction"] if msg["gesture"] == ACTION_ROTATE else None,
        notches=msg["notches"] if msg["gesture"] == ACTION_ROTATE else 0,
        presses=msg["presses"] if msg["gesture"] == ACTION_PRESS else 0,
        source="panel_test",
    )
    if not entry.runtime_data.test_binding_action(action):
        connection.send_result(
            msg["id"], {"ok": False, "error": "binding_not_configured"}
        )
        return
    connection.send_result(msg["id"], {"ok": True, "action_id": action.action_id})


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    """Register once per Home Assistant run.

    WebSocket commands are global rather than per config entry, and Home
    Assistant has no unregister API, so a reload must not re-register: doing so
    would silently replace a live handler.
    """
    if hass.data.get(_COMMANDS_REGISTERED):
        return
    websocket_api.async_register_command(hass, ws_overview)
    websocket_api.async_register_command(hass, ws_overview_subscribe)
    websocket_api.async_register_command(hass, ws_activity_subscribe)
    websocket_api.async_register_command(hass, ws_binding_save)
    websocket_api.async_register_command(hass, ws_binding_delete)
    websocket_api.async_register_command(hass, ws_binding_test)
    hass.data[_COMMANDS_REGISTERED] = True
