"""Protocol-contract tests for matterjs-server 1.1.7 / schema 11."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.ikea_bilresa.matter_ws import (
    MatterWSIncompatible,
    validate_server_info,
)
from custom_components.ikea_bilresa.model import decode_event, parse_node

FIXTURE = Path(__file__).parent / "fixtures" / "matterjs_1_1_7.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_accepts_matterjs_schema_11_server_info() -> None:
    server_info = _fixture()["server_info"]
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
