"""Tests for the Home Assistant-native BILRESA event surface."""

from homeassistant.components.event import EventDeviceClass

from custom_components.ikea_bilresa.event import BilresaChannelEvent


def test_channel_event_uses_button_device_class() -> None:
    assert BilresaChannelEvent._attr_device_class is EventDeviceClass.BUTTON
