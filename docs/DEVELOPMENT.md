# Development workflow

This workflow keeps changes reproducible across the owner, Claude Code, Codex,
and GitHub Actions. `PROJECT_STATUS.md` is the live source of truth.

## 1. Orient before editing

Read `AGENTS.md`, `PROJECT_STATUS.md`, and `docs/ROADMAP.md`. For device-facing
work also read `docs/DEVICE_REFERENCE.md`, `docs/MATTERJS_COMPATIBILITY.md`,
`docs/SCROLL_PERFORMANCE.md`, and `docs/HARDWARE_TEST.md`, then inspect:

```powershell
git status --short
git branch --show-current
git log --oneline --decorate -12
git diff --stat
```

Select one backlog item. If the tree is already dirty, finish, verify, or
explicitly preserve that work before starting another feature.

## 2. Work in small, reviewable units

- Separate Matter/protocol changes from Home Assistant UI changes.
- Preserve the passive listener unless Matter-client reuse is the selected task.
- Keep runtime behavior, tests, translations, documentation, and changelog in
  the same coherent change.
- Treat English and Czech user-facing content as a pair.
- Record assumptions about BILRESA firmware or event shapes in code comments and
  `PROJECT_STATUS.md`.

For normal future work, prefer a short-lived feature branch. The current dirty
`main` working tree predates this workflow and should first be resolved without
losing changes. Do not commit or push unless the owner requests it.

## 3. Verification gates

### Gate A: static checks

Run for every code change:

```powershell
python -m json.tool custom_components/ikea_bilresa/strings.json > $null
python -m json.tool custom_components/ikea_bilresa/translations/en.json > $null
python -m json.tool custom_components/ikea_bilresa/translations/cs.json > $null
python -m compileall -q custom_components tests
ruff format --check custom_components tests
ruff check custom_components tests
mypy custom_components/ikea_bilresa
node --check custom_components/ikea_bilresa/frontend/ikea_bilresa_panel.js
node --test tests/panel_frontend.test.mjs tests/iconset_frontend.test.mjs
git diff --check
```

### Gate B: automated tests

```powershell
python -m pytest -q
```

Run coverage through the repository CI command and keep integration-module
coverage above 95% before closing work package `0.5.3`. A missing local
dependency or incompatible interpreter is a recorded limitation, not a pass.

### Gate C: Home Assistant validation

GitHub Actions is the canonical Linux environment for:

- hassfest manifest/string validation;
- HACS structural validation (even while store publication is deferred);
- Ruff, mypy, and pytest.
- the dependency-free panel syntax and frontend lifecycle tests on Node 22.

CI success means only **CI**, not **Hardware**.

### Gate D: BILRESA hardware

Any change to event decoding, bindings, timing, reconnect behavior, or supported
targets requires the relevant checks in `docs/HARDWARE_TEST.md`. Record exact
versions and observations. A feature is release-ready only after applicable
hardware checks pass.

## 4. Review the final diff

Before handoff:

```powershell
git status --short
git diff --stat
git diff --check
git diff
```

Confirm that no unrelated files, secrets, Home Assistant configuration, node
IDs, serials, or private URLs were added.

## 5. Commit and release policy

- One coherent behavior change per commit.
- Use imperative conventional subjects, for example:
  `feat: add scene cycling and hold-to-ramp`.
- Do not combine a hardware-unverified feature with a stable release tag.
- Tags represent owner-tested snapshots. Record the hardware matrix in
  `PROJECT_STATUS.md` before tagging.
- Publication, brand work, and default-HACS submission remain deferred until
  functionality, automated coverage, and physical BILRESA validation are done.

## 6. Required session handoff

Update `PROJECT_STATUS.md` before leaving the repository. Include exact commands
and results, distinguish CI from hardware, list dirty files, and name one best
next action. The next agent should be able to continue without reading chat
history.

When abandoning an approach, record why. Do not silently leave speculative code
in the working tree.
