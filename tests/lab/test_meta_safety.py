"""An expected failure must never hide a safety failure.

``known_issues`` markers are ``xfail(strict=True, raises=AssertionError)``.
``LabSafetyViolation`` is not an ``AssertionError``, and the lab fixtures raise
it for every safety invariant. These tests prove that with the real thing: they
write small probe test files and run them in a separate pytest process, with the
lab's own fixtures, then read the exit code and pytest's own result lines. They
check the classification pytest actually gave each test, not the text of an
exception.

The probes fail inside the child process only. Nothing here touches the network
(the network guard is on in the child too) or any production file.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

REPO = Path(__file__).resolve().parents[2]

PREAMBLE = """
import socket
import time
import pytest
from custom_components.ikea_bilresa import binding as binding_module
from tests.lab.known_issues import SELFTEST_EXPECTED_FAILURE
from tests.lab.service_spy import LabSafetyViolation
"""

_LABELS = {
    "PASSED": "passed",
    "FAILED": "failed",
    "ERROR": "error",
    "XFAIL": "xfailed",
    "XPASS": "xpassed",
    "SKIPPED": "skipped",
}


def run_probe(tmp_path: Path, source: str) -> tuple[int, dict[str, list[str]]]:
    """Run ``source`` as a test file in a child pytest; classify each test.

    The classification is read from pytest's own ``-rA`` summary lines
    (``PASSED``, ``FAILED``, ``ERROR``, ``XFAIL``, ``XPASS``, ``SKIPPED``), so a
    test that is an expected failure *and* has a teardown error shows both.
    """
    # The same asyncio mode the repository's pyproject.toml sets.
    ini = ["[pytest]", "asyncio_mode = auto", ""]
    (tmp_path / "pytest.ini").write_text(chr(10).join(ini), encoding="utf-8")
    (tmp_path / "test_probe.py").write_text(
        PREAMBLE + textwrap.dedent(source), encoding="utf-8"
    )
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    if importlib.util.find_spec("bilresa_windows_local") is not None:
        command += ["-p", "bilresa_windows_local"]
    command += [
        "-p",
        "tests.lab.conftest",
        "-c",
        str(tmp_path / "pytest.ini"),
        "--rootdir",
        str(tmp_path),
        "-rA",
        "--tb=no",
        str(tmp_path / "test_probe.py"),
    ]
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    result = subprocess.run(
        command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=240
    )
    outcomes: dict[str, list[str]] = {}
    for line in result.stdout.splitlines():
        word, _, rest = line.partition(" ")
        if word in _LABELS and "test_probe.py::" in rest:
            name = rest.split("test_probe.py::", 1)[1].split(" ", 1)[0]
            outcomes.setdefault(name, []).append(_LABELS[word])
    return result.returncode, outcomes


# One child process for every probe that leaves the process state clean.
INDEPENDENT_PROBES = """
@SELFTEST_EXPECTED_FAILURE
def test_a_wrong_value():
    assert 10 == 0

@SELFTEST_EXPECTED_FAILURE
def test_violation_in_the_body():
    raise LabSafetyViolation("something left the sandbox")

@SELFTEST_EXPECTED_FAILURE
def test_a_harness_error_is_not_an_expected_failure_either():
    raise KeyError("a harness error")

@SELFTEST_EXPECTED_FAILURE
def test_unacknowledged_refusal(lab):
    lab.safety.record("something_refused")
    assert False

@SELFTEST_EXPECTED_FAILURE
def test_a_refused_service_call_that_was_caught_and_ignored(lab):
    call = lab.hass.services.async_call("script", "turn_on", {"entity_id": "x.y"})
    try:
        lab.tasks.run_now(call)
    except LabSafetyViolation:
        pass
    assert False

@SELFTEST_EXPECTED_FAILURE
def test_a_leaked_timer(lab):
    lab.scheduler.call_later(60, lambda now: None, "production_timer")
    assert False

