# Agent instructions

These instructions apply to the entire repository and to every coding agent.

## Start every session

1. Read `PROJECT_STATUS.md` completely. It is the canonical source of truth for
   current work, validation state, decisions, and backlog.
2. Read `docs/DEVELOPMENT.md` before changing code. For device-facing changes,
   also read `docs/DEVICE_REFERENCE.md`, `docs/MATTERJS_COMPATIBILITY.md`, and
   `docs/HARDWARE_TEST.md`.
3. Read `docs/ROADMAP.md` before selecting work from the `0.5.x` stabilization
   train. Work on one package at a time and preserve its validation gates.
4. Inspect `git status --short`, the current branch, the recent log, and the
   relevant diff. Preserve existing user/agent work.
5. Confirm whether the selected task is already implemented, only statically
   verified, CI-verified, or hardware-verified. Never collapse these states.

## Project guardrails

- This is specifically an IKEA BILRESA scroll-wheel integration over Matter.
  Do not change endpoint discovery, Matter event decoding, gesture semantics,
  or WebSocket protocol assumptions without evidence from device logs, the
  Matter specification, or verified BILRESA telemetry.
- Never claim hardware validation unless the result was observed on a physical
  BILRESA and recorded in `PROJECT_STATUS.md` and `docs/HARDWARE_TEST.md`.
- Keep all Matter access passive and read-only. Prefer the URL-matched core
  Matter client through its feature-detected `subscribe_events` API, and retain
  the dedicated passive WebSocket as the compatibility fallback. Do not issue
  Matter device-control commands.
- Current product scope is private/home use. Brand assets, the default HACS
  store, and other publication work are deferred until the integration is
  finished, automated tests are comprehensive, and hardware validation passes.
- Battery-low repairs are out of scope unless testing proves that core Matter
  does not already handle them.

## Change discipline

- Make one coherent change at a time. Avoid mixing refactors with behavior
  changes.
- Add or update tests for changed behavior when the test environment permits.
- Run the proportional verification gates from `docs/DEVELOPMENT.md`.
- Do not commit, push, tag, release, or open external pull requests unless the
  user explicitly requests it.
- Keep English and Czech user-facing strings/documentation aligned.
- Update `CHANGELOG.md` for user-visible behavior.

## Required handoff

Before ending a coding session, update `PROJECT_STATUS.md` in the same working
tree with:

- what changed and which files are involved;
- exact validation commands and results;
- what was not run and why;
- hardware validation status;
- known risks or assumptions;
- the single best next action.

Do not use chat history as the only record of unfinished work.
