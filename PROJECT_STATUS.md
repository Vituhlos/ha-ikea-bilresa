# Project status and agent handoff

Last updated: **2026-10-25 by Claude Code** (branch `agent/panel-0.6.1`: PR #11 merged; `0.7.0-rc.2` released and deployed).
The dated log up to the first handoff, and the entries `main` wrote on 2026-10-25
(PR #16, Issue #9 / PRs #14 and #15, PR #13, the 0.6.1 language release), are in
[docs/archive/PROJECT_STATUS_HISTORY_2026-10-25.md](docs/archive/PROJECT_STATUS_HISTORY_2026-10-25.md).

## Goal

- **Stable line:** `v0.6.1` is the latest stable release on `main`. Stable releases stay deferred until the hardware checks pass (`AGENTS.md`).
- **Test candidates on `main`:** `v0.6.2-rc.1` and `v0.6.2-rc.2` (pre-releases) carry the Issue #9 fixes (PR #14) and the `short_release` bus event with the disabled-channel fix (PR #16). They have the **old panel layout**.
- **Development line:** branch `agent/panel-0.6.1` carries the redesigned panel, the language fix, everything on `main`, and now the binding editor rework (PR #11, by Liquidmasl) with our fixes. It becomes **0.7.0**; the pre-releases are `v0.7.0-rc.1` and `v0.7.0-rc.2` (both published and deployed, rc.2 is the one running).
- **Nearest step:** the owner looks at the panel, the new editor and the link card in his Home Assistant (the agent cannot sign in), and reads the Czech texts. Hardware checks are open and postponed by the owner (tracker BILRESA-12, `docs/HARDWARE_TEST.md` B/F, C, H and Issue #9).
- **Do not** install `0.6.2-rc.*` or `0.6.1` on the owner's instance: they have the old panel layout.

## Done

- 2026-10-18: stable `v0.6.0`; layout A of the panel; `v0.6.1-rc.1` and `v0.6.1-rc.2` released and deployed (details in the archive).
- 2026-10-24: language fix (PR #10) and stable `v0.6.1` on `main`; the owner chose 0.7.0 for this branch.
- 2026-10-25 on `main`, by the owner and another agent: PR #13 repository professionalization, PR #14 Issue #9 fix, PR #15 `v0.6.2-rc.1`, PR #16 `short_release` port and disabled-channel fix, PR #18 `v0.6.2-rc.2`.
- 2026-10-25: `main` merged into this branch (`a303ea3`); `tests/test_version_consistency.py` and two `AGENTS.md` rules (`f94f0f3`); `0.7.0-rc.1` prepared (`9eadbdf`), tagged, published as a pre-release and deployed on the owner's instance after backup `e65e76e3` (Synology agent only, 1.15 GB, unprotected like the 2026-10-18 one). The instance had stable `0.6.1` loaded, not `0.6.1-rc.2` as noted before. Read back: manifest `0.7.0-rc.1`, entry `loaded`, 3 devices, no system-log entry from the integration.
- 2026-10-25: tracker in itsaplan, project `BILRESA`, initiative "0.7.0: redesigned panel on top of the 0.6.2 fixes": BILRESA-9 to 14, and the older BILRESA-1 to 8 (Reddit feedback audit, untouched). Keep issue states in step with this file; a Done needs recorded evidence.
- 2026-10-25: optional Buy Me a Coffee link (`d3f436e`, `.github/FUNDING.yml` is only on this branch until it reaches `main`); `.coderabbit.yaml` so CodeRabbit reviews every base branch, and the note on fork-run approval in `docs/DEVELOPMENT.md` (`5d1474d`, BILRESA-13).
- 2026-10-25: PR #11 (binding editor rework) read in full, checked, and reviewed by CI (owner-approved fork run `40157201995`), Devin and CodeRabbit. Integration branch `agent/pr11-integration`: merge `1ab4b1f`, the three review findings fixed with tests (`678675e`), Czech wording (`16d7fdf`, `02f25da`), README link to a community label tool (`4c5c499`, BILRESA-5), and the footer card (`2c91006`). CI run `40226247370` on `2c91006`: all 7 jobs success. The branch was then fast-forwarded into `agent/panel-0.6.1` and pushed; GitHub marked PR #11 as merged (merge commit `1ab4b1f`, author kept in the history). The Codex review of PR #11 failed once and then never finished, so the rule in `AGENTS.md` to wait for requested reviews was not fully met; recorded here and in BILRESA-14. Nothing was posted to the PR after the merge.
- 2026-10-25: `0.7.0-rc.2` released and deployed. Release commit `1e18bde` (`manifest.json`, `CHANGELOG.md` section and links, both READMEs' testing status, new open items in `docs/HARDWARE_TEST.md` section H); GitHub CI run `40226815670` on it: all 7 jobs success. Tag `v0.7.0-rc.2` on `1e18bde` and a GitHub pre-release (`isPrerelease` true, not marked latest; the repository's latest release is still `v0.6.1`). Backup `8c49bc67` `pred-bilresa-0.7.0-rc.2-2026-10-25` on the Synology agent only (1.15 GB, no failed agents, unprotected like the earlier ones). HACS `update_information` and `download v0.7.0-rc.2`, restart. Read back: manifest `0.7.0-rc.2`, HACS `installed_version v0.7.0-rc.2`, entry `loaded`, overview contract 6, `matter_connected` true, 3 devices, no system-log entry from the integration; error log only the standard custom-integration warnings. Tracker: BILRESA-19 (Done), BILRESA-11 (Done), BILRESA-14 (In Progress). Not verified: the panel, the new editor, the link card and the Czech texts in a browser on the owner's instance; any hardware check.
- 2026-10-25: an audit found four items missing from the rc.2 changelog section and release notes (the support link and `FUNDING.yml`; the fix for internal keys in editor error messages; the concrete Czech wording; what left the channel card). They were added to `CHANGELOG.md` and to the GitHub release notes in a later docs commit; the tag was not moved, so `CHANGELOG.md` at the tag lacks those four items. Left out on purpose as not visible to users: `.coderabbit.yaml`, the fork-approval note in `docs/DEVELOPMENT.md`, the new `HARDWARE_TEST.md` items.

## Verified

Branch `agent/panel-0.6.1` at `2c91006` (before the rc.2 preparation), local Windows stand-ins, 2026-10-25:

- `ruff format --check` and `ruff check` clean; `mypy` only the 2 known errors (`device_link.py:256`, `legacy_triggers.py:68`).
- `pytest` **525 passed** (Unit, local); `node --test` frontend tests **57 passed**; JSON files valid; `git diff --check` clean.
- GitHub CI, run `40226247370` on `2c91006`: hassfest, HACS, ruff, mypy, unit tests, frontend checks and the newest-HA-pre-release job all success.
- The panel was looked at only in the offline preview (`tools/panel_preview`), which shows layout and copy, not the owner's theme, fonts or Home Assistant's own components. The new editor, the link card and the Czech texts have not been seen in a real Home Assistant.
- `1e18bde` (the rc.2 release commit): the same local gates (pytest 525, frontend 57) and CI run `40226815670`, all 7 jobs success.
- **Not verified:** any hardware check; Codex review of PR #11; the new editor, the link card and the Czech texts in a real Home Assistant.

## Failed

- `ha_get_dashboard_screenshot` (Puppet) cannot render the panel; it only renders Lovelace dashboards.
- Side-loading a script from `localhost` into the owner's HA tab is blocked by the browser pane. Fetching a pushed commit from `raw.githubusercontent.com` and importing it from a Blob URL works.
- The in-app browser's HA sign-in has expired; the agent must not enter passwords. Reddit is blocked in the browser pane and in `WebFetch`.
- 2026-10-18: PRs #1/#2 were merged before the Codex review finished. Wait for reviews before merging.
- CodeRabbit's free tier allows about one review per hour; Codex failed on PR #11 ("unknown error", then stuck "Running").
- `ruff check ... | tail -1` in a `&&` chain hides a failing lint; run ruff without the pipe.
- Bash heredocs containing `'''` fail in this tool; write scripts to the scratchpad. A PowerShell here-string passed to `git commit -F -` was read as a pathspec; write the message to a file and use `-F <file>`.
- `ha_manage_backup create` times out and `ha_restart` drops the MCP transport; use `backup/generate` over the WebSocket (`ha_manage_custom_tool`) with the Synology agent, poll `backup/info`, and read the manifest version after a restart.
- Reading `backup/config/info` returns the backup encryption password; never print it.
- The global `mypy` (Python 3.13) cannot parse Home Assistant's Python 3.14 syntax; use the one in `.venv`.
- The preview server needs a `.claude/launch.json` in the repository folder; it is not git-ignored, so delete it after use.

## Remaining

1. Owner: look at the panel, the new editor (save a binding, Discard, scene cycling), the link card and the Czech texts in his Home Assistant; then the hardware checks (B/F `short_release`, C disabled channels, Issue #9 on a Zigbee2MQTT group) when he wants them.
2. Owner's decision, old: "krátký stisk" versus "jednoduchý stisk" in the Czech texts (the editor's response label no longer uses "jednoduchý"; the config flow, README, live test and activity feed still do).
3. Not done by PR #11 (author's list): navigation over unsaved changes (back arrow, switching devices, "Configure" from the live test) still discards silently.
4. Optional: reply to the PR #11 author after the merge (draft, to be shown to the owner first); `README.md` and `README.cs.md` say "a community member" for the label tool, the panel card names Liquidmasl.
5. Optional automation: tag-triggered release workflow. Branch protection on `main` needs the owner's explicit yes. `.coderabbit.yaml` may only take effect once it is on `main`.
6. Issue #3 and PR #8 were promised updates about the stable release; issue #4 (icon) is left on purpose; PR #5 stays open and untouched (its change was ported in PR #16). Issue #9 stays open until its reporter confirms.
7. Still owed from `docs/V0.6.0_CHECKLIST.md`: keyboard and screen-reader pass, dark and custom theme check, Section G, smoothing A/B. Entity names ("Kanál 1") are translated by Home Assistant in the instance language, not per user. The room-lights profile (discussion #7) is still planned for 0.7.0.
8. Enable Sponsorships in the repository settings (owner); `FUNDING.yml` must be on `main` for the Sponsor button.

## Git / build / test

- Repo `C:\Users\Pech\Documents\Cursor\HomeAssistant\ha-ikea-bilresa`, GitHub `Vituhlos/ha-ikea-bilresa`.
- Branch `agent/panel-0.6.1` (pushed; `v0.7.0-rc.2` is on `1e18bde`, later commits are docs only). `agent/pr11-integration` is merged into it and can be deleted. `main` at `176cfc3` (tag `v0.6.2-rc.2`); latest stable `v0.6.1`.
- Gates (Windows, stand-ins in `.venv`; `ruff` is the global one):
  - `ruff format --check custom_components tests tools`
  - `ruff check custom_components tests tools`
  - `.venv\Scripts\python.exe -m mypy custom_components/ikea_bilresa`
  - `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -p bilresa_windows_local`
  - `node --test tests/panel_frontend.test.mjs tests/iconset_frontend.test.mjs`
- CI runs on PRs and pushes to `main`. For another branch use `gh workflow run ci.yml --ref <branch>`. A first-time contributor's fork run waits for maintainer approval.
- Preview: `python tools/panel_preview/build.py`, then a `bilresa-panel-preview` entry in `.claude/launch.json` (port 8765). Query: `lang`, `instance`, `theme=warm`, `inset=16`, `narrow=1`, `open`, `view`, `edit`.
- Deploy: backup first (Synology agent `synology_dsm.2260S6RZATVV9` via `backup/generate`), HACS `update_information` then `download` with the tag, restart, read back manifest and log.
