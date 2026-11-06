"""Tell the maintainers when Home Assistant or the Matter Server has a new release.

    python tools/compat_watch.py              # compare, and open/update/close the issue
    python tools/compat_watch.py --dry-run    # compare and print, touch nothing

It compares the newest stable releases of Home Assistant Core, the Matter Server
app (add-on) and matterjs-server with the versions the integration was last
checked against (``.github/compat-baseline.json``) and keeps one open issue,
"Compatibility watch", while any of them is newer. It only reports: it changes
no code, installs nothing and decides nothing. After checking a new version
(docs/MATTERJS_COMPATIBILITY.md has the list), update the baseline in the same
pull request that records the result; the next run then closes the issue.

Runs weekly from ``.github/workflows/compat-watch.yml`` with the repository's own
token (``issues: write``) and needs the GitHub CLI (``gh``).
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / ".github" / "compat-baseline.json"
TITLE = "Compatibility watch"

# key in the baseline -> (what it is, where its releases are)
SOURCES = {
    "home_assistant": (
        "Home Assistant Core",
        "https://github.com/home-assistant/core/releases",
    ),
    "matter_server_app": (
        "Matter Server app (add-on)",
        "https://github.com/home-assistant/addons/blob/master/matter_server/CHANGELOG.md",
    ),
    "matterjs_server": (
        "matterjs-server",
        "https://github.com/matter-js/matterjs-server/releases",
    ),
}


def _gh(*args: str) -> str:
    done = subprocess.run(
        ["gh", *args], capture_output=True, text=True, encoding="utf-8", check=False
    )
    if done.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout


def parse_app_version(config_yaml: str) -> str:
    """The ``version:`` of an app's config.yaml."""
    match = re.search(r"^version:\s*[\"']?([^\"'\s]+)", config_yaml, flags=re.M)
    if not match:
        raise ValueError("no version in the app's config.yaml")
    return match.group(1)


def latest() -> dict[str, str]:
    """The newest stable release of each source."""
    config = _gh(
        "api",
        "repos/home-assistant/addons/contents/matter_server/config.yaml",
        "--jq",
        ".content",
    )
    return {
        "home_assistant": _gh(
            "api", "repos/home-assistant/core/releases/latest", "--jq", ".tag_name"
        ).strip(),
        "matter_server_app": parse_app_version(
            base64.b64decode(config).decode("utf-8")
        ),
        "matterjs_server": _gh(
            "api",
            "repos/matter-js/matterjs-server/releases/latest",
            "--jq",
            ".tag_name",
        ).strip(),
    }


def news(found: dict[str, str], tested: dict[str, str]) -> dict[str, tuple[str, str]]:
    """What differs from the tested versions: key -> (tested, found)."""
    return {
        key: (tested.get(key, "not recorded"), version)
        for key, version in found.items()
        if version != tested.get(key)
    }


def body(found: dict[str, str], tested: dict[str, str]) -> str:
    """The text of the issue."""
    changed = news(found, tested)
    lines = [
        "A release is newer than the version this integration was last checked "
        "against. Written by `tools/compat_watch.py`; it only reports.",
        "",
        "| Component | Tested | Newest stable | |",
        "|---|---|---|---|",
    ]
    for key, (name, link) in SOURCES.items():
        mark = "**new**" if key in changed else "same"
        lines.append(
            f"| [{name}]({link}) | {tested.get(key, 'not recorded')} "
            f"| {found.get(key, '?')} | {mark} |"
        )
    lines += [
        "",
        "Check, in this order (`docs/MATTERJS_COMPATIBILITY.md` has the detail):",
        "",
        "- [ ] read the release notes and the developer blog for breaking changes "
        "to what the integration uses (config entries and subentries, the script "
        "helper, `panel_custom` and the frontend loaders, the Matter client of the "
        "core integration and its events)",
        "- [ ] the server's WebSocket schema bounds still admit client schema 11",
        "- [ ] `python tools/check.py` against the new Home Assistant "
        "(the weekly CI job already runs the newest pre-release)",
        "- [ ] on a real instance: every press and the rotation fire once, the "
        "panel and its action editor load, the integration stays installed and "
        "updatable",
        "- [ ] record the result in `docs/MATTERJS_COMPATIBILITY.md` and update "
        "`.github/compat-baseline.json` in the same pull request",
    ]
    return "\n".join(lines) + "\n"


def _existing_issue() -> str | None:
    raw = _gh(
        "issue",
        "list",
        "--state",
        "open",
        "--search",
        f'"{TITLE}" in:title',
        "--json",
        "number,title",
    )
    for issue in json.loads(raw or "[]"):
        if issue["title"] == TITLE:
            return str(issue["number"])
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tested = json.loads(BASELINE.read_text(encoding="utf-8"))
    found = latest()
    changed = news(found, tested)
    text = body(found, tested)
    print(text if changed else "Nothing is newer than the tested versions.")
    if args.dry_run:
        return 0
    number = _existing_issue()
    if changed and number:
        _gh("issue", "edit", number, "--body", text)
    elif changed:
        _gh("issue", "create", "--title", TITLE, "--body", text)
    elif number:
        _gh("issue", "close", number, "--comment", "Everything is checked: closing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
