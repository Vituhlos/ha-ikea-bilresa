"""The developer tools must not report a red gate as green."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))

import check  # noqa: E402
import pr_watch  # noqa: E402

LEGACY = (
    "custom_components/ikea_bilresa/legacy_triggers.py:68: error: Generator has "
    'incompatible item type "str | UndefinedType"; expected "str"  [misc]'
)
LINK = (
    "custom_components/ikea_bilresa/device_link.py:256: error: Argument 1 to "
    '"MatterDeviceLink" has incompatible type "X"; expected "Y"  [arg-type]'
)
NEW = "custom_components/ikea_bilresa/binding.py:10: error: Something new  [misc]"


def test_mypy_is_green_only_for_the_known_errors() -> None:
    known = f"{LEGACY}\n{LINK}\nFound 2 errors in 2 files"
    assert check._summary("mypy", known, 1)[0]
    assert check._summary("mypy", "Success: no issues found", 0)[0]
    # One fewer is fine; a new error is not, even when the count stays the same.
    assert check._summary("mypy", f"{LEGACY}\nFound 1 error", 1)[0]
    swapped = f"{LEGACY}\n{NEW}\nFound 2 errors in 2 files"
    assert check._summary("mypy", swapped, 1)[0] is False
    # mypy that crashed prints its summary and exits 2.
    assert check._summary("mypy", f"{LEGACY}\nFound 1 error", 2)[0] is False


def test_a_failing_gate_is_never_green() -> None:
    assert check._summary("pytest", "1 failed, 5 passed", 1)[0] is False
    assert check._summary("pytest", "6 passed in 1s", 0) == (True, "6 passed in 1s")
    assert check._summary("node", "ℹ pass 3\nℹ fail 1", 1)[0] is False


def test_a_missing_program_is_a_red_gate_not_a_traceback() -> None:
    name, ok, summary, _output, _seconds = check._run(
        ("tool", ["this-program-does-not-exist-anywhere"])
    )

    assert (name, ok) == ("tool", False)
    assert "cannot run" in summary


def test_every_documented_gate_runs() -> None:
    names = [name for name, _command in check._gates(fast=False)]

    for expected in ("json", "compile", "syntax", "diff", "format", "lint", "mypy"):
        assert expected in names
    assert "pytest" in names
    assert "pytest" not in [n for n, _c in check._gates(fast=True)]


def _thread(body: str, *, resolved: bool = False, login: str = "devin-ai-bot") -> dict:
    return {
        "isResolved": resolved,
        "path": "a.py",
        "line": 3,
        "comments": {"nodes": [{"author": {"login": login}, "body": body}]},
    }


def test_a_thread_stays_open_until_resolved_or_answered() -> None:
    answered = _thread("🔴 **A bug**")
    answered["comments"]["nodes"].append(
        {"author": {"login": "devin-ai-bot"}, "body": "✅ **Resolved**: fixed"}
    )
    threads = [
        _thread("🔴 **Open finding**"),
        _thread("fixed already", resolved=True),
        answered,
        _thread("**Minor** x\n\nAddressed in commit abc", login="coderabbitai[bot]"),
        _thread("a human's remark", login="someone"),
    ]

    opened = pr_watch._open_threads(threads)

    assert len(opened) == 1
    assert "Open finding" in opened[0]


def test_older_findings_count_and_html_is_dropped() -> None:
    body = (
        "<!-- id -->\n🔴 **A bug**\n<details><summary>x</summary>long</details>\nText"
    )

    assert pr_watch._clean(body) == "🔴 **A bug** Text"


def test_the_exit_status_says_whether_the_pull_request_is_ready() -> None:
    passed = [{"name": "Unit tests", "bucket": "pass"}]
    everyone = {"devin", "codex", "coderabbit"}

    assert pr_watch._verdict(passed, 0, everyone) == 0
    assert pr_watch._verdict(passed, 1, everyone) == 1
    assert pr_watch._verdict([], 0, everyone) == 1  # nothing ran: not verified
    pending = [*passed, {"name": "Devin Review", "bucket": "pending"}]
    assert pr_watch._verdict(pending, 0, everyone) == 1
    failed = [{"name": "Lint", "bucket": "fail"}]
    assert pr_watch._verdict(failed, 0, everyone) == 1
    # A review bot that never showed up is not a passed review.
    assert pr_watch._verdict(passed, 0, {"devin", "codex"}) == 2


def test_waiting_ends_only_when_every_check_has_stopped() -> None:
    running = [
        {"name": "Unit tests", "bucket": "pass"},
        {"name": "x", "bucket": "pending"},
    ]

    assert not pr_watch._finished(running)
    assert not pr_watch._finished([])
    assert pr_watch._finished([{"name": "Unit tests", "bucket": "pass"}])


def test_a_look_alike_error_is_not_excused_by_a_known_one() -> None:
    twice = f"{LEGACY}\n{LEGACY}\n{LINK}\nFound 3 errors in 2 files"

    assert check._summary("mypy", twice, 1)[0] is False


def test_a_cancelled_job_never_passes() -> None:
    everyone = {"devin", "codex", "coderabbit"}
    cancelled = [{"name": "Unit tests", "bucket": "cancel"}]
    skipped = [
        {"name": "Unit tests", "bucket": "pass"},
        {"name": "CodeRabbit", "bucket": "skipping"},
    ]

    assert pr_watch._verdict(cancelled, 0, everyone) == 1
    assert pr_watch._verdict(skipped, 0, everyone) == 0


def test_waiting_goes_on_for_a_bot_that_has_not_reviewed_yet() -> None:
    done = [{"name": "Unit tests", "bucket": "pass"}]
    skipped = [*done, {"name": "CodeRabbit", "bucket": "skipping"}]

    assert pr_watch._awaited(done, {"devin"}) == {"codex", "coderabbit"}
    # CI itself says CodeRabbit will not review: no point in waiting for it.
    assert pr_watch._awaited(skipped, {"devin", "codex"}) == set()


def test_only_a_review_of_the_current_head_counts(monkeypatch) -> None:
    def page(reviews: list, after_cursor: str | None, more: bool) -> str:
        return json.dumps(
            {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "headRefOid": "new",
                            "reviews": {"nodes": reviews},
                            "reviewThreads": {
                                "pageInfo": {"hasNextPage": more, "endCursor": "c"},
                                "nodes": [_thread(f"finding {after_cursor}")],
                            },
                        }
                    }
                }
            }
        )

    def review(login: str, oid: str) -> dict:
        return {"author": {"login": login}, "commit": {"oid": oid}}

    calls: list[tuple] = []

    def fake_gh(*args: str) -> str:
        calls.append(args)
        if args[0] == "repo":
            return "o/r"
        first = not any("after=" in part for part in args)
        if first:
            old = [review("devin-ai-bot", "old"), review("codex", "new")]
            return page(old, "1", True)
        return page([review("coderabbitai[bot]", "new")], "2", False)

    monkeypatch.setattr(pr_watch, "_gh", fake_gh)

    threads, seen = pr_watch._review_data("5")

    assert seen == {"codex", "coderabbit"}  # devin reviewed the old commit only
    assert len(threads) == 2  # the second page was read as well


def test_an_inline_comment_on_the_head_counts_as_a_review(monkeypatch) -> None:
    thread = _thread("finding", login="coderabbitai[bot]")
    thread["comments"]["nodes"][0]["originalCommit"] = {"oid": "new"}
    stale = _thread("old finding", login="codex")
    stale["comments"]["nodes"][0]["originalCommit"] = {"oid": "old"}
    pull = {
        "headRefOid": "new",
        "reviews": {"nodes": []},
        "reviewThreads": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [thread, stale],
        },
    }

    def fake_gh(*args: str) -> str:
        if args[0] == "repo":
            return "o/r"
        return json.dumps({"data": {"repository": {"pullRequest": pull}}})

    monkeypatch.setattr(pr_watch, "_gh", fake_gh)

    assert pr_watch._review_data("5")[1] == {"coderabbit"}
