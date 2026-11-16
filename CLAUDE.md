# Claude Code project instructions

The shared repository instructions are in `AGENTS.md`; follow them in full.

In the main session, follow "Start every session" in `AGENTS.md`. A subagent
follows the same guardrails; it does not run that list, and reads the files its
prompt names plus the files it finds with `Grep` and `Glob` inside the scope the
prompt sets.

`PROJECT_STATUS.md` is the canonical handoff between Claude Code, Codex, and the
owner. Read every section except `## Done`; `grep` `## Done` and `docs/archive/`
for the item at hand. Update it before ending any coding session. Do not infer
hardware success from CI success, and do not resume work solely from
conversation history.

## Delegation

The main Sonnet session solves a task alone and is the only writer. Two
read-only subagents exist; use them only when they save work:

- `repo-scout` (Haiku), optional: a wider survey of the code (a call chain,
  where something is defined and tested across many files). Not for a single
  lookup (use `grep`) and not for an ordinary mid-size survey, unless it clearly
  pays off.
- `critical-reviewer` (Opus): truly critical changes and questions (Matter
  events, gesture semantics, races, stored data and migrations, security,
  architecture). Consider it after two failed fix attempts. Give it the diff and
  the files, not the whole repository.

At most two subagents run at a time. No other subagents, skills or hooks for
this. Give a subagent a narrow task and ask for `path:line` citations. When it
returns, do not repeat its survey or re-read whole files it read: verify its
important conclusions by reading the exact cited ranges, then answer. For a
critical change verify everything that is needed, with no cap on the checks.
Simulation and review never replace CI or a test on a physical BILRESA.