@SELFTEST_EXPECTED_FAILURE
def test_a_leaked_dispatcher_subscription(lab):
    lab.dispatcher.connect(None, "some_signal", lambda: None)
    assert False

@SELFTEST_EXPECTED_FAILURE
def test_a_leaked_state_listener(lab):
    lab.registry.track(["light.x"], lambda event: None)
    assert False

@SELFTEST_EXPECTED_FAILURE
def test_a_task_that_would_wait_for_something_real(lab):
    import asyncio
    lab.tasks.create(asyncio.sleep(0))
    assert False

@SELFTEST_EXPECTED_FAILURE
def test_a_blocked_network_attempt_that_was_caught_and_ignored():
    try:
        socket.getaddrinfo("matter-server.invalid", 5580)
    except LabSafetyViolation:
        pass
    assert False
"""

TEARDOWN_PROBES = {
    "test_unacknowledged_refusal",
    "test_a_refused_service_call_that_was_caught_and_ignored",
    "test_a_leaked_timer",
    "test_a_leaked_dispatcher_subscription",
    "test_a_leaked_state_listener",
    "test_a_task_that_would_wait_for_something_real",
    "test_a_blocked_network_attempt_that_was_caught_and_ignored",
}


@pytest.fixture(scope="module")
def independent(tmp_path_factory) -> tuple[int, dict[str, list[str]]]:
    return run_probe(tmp_path_factory.mktemp("independent"), INDEPENDENT_PROBES)


# -- the baseline: an expected functional failure is expected ------------------


def test_a_known_functional_failure_stays_an_expected_failure(independent) -> None:
    _, outcomes = independent
    assert outcomes["test_a_wrong_value"] == ["xfailed"]


# -- a safety failure is a failure, whatever else is expected ------------------


def test_a_lab_safety_violation_in_an_expected_failure_is_a_real_failure(
    independent,
) -> None:
    _, outcomes = independent
    assert outcomes["test_violation_in_the_body"] == ["failed"]


def test_a_harness_error_in_an_expected_failure_is_a_real_failure(independent) -> None:
    _, outcomes = independent
    assert outcomes["test_a_harness_error_is_not_an_expected_failure_either"] == [
        "failed"
    ]


@pytest.mark.parametrize("name", sorted(TEARDOWN_PROBES))
def test_a_safety_failure_in_fixture_teardown_is_not_masked(independent, name) -> None:
    """Each probe is an expected failure that also breaks a safety invariant."""
    _, outcomes = independent
    kinds = outcomes[name]
    assert "error" in kinds, f"{name} was only {kinds}: the safety error was masked"
    assert kinds != ["xfailed"]


def test_the_child_run_as_a_whole_is_not_green(independent) -> None:
    code, outcomes = independent
    assert code != 0
    assert len(outcomes) == 10


# -- a patch that is not restored is a real failure ----------------------------


def test_an_unrestored_patch_fails_the_next_test_even_if_it_is_expected_to_fail(
    tmp_path,
) -> None:
    code, outcomes = run_probe(
        tmp_path,
        """
        def test_a_leaks_a_patch():
            binding_module.time = None  # not restored

        @SELFTEST_EXPECTED_FAILURE
        def test_b_expected_to_fail_but_starts_on_a_dirty_module():
            assert False
        """,
    )

    assert code != 0
    assert "error" in outcomes["test_b_expected_to_fail_but_starts_on_a_dirty_module"]
    # The leaking test itself passes; the damage is caught where it lands.
    assert outcomes["test_a_leaks_a_patch"][0] == "passed"


def test_the_final_session_check_catches_a_patch_left_by_the_last_test(
    tmp_path,
) -> None:
    code, outcomes = run_probe(
        tmp_path,
        """
        def test_the_last_test_leaks_a_patch():
            binding_module.time = None
        """,
    )

    assert code != 0
    assert "error" in outcomes["test_the_last_test_leaks_a_patch"]
