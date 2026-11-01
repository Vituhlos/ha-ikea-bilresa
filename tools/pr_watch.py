"""Wait for a pull request's checks and reviews, then print only what matters.

    python tools/pr_watch.py 34            # wait up to 15 minutes
    python tools/pr_watch.py 34 --now      # print the current state, do not wait

Prints one line per check, then every review comment a bot left on the newest
commit (the ones already answered are marked resolved by the reviewer and are
left out), trimmed to its first lines. It needs the GitHub CLI (``gh``) signed
in. Required checks are waited for; the review bots are waited for a little
longer, because they finish last and CodeRabbit often does not run at all.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time

REVIEWERS = ("devin", "codex", "chatgpt-codex", "coderabbit")
SLOW = ("devin", "coderabbit")  # reviewers that finish after the real checks
POLL_SECONDS = 15
BODY_LINES = 6


def _gh(*args: str) -> str:
    done = subprocess.run(
        ["gh", *args], capture_output=True, text=True, encoding="utf-8", check=False
    )
    return done.stdout


def _checks(number: str) -> list[dict]:
    raw = _gh("pr", "checks", number, "--json", "name,bucket")
    return json.loads(raw) if raw.strip() else []


def _is_slow(name: str) -> bool:
    return any(word in name.lower() for word in SLOW)


def _settled(checks: list[dict], wait_for_reviewers: bool) -> bool:
    if not checks:
        return False
    return all(
        check["bucket"] != "pending"
        for check in checks
        if wait_for_reviewers or not _is_slow(check["name"])
    )


def _newest_commit_time(number: str) -> str:
    raw = _gh("pr", "view", number, "--json", "commits")
    commits = json.loads(raw)["commits"]
    return max(commit["committedDate"] for commit in commits)


def _clean(body: str) -> str:
    body = re.sub(r"(?s)<details>.*?</details>", "", body)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"<[^>]+>", "", body)
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    return " ".join(lines[:BODY_LINES])[:600]


def _comments(number: str, since: str) -> list[str]:
    repo = _gh(
        "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"
    ).strip()
    raw = _gh("api", f"repos/{repo}/pulls/{number}/comments", "--paginate")
    found = []
    for comment in json.loads(raw) if raw.strip() else []:
        login = comment["user"]["login"].lower()
        if not any(word in login for word in REVIEWERS):
            continue
        if comment["created_at"] < since or "Resolved" in comment["body"][:40]:
            continue
        line = comment.get("line") or comment.get("original_line") or "?"
        found.append(f"{login} {comment['path']}:{line}\n    {_clean(comment['body'])}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("number")
    parser.add_argument("--now", action="store_true", help="do not wait")
    parser.add_argument("--minutes", type=int, default=15)
    args = parser.parse_args()

    deadline = time.monotonic() + args.minutes * 60
    checks = _checks(args.number)
    while not args.now and time.monotonic() < deadline:
        # Required checks first; the reviewers get the rest of the time.
        if _settled(checks, wait_for_reviewers=True):
            break
        time.sleep(POLL_SECONDS)
        checks = _checks(args.number)

    for check in sorted(checks, key=lambda item: item["name"]):
        print(f"{check['bucket']:<8} {check['name']}")
    since = _newest_commit_time(args.number)
    comments = _comments(args.number, since)
    print(f"\n{len(comments)} open review comment(s) on the newest commit")
    for comment in comments:
        print(f"- {comment}")
    failed = any(check["bucket"] == "fail" for check in checks)
    return 1 if failed or comments else 0


if __name__ == "__main__":
    sys.exit(main())
