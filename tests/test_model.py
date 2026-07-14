"""Unit tests for BILRESA node parsing and event decoding."""

from __future__ import annotations

from custom_components.ikea_bilresa.const import (
    ROLE_BUTTON,
    ROLE_SCROLL_DOWN,
    ROLE_SCROLL_UP,
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
