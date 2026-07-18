"""Tests for event-source fallback and privacy-safe telemetry."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.ikea_bilresa.const import (
    ACTION_PRESS,
    CLUSTER_SWITCH,
    CONF_CHANNEL,
    CONF_ENDPOINT,
    CONF_NODE_ID,
    DOMAIN,
    EVENT_BILRESA,
    SUBENTRY_BINDING,
    signal_raw_button,
)
from custom_components.ikea_bilresa.coordinator import BilresaCoordinator
from custom_components.ikea_bilresa.engine import WheelAction
from custom_components.ikea_bilresa.matter_core import CoreMatterUnavailable
from custom_components.ikea_bilresa.model import BilresaWheel


class FailingCoreSource:
    source = "core_matter_client"
    server_info = None

    def __init__(self, *_args) -> None:
        self.stop = AsyncMock()

    async def start(self) -> None:
        raise CoreMatterUnavailable("unsupported test client")


class FakeWebSocketSource:
    source = "dedicated_websocket"
    server_info = {"sdk_version": "test"}

    def __init__(self, *_args) -> None:
        self.start = AsyncMock()
        self.stop = AsyncMock()


@pytest.mark.asyncio
async def test_initial_core_failure_falls_back_and_records_reason(monkeypatch) -> None:
    hass = SimpleNamespace()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
        FailingCoreSource,
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.MatterWSClient",
        FakeWebSocketSource,
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.async_get_clientsession",
        lambda _hass: Mock(),
    )

    coordinator = BilresaCoordinator(hass, "ws://matter/ws")
    await coordinator.async_start()

    assert coordinator.event_source == "dedicated_websocket"
    assert coordinator.telemetry["fallback_count"] == 1
    assert coordinator.telemetry["last_fallback_reason"] == "unsupported test client"
    coordinator._client.start.assert_awaited_once()


def test_recent_telemetry_is_bounded_and_excludes_node_id(monkeypatch) -> None:
    hass = SimpleNamespace()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
        lambda *_args: SimpleNamespace(source="core", server_info=None),
    )
    coordinator = BilresaCoordinator(hass, "ws://matter/ws")

    for event_number in range(25):
        coordinator._on_event(
            "node_event",
            {
                "node_id": 123456,
                "endpoint_id": 1,
                "cluster_id": 59,
                "event_id": 5,
                "event_number": event_number,
            },
        )

    recent = coordinator.telemetry["recent_events"]
    assert len(recent) == 20
    assert recent[0]["event_number"] == 5
    assert all("node_id" not in event for event in recent)


def test_existing_wheel_metadata_is_refreshed(monkeypatch) -> None:
    """A firmware update may add serial metadata to an already known node."""
    hass = SimpleNamespace()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
        lambda *_args: SimpleNamespace(source="core", server_info=None),
    )
    coordinator = BilresaCoordinator(hass, "ws://matter/ws")
    original = BilresaWheel(
        node_id=12,
        name="BILRESA scroll wheel",
        product_name="BILRESA scroll wheel",
        serial=None,
        endpoints={},
    )
    updated = BilresaWheel(
        node_id=12,
        name="BILRESA scroll wheel",
        product_name="BILRESA scroll wheel",
        serial="new-serial",
        endpoints={},
    )
    wheels = iter([original, updated, updated])
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.parse_node",
        lambda _node: next(wheels),
    )

    assert coordinator._register_wheel({}) is True
    assert coordinator._register_wheel({}) is True
    assert coordinator.wheels[12].serial == "new-serial"
    assert coordinator._register_wheel({}) is False


def test_schema_12_node_updated_refreshes_metadata(monkeypatch) -> None:
    hass = SimpleNamespace()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
        lambda *_args: SimpleNamespace(source="core", server_info=None),
    )
    coordinator = BilresaCoordinator(hass, "ws://matter/ws")
    coordinator._add_node = Mock()

    payload = {"node_id": 12, "attributes": {}}
    coordinator._on_event("node_updated", payload)

    coordinator._add_node.assert_called_once_with(payload)


def test_current_position_is_forwarded_only_as_engine_safety_hint(
    monkeypatch,
) -> None:
    hass = SimpleNamespace()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
        lambda *_args: SimpleNamespace(source="core", server_info=None),
    )
    coordinator = BilresaCoordinator(hass, "ws://matter/ws")
    coordinator.wheels[12] = BilresaWheel(
        node_id=12,
        name="Test button",
        product_name="BILRESA dual button",
        serial=None,
        endpoints={1: SimpleNamespace()},
    )
    coordinator._engine.observe_position = Mock()
    coordinator._dispatch = Mock()

    coordinator._on_event("attribute_updated", [12, "1/59/0", 0])

    coordinator._engine.observe_position.assert_called_once_with(12, 1, 0)
    coordinator._dispatch.assert_not_called()


def test_server_shutdown_marks_connection_disconnected(monkeypatch) -> None:
    hass = SimpleNamespace()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
        lambda *_args: SimpleNamespace(source="core", server_info=None),
    )
    coordinator = BilresaCoordinator(hass, "ws://matter/ws")
    coordinator.connected = True
    coordinator._set_connected = Mock()

    coordinator._on_event("server_shutdown", None)

    coordinator._set_connected.assert_called_once_with(False)


def test_raw_gesture_hint_is_dispatched_only_internally(monkeypatch) -> None:
    hass = SimpleNamespace()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
        lambda *_args: SimpleNamespace(source="core", server_info=None),
    )
    dispatch = Mock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.async_dispatcher_send", dispatch
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.decode_event",
        lambda *_args: {
            "role": "button",
            "channel": 2,
            "endpoint_id": 3,
            "event_type": "short_release",
        },
    )
    coordinator = BilresaCoordinator(hass, "ws://matter/ws")
    coordinator._engine.process = Mock(return_value=None)
    coordinator.wheels[12] = BilresaWheel(
        node_id=12,
        name="Test wheel",
        product_name="BILRESA scroll wheel",
        serial=None,
        endpoints={},
    )

    coordinator._handle_node_event(
        {"node_id": 12, "cluster_id": CLUSTER_SWITCH, "endpoint_id": 3}
    )

    dispatch.assert_called_once_with(
        hass, signal_raw_button(12, 2), "button", "short_release", 3
    )


def test_button_binding_keys_separate_endpoints_and_multiple_devices(
    monkeypatch,
) -> None:
    hass = SimpleNamespace()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
        lambda *_args: SimpleNamespace(source="core", server_info=None),
    )
    created = []

    class FakeBinding:
        def __init__(self, _hass, data) -> None:
            self.node_id = int(data[CONF_NODE_ID])
            self.channel = int(data[CONF_CHANNEL]) if CONF_CHANNEL in data else None
            self.endpoint_id = (
                int(data[CONF_ENDPOINT]) if CONF_ENDPOINT in data else None
            )
            kind = CONF_CHANNEL if self.channel is not None else CONF_ENDPOINT
            address = self.channel if self.channel is not None else self.endpoint_id
            self.binding_key = (self.node_id, kind, address)
            self.test_action = Mock()
            created.append(self)

        def async_attach(self):
            return Mock()

    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.LightBinding", FakeBinding
    )
    entry = SimpleNamespace(
        subentries={
            "button-a-1": SimpleNamespace(
                subentry_type=SUBENTRY_BINDING,
                data={CONF_NODE_ID: "101", CONF_ENDPOINT: "1"},
            ),
            "button-a-2": SimpleNamespace(
                subentry_type=SUBENTRY_BINDING,
                data={CONF_NODE_ID: "101", CONF_ENDPOINT: "2"},
            ),
            "button-b-1": SimpleNamespace(
                subentry_type=SUBENTRY_BINDING,
                data={CONF_NODE_ID: "202", CONF_ENDPOINT: "1"},
            ),
            "wheel": SimpleNamespace(
                subentry_type=SUBENTRY_BINDING,
                data={CONF_NODE_ID: "303", CONF_CHANNEL: "1"},
            ),
        }
    )
    coordinator = BilresaCoordinator(hass, "ws://matter/ws")

    coordinator.async_setup_bindings(entry)

    assert set(coordinator._bindings) == {
        (101, CONF_ENDPOINT, 1),
        (101, CONF_ENDPOINT, 2),
        (202, CONF_ENDPOINT, 1),
        (303, CONF_CHANNEL, 1),
    }
    action = WheelAction(
        node_id=202,
        wheel_name="Second dual button",
        channel=None,
        endpoint_id=1,
        type=ACTION_PRESS,
        presses=1,
    )
    assert coordinator.test_binding_action(action) is True
    created[2].test_action.assert_called_once_with(action)
    assert all(
        binding.test_action.call_count == (1 if binding is created[2] else 0)
        for binding in created
    )


def test_public_event_includes_registry_device_id_without_breaking_payload(
    monkeypatch,
) -> None:
    bus = SimpleNamespace(async_fire=Mock())
    hass = SimpleNamespace(bus=bus)
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
        lambda *_args: SimpleNamespace(source="core", server_info=None),
    )
    registry = SimpleNamespace(
        async_get_device=Mock(return_value=SimpleNamespace(id="device-123"))
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.dr.async_get",
        lambda _hass: registry,
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.coordinator.async_dispatcher_send", Mock()
    )
    coordinator = BilresaCoordinator(hass, "ws://matter/ws")
    action = WheelAction(
        node_id=12,
        wheel_name="Test wheel",
        channel=2,
        endpoint_id=3,
        type=ACTION_PRESS,
        presses=1,
    )

    coordinator._dispatch(action)

    registry.async_get_device.assert_called_once_with(identifiers={(DOMAIN, "12")})
    event_type, event_data = bus.async_fire.call_args.args
    assert event_type == EVENT_BILRESA
    assert event_data["device_id"] == "device-123"
    assert event_data["node_id"] == 12
    assert event_data["presses"] == 1
