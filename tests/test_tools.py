"""The developer tools must not report a red gate as green."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))

import check  # noqa: E402
import pr_watch  # noqa: E402


def test_mypy_is_green_only_while_the_known_errors_do_not_grow() -> None:
    known = check.KNOWN_MYPY_ERRORS
    assert check._summary("mypy", f"Found {known} errors in 2 files", 1)[0]
    assert check._summary("mypy", f"Found {known + 1} errors in 3 files", 1)[0] is False
    assert check._summary("mypy", "Success: no issues found", 0)[0]


def test_a_failing_gate_is_never_green() -> None:
    assert check._summary("pytest", "1 failed, 5 passed", 1)[0] is False
    assert check._summary("pytest", "6 passed in 1s", 0) == (True, "6 passed in 1s")
    assert check._summary("node", "ℹ pass 3\nℹ fail 1", 1)[0] is False


def test_review_bots_are_waited_for_after_the_real_checks() -> None:
    checks = [
        {"name": "Unit tests", "bucket": "pass"},
        {"name": "Devin Review", "bucket": "pending"},
    ]
    assert pr_watch._settled(checks, wait_for_reviewers=False)
    assert not pr_watch._settled(checks, wait_for_reviewers=True)
    assert not pr_watch._settled([], wait_for_reviewers=False)


def test_a_review_comment_is_reduced_to_its_words() -> None:
    body = (
        "<!-- id -->\n🔴 **A bug**\n<details><summary>x</summary>long</details>\nText"
    )

    assert pr_watch._clean(body) == "🔴 **A bug** Text"
