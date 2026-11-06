"""Wait for a pull request's checks and reviews, then print only what matters.

    python tools/pr_watch.py 34            # wait up to 15 minutes
    python tools/pr_watch.py 34 --now      # print the current state, do not wait

Prints one line per check, which review bots have been seen, and every review
thread of a bot that is still open, trimmed to its first lines. It needs the
GitHub CLI (``gh``) signed in.

A thread is open until it is resolved on GitHub or one of its comments says the
finding was dealt with (Devin writes "Resolved", CodeRabbit "Addressed"). Threads
of older commits count: a finding stays a finding after the next push.

Reviews of an older commit do not count as seen.

Exit status: 0 when every check passed, no thread is open and Devin, Codex and
CodeRabbit have all reviewed; 1 when a check failed or is still pending (or none
ran) or a thread is open; 2 when that is all fine but a review bot was not seen
(AGENTS.md: a skipped review is not a passed review).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time

# (name to show, words that identify the bot's login)
REVIEWERS = (
    ("devin", ("devin",)),
    ("codex", ("codex",)),
    ("coderabbit", ("coderabbit",)),
)
POLL_SECONDS = 15
BODY_LINES = 6
THREADS = """
query($owner: String!, $name: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      headRefOid
      reviews(last: 100) { nodes { author { login } commit { oid } } }
      reviewThreads(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          isResolved
          path
          line
          comments(first: 50) { nodes { author { login } body originalCommit { oid } } }
        }
      }
    }
  }
}
"""


def _gh(*args: str) -> str:
    done = subprocess.run(
        ["gh", *args], capture_output=True, text=True, encoding="utf-8", check=False
    )
    return done.stdout


def _checks(number: str) -> list[dict]:
    raw = _gh("pr", "checks", number, "--json", "name,bucket")
    return json.loads(raw) if raw.strip() else []


def _finished(checks: list[dict]) -> bool:
    """Every check, the review bots' included, has stopped running."""
    return bool(checks) and all(check["bucket"] != "pending" for check in checks)


def _clean(body: str) -> str:
    body = re.sub(r"(?s)<details>.*?</details>", "", body)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"<[^>]+>", "", body)
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    return " ".join(lines[:BODY_LINES])[:600]


def _reviewer(login: str) -> str | None:
    lowered = login.lower()
    for name, words in REVIEWERS:
        if any(word in lowered for word in words):
            return name
    return None


def _answered(comment: dict) -> bool:
    body = comment["body"]
    return "Resolved**" in body[:60] or "Addressed in commit" in body


def _open_threads(threads: list[dict]) -> list[str]:
    """The bots' threads nobody has resolved or answered, ready to print."""
    found = []
    for thread in threads:
        comments = thread["comments"]["nodes"]
        if thread["isResolved"] or not comments:
            continue
        first = comments[0]
        bot = _reviewer((first.get("author") or {}).get("login", ""))
        if bot is None or any(_answered(comment) for comment in comments):
            continue
        place = f"{thread['path']}:{thread.get('line') or '?'}"
        found.append(f"{bot} {place}\n    {_clean(first['body'])}")
    return found


def _review_data(number: str) -> tuple[list[dict], set[str]]:
    """Every review thread, and which bots have reviewed the current head."""
    repo = _gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")
    owner, name = repo.strip().split("/")
    threads: list[dict] = []
    seen: set[str] = set()
    after = None
    while True:
        command = [
            "api",
            "graphql",
            "-f",
            f"query={THREADS}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
            "-F",
            f"number={number}",
        ]
        if after:
            command += ["-F", f"after={after}"]
        pull = json.loads(_gh(*command))["data"]["repository"]["pullRequest"]
        threads += pull["reviewThreads"]["nodes"]
        # A review of an older commit says nothing about the code now pushed.
        seen |= {
            bot
            for review in pull["reviews"]["nodes"]
            if (review.get("commit") or {}).get("oid") == pull["headRefOid"]
            if (bot := _reviewer((review.get("author") or {}).get("login", "")))
        }
        # An inline comment can come without a review: it counts when it was
        # made on the current head.
        seen |= {
            bot
            for thread in pull["reviewThreads"]["nodes"]
            for comment in thread["comments"]["nodes"]
            if (comment.get("originalCommit") or {}).get("oid") == pull["headRefOid"]
            if (bot := _reviewer((comment.get("author") or {}).get("login", "")))
        }
        page = pull["reviewThreads"]["pageInfo"]
        if not page["hasNextPage"]:
            return threads, seen
        after = page["endCursor"]


def _awaited(checks: list[dict], seen: set[str]) -> set[str]:
    """The bots still worth waiting for: not yet seen and not skipped by CI."""
    skipped = {
        name
        for name, words in REVIEWERS
        for check in checks
        if check["bucket"] == "skipping"
        and any(word in check["name"].lower() for word in words)
    }
    return {name for name, _words in REVIEWERS} - seen - skipped


def _verdict(checks: list[dict], open_count: int, seen: set[str]) -> int:
    # Only a pass or a skip is fine: a cancelled job never passed.
    if not checks or any(c["bucket"] not in ("pass", "skipping") for c in checks):
        return 1
    if open_count:
        return 1
    return 0 if {name for name, _words in REVIEWERS} <= seen else 2


def main() -> int:
    # Review comments carry emoji; a Windows console would refuse them.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("number")
    parser.add_argument("--now", action="store_true", help="do not wait")
    parser.add_argument("--minutes", type=int, default=15)
    args = parser.parse_args()

    deadline = time.monotonic() + args.minutes * 60
    checks = _checks(args.number)
    threads, seen = _review_data(args.number)
    # Waits for the checks and for every bot to review the head: CI may finish
    # before a bot has said anything.
    while (
        not args.now
        and not (_finished(checks) and not _awaited(checks, seen))
        and time.monotonic() < deadline
    ):
        time.sleep(POLL_SECONDS)
        checks = _checks(args.number)
        threads, seen = _review_data(args.number)

    for check in sorted(checks, key=lambda item: item["name"]):
        print(f"{check['bucket']:<8} {check['name']}")
    if not checks:
        print("no checks have run (yet)")
    opened = _open_threads(threads)
    missing = sorted({name for name, _words in REVIEWERS} - seen)
    print(f"\nreviewed by: {', '.join(sorted(seen)) or 'nobody'}")
    if missing:
        print(f"NOT SEEN: {', '.join(missing)} (a skipped review is not a passed one)")
    print(f"{len(opened)} open review thread(s)")
    for thread in opened:
        print(f"- {thread}")
    return _verdict(checks, len(opened), seen)


if __name__ == "__main__":
    sys.exit(main())
