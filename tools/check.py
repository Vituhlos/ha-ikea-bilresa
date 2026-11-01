"""Run every local gate once and print one line each; details only on failure.

    python tools/check.py            # all gates, in parallel
    python tools/check.py --fast     # skip the full pytest run

It prints what a person (or an agent) needs to decide "is this green": a status
and the summary line per gate, and the tail of the output for a gate that
failed. mypy reports two errors that are known and accepted (see
PROJECT_STATUS.md); that count is compared, not ignored, so a third one fails.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
# ruff is installed on its own, not in the project environment.
RUFF = [shutil.which("ruff") or "ruff"]
KNOWN_MYPY_ERRORS = 2
TAIL_LINES = 25


def _pytest_command() -> list[str]:
    command = [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    # The Windows-only plugin keeps the suite runnable on a developer machine.
    if importlib.util.find_spec("bilresa_windows_local") is not None:
        command += ["-p", "bilresa_windows_local"]
    return command


def _gates(fast: bool) -> list[tuple[str, list[str]]]:
    targets = ["custom_components", "tests", "tools"]
    gates = [
        ("format", [*RUFF, "format", "--check", *targets]),
        ("lint", [*RUFF, "check", *targets]),
        ("mypy", [PY, "-m", "mypy", "custom_components/ikea_bilresa"]),
        (
            "node",
            [
                "node",
                "--test",
                "tests/panel_frontend.test.mjs",
                "tests/iconset_frontend.test.mjs",
            ],
        ),
    ]
    if not fast:
        gates.append(("pytest", _pytest_command()))
    return gates


def _summary(name: str, output: str, code: int) -> tuple[bool, str]:
    lines = [line for line in output.strip().splitlines() if line.strip()]
    if name == "mypy":
        found = re.search(r"Found (\d+) errors?", output)
        count = int(found.group(1)) if found else 0
        ok = count <= KNOWN_MYPY_ERRORS if found else code == 0
        return ok, f"{count} errors (known: {KNOWN_MYPY_ERRORS})"
    if name == "node":
        passed = re.search(r"ℹ pass (\d+)", output)
        failed = re.search(r"ℹ fail (\d+)", output)
        text = f"{passed.group(1) if passed else '?'} passed"
        return code == 0, f"{text}, {failed.group(1) if failed else '?'} failed"
    return code == 0, lines[-1] if lines else "no output"


def _run(gate: tuple[str, list[str]]) -> tuple[str, bool, str, str, float]:
    name, command = gate
    started = time.monotonic()
    done = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = done.stdout + done.stderr
    ok, summary = _summary(name, output, done.returncode)
    return name, ok, summary, output, time.monotonic() - started


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fast", action="store_true", help="skip the full pytest run")
    args = parser.parse_args()

    gates = _gates(args.fast)
    with ThreadPoolExecutor(max_workers=len(gates)) as pool:
        results = list(pool.map(_run, gates))

    failed = False
    for name, ok, summary, _output, seconds in results:
        print(f"{'ok  ' if ok else 'FAIL'} {name:<7} {summary} ({seconds:.0f}s)")
        failed |= not ok
    for name, ok, _summary_line, output, _seconds in results:
        if not ok:
            print(f"\n--- {name} (last {TAIL_LINES} lines) ---")
            print("\n".join(output.strip().splitlines()[-TAIL_LINES:]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
