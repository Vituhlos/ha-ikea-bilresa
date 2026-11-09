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
- Current product scope is private/home use. Brand assets, default-HACS
  store publication, and stable releases are deferred until the integration is
  finished, automated tests are comprehensive, and hardware validation passes.
  A maintainer-authorized GitHub pre-release may be published earlier solely as
  a clearly labelled hardware-test candidate when installation is needed to
  perform the checks. Its release notes must list pending hardware checks, the
  matching checklist items must remain open, and it must never be described as
  stable or hardware-validated before results are recorded in
  `PROJECT_STATUS.md` and `docs/HARDWARE_TEST.md`.
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
- Do not merge a pull request until its required CI checks and the automated
  reviews requested on it (Codex and CodeRabbit) have finished and their
  findings are answered. A skipped review is not a passed review: where CI or a
  review does not run on a pull request's base branch, run the gates locally,
  trigger the review by comment, and say so in the pull request.
- User documentation is the short `README.md` / `README.cs.md` and the guides in
  `docs/en` and `docs/cs`. Change both languages in one commit and keep the
  README an overview; `tests/test_docs.py` checks links, structure and length.
- A release changes the version in `manifest.json`, `CHANGELOG.md` (section and
  link reference), both READMEs and `PROJECT_STATUS.md` in one commit.
  `tests/test_version_consistency.py` fails when they disagree.

## Working method (cost and quality)

- **One command for the gates:** `python tools/check.py` runs format, lint, mypy
  (two known errors), the frontend tests and pytest in parallel and prints one
  line each, with the tail only for a gate that failed. `--fast` skips pytest.
  Use it instead of running the five tools by hand and reading their output.
- **One command for a pull request:** `python tools/pr_watch.py <number>` waits
  for the checks and the review bots and prints the checks and only the review
  comments left on the newest commit. Read nothing else from the PR.
- **Read less, not more:** `PROJECT_STATUS.md`, the changelog and the archive are
  long. Search them (`grep`) for the item at hand; read a file in ranges; do not
  re-read a file you just wrote.
- **Use a stronger model for what is expensive to get wrong or to read:**
  research that needs many files or external sources (HA core, the frontend, a
  third-party project), and an independent review of a finished change before it
  is pushed, in a read-only agent with a self-contained prompt that names the
  files and the question and asks for a short, cited answer. Check its claims
  against the code before relying on them. Keep the writing of code in the main
  session, one writer per set of files.
- **Review before the bots do:** a read-only review of the diff for races,
  stored-data compatibility, strings in both languages and missing tests saves a
  round of fix commits; the bots still run.
- **Record what was decided, not what was said:** the tracker item and
  `PROJECT_STATUS.md` hold decisions, results and what was not verified.

## Replying on GitHub (issues and pull requests)

**Every comment an agent posts on GitHub says that an agent wrote it,** not only
replies to contributors: also short ones (a review request such as `@codex review`,
"fixed in <commit>", a status note, an answer to a review thread) and review
replies. They are posted under the owner's account, so without the line they look
as if the owner wrote them. A short comment gets the short form:

```
*🤖 Agent-assisted: this comment was written by Claude, an AI assistant working on this repository with the maintainer (@Vituhlos), who asked for it.*
```

at the top and the signature line at the end. A comment that is a bot command (for
example `@codex review`) starts with the command and carries the lines after it, so
the bot still recognises it. Name the agent that really wrote it. Pull request
descriptions end with `🤖 Generated with [<agent>](<its link>)` naming the agent that
wrote them (`[Claude Code](https://claude.com/claude-code)` for Claude Code).

The rest of this section is about a longer reply to a contributor.
Short comments on our own pull requests (review requests, "fixed in <commit>",
status notes) need no approval of the text. A reply to a contributor is posted only
after the owner approved the text. It is written like the ones to @amodig on PR #5 and #23:

- **Language and voice:** English (the project's language), warm and specific.
  Answer what this person wrote, thank them for something concrete, and say what
  was done with their idea instead of a generic "thanks for the report".
- **First line, in italics:** `*🤖 Agent-assisted: this reply was written by
  Claude, an AI assistant working on this repository with the maintainer
  (@Vituhlos), who read and approved it before it was posted.*` Then a greeting
  with the person's `@login` and a 👋.
- **Bold lead sentences** that carry the point of each paragraph (what was
  decided, what works today, what is coming). A reader who only reads the bold
  text still gets the answer.
- **A few emoji as markers, not decoration:** ✅ already out, 🔜 coming,
  🧪 what has not been verified, ❓ questions, 🙏 a thank-you or a request for
  help. At most one or two per paragraph.
- **A small table** when it shows a mapping (helper to actions, gesture to
  action, variable to colour); `<details>` for side material such as setup steps.
- **Always say what is not verified,** in its own paragraph. Never claim hardware
  success from tests or CI. Name versions exactly and say whether a feature is in
  a release, a pre-release or only on the development line. Promise no dates.
- **Numbered questions** at the end, specific to the person (which device, what
  behaviour they expect), so the reply is useful to answer.
- **Last line:** `🤖 Agent-authored: <agent>, model ` followed by the model id in
  backticks. Name the agent that really wrote the reply (Claude Code, Codex) in
  this line and in the first one, not always Claude.
- Keep the issue open until the change is in a release (or the reporter
  confirms). Do not paste anything from the owner's own Home Assistant (names,
  ids, paths): documents and replies stay generic.

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
