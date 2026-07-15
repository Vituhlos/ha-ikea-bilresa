"""Phase 0 spike: the read-only WebSocket surface must leak nothing and leak no
subscriptions."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.ikea_bilresa.const import DOMAIN, SIGNAL_CONNECTION
from custom_components.ikea_bilresa.model import BilresaWheel
from custom_components.ikea_bilresa.panel_api import (
    TYPE_INFO,
    TYPE_SUBSCRIBE,
    _snapshot,
    async_register_commands,
    ws_info,
    ws_subscribe,
)


def _wheel(node_id: int) -> BilresaWheel:
    return BilresaWheel(
        node_id=node_id,
        name="BILRESA scroll wheel",
        product_name="BILRESA scroll wheel",
        serial="household-serial",
        endpoints={},
    )


def _hass(*, loaded: bool = True, connected: bool = True) -> SimpleNamespace:
    coordinator = SimpleNamespace(
        connected=connected,
        wheels={7: _wheel(7), 8: _wheel(8)},
        url="ws://matter/ws",
    )
    entry = SimpleNamespace(runtime_data=coordinator)
    return SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_loaded_entries=lambda domain: (
                [entry] if loaded and domain == DOMAIN else []
            )
        ),
    )


def test_snapshot_carries_no_identifiers() -> None:
    """Three scalars. Not a view model, and nothing from the household."""
    snapshot = _snapshot(_hass())

    assert snapshot == {"loaded": True, "connected": True, "wheel_count": 2}
    rendered = str(snapshot)
    assert "household-serial" not in rendered
    assert "ws://matter/ws" not in rendered
    assert "7" not in rendered.replace("'wheel_count': 2", "")


def test_snapshot_survives_an_unloaded_integration() -> None:
    """A browser can hold the sidebar open across a config-entry unload."""
    assert _snapshot(_hass(loaded=False)) == {
        "loaded": False,
        "connected": False,
        "wheel_count": 0,
    }


def test_info_replies_with_the_snapshot() -> None:
    connection = MagicMock()
    ws_info(_hass(), connection, {"id": 1, "type": TYPE_INFO})

    connection.send_result.assert_called_once_with(
        1, {"loaded": True, "connected": True, "wheel_count": 2}
    )


def test_subscription_is_handed_to_home_assistant_for_cleanup(monkeypatch) -> None:
    """A subscription that outlives its socket is a leak HA must be able to undo."""
    unsub = MagicMock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.async_dispatcher_connect",
        MagicMock(return_value=unsub),
    )
    connection = MagicMock()
    connection.subscriptions = {}

    ws_subscribe(_hass(), connection, {"id": 5, "type": TYPE_SUBSCRIBE})

    assert connection.subscriptions[5] is unsub


def test_subscription_forwards_connection_changes(monkeypatch) -> None:
    captured = {}

    def _connect(_hass, signal, target):
        captured["signal"] = signal
        captured["target"] = target
        return MagicMock()

    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.async_dispatcher_connect", _connect
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.websocket_api.event_message",
        lambda msg_id, payload: {"id": msg_id, "event": payload},
    )
    connection = MagicMock()
    connection.subscriptions = {}

    ws_subscribe(_hass(), connection, {"id": 5, "type": TYPE_SUBSCRIBE})
    assert captured["signal"] == SIGNAL_CONNECTION

    captured["target"]()
    connection.send_message.assert_called_once_with(
        {"id": 5, "event": {"loaded": True, "connected": True, "wheel_count": 2}}
    )


def test_commands_register_once(monkeypatch) -> None:
    """WebSocket commands are global and HA has no unregister API."""
    register = MagicMock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.websocket_api.async_register_command",
        register,
    )
    hass = _hass()

    async_register_commands(hass)
    async_register_commands(hass)

    assert register.call_count == 2  # ws_info + ws_subscribe, once each
