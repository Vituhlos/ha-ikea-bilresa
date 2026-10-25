## Summary

<!-- What does this change and why? Link the issue if there is one. -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor / internal change
- [ ] Documentation or repository maintenance

## Checks performed

<!-- Tick what you actually ran; delete lines that do not apply.
     Full command list: docs/DEVELOPMENT.md → "Verification gates". -->

- [ ] `ruff format --check` and `ruff check`
- [ ] `mypy custom_components/ikea_bilresa`
- [ ] `pytest -q`
- [ ] Frontend checks (`node --check`, `node --test`)
- [ ] JSON files validated (`strings.json`, `translations/*.json`)

## Hardware validation

<!-- Green CI is not hardware validation. -->

- [ ] Tested on a physical BILRESA — describe below
- [ ] Not tested on hardware
- [ ] Not applicable (docs/CI/tests only)

## Documentation and translations

- [ ] English and Czech updated together (translations and/or READMEs)
- [ ] `CHANGELOG.md` updated for user-visible changes
- [ ] `PROJECT_STATUS.md` updated with validation state and next action

## Confirmations

- [ ] This PR contains only the changes described above — no unrelated edits
- [ ] No secrets, tokens, node IDs of a private installation, or personal data
