"""Check a release tag and write its notes from the changelog.

    python tools/release_notes.py check v0.7.0-rc.5       # all three agree
    python tools/release_notes.py notes v0.7.0-rc.5       # the changelog section
    python tools/release_notes.py prerelease v0.7.0-rc.5  # true or false

Used by ``.github/workflows/release.yml`` when a version tag is pushed, so a
release is never published with notes that are missing or that belong to
another version.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "custom_components" / "ikea_bilresa" / "manifest.json"
CHANGELOG = ROOT / "CHANGELOG.md"


def version_of(tag: str) -> str:
    """``v0.7.0-rc.5`` -> ``0.7.0-rc.5``."""
    if not re.fullmatch(r"v\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?", tag):
        raise ValueError(f"{tag!r} is not a version tag like v1.2.3 or v1.2.3-rc.1")
    return tag[1:]


def section(changelog: str, version: str) -> str:
    """The body of ``## [version] - date``, up to the next version heading."""
    heading = re.compile(rf"^## \[{re.escape(version)}\][^\n]*\n", flags=re.M)
    found = heading.search(changelog)
    if not found:
        raise ValueError(f"CHANGELOG.md has no section for {version}")
    rest = changelog[found.end() :]
    following = re.search(r"^## \[|^\[[^\]]+\]: ", rest, flags=re.M)
    body = rest[: following.start()] if following else rest
    if not body.strip():
        raise ValueError(f"the CHANGELOG.md section for {version} is empty")
    return body.strip() + "\n"


def check(tag: str) -> str:
    """Raise unless the tag, the manifest and the changelog describe one version."""
    version = version_of(tag)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]
    if manifest != version:
        raise ValueError(f"the tag is {version} but manifest.json says {manifest}")
    section(CHANGELOG.read_text(encoding="utf-8"), version)
    return version


def is_prerelease(tag: str) -> bool:
    return "-" in version_of(tag)


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("check", "notes", "prerelease"):
        print(__doc__)
        return 2
    command, tag = argv[1], argv[2]
    try:
        if command == "check":
            print(f"{check(tag)} is consistent")
        elif command == "prerelease":
            print("true" if is_prerelease(tag) else "false")
        else:
            text = section(CHANGELOG.read_text(encoding="utf-8"), version_of(tag))
            sys.stdout.buffer.write(text.encode("utf-8"))
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
