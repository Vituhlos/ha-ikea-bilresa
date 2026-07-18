"""Panel API privacy, subscription lifecycle and binding mutation tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.ikea_bilresa.const import (
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_CLICK_TARGET,
    CONF_ENDPOINT,
    CONF_HOLD_ACTION,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_TARGET,
    DOMAIN,
    EVENT_BILRESA,
    SIGNAL_BINDINGS_UPDATED,
    SIGNAL_CONNECTION,
    SIGNAL_WHEELS_UPDATED,
    SUBENTRY_BINDING,
)
from custom_components.ikea_bilresa.model import BilresaWheel, SwitchEndpoint
from custom_components.ikea_bilresa.panel_api import (
    TYPE_ACTIVITY_SUBSCRIBE,
    TYPE_BINDING_DELETE,
    TYPE_BINDING_SAVE,
    TYPE_BINDING_TEST,
    TYPE_OVERVIEW,
    TYPE_OVERVIEW_SUBSCRIBE,
    async_register_commands,
    ws_activity_subscribe,
    ws_binding_delete,
    ws_binding_save,
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
            ),
            async_add_subentry=MagicMock(),
            async_update_subentry=MagicMock(),
            async_remove_subentry=MagicMock(),
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

    assert set(signals) == {
        SIGNAL_CONNECTION,
        SIGNAL_WHEELS_UPDATED,
        SIGNAL_BINDINGS_UPDATED,
    }


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
    assert len(handed_out) == 3

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
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.async_dispatcher_connect",
        lambda *_args: MagicMock(),
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


def test_activity_forwards_only_safe_observed_duration(monkeypatch) -> None:
    hass, connection = _hass(), _connection()
    _fire(
        hass,
        connection,
        monkeypatch,
        {
            "node_id": NODE_A,
            "channel": 1,
            "type": "release",
            "observed_duration_ms": 2250,
        },
    )

    payload = connection.send_message.call_args.args[0]["event"]
    assert payload["observed_duration_ms"] == 2250


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


def test_dual_button_activity_exposes_safe_button_number_only(monkeypatch) -> None:
    hass, _entry = _mutation_hass(dual_button=True)
    connection = _connection()
    _fire(
        hass,
        connection,
        monkeypatch,
        {
            "node_id": NODE_A,
            "endpoint_id": 2,
            "channel": None,
            "type": "press",
            "presses": 2,
        },
    )

    payload = connection.send_message.call_args.args[0]["event"]
    assert payload["button"] == 2
    assert payload["channel"] is None
    assert payload["gesture"] == "press"
    assert payload["presses"] == 2
    assert "endpoint_id" not in payload


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


def test_activity_subscription_unwinds_bus_and_binding_listener(monkeypatch) -> None:
    hass, connection = _hass(), _connection()
    bus_handle = MagicMock()
    binding_handle = MagicMock()
    hass.bus.async_listen.return_value = bus_handle
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.async_dispatcher_connect",
        lambda *_args: binding_handle,
    )

    ws_activity_subscribe(hass, connection, {"id": 7, "type": TYPE_ACTIVITY_SUBSCRIBE})

    connection.subscriptions[7]()
    bus_handle.assert_called_once()
    binding_handle.assert_called_once()


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

    assert register.call_count == 6


def test_write_surface_is_limited_to_binding_mutations_and_tests() -> None:
    """The panel must not gain arbitrary config-entry or Matter mutation."""
    import custom_components.ikea_bilresa.panel_api as api

    exported = {name for name in dir(api) if name.startswith("ws_")}
    assert exported == {
        "ws_activity_subscribe",
        "ws_binding_delete",
        "ws_binding_save",
        "ws_binding_test",
        "ws_overview",
        "ws_overview_subscribe",
    }


def _mutation_hass(subentries=None, *, dual_button: bool = False):
    wheel = BilresaWheel(
        node_id=NODE_A,
        name="Dual button" if dual_button else "Wheel",
        product_name="BILRESA",
        serial=None,
        endpoints=(
            {
                1: SwitchEndpoint(1, None, "button", multi_press_max=2),
                2: SwitchEndpoint(2, None, "button", multi_press_max=2),
            }
            if dual_button
            else {
                1: SwitchEndpoint(1, 1, "scroll_up"),
                2: SwitchEndpoint(2, 1, "scroll_down"),
                3: SwitchEndpoint(3, 1, "button"),
            }
        ),
    )
    entry = SimpleNamespace(
        subentries=subentries or {},
        runtime_data=SimpleNamespace(
            wheels={NODE_A: wheel},
            connected=True,
            event_source="core_matter_client",
        ),
    )
    hass = _hass()
    hass.config = SimpleNamespace(language="en")
    hass.config_entries.async_loaded_entries = lambda domain: (
        [entry] if domain == DOMAIN else []
    )
    return hass, entry


def _stored_binding(revision_data=None):
    return SimpleNamespace(
        subentry_id="binding-1",
        subentry_type=SUBENTRY_BINDING,
        title="Wheel · Channel 1",
        unique_id=None,
        data={
            CONF_NODE_ID: str(NODE_A),
            CONF_CHANNEL: "1",
            CONF_TARGET: "light.office",
            CONF_MODE: "brightness",
            **(revision_data or {}),
        },
    )


def _stored_button_binding(endpoint: int = 1):
    return SimpleNamespace(
        subentry_id=f"button-binding-{endpoint}",
        subentry_type=SUBENTRY_BINDING,
        title=f"Dual button · BTN {endpoint}",
        unique_id=None,
        data={
            CONF_NODE_ID: str(NODE_A),
            CONF_ENDPOINT: str(endpoint),
            CONF_CLICK_ACTION: "toggle",
            CONF_CLICK_TARGET: f"light.button_{endpoint}",
            CONF_HOLD_ACTION: "none",
        },
    )


def test_binding_save_rejects_stale_revision(monkeypatch) -> None:
    subentry = _stored_binding()
    hass, _entry = _mutation_hass({subentry.subentry_id: subentry})
    connection = _connection()

    ws_binding_save(
        hass,
        connection,
        {
            "id": 20,
            "type": TYPE_BINDING_SAVE,
            "wheel": wheel_key(NODE_A),
            "channel": 1,
            "binding_id": subentry.subentry_id,
            "expected_revision": "stale",
            "data": {CONF_TARGET: "light.office", CONF_MODE: "brightness"},
        },
    )

    result = connection.send_result.call_args.args[1]
    assert result["ok"] is False
    assert result["error"] == "conflict"
    hass.config_entries.async_update_subentry.assert_not_called()


def test_binding_save_creates_only_normalized_subentry(monkeypatch) -> None:
    hass, _entry = _mutation_hass()
    connection = _connection()
    created = {}

    def _subentry(**kwargs):
        item = SimpleNamespace(subentry_id="new", **kwargs)
        created["item"] = item
        return item

    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.ConfigSubentry", _subentry
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api._binding_title",
        lambda *_args, **_kwargs: "Wheel · Channel 1",
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.async_dispatcher_send", MagicMock()
    )

    ws_binding_save(
        hass,
        connection,
        {
            "id": 21,
            "type": TYPE_BINDING_SAVE,
            "wheel": wheel_key(NODE_A),
            "channel": 1,
            "data": {
                CONF_TARGET: "light.office",
                CONF_MODE: "brightness",
            },
        },
    )

    result = connection.send_result.call_args.args[1]
    assert result["ok"] is True
    assert dict(created["item"].data)[CONF_NODE_ID] == str(NODE_A)
    assert dict(created["item"].data)[CONF_CHANNEL] == "1"
    hass.config_entries.async_add_subentry.assert_called_once()


def test_button_save_maps_display_number_to_endpoint_without_leaking_it(
    monkeypatch,
) -> None:
    hass, _entry = _mutation_hass(dual_button=True)
    connection = _connection()
    created = {}

    def _subentry(**kwargs):
        item = SimpleNamespace(subentry_id="new-button", **kwargs)
        created["item"] = item
        return item

    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.ConfigSubentry", _subentry
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api._binding_title",
        lambda *_args, **_kwargs: "Dual button · BTN 2",
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_api.async_dispatcher_send", MagicMock()
    )

    ws_binding_save(
        hass,
        connection,
        {
            "id": 23,
            "type": TYPE_BINDING_SAVE,
            "wheel": wheel_key(NODE_A),
            "button": 2,
            "data": {
                CONF_CLICK_ACTION: "toggle",
                CONF_CLICK_TARGET: "light.second",
                CONF_HOLD_ACTION: "none",
            },
        },
    )

    result = connection.send_result.call_args.args[1]
    assert result["ok"] is True
    assert dict(created["item"].data)[CONF_ENDPOINT] == "2"
    assert CONF_ENDPOINT not in result["binding"]["data"]
    assert CONF_CHANNEL not in dict(created["item"].data)


def test_button_save_rejects_channel_shaped_request() -> None:
    hass, _entry = _mutation_hass(dual_button=True)
    connection = _connection()

    ws_binding_save(
        hass,
        connection,
        {
            "id": 24,
            "type": TYPE_BINDING_SAVE,
            "wheel": wheel_key(NODE_A),
            "channel": 1,
            "data": {},
        },
    )

    result = connection.send_result.call_args.args[1]
    assert result == {"ok": False, "error": "control_mismatch"}
    hass.config_entries.async_add_subentry.assert_not_called()


def test_button_save_reports_button_occupied() -> None:
    subentry = _stored_button_binding(1)
    hass, _entry = _mutation_hass({subentry.subentry_id: subentry}, dual_button=True)
    connection = _connection()

    ws_binding_save(
        hass,
        connection,
        {
            "id": 25,
            "type": TYPE_BINDING_SAVE,
            "wheel": wheel_key(NODE_A),
            "button": 1,
            "data": {
                CONF_CLICK_ACTION: "toggle",
                CONF_CLICK_TARGET: "light.other",
                CONF_HOLD_ACTION: "none",
            },
        },
    )

    result = connection.send_result.call_args.args[1]
    assert result["ok"] is False
    assert result["error"] == "button_occupied"
    assert CONF_ENDPOINT not in result["binding"]["data"]
    hass.config_entries.async_add_subentry.assert_not_called()


def test_binding_delete_requires_latest_revision() -> None:
    subentry = _stored_binding()
    hass, _entry = _mutation_hass({subentry.subentry_id: subentry})
    connection = _connection()

    ws_binding_delete(
        hass,
        connection,
        {
            "id": 22,
            "type": TYPE_BINDING_DELETE,
            "binding_id": subentry.subentry_id,
            "expected_revision": "stale",
        },
    )

    assert connection.send_result.call_args.args[1]["error"] == "conflict"
    hass.config_entries.async_remove_subentry.assert_not_called()


def test_binding_test_command_is_registered() -> None:
    assert TYPE_BINDING_TEST.endswith("/binding/test")
