"""Unit tests for BILRESA node parsing and event decoding."""

from __future__ import annotations

from custom_components.ikea_bilresa.const import (
    ROLE_BUTTON,
    ROLE_SCROLL_DOWN,
    ROLE_SCROLL_UP,
    VARIANT_DUAL_BUTTON,
    VARIANT_WHEEL,
)
from custom_components.ikea_bilresa.model import (
    BilresaWheel,
    SwitchEndpoint,
    decode_event,
    parse_node,
    parse_taglist,
)

# Descriptor TagList entries use TLV field numbers as string keys:
#   "1" = NamespaceID, "2" = Tag, "3" = Label
UP_TAGS = [{"1": 8, "2": 6, "3": "1"}, {"1": 67, "2": 3}]
DOWN_TAGS = [{"1": 8, "2": 6, "3": "1"}, {"1": 67, "2": 4}]
BUTTON_TAGS = [{"1": 8, "2": 6, "3": "1"}, {"1": 67, "2": 8, "3": "button"}]

# The dual button (E2489) exposes two button endpoints with no numeric channel
# label and no up/down switch tags. This shape is what distinguishes it from a
# wheel; the fixture matches a real node observed via Home Assistant, not the
# code's assumptions. MultiPressMax is 2 (single/double only) on this device.
DUAL_BUTTON_TAGS = [{"1": 67, "2": 8}]


def _dual_button_node() -> dict:
    return {
        "node_id": 15,
        "attributes": {
            "0/40/3": "BILRESA dual button",
            "0/29/3": [1, 2],
            "1/59/65532": 30,
            "1/59/2": 2,  # Switch.MultiPressMax
            "1/29/4": DUAL_BUTTON_TAGS,
            "2/59/65532": 30,
            "2/59/2": 2,
            "2/29/4": DUAL_BUTTON_TAGS,
        },
    }


def _node() -> dict:
    return {
        "node_id": 12,
        "attributes": {
            "0/40/3": "BILRESA scroll wheel",
            "0/40/15": "SER123",
            "0/29/3": [1, 2, 3],
            "1/59/65532": 22,
            "1/29/4": UP_TAGS,
            "2/59/65532": 22,
            "2/29/4": DOWN_TAGS,
            "3/59/65532": 30,
            "3/29/4": BUTTON_TAGS,
        },
    }


def test_parse_taglist_roles() -> None:
    assert parse_taglist(UP_TAGS) == (1, ROLE_SCROLL_UP)
    assert parse_taglist(DOWN_TAGS) == (1, ROLE_SCROLL_DOWN)
    assert parse_taglist(BUTTON_TAGS) == (1, ROLE_BUTTON)


def test_parse_node_discovers_channels() -> None:
    wheel = parse_node(_node())
    assert wheel is not None
    assert wheel.node_id == 12
    assert wheel.serial == "SER123"
    assert wheel.endpoints[1].role == ROLE_SCROLL_UP
    assert wheel.endpoints[2].role == ROLE_SCROLL_DOWN
    assert wheel.endpoints[3].role == ROLE_BUTTON
    assert {e.channel for e in wheel.endpoints.values()} == {1}


def test_parse_node_rejects_non_bilresa() -> None:
    node = _node()
    node["attributes"]["0/40/3"] = "Some Other Remote"
    assert parse_node(node) is None


def test_wheel_variant_is_wheel_when_rotary_endpoints_present() -> None:
    wheel = parse_node(_node())
    assert wheel is not None
    assert wheel.variant == VARIANT_WHEEL
    assert wheel.is_dual_button is False


def test_parse_node_discovers_dual_button() -> None:
    device = parse_node(_dual_button_node())
    assert device is not None
    assert device.node_id == 15
    # Both endpoints are buttons; neither carries a channel label.
    assert device.endpoints[1].role == ROLE_BUTTON
    assert device.endpoints[2].role == ROLE_BUTTON
    assert {e.channel for e in device.endpoints.values()} == {None}


def test_dual_button_variant_from_endpoint_shape() -> None:
    device = parse_node(_dual_button_node())
    assert device is not None
    assert device.variant == VARIANT_DUAL_BUTTON
    assert device.is_dual_button is True


def test_parse_node_reads_multi_press_max() -> None:
    device = parse_node(_dual_button_node())
    assert device is not None
    assert device.endpoints[1].multi_press_max == 2
    assert device.endpoints[2].multi_press_max == 2
    # A wheel that does not report the attribute yields None, not a guess.
    wheel = parse_node(_node())
    assert wheel is not None
    assert wheel.endpoints[3].multi_press_max is None


def test_variant_never_disagrees_with_endpoints() -> None:
    # variant is derived, not stored, so a hand-built button-only device is a
    # dual button even though the class name is historical.
    device = BilresaWheel(
        node_id=15,
        name="Buttons",
        product_name="BILRESA dual button",
        serial=None,
        endpoints={
            1: SwitchEndpoint(1, None, ROLE_BUTTON),
            2: SwitchEndpoint(2, None, ROLE_BUTTON),
        },
    )
    assert device.is_dual_button is True


def test_decode_event_maps_ongoing_count() -> None:
    wheel = BilresaWheel(
        node_id=12,
        name="Test",
        product_name="BILRESA scroll wheel",
        serial="SER123",
        endpoints={1: SwitchEndpoint(1, 1, ROLE_SCROLL_UP)},
    )
    node_event = {
        "node_id": 12,
        "endpoint_id": 1,
        "cluster_id": 0x003B,
        "event_id": 0x05,
        "data": {"newPosition": 1, "currentNumberOfPressesCounted": 4},
    }
    decoded = decode_event(wheel, node_event)
    assert decoded is not None
    assert decoded["role"] == ROLE_SCROLL_UP
    assert decoded["event_type"] == "multi_press_ongoing"
    assert decoded["count"] == 4


def test_decode_event_ignores_other_clusters() -> None:
    wheel = BilresaWheel(
        node_id=12,
        name="Test",
        product_name="BILRESA scroll wheel",
        serial=None,
        endpoints={1: SwitchEndpoint(1, 1, ROLE_SCROLL_UP)},
    )
    assert (
        decode_event(wheel, {"endpoint_id": 1, "cluster_id": 6, "event_id": 0}) is None
    )
