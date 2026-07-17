"""Tests for the Home Assistant-native BILRESA event surface."""

from types import SimpleNamespace
from unittest.mock import Mock

from homeassistant.components.event import EventDeviceClass

from custom_components.ikea_bilresa.event import BilresaChannelEvent


def test_channel_event_uses_button_device_class() -> None:
    entity = BilresaChannelEvent(
        Mock(),
        SimpleNamespace(node_id=101, name="Test wheel"),
        1,
        {("matter", "test")},
        linked_to_matter=True,
    )

    assert entity.device_class is EventDeviceClass.BUTTON
