"""The compatibility watch must notice a new release, and only then."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))

import compat_watch  # noqa: E402

TESTED = {
    "home_assistant": "2026.11.0",
    "matter_server_app": "9.3.0",
    "matterjs_server": "v1.5.5",
}


def test_the_baseline_names_every_source() -> None:
    baseline = json.loads(compat_watch.BASELINE.read_text(encoding="utf-8"))

    assert set(baseline) == set(compat_watch.SOURCES)


def test_nothing_is_reported_while_everything_is_the_tested_version() -> None:
    assert compat_watch.news(dict(TESTED), TESTED) == {}


def test_a_newer_release_is_reported_with_both_versions() -> None:
    found = {**TESTED, "home_assistant": "2026.12.0"}

    assert compat_watch.news(found, TESTED) == {
        "home_assistant": ("2026.11.0", "2026.12.0")
    }
    text = compat_watch.body(found, TESTED)
    assert "2026.12.0" in text and "**new**" in text
    assert text.count("**new**") == 1


def test_a_source_missing_from_the_baseline_counts_as_new() -> None:
    found = dict(TESTED)
    tested = {key: value for key, value in TESTED.items() if key != "matterjs_server"}

    assert compat_watch.news(found, tested) == {
        "matterjs_server": ("not recorded", "v1.5.5")
    }


def test_the_version_of_an_app_is_read_from_its_config() -> None:
    config = (
        'name: Matter Server\nslug: matter_server\nversion: "9.3.0"\narch:\n  - amd64\n'
    )

    assert compat_watch.parse_app_version(config) == "9.3.0"
    assert compat_watch.parse_app_version("version: 9.4.0b1\n") == "9.4.0b1"


def test_the_owner_is_told_through_the_environment(monkeypatch) -> None:
    monkeypatch.delenv("COMPAT_NOTIFY", raising=False)
    assert compat_watch.who_to_tell() is None
    monkeypatch.setenv("COMPAT_NOTIFY", "someone")
    assert compat_watch.who_to_tell() == "someone"
