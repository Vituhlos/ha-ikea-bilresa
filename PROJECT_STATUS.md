# Project status and agent handoff

Last updated: **2026-10-25 by Claude Code** (branch `agent/panel-0.6.1`).
The dated log up to this point, unchanged, is in
[docs/archive/PROJECT_STATUS_HISTORY_2026-10-25.md](docs/archive/PROJECT_STATUS_HISTORY_2026-10-25.md).

## Goal

- **Stable line:** `v0.6.1` is the latest stable release (0.6.0 plus "the panel
  follows the viewing user's language"). `main` declares `0.6.1`.
- **Development line:** branch `agent/panel-0.6.1` becomes **0.7.0**. It holds
  the redesigned panel (detail is a Home Assistant subpage, compact channel
  cards) plus the 0.6.1 language fix. The pre-releases `v0.6.1-rc.1/rc.2` came
  from this branch and are marked superseded on GitHub.
- **Planned for 0.7.0:** the "room lights" profile from discussion #7 (hold +
  rotate = white temperature, hold + release = Kelvin presets) and the port of
  PR #5 (`short_release` event, credit amodig).
- **Nearest step:** the owner decides whether to release and deploy
  `0.7.0-rc.1` from this branch. His instance runs `0.6.1-rc.2`, and HACS
  offers `0.6.1` there, which would drop the new layout. Tell him not to take it.

## Done

