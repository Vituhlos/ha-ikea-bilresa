"""Tests for the Home Assistant-native BILRESA event surface."""

from types import SimpleNamespace
from unittest.mock import Mock

from homeassistant.components.event import EventDeviceClass

from custom_components.ikea_bilresa.const import (
    ACTION_PRESS,
    ACTION_RELEASE,
    ET_DOUBLE_PRESS,
    ET_HOLD,
    ET_PRESS,
    ET_RELEASE,
    ET_TRIPLE_PRESS,
    button_event_types,
)
from custom_components.ikea_bilresa.engine import WheelAction
from custom_components.ikea_bilresa.event import BilresaButtonEvent, BilresaChannelEvent


def test_channel_event_uses_button_device_class() -> None:
    entity = BilresaChannelEvent(
        Mock(),
        SimpleNamespace(node_id=101, name="Test wheel"),
        1,
        {("matter", "test")},
        linked_to_matter=True,
    )

    assert entity.device_class is EventDeviceClass.BUTTON


def test_button_event_types_respect_multi_press_max() -> None:
    # The dual button (max 2) must not advertise a triple press it cannot fire.
    assert button_event_types(2) == [ET_PRESS, ET_DOUBLE_PRESS, ET_HOLD, ET_RELEASE]
    assert ET_TRIPLE_PRESS in button_event_types(3)
    # Unknown max defaults to the dual button's shape (single + double).
    assert ET_TRIPLE_PRESS not in button_event_types(None)


def _button(endpoint_id: int, *, multi_press_max: int | None = 2) -> BilresaButtonEvent:
    return BilresaButtonEvent(
        Mock(),
        SimpleNamespace(node_id=15, name="Buttons"),
        endpoint_id,
        endpoint_id,
        multi_press_max,
        {("matter", "test")},
        linked_to_matter=True,
    )


def test_button_event_identity_and_types() -> None:
    entity = _button(2)
    assert entity.device_class is EventDeviceClass.BUTTON
    assert entity.unique_id == "15_ep2"
    assert entity.name == "Button 2"
    assert entity.icon == "bilresa:dual-button"
    assert ET_TRIPLE_PRESS not in entity.event_types


def _action(endpoint_id: int, action_type: str, presses: int = 0) -> WheelAction:
    return WheelAction(
        node_id=15,
        wheel_name="Buttons",
        channel=None,
        endpoint_id=endpoint_id,
        type=action_type,
        presses=presses,
    )


def test_button_event_only_handles_its_own_endpoint() -> None:
    entity = _button(1)
    entity._trigger_event = Mock()
    entity.async_write_ha_state = Mock()

    # Both buttons share the channel=None signal; a sibling endpoint is ignored.
    entity._handle_action(_action(2, ACTION_PRESS, presses=1))
    entity._trigger_event.assert_not_called()

    entity._handle_action(_action(1, ACTION_PRESS, presses=1))
    entity._trigger_event.assert_called_once_with(ET_PRESS, {"presses": 1})


def test_button_event_drops_unadvertised_press_count() -> None:
    # A triple press on a max-2 device would raise on an unknown event type;
    # it is dropped instead. (The firmware should not send it, but be safe.)
    entity = _button(1, multi_press_max=2)
    entity._trigger_event = Mock()
    entity.async_write_ha_state = Mock()

    entity._handle_action(_action(1, ACTION_PRESS, presses=3))
    entity._trigger_event.assert_not_called()


def test_button_event_maps_hold_and_release() -> None:
    entity = _button(1)
    entity._trigger_event = Mock()
    entity.async_write_ha_state = Mock()

    entity._handle_action(_action(1, "hold"))
    entity._trigger_event.assert_called_once_with(ET_HOLD)

    entity._trigger_event.reset_mock()
    entity._handle_action(_action(1, ACTION_RELEASE))
    entity._trigger_event.assert_called_once_with(ET_RELEASE)


def test_button_release_exposes_observed_duration_when_available() -> None:
    entity = _button(1)
    entity._trigger_event = Mock()
    entity.async_write_ha_state = Mock()
    action = _action(1, ACTION_RELEASE)
    action.observed_duration_ms = 2250

    entity._handle_action(action)

    entity._trigger_event.assert_called_once_with(
        ET_RELEASE, {"observed_duration_ms": 2250}
    )
