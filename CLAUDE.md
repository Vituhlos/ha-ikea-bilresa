# Claude Code project instructions

The shared repository instructions are in `AGENTS.md`; follow them in full.

In the main session, follow "Start every session" in `AGENTS.md`. A subagent
follows the same guardrails but reads only the files its prompt names.

`PROJECT_STATUS.md` is the canonical handoff between Claude Code, Codex, and the
owner. Read every section except `## Done`; `grep` `## Done` and `docs/archive/`
for the item at hand. Update it before ending any coding session. Do not infer
hardware success from CI success, and do not resume work solely from
conversation history.
