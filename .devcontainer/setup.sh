#!/usr/bin/env bash
# Codespaces bootstrap: development tools only; no access to Home Assistant or Matter devices.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

python -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check --upgrade pip
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-test.txt ruff mypy

printf '\nBILRESA Codespace ready. Activate tools with: source .venv/bin/activate\n'
printf 'Run checks: ruff check custom_components tests && mypy --no-site-packages custom_components/ikea_bilresa && python -m pytest -q\n'
printf 'Frontend: node --test tests/panel_frontend.test.mjs tests/iconset_frontend.test.mjs\n'
printf 'Hardware validation still requires a real BILRESA and Home Assistant.\n'
