"""The project's subagent definitions in ``.claude/agents`` stay valid and read-only.

Claude Code reads the header of each file. An unquoted ``: `` inside the description
makes that header invalid YAML, which a strict reader rejects, so the checks are
mechanical: the header parses, the required keys are there, the tools are the
read-only three and each agent keeps its model. The project allows exactly these
two agents; adding one means changing this test on purpose.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

AGENTS = Path(__file__).resolve().parent.parent / ".claude" / "agents"
READ_ONLY_TOOLS = {"Read", "Grep", "Glob"}
EXPECTED = {
    "repo-scout": {"model": "haiku", "effort": "low", "maxTurns": 8},
    "critical-reviewer": {"model": "opus", "effort": "high", "maxTurns": 12},
}


def load_header(path: Path) -> dict:
    """Parse the YAML header of an agent file; fail with the file name."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert text.startswith("---\n"), f"{path.name}: no YAML header"
    header, closed, body = text[4:].partition("\n---\n")
    assert closed and body.strip(), f"{path.name}: header not closed or body empty"
    data = yaml.safe_load(header)
    assert isinstance(data, dict), f"{path.name}: header is not a mapping"
    return data


def test_only_the_expected_agents_exist() -> None:
    assert {path.stem for path in AGENTS.glob("*.md")} == set(EXPECTED)


@pytest.mark.parametrize("path", sorted(AGENTS.glob("*.md")), ids=lambda p: p.stem)
def test_agent_header_is_valid_and_read_only(path: Path) -> None:
    data = load_header(path)

    assert data["name"] == path.stem
    assert isinstance(data["description"], str) and data["description"].strip()
    assert {tool.strip() for tool in str(data["tools"]).split(",")} == READ_ONLY_TOOLS
    assert data["omitClaudeMd"] is True
    for key, value in EXPECTED.get(path.stem, {}).items():
        assert data[key] == value, f"{path.name}: {key} must be {value!r}"
