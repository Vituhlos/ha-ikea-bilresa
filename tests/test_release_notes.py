"""The release tool must refuse a tag that does not match the repository."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import release_notes  # noqa: E402

CHANGELOG = """\
# Changelog

## [Unreleased]

### Fixed
- Something not released yet.

## [0.6.2-rc.2] - 2026-10-25

Candidate text.

### Hardware validation pending
- Check the thing.

### Added
- A thing.

## [0.6.1] - 2026-09-01

- Older.

[0.6.1]: https://example.invalid/0.6.1
"""


def _repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str, log: str
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"version": version}), encoding="utf-8")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(log, encoding="utf-8")
    monkeypatch.setattr(release_notes, "MANIFEST", manifest)
    monkeypatch.setattr(release_notes, "CHANGELOG", changelog)


def test_version_of_accepts_only_version_tags() -> None:
    assert release_notes.version_of("v1.2.3") == "1.2.3"
    assert release_notes.version_of("v0.7.0-rc.5") == "0.7.0-rc.5"
    for bad in ("1.2.3", "v1.2", "release-1", "v1.2.3-", "v1.0.0-.rc", "v1.0.0-rc."):
        with pytest.raises(ValueError):
            release_notes.version_of(bad)


def test_section_is_bounded_by_the_next_heading() -> None:
    body = release_notes.section(CHANGELOG, "0.6.2-rc.2")
    assert body.startswith("Candidate text.")
    assert "- A thing." in body
    assert "Older" not in body
    assert "Something not released" not in body


def test_last_section_stops_at_link_references() -> None:
    body = release_notes.section(CHANGELOG, "0.6.1")
    assert body == "- Older.\n"


def test_a_reference_inside_the_notes_is_kept() -> None:
    text = (
        "## [1.0.0] - 2026-01-01\n\nSee below.\n\n[the guide]: here.\n\n"
        "More text.\n\n[1.0.0]: https://example.invalid\n"
    )

    body = release_notes.section(text, "1.0.0")

    assert "[the guide]: here." in body
    assert "More text." in body
    assert "example.invalid" not in body


def test_missing_or_empty_section_is_an_error() -> None:
    with pytest.raises(ValueError, match="no section"):
        release_notes.section(CHANGELOG, "9.9.9")
    with pytest.raises(ValueError, match="empty"):
        release_notes.section("## [1.0.0] - 2026-01-01\n\n## [0.9.0]\n- x\n", "1.0.0")


def test_prerelease_is_a_tag_with_a_suffix() -> None:
    assert release_notes.is_prerelease("v0.7.0-rc.5")
    assert not release_notes.is_prerelease("v0.7.0")


def test_check_requires_tag_manifest_and_changelog_to_agree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, monkeypatch, "0.6.2-rc.2", CHANGELOG)

    assert release_notes.check("v0.6.2-rc.2") == "0.6.2-rc.2"
    with pytest.raises(ValueError, match="manifest.json says"):
        release_notes.check("v0.6.1")

    _repo(tmp_path, monkeypatch, "0.7.0", CHANGELOG)
    with pytest.raises(ValueError, match="no section"):
        release_notes.check("v0.7.0")


def test_a_pre_release_must_say_which_hardware_checks_are_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = "## [1.0.0-rc.1] - 2026-01-01\n\n- Generic text.\n"
    _repo(tmp_path, monkeypatch, "1.0.0-rc.1", log)

    with pytest.raises(ValueError, match="hardware"):
        release_notes.check("v1.0.0-rc.1")


def test_the_real_repository_is_consistent_with_its_own_version() -> None:
    version = json.loads(release_notes.MANIFEST.read_text(encoding="utf-8"))["version"]
    release_notes.check(f"v{version}")
