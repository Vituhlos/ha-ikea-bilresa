# Project status and agent handoff

Last updated: **2026-10-25 by Claude Code** (branch `agent/panel-0.6.1`, `main` merged in; release commit `9eadbdf` for `0.7.0-rc.1` pushed, CI green; tag `v0.7.0-rc.1` and the GitHub pre-release published, deployed on the owner's instance).
The dated log up to the first handoff is in
[docs/archive/PROJECT_STATUS_HISTORY_2026-10-25.md](docs/archive/PROJECT_STATUS_HISTORY_2026-10-25.md).
The entries `main` wrote on 2026-10-25 (PR #16, Issue #9 / PRs #14 and #15, PR #13,
the 0.6.1 language release) were appended to the end of that file.

## Goal

- **Stable line:** `v0.6.1` is the latest stable release on `main`.
- **Test candidates on `main`:** `v0.6.2-rc.1` and `v0.6.2-rc.2` (pre-releases) carry
  the Issue #9 fixes (PR #14) and the `short_release` bus event with the
  disabled-channel fix (PR #16). They have the **old panel layout**. Hardware
  validation of both is pending; Issue #9 stays open until its reporter confirms.
- **Development line:** this branch carries the redesigned panel (detail is a Home
  Assistant subpage, compact channel cards), the language fix, and now everything
  on `main`. It becomes **0.7.0**. The manifest says `0.7.0-rc.1` (commit `9eadbdf`).
- **Nearest step:** the owner looks at the redesigned panel on desktop and phone (the agent cannot sign in), then the hardware checks (tracker BILRESA-12, `docs/HARDWARE_TEST.md` B/F, C, H and Issue #9).
  His instance runs `0.6.1-rc.2`; HACS offers `0.6.2-rc.2` there, which has the old
  layout. Tell him not to take it.

## Done

- 2026-10-18: stable `v0.6.0`; panel critique; layout A implemented; `v0.6.1-rc.1` and `v0.6.1-rc.2` released and deployed (details in the archive).
- 2026-10-24: language fix (PR #10) and stable `v0.6.1` on `main`; owner chose 0.7.0 as the number of this branch.
- 2026-10-25 (done on `main` by the owner and another agent, not by this branch): PR #13 repository professionalization, PR #14 Issue #9 fix, PR #15 `v0.6.2-rc.1`, PR #16 `short_release` port and disabled-channel fix, PR #18 `v0.6.2-rc.2`; Issue #9 answered with `v0.6.2-rc.2`.
- 2026-10-25: handoff committed (`31d937d`). Then `origin/main` (`176cfc3`) was merged into this branch with a merge commit (local, unpushed). Conflicts resolved by hand in `CHANGELOG.md` (both histories kept: `main`'s `0.6.2-rc.*` and `0.6.1` sections, then this branch's `0.6.1-rc.2` and `rc.1`), `tools/panel_preview/build.py` (docstring keeps `theme=warm`), `manifest.json` (this branch's `0.6.1-rc.2` kept) and this file.

- 2026-10-25: the merge was pushed (`a303ea3`); CI run `40212877477` passed all 7 jobs. Step 1: `tests/test_version_consistency.py` and two `AGENTS.md` rules, commit `f94f0f3`, CI run `40214428726` all 7 jobs success.
- 2026-10-25: tracker in itsaplan, project `BILRESA` (HA IKEA BILRESA): initiative "0.7.0: redesigned panel on top of the 0.6.2 fixes" with BILRESA-9 (merge, Done), BILRESA-10 (version guard, Done), BILRESA-11 (release 0.7.0-rc.1, In Progress), BILRESA-12 (hardware validation), BILRESA-13 (CI and reviews for non-default bases), BILRESA-14 (review PR #11). The older BILRESA-1 to 8 (Reddit feedback audit) were not touched. Keep issue states in step with this file; a Done needs recorded evidence.
- 2026-10-25, deployed `v0.7.0-rc.1` on the owner's instance (HA 2026.10.3). It had stable `0.6.1` (old layout) loaded, not `0.6.1-rc.2` as written earlier. Backup `e65e76e3` `pred-bilresa-0.7.0-rc.1-2026-10-25` on the Synology agent only (1.15 GB, unprotected like the 2026-10-18 one). HACS `update_information` + `download v0.7.0-rc.1`, restart. Read back: manifest `0.7.0-rc.1`, HACS `installed_version v0.7.0-rc.1`, entry `loaded`, overview contract 6, `matter_connected` true, 3 devices, no system-log entry from the integration; error log only the standard custom-integration warning. Not verified: the panel in a browser, any hardware check.
- 2026-10-25, release commit `9eadbdf` pushed; GitHub CI run `40215590846` on it: all 7 jobs success. Tag `v0.7.0-rc.1` (on `9eadbdf`) pushed and GitHub pre-release published 2026-10-25 (`isPrerelease` true, latest release still `v0.6.1`); not deployed. The preparation, uncommitted until then, was: `0.7.0-rc.1` = `manifest.json` `0.7.0-rc.1`, `CHANGELOG.md` section and link references (pending hardware checks listed), both READMEs' testing status, new section H "Redesigned panel" in `docs/HARDWARE_TEST.md` (all open). PR #11 deliberately not included.

## Verified

With the version test added (521 passed; ruff, mypy and node results unchanged from below). The test was shown to fail when the manifest version or a README's stable release was changed.

Merged tree, local Windows stand-ins, 2026-10-25:

- `ruff format --check custom_components tests tools`: 58 files already formatted.
- `ruff check custom_components tests tools`: all checks passed.
- `.venv\Scripts\python.exe -m mypy custom_components/ikea_bilresa` (mypy 2.4.0, installed into the ignored `.venv`): only the 2 known errors, `device_link.py:256` and `legacy_triggers.py:68`, as on `main`.
- JSON of `strings.json`, `translations/en.json`, `translations/cs.json`, `manifest.json` valid; `compileall` clean; `node --check` on the panel clean; `git diff --check` clean.
- `pytest` **514 passed** (Unit, local, Windows stand-ins).
- `node --test tests/panel_frontend.test.mjs tests/iconset_frontend.test.mjs`: 46 passed.
- **Not run:** GitHub CI on the merged tree (nothing pushed); hardware of any kind.
- On `main`: CI success on merge `176cfc3` (run `40208892387`); `v0.6.2-rc.2` is a pre-release.
- 2026-10-18, owner's instance on `v0.6.1-rc.2`: manifest `0.6.1-rc.2`, entry `loaded`, 3 devices, no log entry from the integration. Backup `pred-bilresa-0.6.1-rc.2-2026-10-18` on the Synology agent.

## Failed

- `ha_get_dashboard_screenshot` (Puppet) cannot render the panel; it only renders Lovelace dashboards.
- Side-loading a script from `localhost` into the owner's HA tab is blocked by the browser pane. Fetching a pushed commit from `raw.githubusercontent.com` and importing it from a Blob URL works.
- The in-app browser's HA sign-in has expired; the agent must not enter passwords.
- 2026-10-18: PRs #1/#2 were merged before the Codex review finished. Wait for reviews before merging.
- CodeRabbit's free tier ran out on PR #10; `@codex review` was used instead.
- `ruff check ... | tail -1` in a `&&` chain hides a failing lint; run ruff without the pipe.
- Bash heredocs containing `'''` fail in this tool; write scripts to the scratchpad. A PowerShell here-string passed to `git commit -F -` was read as a pathspec; write the message to a file and use `-F <file>`.
- `ha_manage_backup create` and `ha_restart` time out or drop the MCP transport; do not repeat them. Poll `backup/info` and read the manifest version instead.
- Reading `backup/config/info` returns the backup encryption password; never print it.
- The global `mypy` (Python 3.13) cannot parse Home Assistant's Python 3.14 syntax; use the one in `.venv`.

## Remaining

1. Owner's decision: push the merge (needs `gh workflow run ci.yml --ref agent/panel-0.6.1` afterwards), then `0.7.0-rc.1` from this branch: manifest, CHANGELOG section that folds the `0.6.1-rc.*` redesign entries into 0.7.0, tag, pre-release whose notes list the open hardware checks (`AGENTS.md` rule from `main`). Deploy only with a Synology backup first.
2. PR #11 integration, prepared locally on branch `agent/pr11-integration` (not pushed, not merged anywhere): `agent/panel-0.6.1` + PR #11 head `37e02aa` (merge `1ab4b1f`; conflicts only in CHANGELOG.md and PROJECT_STATUS.md) + commit `678675e` fixing the three review findings (stale short-press target behind a scene cycle or "no action", disclosure not opened on a rejected rotation limit, Discard button without an id), each with a test that fails without the fix. Local gates on it: ruff clean, mypy only the 2 known errors, pytest 523 passed, frontend tests 56 passed, version test passes. Reviews on `37e02aa`: CI green (run `40157201995`, approved by the owner), Devin and CodeRabbit commented, Codex failed once and then stayed "Running"; none of it is a hardware check. Merge only on the owner's explicit go, after he has read the Czech strings and saved a binding and used Discard in the new editor on his instance. Not done by the PR (author's list): navigation over unsaved changes still discards silently. Original entry for reference: PR #11 (Liquidmasl, binding editor rework, base `agent/panel-0.6.1`): not reviewed beyond a first read. No CI ran on it because its fork run (`40157201995`, head `37e02aa`) waits for maintainer approval (first-time contributor, policy `first_time_contributors`); approving it executes the contributor's code, so read the diff first, owner's call. CodeRabbit skipped it (base is not the default branch); `.coderabbit.yaml` (commit `5d1474d`) now reviews every base, but it may only take effect once it is on `main`. It conflicted with the old `PROJECT_STATUS.md` and may conflict with `CHANGELOG.md` and `tests/test_panel.py` now; not test-merged against this merge. Review after the merge is pushed; the owner must read its Czech strings; a save through the new editor and a press on a BILRESA are untested. Nothing posted, closed or merged.
3. Hardware checks still open on `main`'s candidates: `short_release` (B/F), Fast/Instant on a disabled channel (C), Issue #9 on a Zigbee2MQTT group (see `docs/HARDWARE_TEST.md`).
4. Automation: the version-consistency test is done (`f94f0f3`); CI already runs on PRs to any base (the gap was the fork approval); `.coderabbit.yaml` and the note in `docs/DEVELOPMENT.md` are done locally (`5d1474d`, tracker BILRESA-13, not pushed). Not started: tag-triggered release workflow. Branch protection on `main` needs the owner's explicit yes.
5. Owner to confirm the panel on desktop and phone; the agent cannot sign in to look.
6. Still owed from `docs/V0.6.0_CHECKLIST.md`: keyboard and screen-reader pass, dark and custom theme check, Section G, smoothing A/B.
7. Issue #3 and PR #8 were promised updates about the stable release; issue #4 (icon) is left on purpose. PR #5 stays open and untouched (its change was ported in PR #16).
8. Entity names ("Kanál 1") are translated by Home Assistant in the instance language, not per user.
9. The room-lights profile (discussion #7) is still planned for 0.7.0.

## Git / build / test

- Repo `C:\Users\Pech\Documents\Cursor\HomeAssistant\ha-ikea-bilresa`, GitHub `Vituhlos/ha-ikea-bilresa`.
- Branch `agent/panel-0.6.1`: `origin` is at `31d937d`; the local branch has the merge commit of `origin/main` (`176cfc3`) on top, unpushed.
- `main` at `176cfc3` (tag `v0.6.2-rc.2`); latest stable `v0.6.1`.
- Gates (Windows, stand-ins in `.venv`; `ruff` is the global one):
  - `ruff format --check custom_components tests tools`
  - `ruff check custom_components tests tools`
  - `.venv\Scripts\python.exe -m mypy custom_components/ikea_bilresa`
  - `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -p bilresa_windows_local`
  - `node --test tests/panel_frontend.test.mjs tests/iconset_frontend.test.mjs`
- CI runs on PRs and pushes to `main`. For another branch use `gh workflow run ci.yml --ref <branch>`.
- Preview: `python tools/panel_preview/build.py`, then start `bilresa-panel-preview` from `..\.claude\launch.json` (port 8765). Query: `lang`, `instance`, `theme=warm`, `inset=16`, `narrow=1`, `open`, `view`, `edit`.
- Deploy: backup first (Synology agent `synology_dsm.2260S6RZATVV9` via `backup/generate`), HACS `update_information` then `download` with the tag, restart, read back manifest and log. Do not install `0.6.2-rc.*` or `0.6.1` on the owner's instance: they would drop the new panel layout.
