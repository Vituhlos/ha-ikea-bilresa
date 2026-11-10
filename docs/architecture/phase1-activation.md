# Phase 1 activation runbook — Codespaces and branch protection

This runbook complements [the owner-approved roadmap](ai-development-automation.md).
**Do not enable anything silently.** This repository is public and supports
both a stable and a development release line.

## A. Before merging the Phase 1 PR

1. Open the [Phase 1 draft PR](https://github.com/Vituhlos/ha-ikea-bilresa/pull/68).
2. Confirm that the six standard **CI** jobs and CodeQL completed successfully.
3. The additional `Devcontainer smoke` workflow builds the same devcontainer
   configuration and runs Python and frontend checks; it only runs when
   `.devcontainer/**`, `requirements-test.txt`, or its own workflow changes. **Never make this
   path-filtered check required**, since unrelated PRs intentionally skip it.
4. Before opening any PR branch in Codespaces, **review and trust** its
   `.devcontainer/devcontainer.json`, bootstrap scripts and dependencies.
   Untrusted PR code can execute with your Codespace credentials; never open
   untrusted branches with privileged tokens or configured secrets. Use a
   least-privileged environment.
5. Optionally open the PR in a **2-core Codespace** via the PR's **Code →
   Codespaces → Create codespace**. The startup should run
   `.devcontainer/setup.sh` automatically, installing an isolated `.venv`.
   An actual interactive Codespace session is the final end-to-end validation;
   a green smoke workflow alone is not proof that the Codespaces UI opened.
6. In the Codespace terminal, if you start one:

   ```bash
   source .venv/bin/activate
   python --version
   node --version
   ruff check custom_components tests
   mypy --no-site-packages custom_components/ikea_bilresa
   python -m pytest -q
   node --test tests/panel_frontend.test.mjs tests/iconset_frontend.test.mjs
   ```

   Never treat these automated checks as hardware validation. Stop your
   Codespace after testing. In personal Codespaces settings, consider an
   idle timeout of 10 minutes and review storage limits and billing.

7. Mark the PR ready for review and merge it **only** after checking its diff,
   CodeRabbit feedback and run results.

## B. Required status checks verified on both branch targets

The following job names exist in
[`ci.yml`](https://github.com/Vituhlos/ha-ikea-bilresa/blob/main/.github/workflows/ci.yml)
and ran successfully on PRs to both branch targets:

| Required check context | `main` PR #68 | development PR #66 |
| --- | --- | --- |
| `Validate manifest (hassfest)` | success | success |
| `Validate HACS` | success | success |
| `Lint (ruff)` | success | success |
| `Type check (mypy)` | success | success |
| `Frontend checks` | success | success |
| `Unit tests` | success | success |

Evidence: [main-target CI run](https://github.com/Vituhlos/ha-ikea-bilresa/actions/runs/42790044346),
[development-target CI run](https://github.com/Vituhlos/ha-ikea-bilresa/actions/runs/42659597208).

Do **not** require `Unit tests (newest Home Assistant pre-release)`: it
normally runs only on schedule/manual invocation and is skipped on PRs.
Do not require CodeRabbit, CodeQL, or the path-filtered Devcontainer smoke
workflow in the first rollout.

## C. Configure branch rulesets (maintainer/admin action)

The corrected import templates are staged with **`enforcement: disabled`**.
The maintainer has already imported an **older version** of each template;
these live disabled rulesets are **not automatically updated by editing JSON
in the repository**. Reconcile the imported copies before activation:
- [ruleset-main.json](ruleset-main.json) → only `refs/heads/main`;
- [ruleset-development.json](ruleset-development.json) →
  only `refs/heads/agent/panel-0.6.1`.

Both specify:
- require a PR to merge, with **zero** mandatory approvals;
- require the six CI checks above;
- require resolving PR conversations;
- reject force pushes and branch deletion;
- no bypass roles, including bots; and
- strict required-check freshness: PR checks must use the latest target branch
  revision. This may rerun CI after other PRs merge, but protects against
  combining changes that have never been tested together.

### Rollout sequence

1. Confirm the imported rulesets are still **Disabled**, verify and update
   their expected GitHub Actions check sources and strict freshness (or
   delete/reimport updated versions while disabled), and inspect
   **Settings → Branches** for any older/classic protection. Avoid keeping
   duplicate rulesets active at the same time.
2. Use the corrected `ruleset-main.json` from the approved Phase 1 PR or
   merged repo, **not the earlier downloaded JSON/ZIP**.
3. Open https://github.com/Vituhlos/ha-ikea-bilresa/settings/rules
4. If you chose to reimport rather than edit the existing disabled ruleset:
   **New ruleset → Import a ruleset**, select the corrected JSON, check the
   target branch, source binding and required checks, then keep enforcement
   **Disabled**. Remove the obsolete disabled duplicate to avoid confusion.
5. For **every** required CI check, verify that the expected source is
   **GitHub Actions** (GitHub App integration ID `15368`). Do not activate
   if GitHub shows **Any source** or the source cannot be verified. The
   updated import templates specify `integration_id: 15368`, but the two
   rulesets you already imported may contain their previous settings.
   Edit their required-check source in Settings, or replace the disabled
   imports with the corrected templates, before enabling either ruleset.
   Confirm **Require branches to be up to date before merging** is checked.
   If a source cannot be selected, keep the ruleset disabled and investigate.
6. After verifying source bindings and strict freshness, change enforcement to
   **Active** for `main`. Open a small real PR and verify GitHub requires
   green checks and resolved conversations to merge. Confirm direct pushes
   are blocked; do not test with destructive force pushes.
7. Only once `main` is verified, repeat for `ruleset-development.json`.
   Do not allow a self-review requirement that would lock out the solo
   maintainer. Verify a PR targeting the development branch.
8. If protection blocks legitimate changes due to a misconfigured check,
   return the ruleset to **Disabled**, correct it, and retest. Do not
   grant permanent administrator/agent bypass as a workaround.

The connected GitHub integration currently cannot edit repository
administration/rulesets. Merely committing the JSON files does **not**
activate rules; the maintainer needs to import and enable them from
GitHub Settings.

## D. Safety and later automation

No GitHub App, Codex API token, autonomous issue triggers, auto-merge or
release automation are installed in Phase 1. Phase 2 must start from a
separate reviewed design and explicit authorization of any incremental
costs. Hardware-facing code and Home Assistant configuration stay unchanged.
