# Phase 1 activation runbook — Codespaces and branch protection

This runbook complements [the owner-approved roadmap](ai-development-automation.md).
**Do not enable anything silently.** This repository is public and supports
both a stable and a development release line.

## A. Before merging the Phase 1 PR

1. Open the [Phase 1 draft PR](https://github.com/Vituhlos/ha-ikea-bilresa/pull/68).
2. Confirm that the six standard **CI** jobs and CodeQL completed successfully.
3. The additional `Devcontainer smoke` workflow builds the same devcontainer
   configuration and runs Python and frontend checks; it only runs when
   `.devcontainer/**` or its own workflow changes. **Never make this
   path-filtered check required**, since unrelated PRs intentionally skip it.
4. Optionally open the PR in a **2-core Codespace** via the PR's **Code →
   Codespaces → Create codespace**. The startup should run
   `.devcontainer/setup.sh` automatically, installing an isolated `.venv`.
   An actual interactive Codespace session is the final end-to-end validation;
   a green smoke workflow alone is not proof that the Codespaces UI opened.
5. In the Codespace terminal, if you start one:

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

6. Mark the PR ready for review and merge it **only** after checking its diff,
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

The two import templates are staged with **`enforcement: disabled`**:
- [ruleset-main.json](ruleset-main.json) → only `refs/heads/main`;
- [ruleset-development.json](ruleset-development.json) →
  only `refs/heads/agent/panel-0.6.1`.

Both specify:
- require a PR to merge, with **zero** mandatory approvals;
- require the six CI checks above;
- require resolving PR conversations;
- reject force pushes and branch deletion;
- no bypass roles, including bots; and
- loose required-check freshness (avoids unnecessary rebuilds when the target
  branch advances; reconsider strict mode if collisions become a problem).

### Rollout sequence

1. Confirm the rulesets page contains no conflicting rules; also inspect
   **Settings → Branches** for any older/classic protection.
2. Download `ruleset-main.json` from the approved Phase 1 PR or merged repo.
3. Open https://github.com/Vituhlos/ha-ikea-bilresa/settings/rules
4. **New ruleset → Import a ruleset**, select the JSON, review the branch
   pattern and required checks, and leave enforcement **Disabled** initially.
5. Make sure GitHub recognizes each CI check; when offered an expected
   source, prefer **GitHub Actions** (not arbitrary external statuses).
6. After verifying the ruleset configuration, change enforcement to
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
