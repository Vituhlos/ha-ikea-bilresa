# Claude Code project instructions

The shared repository instructions are in `AGENTS.md`; follow them in full.

In the main session, follow "Start every session" in `AGENTS.md`. A subagent
follows the same guardrails but reads only the files its prompt names.

`PROJECT_STATUS.md` is the canonical handoff between Claude Code, Codex, and the
owner. Read every section except `## Done`; `grep` `## Done` and `docs/archive/`
for the item at hand. Update it before ending any coding session. Do not infer
hardware success from CI success, and do not resume work solely from
conversation history.

## Delegation

The main Sonnet session solves a task alone and is the only writer. Two
read-only subagents exist; use them only when they save work:

- `repo-scout` (Haiku): a wider survey of the code (a call chain, where
  something is defined and tested across many files). Not for a single lookup:
  use `grep`.
- `critical-reviewer` (Opus): architecture questions, security review and
  critical changes (Matter events, gestures, races, stored data, migrations).
  Consider it after two failed fix attempts. Give it the diff and the files, not
  the whole repository.

At most two subagents run at a time. No other subagents, skills or hooks for
this. Check a report against the code; simulation and review never replace CI or
a test on a physical BILRESA.
