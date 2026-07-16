"""Authenticated read-only WebSocket API for the panel.

`PANEL_ROADMAP.md` Phase 2. This replaces the Phase 0 spike's two throwaway
commands, which existed only to prove the transport and are now deleted rather
than extended, as that package said they would be.

Three commands, all admin-only, all read-only:

- `ikea_bilresa/overview` — one snapshot.
- `ikea_bilresa/overview/subscribe` — pushes a fresh snapshot when the wheel set
  or the connection changes.
- `ikea_bilresa/activity/subscribe` — live gestures, opt-in, for the live-test
  view only.

**There is no write command, by design.** `0.5.8` is read-only, so there is no
mutation path here to forget about, mis-authorize or have to remove later.
Bindings are still edited through the native config flows.

Serialization lives in `panel_models.py`; this module only moves bytes and
decides who may ask.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
import voluptuous as vol

from .const import (
    DOMAIN,
    EVENT_BILRESA,
    SIGNAL_CONNECTION,
    SIGNAL_WHEELS_UPDATED,
)
from .panel_models import CONTRACT_VERSION, async_overview_snapshot, wheel_key

TYPE_OVERVIEW = f"{DOMAIN}/overview"
TYPE_OVERVIEW_SUBSCRIBE = f"{DOMAIN}/overview/subscribe"
TYPE_ACTIVITY_SUBSCRIBE = f"{DOMAIN}/activity/subscribe"

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
    """Stream decoded gestures while the live-test view is open.

    Listens to the already-public `ikea_bilresa_event` bus event rather than
    reaching into the coordinator, so this adds nothing to the dispatch path.
    The panel being open or closed cannot change gesture timing or binding
    latency: a bus listener runs after the action has already been dispatched.

    The bus payload carries `node_id`, `wheel_name` and `endpoint_id`. None of
    them may cross the wire — the wheel is addressed by its opaque key, as
    everywhere else.

    **`result` and `dispatched` are absent, not forgotten.** `PANEL_DESIGN.md`
    makes the outcome ("brightness 42 -> 58%") the hero of the live-test view,
    but bindings do not report what they computed and dispatch outcome is only a
    global counter. Those are GAP-2 and GAP-3 in this file's sibling notes, both
    open, both needing `binding.py` and their own hardware gate. Until then the
    view can show the gesture and nothing about whether it landed.

    No queue is kept: each event is written straight to the socket and dropped.
    There is therefore no backlog to bound. Rotation is rate-limited by the
    device's own 0.5–1 s batching, so this cannot become a flood.
    """

    @callback
    def _forward(event: Event) -> None:
        data = event.data
        node_id = data.get("node_id")
        if not isinstance(node_id, int):
            return
        connection.send_message(
            websocket_api.event_message(
                msg["id"],
                {
                    "wheel": wheel_key(node_id),
                    "channel": data.get("channel"),
                    "gesture": data.get("type"),
                    "direction": data.get("direction"),
                    "notches": data.get("notches"),
                    "presses": data.get("presses"),
                    # GAP-2 / GAP-3: no source exists for either yet.
                    "result": None,
                    "dispatched": None,
                },
            )
        )

    connection.subscriptions[msg["id"]] = hass.bus.async_listen(EVENT_BILRESA, _forward)
    connection.send_result(msg["id"])


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
    hass.data[_COMMANDS_REGISTERED] = True
