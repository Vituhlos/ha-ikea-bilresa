# Handoff entries written on `main`, 2026-11-06 to 2026-11-10

Moved here verbatim when `main` was merged into `agent/panel-0.6.1` (see `PROJECT_STATUS.md`,
section "Merged from `main`"). They describe the state at the time they were written, not the
current state.

## GitHub development automation — Phase 2A proposed (2026-11-10)

**Phase 1: complete.** PR [#68](https://github.com/Vituhlos/ha-ikea-bilresa/pull/68) was merged into main. Maintainer created and stopped an interactive Codespace after **543 Python tests and 47 Node tests passed**; Ruff and mypy (existing no-site-packages baseline) were clean. Both GitHub branch rulesets are **active**: main #26934594 and agent/panel-0.6.1 #26934615, with six source-pinned CI checks, required PRs and resolved conversations. Actual enforcement on a new post-activation PR remains to be observed. Physical device validation is separate.

**Phase 2A: proposed in [PR #69](https://github.com/Vituhlos/ha-ikea-bilresa/pull/69), branch chore/phase2a-agent-handoff-20261110; unmerged.** Owner-approved plan: docs/architecture/ai-development-automation.md. Detailed instructions and threat model: docs/architecture/phase2-agent-handoff.md.

### Changed files

- New owner-only GitHub Actions workflow .github/workflows/ai-issue-handoff.yml triggered by an **exact owner GitHub issue comment** (/agent prepare dev or /agent prepare main), and no manual dispatch. It reads an existing open issue and posts/updates a copyable, **owner-reviewed** task prompt to the same public issue.
- New pure JS handoff helper tools/agent_handoff.mjs and new tests/agent_handoff.test.mjs validate owner/branch controls, data-only issue handling, safe Markdown wrapping, bounded issue content, idempotent comments, and no AI execution.
- Extended the existing Frontend checks CI job with the handoff Node unit test; status context name unchanged. Updated roadmap and this project status.
- No OpenAI API calls, external services, GitHub App private keys, self-hosted runner, paid compute, automatic Codex task creation, auto-PR, auto-merge, releases or Home Assistant/device code are part of Phase 2A.

### Verification status

- Static: reviewed intended read-only/limited permissions; workflow runs only from exact owner issue comments, is pinned to trusted main and immutable action SHAs, checks both original and rerun actor, never persists checkout credentials, and never executes issue text. New Node unit tests have passed CI in earlier iterations; current final revision needs fresh verification.
- CI: [CI run 42806045021](https://github.com/Vituhlos/ha-ikea-bilresa/actions/runs/42806045021) **passed**, including the new Node handoff security tests and all six standard jobs. [CodeQL run 42806045255](https://github.com/Vituhlos/ha-ikea-bilresa/actions/runs/42806045255) **passed**. Early Codex/Sourcery/CodeRabbit reviews found security concerns. The workflow was changed to issue-comment-only, rerun authorization was tightened, pinned action SHAs and explicit main checkout were added, issue content is visibly quoted as untrusted data, and source changes are covered by tests. The newest revision still requires CI/review verification. After merge, the maintainer must test one real issue command because issue_comment workflows only run from the default branch.
- Hardware: **not applicable** (no runtime or Matter changes). No physical BILRESA testing or Home Assistant changes were performed.

### Known limitations and next action

- /agent prepare prepares a **manual handoff only**: the owner must paste the prompt into Codex Cloud and initiate a new task. It does **not** start a model or create PRs.
- A separate bilresa-assistant[bot] GitHub App identity and fully automatic issue→code→draft PR cannot be assumed free: openai/codex-action requires separately billed API credentials, and GitHub Copilot coding-agent access is separate from GitHub Pro. Explicit owner approval of any billing, GitHub App registration, secret storage and safe trigger design is required first.
- Existing Phase 1 stricter full-environment mypy differences (39 typing errors across four files) remain outside this infrastructure-only change.
- **Single best next action:** review Phase 2A [PR #69](https://github.com/Vituhlos/ha-ikea-bilresa/pull/69) and any outstanding AI review findings. The owner may then merge, test one /agent prepare dev comment on a suitable open issue, and manually hand the resulting prompt to Codex Cloud. Only after this path works should an autonomous backend and distinct bot identity be considered.

---

**Current snapshot — reviewed 2026-10-25**

- **Latest stable release:** [`v0.6.1`](https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.6.1), 2026-10-24: 0.6.0 plus the fix that makes the panel follow each user's language (PR #10). Before that, [`v0.6.0`](https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.6.0), 2026-10-18.
- **Issue #9 fix:** PR [#14](https://github.com/Vituhlos/ha-ikea-bilresa/pull/14) is merged. Its fixes are included in `v0.6.2-rc.1`; physical validation against the reporter's Zigbee2MQTT group is still pending.

- **Pre-releases:** [`v0.6.2-rc.1`](https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.6.2-rc.1) is published for Issue #9 hardware validation. PR [#16](https://github.com/Vituhlos/ha-ikea-bilresa/pull/16) has now merged the `short_release` bus event and Fast/Instant disabled-channel fix. This branch prepares `v0.6.2-rc.2`; it is not yet published. Both candidates are pre-releases, not stable.

- **Development line:** the redesigned panel published as the pre-releases [`v0.6.1-rc.1`](https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.6.1-rc.1) and [`v0.6.1-rc.2`](https://github.com/Vituhlos/ha-ikea-bilresa/releases/tag/v0.6.1-rc.2) is **not** in 0.6.1; it continues as 0.7.0 on branch `agent/panel-0.6.1`, which also carries the language fix. The owner saw rc.1 in his Home Assistant; rc.2 is deployed there but not yet confirmed by him.
- **Manifest/release distinction:** the stable release remains `v0.6.1`. A manifest version `0.6.2-rc.2` on its own is not a published release; it becomes available as a candidate only when the matching pre-release tag/release is published. Do not describe either RC as stable.

- **Minimum Home Assistant Core:** 2026.8.0. Upgrading from 0.5.x has breaking changes: old device triggers were removed, and first startup can remove duplicate BILRESA device-registry entries. Users should back up before upgrading and follow [CHANGELOG.md](CHANGELOG.md).
- **Validation:** the project has automated tests and some real-device/real-Home-Assistant checks, but the hardware checklist still contains open items. Do not claim that every gesture, device variant, firmware or configuration has been fully validated. See [docs/HARDWARE_TEST.md](docs/HARDWARE_TEST.md) for the authoritative checklist.

- **Repository tooling (2026-11-06, PR #42):** quiet CodeRabbit profile, weekly Dependabot, CodeQL, a stale workflow for issues labelled `needs-info`, `CODEOWNERS`, and a release workflow that publishes a GitHub **pre-release** from a `v*-*` tag with the notes of the matching `CHANGELOG.md` section (`tools/release_notes.py` refuses a tag that does not match `manifest.json`, a missing or empty section, or pre-release notes that do not name the pending hardware checks); a stable tag is deliberately left to a manual release after the validation recorded here. Validated locally: `ruff`, `mypy tools/release_notes.py`, `python -m pytest tests/test_release_notes.py -q -p no:cacheprovider` (9 passed), all workflow YAML parses, `.coderabbit.yaml` against the CodeRabbit schema. Not validated: the workflows on GitHub (the scheduled ones run only from `main`; the release workflow first runs on the next pre-release tag). Risk: CodeQL and the stale workflow may open findings or close issues once active. Single best next action: after merging, run `gh workflow run stale.yml` and `codeql.yml` once and read the logs.

The dated entries below are preserved as a historical implementation and testing log. Their status lines and “single best next action” notes describe the state at the time they were written; they are not current release status. Use this snapshot, [CHANGELOG.md](CHANGELOG.md), and the hardware checklist for current information.

---


## Which branch a contribution goes to (2026-11-09)

`CONTRIBUTING.md` and the pull request template on `main` now say that new features go to the development line `agent/panel-0.6.1` and that `main` takes bug fixes of the stable release and Dependabot updates. Cause: a contributor sent a feature pull request (`input_boolean`) to `main` after our own invitation. Validated: only the CI checks of the pull request (`tests/test_docs.py` exists on the development line, not on `main`, so there is no documentation test to run here). Not applicable: hardware. Next: none; the same text is in `AGENTS.md` on the development line.

## Dependabot PR #53 cannot work; Dependabot ignores Home Assistant (2026-11-09)

Dependabot PR #53 bumped `homeassistant` in `requirements-test.txt` from 2026.10.4 to 2026.11.0, but `pytest-homeassistant-custom-component` 0.13.375 pins Home Assistant 2026.10.4 and is the last release of that package: pip fails with `ResolutionImpossible` and the Unit tests check failed. `.github/dependabot.yml` now ignores `homeassistant` and that package; the pre-release job of `ci.yml` covers the newest Home Assistant with the official `pytest-homeassistant`. Validated: the YAML parses; the failure was read from the CI log of PR #53. Not verified: that Dependabot honours the ignore (it shows on its next run). Next: the owner decides about closing PR #53 and merging PR #54 (`codeql-action` 4, all checks green).

## Backport of the compatibility watch and the 2026.11 CI to `main` (2026-11-06)

Copied from the development line (PR #40 and PR #41), because scheduled workflows run only from `main`: `compat-watch.yml` with `tools/compat_watch.py` and `.github/compat-baseline.json` (Home Assistant 2026.11.0, Matter Server app 9.3.0, matterjs-server v1.5.5), the pre-release job of `ci.yml` on the new `pytest-homeassistant`, `tests/ha_common.py` and `tests/ha_typing.py`, and the import changes in six test files. Validated: `pytest` 532 passed on Home Assistant 2026.9.4 (old package) and on 2026.11.0 (`pytest-homeassistant`, `-p no:respx`), ruff clean, mypy only the two known errors. Not run: the workflows on GitHub, and nothing on a real instance. The baseline says what was *tested*, so update it only in a pull request that records a check of a newer version. The garbled-Czech test and the tools of the development line are not backported. The audit section of `docs/MATTERJS_COMPATIBILITY.md` is copied too: it is what the baseline versions rest on (from sources and tests, not a real instance).

Validation commands: `ruff format --check custom_components tests tools`, `ruff check custom_components tests tools`, `mypy custom_components/ikea_bilresa` (two known errors), `python -m pytest -q -p no:cacheprovider` (add `-p no:respx` with `pytest-homeassistant` on 2026.11; on Windows the stand-ins of `docs/DEVELOPMENT.md`). Known risks: the compatibility watch reads the Matter Server app version from the default branch of the add-ons repository and has never run on GitHub; the baseline can claim more than a real instance has seen. Single best next action: run the `Compatibility watch` workflow once by hand (`gh workflow run compat-watch.yml`) after the merge and read the log; with no newer release it must print "Nothing is newer than the tested versions."
