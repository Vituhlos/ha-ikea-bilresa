"""Authenticated read-only WebSocket API for the panel.

**Phase 0 spike.** These two commands exist to prove the transport works —
an authenticated request and an authenticated subscription that unsubscribes
itself — not to be the panel's API. `PANEL_ROADMAP.md` requires a versioned
contract with three distinct view models before real UI is built; the draft of
that contract lives outside this repository. Expect these two commands to be
deleted, not extended.

What they deliberately do NOT do:

- serialize coordinator internals. `PANEL_ROADMAP.md` forbids it, and the reply
  below is hand-built from three scalars for exactly that reason.
- expose node IDs, names, serials or the Matter Server URL.
- offer any write. `0.5.8` is read-only; there is no mutation path here to
  forget about later.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
import voluptuous as vol

from .const import DOMAIN, SIGNAL_CONNECTION

TYPE_INFO = f"{DOMAIN}/spike/info"
TYPE_SUBSCRIBE = f"{DOMAIN}/spike/subscribe"

_COMMANDS_REGISTERED = f"{DOMAIN}_ws_registered"


def _coordinator(hass: HomeAssistant) -> Any | None:
    """Return the single coordinator, or None when not loaded.

    The panel must not assume the integration is set up: a browser can hold the
    sidebar entry open across a config-entry unload.
    """
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        return None
    return getattr(entries[0], "runtime_data", None)


def _snapshot(hass: HomeAssistant) -> dict[str, Any]:
    """Three scalars, none of them identifying. Not a view model."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        return {"loaded": False, "connected": False, "wheel_count": 0}
    return {
        "loaded": True,
        "connected": bool(coordinator.connected),
        "wheel_count": len(coordinator.wheels),
    }


# Decorator order follows Home Assistant's convention: the command declaration
# outermost, the auth check in the middle, @callback innermost. Every order
# happens to work because require_admin uses functools.wraps and so carries the
# `_ws_command` metadata through -- but do not rely on that by accident.
@websocket_api.websocket_command({vol.Required("type"): TYPE_INFO})
@websocket_api.require_admin
@callback
def ws_info(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Prove an authenticated read-only request reaches the integration."""
    connection.send_result(msg["id"], _snapshot(hass))


@websocket_api.websocket_command({vol.Required("type"): TYPE_SUBSCRIBE})
@websocket_api.require_admin
@callback
def ws_subscribe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Prove an authenticated subscription pushes and then cleans up.

    Cleanup is the whole point. `connection.subscriptions` is what Home Assistant
    unwinds when the client unsubscribes, the socket drops or HA stops, so the
    dispatcher listener must be handed to it rather than kept here. A subscription
    that outlives its socket is a leak the panel would hide until a soak test.
    """

    @callback
    def _forward() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], _snapshot(hass)))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass, SIGNAL_CONNECTION, _forward
    )
    connection.send_result(msg["id"], _snapshot(hass))


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    """Register once per Home Assistant run.

    WebSocket commands are global, not per config entry, and Home Assistant has
    no unregister API. Re-registering on reload would silently replace the
    handler, so this is guarded instead.
    """
    if hass.data.get(_COMMANDS_REGISTERED):
        return
    websocket_api.async_register_command(hass, ws_info)
    websocket_api.async_register_command(hass, ws_subscribe)
    hass.data[_COMMANDS_REGISTERED] = True
