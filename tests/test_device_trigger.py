"""Device-trigger listing and attachment for wheels and the dual button."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from custom_components.ikea_bilresa import device_trigger
from custom_components.ikea_bilresa.const import (
    ACTION_PRESS,
    DOMAIN,
    ET_DOUBLE_PRESS,
    ET_HOLD,
    ET_PRESS,
    ET_RELEASE,
    ET_ROTATE_UP,
    ET_TRIPLE_PRESS,
    ROLE_BUTTON,
    ROLE_SCROLL_UP,
)
from custom_components.ikea_bilresa.model import BilresaWheel, SwitchEndpoint


def _dual_button(node_id: int = 15) -> BilresaWheel:
    return BilresaWheel(
        node_id=node_id,
        name="Buttons",
        product_name="BILRESA dual button",
        serial=None,
        endpoints={
            1: SwitchEndpoint(1, None, ROLE_BUTTON, multi_press_max=2),
            2: SwitchEndpoint(2, None, ROLE_BUTTON, multi_press_max=2),
        },
    )


def _wheel(node_id: int = 12) -> BilresaWheel:
    return BilresaWheel(
        node_id=node_id,
        name="Wheel",
        product_name="BILRESA scroll wheel",
        serial=None,
        endpoints={
            1: SwitchEndpoint(1, 1, ROLE_SCROLL_UP),
            3: SwitchEndpoint(3, 1, ROLE_BUTTON, multi_press_max=3),
        },
    )


def _hass(wheel: BilresaWheel, monkeypatch) -> tuple[SimpleNamespace, str]:
    device = SimpleNamespace(identifiers={(DOMAIN, str(wheel.node_id))})
    registry = MagicMock()
    registry.async_get.return_value = device
    monkeypatch.setattr(device_trigger.dr, "async_get", lambda _hass: registry)
    coordinator = SimpleNamespace(wheels={wheel.node_id: wheel})
    entry = SimpleNamespace(runtime_data=coordinator)
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda _domain: [entry])
    )
    return hass, "dev"


def test_button_endpoint_maps_index_to_endpoint() -> None:
    wheel = _dual_button()
    assert device_trigger._button_endpoint(wheel, 1) == 1
    assert device_trigger._button_endpoint(wheel, 2) == 2
    assert device_trigger._button_endpoint(wheel, 3) is None
    assert device_trigger._button_endpoint(None, 1) is None


@pytest.mark.asyncio
async def test_dual_button_offers_button_triggers(monkeypatch) -> None:
    hass, device_id = _hass(_dual_button(), monkeypatch)

    triggers = await device_trigger.async_get_triggers(hass, device_id)

    subtypes = {t["subtype"] for t in triggers}
    types = {t["type"] for t in triggers}
    assert subtypes == {"button_1", "button_2"}
    # No rotation and no triple press on a max-2 device.
    assert ET_ROTATE_UP not in types
    assert ET_TRIPLE_PRESS not in types
    assert {ET_PRESS, ET_DOUBLE_PRESS, ET_HOLD, ET_RELEASE} <= types


@pytest.mark.asyncio
async def test_wheel_still_offers_channel_triggers(monkeypatch) -> None:
    hass, device_id = _hass(_wheel(), monkeypatch)

    triggers = await device_trigger.async_get_triggers(hass, device_id)

    subtypes = {t["subtype"] for t in triggers}
    assert subtypes == {"channel_1", "channel_2", "channel_3"}
    assert ET_ROTATE_UP in {t["type"] for t in triggers}


@pytest.mark.asyncio
async def test_attach_button_trigger_filters_by_endpoint(monkeypatch) -> None:
    hass, device_id = _hass(_dual_button(), monkeypatch)
    captured: dict = {}

    monkeypatch.setattr(device_trigger.event_trigger, "TRIGGER_SCHEMA", lambda cfg: cfg)

    async def _fake_attach(_hass, config, _action, _info, *, platform_type):
        captured["config"] = config
        return lambda: None

    monkeypatch.setattr(
        device_trigger.event_trigger, "async_attach_trigger", _fake_attach
    )

    config = {
        "platform": "device",
        "domain": DOMAIN,
        "device_id": device_id,
        "type": ET_DOUBLE_PRESS,
        "subtype": "button_2",
    }
    await device_trigger.async_attach_trigger(hass, config, None, None)

    event_data = captured["config"][device_trigger.event_trigger.CONF_EVENT_DATA]
    assert event_data["node_id"] == 15
    assert event_data["endpoint_id"] == 2  # button_2 -> endpoint 2, not a channel
    assert "channel" not in event_data
    assert event_data["type"] == ACTION_PRESS
    assert event_data["presses"] == 2
