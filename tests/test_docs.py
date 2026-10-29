"""The user documentation: every link works, and the two languages match.

A README is the first thing a user reads and the first thing to rot, so the checks
are mechanical: no link may point at a file or a heading that is not there, the
English and Czech guides must have the same files with the same structure, and
the README must stay a short overview that points at the guides.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parent.parent
README_EN = ROOT / "README.md"
README_CS = ROOT / "README.cs.md"
GUIDES_EN = ROOT / "docs" / "en"
GUIDES_CS = ROOT / "docs" / "cs"
DOC_INDEX = ROOT / "docs" / "README.md"

# The README is an overview that points at the guides; it must not grow back into
# the one long text it was split from.
README_MAX_LINES = 160

# A link destination: plain, with one level of parentheses in it, or in angle
# brackets, optionally followed by a title.
_LINK = re.compile(
    r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]"
    r"\(\s*(<[^>]+>|(?:[^()\s]|\([^()\s]*\))+)(?:\s+\"[^\"]*\")?\s*\)"
)
_HEADING = re.compile(r"^(#{1,6}) (.+?)\s*$")


def _documents() -> list[Path]:
    files = [README_EN, README_CS, DOC_INDEX]
    files += sorted(GUIDES_EN.glob("*.md")) + sorted(GUIDES_CS.glob("*.md"))
    return files


def _lines_outside_fences(path: Path) -> list[str]:
    lines: list[str] = []
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            lines.append(line)
    return lines


def _slug(title: str) -> str:
    """GitHub's anchor for a heading."""
    text = re.sub(r"[`*_]", "", title.strip().lower())
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def _headings(path: Path) -> list[tuple[int, str]]:
    found = []
    for line in _lines_outside_fences(path):
        match = _HEADING.match(line)
        if match:
            found.append((len(match.group(1)), match.group(2)))
    return found


def _anchors(path: Path) -> set[str]:
    seen: dict[str, int] = {}
    anchors: set[str] = set()
    for _level, title in _headings(path):
        slug = _slug(title)
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        anchors.add(slug if count == 0 else f"{slug}-{count}")
    return anchors


def _links(path: Path) -> list[str]:
    targets = []
    for line in _lines_outside_fences(path):
        targets += [t.strip("<>") for t in _LINK.findall(line)]
    return targets


@pytest.mark.parametrize("path", _documents(), ids=lambda p: str(p.relative_to(ROOT)))
def test_every_relative_link_and_anchor_resolves(path: Path) -> None:
    broken = []
    for target in _links(path):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        file_part, _, fragment = target.partition("#")
        destination = path if not file_part else (path.parent / file_part).resolve()
        if not destination.exists():
            broken.append(f"{target}: no such file")
            continue
        if (
            fragment
            and destination.suffix == ".md"
            and fragment.lower() not in _anchors(destination)
        ):
            broken.append(f"{target}: no such heading in {destination.name}")
    assert not broken, f"{path.relative_to(ROOT)} has broken links: {broken}"


def test_the_two_languages_have_the_same_guides() -> None:
    english = {p.name for p in GUIDES_EN.glob("*.md")}
    czech = {p.name for p in GUIDES_CS.glob("*.md")}

    assert english, "no English guides"
    assert english == czech


@pytest.mark.parametrize("name", sorted(p.name for p in GUIDES_EN.glob("*.md")))
def test_a_guide_has_the_same_structure_in_both_languages(name: str) -> None:
    english = [level for level, _title in _headings(GUIDES_EN / name)]
    czech = [level for level, _title in _headings(GUIDES_CS / name)]

    assert english == czech


def test_the_two_readmes_have_the_same_structure() -> None:
    english = [level for level, _title in _headings(README_EN)]
    czech = [level for level, _title in _headings(README_CS)]

    assert english == czech


@pytest.mark.parametrize("path", [README_EN, README_CS], ids=lambda p: p.name)
def test_the_readme_stays_an_overview(path: Path) -> None:
    assert len(path.read_text(encoding="utf-8").splitlines()) <= README_MAX_LINES


@pytest.mark.parametrize("path", [README_EN, README_CS], ids=lambda p: p.name)
def test_the_readme_points_at_every_guide(path: Path) -> None:
    language = "en" if path == README_EN else "cs"
    linked = {
        target.partition("#")[0]
        for target in _links(path)
        if target.startswith(f"docs/{language}/")
    }
    guides = {f"docs/{language}/{p.name}" for p in (GUIDES_EN).glob("*.md")}

    assert guides <= linked


def test_every_guide_links_back_and_to_its_twin() -> None:
    for name in sorted(p.name for p in GUIDES_EN.glob("*.md")):
        english = _links(GUIDES_EN / name)
        czech = _links(GUIDES_CS / name)
        assert "../../README.md" in english
        assert f"../cs/{name}" in english
        assert "../../README.cs.md" in czech
        assert f"../en/{name}" in czech


def test_the_docs_index_lists_every_guide() -> None:
    linked = {t.partition("#")[0] for t in _links(DOC_INDEX)}
    for language in ("en", "cs"):
        for guide in (ROOT / "docs" / language).glob("*.md"):
            assert f"{language}/{guide.name}" in linked


def test_the_link_pattern_reads_titles_and_parentheses() -> None:
    line = (
        "[a](plain.md) [b](page_(draft).md#x) [c](<with space.md>) "
        '[d](titled.md "A title") ![e](img.png)'
    )

    assert [t.strip("<>") for t in _LINK.findall(line)] == [
        "plain.md",
        "page_(draft).md#x",
        "with space.md",
        "titled.md",
        "img.png",
    ]