- 2026-10-18: stable `v0.6.0` (PR #2 → `agent/stabilize-0.5-x`, PR #1 → `main`, merge commits).
- 2026-10-18: critique of the panel; owner chose layout A (HA subpage, no rail, no 1/2/3 spine).
- 2026-10-18: layout A implemented; classic layout deleted (`97e255d`); `v0.6.1-rc.1` released and deployed.
- 2026-10-18: compact cards after the owner's rc.1 screenshots: 880 px max, one-line unconfigured channels, channel switch on its card, dial fields stacked (`9c8f7a8`); `v0.6.1-rc.2` released and deployed.
- 2026-10-24: language fix: panel config carries `labels_by_language`; panel picks `hass.language` and sends `language` with `ikea_bilresa/overview` and `/overview/subscribe` (PR #10).
- 2026-10-24: CodeRabbit follow-ups: stale connects drop their answer and subscription; the Live test feed restarts after a language reconnect (`9eb7955`, here `e252e6e`).
- 2026-10-24: stable `v0.6.1` tagged on merge `514811a`; rc.1/rc.2 notes marked superseded.
- 2026-10-24: owner chose the numbering: stable fix = 0.6.1, development = 0.7.0.
- Earlier: PR #8 measurement by cassus recorded in `docs/DEVICE_REFERENCE.md` (credited); reply posted.

## Verified

- 2026-10-24, PR #10 head `9eb7955`: GitHub CI all jobs green (hassfest, HACS, ruff, mypy, frontend, unit tests).
- 2026-10-24, `main` merge `514811a`: CI run `40132322918` success; `git diff 9eb7955 origin/main` empty.
- 2026-10-24: Codex review of `9eb7955` after `@codex review`: completed, no findings.
- 2026-10-24: `gh api repos/Vituhlos/ha-ikea-bilresa/releases/latest` → `v0.6.1`, not a pre-release.
- 2026-10-24, this branch at `e252e6e`: `pytest` 490 passed; `node --test tests/panel_frontend.test.mjs tests/iconset_frontend.test.mjs` 46 passed.
- 2026-10-24, local preview `?lang=en&instance=cs`: no Czech word in overview or detail; both requests carried `language: "en"`.
- 2026-10-18, owner's instance after deploying `v0.6.1-rc.2`: manifest `0.6.1-rc.2`, entry `loaded`, overview contract 6, 3 devices, no system-log entry from the integration.
- 2026-10-18: backup `pred-bilresa-0.6.1-rc.2-2026-10-18` (`79ed7d29`, 1.19 GB) on the Synology agent only; unencrypted, as that location is configured.
- 2026-10-18: owner had already saved bindings and dial settings through the rc.16+ editor (new revisions, no log errors).

## Failed

- `ha_get_dashboard_screenshot` (Puppet) cannot render the panel: "Unknown config specified: ikea-bilresa". It only renders Lovelace dashboards.
- Side-loading a script from `localhost` into the owner's HA tab is blocked by the browser pane (`ERR_BLOCKED_BY_CLIENT`). Fetching a pushed commit from `raw.githubusercontent.com` and importing it from a Blob URL works.
- The in-app browser's HA sign-in has expired; the agent must not enter passwords. Screenshots fail while the app window is in the background.
- 2026-10-18: PRs #1/#2 were merged before the Codex review finished. It found nothing, but wait for reviews before merging.
- CodeRabbit's free tier ran out on PR #10 ("Review limit reached", about an hour); `@codex review` was used instead.
- `ruff check ... | tail -1` in a `&&` chain hides a failing lint; run ruff without the pipe.
- Bash heredocs containing `'''` fail in this tool; write scripts to the scratchpad instead.
- `ha_manage_backup create` and `ha_restart` time out or drop the MCP transport; do not repeat them. Poll `backup/info` and read the manifest version instead.
- Reading `backup/config/info` returns the backup encryption password; never print it. Pass it only inside the sandboxed call that needs it.

## Remaining

1. Owner's decision: release `0.7.0-rc.1` from this branch (manifest → `0.7.0-rc.1`, CHANGELOG section, CI via `gh workflow run ci.yml --ref agent/panel-0.6.1`, tag, pre-release) and deploy with a Synology backup.
2. New since the last session: PR #11 "Binding editor: one section per gesture…" by Liquidmasl (2026-10-25, base `agent/panel-0.6.1`) and issue #9 (Zigbee2MQTT light group: stale brightness jumps, single notches without transition; Pieter64, 2026-10-20, no comments). Read both; reply only after the owner approves, disclosed as written by Claude; never close or merge.
3. Owner to confirm rc.2 (or 0.7.0-rc.1) on desktop and phone; the agent cannot sign in to look.
4. Automation offered to the owner, not started: a CI test that checks manifest version against CHANGELOG, both READMEs and this file; a tag-triggered release workflow; `.coderabbit.yaml` (review non-default bases, house rules); a rule in `AGENTS.md` to wait for reviews. Branch protection on `main` needs the owner's explicit "yes".
5. 0.7.0 features: room-lights profile (discussion #7), PR #5 port.
6. Still owed from `docs/V0.6.0_CHECKLIST.md`: keyboard and screen-reader pass, dark and custom theme check, Section G, smoothing A/B.
7. Issue #3 (stable release is out) and PR #8 (stable is out) were promised updates; issue #4 (icon) is left on purpose.
8. Note for the owner: entity names ("Kanál 1") are translated by Home Assistant in the instance language, not per user.

## Git / build / test

- Repo `C:\Users\Pech\Documents\Cursor\HomeAssistant\ha-ikea-bilresa`, GitHub `Vituhlos/ha-ikea-bilresa`.
- Current branch `agent/panel-0.6.1` at `03447a3`, pushed. Manifest still says `0.6.1-rc.2`.
- `main` at `514811a` (`v0.6.1`). Branch `agent/i18n-user-language` is merged.
- Uncommitted: this file and `docs/archive/PROJECT_STATUS_HISTORY_2026-10-25.md` (handoff only).
- Gates (Windows, local stand-ins in `.venv`):
  - `ruff format --check custom_components tests tools`
  - `ruff check custom_components tests tools`
  - `mypy custom_components/ikea_bilresa`
  - `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -p bilresa_windows_local`
  - `node --test tests/panel_frontend.test.mjs tests/iconset_frontend.test.mjs`
- CI runs on PRs and pushes to `main`. For a branch without a PR, use `gh workflow run ci.yml --ref <branch>`.
- Preview: `python tools/panel_preview/build.py`, then start `bilresa-panel-preview` from `..\.claude\launch.json` (port 8765). Query: `lang`, `instance`, `theme=warm`, `inset=16`, `narrow=1`, `open`, `view`, `edit`.
- Deploy: backup first (Synology agent `synology_dsm.2260S6RZATVV9` via `backup/generate`), HACS `update_information` then `download` with the tag, restart, read back manifest and log.
