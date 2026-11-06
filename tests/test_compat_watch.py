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


def test_an_older_or_pre_release_version_is_not_news() -> None:
    assert compat_watch.news({**TESTED, "home_assistant": "2026.10.4"}, TESTED) == {}
    assert compat_watch.news({**TESTED, "matter_server_app": "9.4.0b1"}, TESTED) == {}
    assert compat_watch.news({**TESTED, "matterjs_server": "v1.5.6"}, TESTED) == {
        "matterjs_server": ("v1.5.5", "v1.5.6")
    }


class _Gh:
    """Stands in for the GitHub CLI and remembers what was asked of it."""

    def __init__(self, issue: dict | None) -> None:
        self.issue = issue
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args: str) -> str:
        self.calls.append(args)
        if args[:2] == ("issue", "list"):
            return json.dumps([self.issue] if self.issue else [])
        return ""

    def verbs(self) -> list[str]:
        return [call[1] for call in self.calls if call[0] == "issue"]


def _run(monkeypatch, found: dict[str, str], issue: dict | None) -> _Gh:
    gh = _Gh(issue)
    monkeypatch.setattr(compat_watch, "_gh", gh)
    monkeypatch.setattr(compat_watch, "latest", lambda: found)
    monkeypatch.setattr(sys, "argv", ["compat_watch.py"])
    monkeypatch.delenv("COMPAT_NOTIFY", raising=False)
    assert compat_watch.main() == 0
    return gh


def _open_issue(found: dict[str, str]) -> dict:
    return {
        "number": 7,
        "title": compat_watch.TITLE,
        "body": compat_watch.body(found, TESTED),
    }


def test_the_issue_is_created_once_and_closed_when_all_is_checked(monkeypatch) -> None:
    newer = {**TESTED, "home_assistant": "2026.12.0"}

    assert _run(monkeypatch, newer, None).verbs() == ["list", "create"]
    assert _run(monkeypatch, dict(TESTED), _open_issue(newer)).verbs() == [
        "list",
        "close",
    ]
    assert _run(monkeypatch, dict(TESTED), None).verbs() == ["list"]


def test_an_unchanged_issue_is_left_alone_even_with_a_ticked_task(monkeypatch) -> None:
    newer = {**TESTED, "home_assistant": "2026.12.0"}
    issue = _open_issue(newer)
    issue["body"] = issue["body"].replace("- [ ] read the", "- [x] read the", 1)

    assert _run(monkeypatch, newer, issue).verbs() == ["list"]


def test_a_further_release_edits_the_issue_and_comments(monkeypatch) -> None:
    older = {**TESTED, "home_assistant": "2026.12.0"}
    newest = {**TESTED, "home_assistant": "2026.12.1"}

    assert _run(monkeypatch, newest, _open_issue(older)).verbs() == [
        "list",
        "comment",
        "edit",
    ]


def test_a_version_that_is_not_news_does_not_rewrite_the_issue(monkeypatch) -> None:
    newer = {**TESTED, "home_assistant": "2026.12.0"}
    issue = _open_issue(newer)
    # Another source moves to a pre-release: still nothing new, so nothing to say.
    pre = {**newer, "matter_server_app": "9.4.0b1"}

    assert _run(monkeypatch, pre, issue).verbs() == ["list"]


def test_a_new_baseline_below_the_latest_release_rewrites_the_issue(
    monkeypatch, tmp_path
) -> None:
    newest = {**TESTED, "home_assistant": "2026.12.1"}
    issue = {
        "number": 7,
        "title": compat_watch.TITLE,
        "body": compat_watch.body(newest, TESTED),
    }
    # The baseline moved up to 2026.12.0, but 2026.12.1 is still newer: the table
    # shows the tested version, so the issue must show the new one.
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps({**TESTED, "home_assistant": "2026.12.0"}), encoding="utf-8"
    )
    monkeypatch.setattr(compat_watch, "BASELINE", baseline)

    assert _run(monkeypatch, newest, issue).verbs() == ["list", "comment", "edit"]
