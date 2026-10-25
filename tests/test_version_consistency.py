"""Static guard: the release version is stated consistently across the repository.

A release touches the manifest, the changelog, both READMEs and the handoff
file. Doing that by hand has drifted before, so this reads them and fails when
they disagree. It checks facts that can be derived, not prose:

* the manifest version is a well-formed release version and has a changelog
  section and a changelog link reference;
* both READMEs name the same latest stable release as the changelog;
* the handoff file names that stable release on its "latest stable" line.

It does not require the manifest to be the newest changelog section: a branch
may carry a release candidate's changelog entry while the manifest still holds
an earlier version until the release commit.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).parent.parent
MANIFEST = ROOT / "custom_components" / "ikea_bilresa" / "manifest.json"
CHANGELOG = ROOT / "CHANGELOG.md"
README_EN = ROOT / "README.md"
README_CS = ROOT / "README.cs.md"
STATUS = ROOT / "PROJECT_STATUS.md"

RELEASE = re.compile(r"^\d+\.\d+\.\d+(-rc\.\d+)?$")
STABLE = re.compile(r"^\d+\.\d+\.\d+$")
SECTION = re.compile(r"^## \[(?P<version>[^\]]+)\]", re.MULTILINE)


def _manifest_version() -> str:
    return str(json.loads(MANIFEST.read_text(encoding="utf-8"))["version"])


def _changelog_versions() -> list[str]:
    """Released section headings, newest first as written; `Unreleased` excluded."""
    text = CHANGELOG.read_text(encoding="utf-8")
    return [
        match["version"]
        for match in SECTION.finditer(text)
        if match["version"] != "Unreleased"
    ]


def _latest_stable() -> str:
    stable = [version for version in _changelog_versions() if STABLE.fullmatch(version)]
    assert stable, "CHANGELOG.md has no stable release section"
    return max(stable, key=lambda version: tuple(int(p) for p in version.split(".")))


def test_manifest_version_is_a_release_version() -> None:
    assert RELEASE.fullmatch(_manifest_version()), _manifest_version()


def test_manifest_version_has_a_changelog_section() -> None:
    version = _manifest_version()
    assert version in _changelog_versions(), (
        f"CHANGELOG.md has no '## [{version}]' section for the manifest version"
    )


def test_manifest_version_has_a_changelog_link() -> None:
    version = _manifest_version()
    text = CHANGELOG.read_text(encoding="utf-8")
    escaped = re.escape(version)
    pattern = re.compile(
        rf"^\[{escaped}\]: \S*/(compare|releases/tag)/\S*v{escaped}\s*$",
        re.MULTILINE,
    )
    assert pattern.search(text), f"CHANGELOG.md has no link reference for [{version}]"


def test_changelog_has_no_duplicate_sections() -> None:
    versions = _changelog_versions()
    assert len(versions) == len(set(versions))


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        (README_EN, "latest stable release"),
        (README_CS, "poslední stabilní vydání"),
    ],
)
def test_readme_names_the_latest_stable_release(path: Path, marker: str) -> None:
    stable = _latest_stable()
    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines() if marker in line
    ]
    assert lines, f"{path.name} has no line containing '{marker}'"
    assert any(f"v{stable}" in line for line in lines), (
        f"{path.name} does not name v{stable} as the latest stable release"
    )


def test_status_names_the_latest_stable_release() -> None:
    stable = _latest_stable()
    lines = [
        line
        for line in STATUS.read_text(encoding="utf-8").splitlines()
        if "latest stable" in line.lower()
    ]
    assert lines, "PROJECT_STATUS.md has no 'latest stable' line"
    assert any(f"v{stable}" in line for line in lines), (
        f"PROJECT_STATUS.md does not name v{stable} on its 'latest stable' line"
    )
