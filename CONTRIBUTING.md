# Contributing

Thanks for helping improve the BILRESA integration! This file is the short
version; [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) is the canonical, detailed
development guide and `AGENTS.md` defines the project guardrails for coding
agents.

## Reporting bugs and proposing features

- Open a GitHub issue with the **Bug report** or **Feature request** form.
- For a bug, the form asks for the versions we need to reproduce it
  (integration, Home Assistant Core, Matter Server), the controller type
  (scroll wheel / dual button) and the affected gesture. Attach a redacted
  debug log — enable it with:

  ```yaml
  logger:
    logs:
      custom_components.ikea_bilresa: debug
  ```

- Do not include credentials, tokens, full configuration backups or unique
  device identifiers (node IDs are fine — they are random per fabric, not
  serials).
- For security reports, see [SECURITY.md](SECURITY.md).

## Development workflow

1. Read `AGENTS.md` and the snapshot at the top of `PROJECT_STATUS.md` first —
   the status file is the live source of truth for what is implemented and
   how far it has been validated.
2. Work on a short-lived feature branch; never commit directly to `main`.
3. Keep one coherent change per pull request. Do not mix refactors with
   behavior changes.
4. Before opening the PR, run the checks for what you touched (full commands
   in `docs/DEVELOPMENT.md`, "Verification gates"):

   ```bash
   ruff format --check custom_components tests
   ruff check custom_components tests
   mypy custom_components/ikea_bilresa
   python -m compileall -q custom_components tests
   node --check custom_components/ikea_bilresa/frontend/ikea_bilresa_panel.js
   node --test tests/panel_frontend.test.mjs tests/iconset_frontend.test.mjs
   python -m pytest -q
   ```

## CI vs. hardware validation

GitHub Actions runs hassfest, the HACS validator, Ruff, mypy, the frontend
tests and pytest on every pull request — but **green CI is not hardware
validation**. Changes to event decoding, control bindings, timing, reconnect
behavior or supported targets also need the relevant checks in
[docs/HARDWARE_TEST.md](docs/HARDWARE_TEST.md) on a physical BILRESA. Say so in
the PR when you could not run them; an honest "not tested on hardware" is
always acceptable, an unverified "works" is not.

## English and Czech

The integration, the panel and the documentation are bilingual. If your change
touches user-visible text, update `translations/en.json` **and**
`translations/cs.json` — and the documentation in both languages together when it
belongs there: the short `README.md` / `README.cs.md` and the guides in `docs/en`
and `docs/cs`. `tests/test_docs.py` fails on a broken link or a heading that
differs between the two languages.

## Changelog and handoff

- Update `CHANGELOG.md` (Keep a Changelog + SemVer) for user-visible changes.
- Update `PROJECT_STATUS.md` when you finish a work session: what changed,
  exact validation commands and results, what was not run, and the single
  best next action.
- Releases and tags are prepared by the maintainer; don't tag or publish.
