"""Protocol-contract tests for matterjs-server schemas 11 and 12."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.ikea_bilresa.matter_ws import (
    MatterWSClient,
    MatterWSIncompatible,
    validate_server_info,
)
from custom_components.ikea_bilresa.model import decode_event, parse_node

FIXTURE = Path(__file__).parent / "fixtures" / "matterjs_1_1_7.json"
FIXTURE_1_2_6 = Path(__file__).parent / "fixtures" / "matterjs_1_2_6.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_accepts_matterjs_schema_11_server_info() -> None:
    server_info = _fixture()["server_info"]
    assert validate_server_info(server_info) is server_info


def test_accepts_matter_server_9_1_schema_12_with_schema_11_minimum() -> None:
    server_info = json.loads(FIXTURE_1_2_6.read_text(encoding="utf-8"))["server_info"]
    assert validate_server_info(server_info) is server_info


@pytest.mark.parametrize(
    "server_info",
    [
        {},
        {"sdk_version": "old", "schema_version": 10, "min_supported_schema_version": 9},
        {
            "sdk_version": "new",
            "schema_version": 12,
            "min_supported_schema_version": 12,
        },
    ],
)
def test_rejects_incompatible_server_info(server_info: dict) -> None:
    with pytest.raises(MatterWSIncompatible):
        validate_server_info(server_info)


def test_decodes_sanitized_matterjs_bilresa_fixture() -> None:
    fixture = _fixture()
    wheel = parse_node(fixture["node"])
    assert wheel is not None
    decoded = decode_event(wheel, fixture["ongoing_event"]["data"])
    assert decoded is not None
    assert decoded["event_type"] == "multi_press_ongoing"
    assert decoded["count"] == 8


def test_schema_12_events_are_forwarded_without_protocol_rewriting() -> None:
    fixture = json.loads(FIXTURE_1_2_6.read_text(encoding="utf-8"))
    received = []
    client = MatterWSClient(
        "ws://matter/ws",
        session=None,  # type: ignore[arg-type]
        on_event=lambda event, data: received.append((event, data)),
    )

    client._handle_message(fixture["node_updated"], {})
    client._handle_message(fixture["attribute_updated"], {})

    assert received == [
        ("node_updated", fixture["node_updated"]["data"]),
        ("attribute_updated", fixture["attribute_updated"]["data"]),
    ]
