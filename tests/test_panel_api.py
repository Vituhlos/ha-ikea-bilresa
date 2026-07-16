"""Phase 2: the read-only API must leak nothing and leak no subscriptions."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.ikea_bilresa.const import (
    DOMAIN,
    EVENT_BILRESA,
    SIGNAL_CONNECTION,
    SIGNAL_WHEELS_UPDATED,
)
from custom_components.ikea_bilresa.panel_api import (
    TYPE_ACTIVITY_SUBSCRIBE,
    TYPE_OVERVIEW,
    TYPE_OVERVIEW_SUBSCRIBE,
    async_register_commands,
    ws_activity_subscribe,
    ws_overview,
    ws_overview_subscribe,
)
from custom_components.ikea_bilresa.panel_models import wheel_key

NODE_A = 13
SNAPSHOT = {
    "wheels": [{"key": wheel_key(NODE_A), "name": "Wheel A"}],
    "matter_connected": True,
    "event_source": "core_matter_client",
    "contract_version": 1,
}


def _hass(*, loaded: bool = True) -> SimpleNamespace:
    entry = SimpleNamespace(runtime_data=SimpleNamespace())
    return SimpleNamespace(
        data={},
        bus=SimpleNamespace(async_listen=MagicMock(return_value=MagicMock())),
        config_entries=SimpleNamespace(
            async_loaded_entries=lambda domain: (
                [entry] if loaded and domain == DOMAIN else []
            )
        ),
    )


def _patch_snapshot(monkeypatch, snapshot=None) -> None:
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.async_overview_snapshot",
        lambda _hass, _entry: dict(snapshot if snapshot is not None else SNAPSHOT),
    )


def _connection() -> MagicMock:
    connection = MagicMock()
    connection.subscriptions = {}
    return connection


# -- overview request ------------------------------------------------------


def test_overview_returns_the_snapshot(monkeypatch) -> None:
    _patch_snapshot(monkeypatch)
    connection = _connection()

    ws_overview(_hass(), connection, {"id": 1, "type": TYPE_OVERVIEW})

    connection.send_result.assert_called_once_with(1, SNAPSHOT)


def test_overview_while_unloaded_is_empty_not_an_error(monkeypatch) -> None:
    """A browser can hold the sidebar open across an unload."""
    _patch_snapshot(monkeypatch)
    connection = _connection()

    ws_overview(_hass(loaded=False), connection, {"id": 1, "type": TYPE_OVERVIEW})

    result = connection.send_result.call_args.args[1]
    assert result["wheels"] == []
    assert result["matter_connected"] is False
    assert result["event_source"] == "unloaded"


# -- overview subscription -------------------------------------------------


def test_overview_subscription_listens_to_both_signals(monkeypatch) -> None:
    _patch_snapshot(monkeypatch)
    signals = []
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.async_dispatcher_connect",
        lambda _h, signal, _t: signals.append(signal) or MagicMock(),
    )
    connection = _connection()

    ws_overview_subscribe(
        _hass(), connection, {"id": 5, "type": TYPE_OVERVIEW_SUBSCRIBE}
    )

    assert set(signals) == {SIGNAL_CONNECTION, SIGNAL_WHEELS_UPDATED}


def test_overview_subscription_unwinds_every_listener(monkeypatch) -> None:
    """Both dispatcher handles must go, not just the last one registered.

    Two signals means two unsubscribes behind one subscription id. Leaking the
    first one is silent: the socket closes, HA calls the handle it was given, and
    a dead connection keeps receiving pushes for the other signal forever.
    """
    _patch_snapshot(monkeypatch)
    handed_out: list[MagicMock] = []

    def _connect(_hass, _signal, _target):
        unsub = MagicMock()
        handed_out.append(unsub)
        return unsub

    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.async_dispatcher_connect", _connect
    )
    connection = _connection()
    ws_overview_subscribe(
        _hass(), connection, {"id": 5, "type": TYPE_OVERVIEW_SUBSCRIBE}
    )
    assert len(handed_out) == 2

    connection.subscriptions[5]()

    for unsub in handed_out:
        unsub.assert_called_once()


def test_overview_subscription_pushes_on_signal(monkeypatch) -> None:
    _patch_snapshot(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.async_dispatcher_connect",
        lambda _h, signal, target: captured.setdefault(signal, target) or MagicMock(),
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.websocket_api.event_message",
        lambda mid, payload: {"id": mid, "event": payload},
    )
    connection = _connection()
    ws_overview_subscribe(
        _hass(), connection, {"id": 5, "type": TYPE_OVERVIEW_SUBSCRIBE}
    )

    captured[SIGNAL_CONNECTION]()

    connection.send_message.assert_called_once_with({"id": 5, "event": SNAPSHOT})


def test_two_clients_get_independent_subscriptions(monkeypatch) -> None:
    _patch_snapshot(monkeypatch)
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.async_dispatcher_connect",
        lambda _h, _s, _t: MagicMock(),
    )
    hass = _hass()
    first, second = _connection(), _connection()

    ws_overview_subscribe(hass, first, {"id": 1, "type": TYPE_OVERVIEW_SUBSCRIBE})
    ws_overview_subscribe(hass, second, {"id": 9, "type": TYPE_OVERVIEW_SUBSCRIBE})

    assert 1 in first.subscriptions
    assert 9 in second.subscriptions
    assert first.subscriptions is not second.subscriptions


# -- activity subscription -------------------------------------------------


def _fire(hass, connection, monkeypatch, data) -> None:
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.websocket_api.event_message",
        lambda mid, payload: {"id": mid, "event": payload},
    )
    ws_activity_subscribe(hass, connection, {"id": 7, "type": TYPE_ACTIVITY_SUBSCRIBE})
    forward = hass.bus.async_listen.call_args.args[1]
    forward(SimpleNamespace(data=data))


def test_activity_listens_to_the_public_bus_event(monkeypatch) -> None:
    """Listening to the bus keeps the dispatch path untouched."""
    hass, connection = _hass(), _connection()
    _fire(
        hass,
        connection,
        monkeypatch,
        {
            "node_id": NODE_A,
            "channel": 1,
            "type": "rotate",
            "direction": "up",
            "notches": 6,
            "presses": 0,
        },
    )

    assert hass.bus.async_listen.call_args.args[0] == EVENT_BILRESA
    payload = connection.send_message.call_args.args[0]["event"]
    assert payload["wheel"] == wheel_key(NODE_A)
    assert payload["gesture"] == "rotate"
    assert payload["notches"] == 6


def test_activity_strips_every_identifier(monkeypatch) -> None:
    """The bus payload carries node_id, wheel_name and endpoint_id. None may pass."""
    hass, connection = _hass(), _connection()
    _fire(
        hass,
        connection,
        monkeypatch,
        {
            "node_id": NODE_A,
            "wheel_name": "BILRESA scroll wheel",
            "endpoint_id": 3,
            "channel": 1,
            "type": "press",
            "presses": 1,
        },
    )

    payload = connection.send_message.call_args.args[0]["event"]
    rendered = str(payload)
    assert "node_id" not in payload
    assert "wheel_name" not in payload
    assert "endpoint_id" not in payload
    assert "BILRESA scroll wheel" not in rendered
    assert str(NODE_A) not in rendered.replace(wheel_key(NODE_A), "")


def test_activity_reports_gap_2_and_3_as_absent_not_healthy(monkeypatch) -> None:
    """No source exists for either. Null is the honest answer, not a guess."""
    hass, connection = _hass(), _connection()
    _fire(
        hass,
        connection,
        monkeypatch,
        {"node_id": NODE_A, "channel": 1, "type": "press", "presses": 1},
    )

    payload = connection.send_message.call_args.args[0]["event"]
    assert payload["result"] is None
    assert payload["dispatched"] is None


def test_activity_ignores_a_malformed_event(monkeypatch) -> None:
    """A bus event without an int node_id cannot be attributed to a wheel."""
    hass, connection = _hass(), _connection()
    _fire(hass, connection, monkeypatch, {"channel": 1, "type": "rotate"})

    connection.send_message.assert_not_called()


def test_activity_subscription_is_handed_to_home_assistant() -> None:
    hass, connection = _hass(), _connection()
    handle = MagicMock()
    hass.bus.async_listen.return_value = handle

    ws_activity_subscribe(hass, connection, {"id": 7, "type": TYPE_ACTIVITY_SUBSCRIBE})

    assert connection.subscriptions[7] is handle


# -- registration ----------------------------------------------------------


def test_commands_register_once(monkeypatch) -> None:
    """Global, and HA has no unregister API — a reload must not replace them."""
    register = MagicMock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.websocket_api.async_register_command",
        register,
    )
    hass = _hass()

    async_register_commands(hass)
    async_register_commands(hass)

    assert register.call_count == 3  # overview, overview/subscribe, activity


def test_there_is_no_write_command() -> None:
    """0.5.8 is read-only. A mutation path must not appear by accident."""
    import custom_components.ikea_bilresa.panel_api as api

    exported = {name for name in dir(api) if name.startswith("ws_")}
    assert exported == {"ws_overview", "ws_overview_subscribe", "ws_activity_subscribe"}
