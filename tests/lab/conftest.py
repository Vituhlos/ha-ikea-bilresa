"""Fixtures for the lab: a harness that cleans up and checks its own safety.

Guards that run around every test in this directory:

* a network guard (``net_guard``): every outbound socket operation and name
  lookup that is not loopback is refused and recorded, whatever the platform's
  socket plugin does;
* a patch guard: no production module may be left patched;
* the harness teardown: no refusal may be left unacknowledged, and the
  coordinator's shutdown must leave no timer, subscription, listener or task.

Every one of these raises ``LabSafetyViolation``, which is *not* an
``AssertionError``. The expected-failure markers of ``known_issues`` accept only
``AssertionError``, so a safety failure can never be reported as an expected
failure, in a test body, in fixture setup or in fixture teardown.
"""

from __future__ import annotations

from collections.abc import Iterator
import time

import pytest

from custom_components.ikea_bilresa import binding as binding_module
from custom_components.ikea_bilresa import coordinator as coordinator_module
from custom_components.ikea_bilresa import matter_core as matter_core_module

from .harness import LabHarness
from .net_guard import NetworkGuard
from .service_spy import LabSafetyViolation

# What the production modules looked like before any lab patch. Captured when
# this file is imported, which is before the first test runs.
_REAL_MONOTONIC = time.monotonic
_PRISTINE = {
    (binding_module, "time"): time,
    (binding_module, "async_call_later"): binding_module.async_call_later,
    (binding_module, "async_track_time_interval"): (
        binding_module.async_track_time_interval
    ),
    (binding_module, "async_track_state_change_event"): (
        binding_module.async_track_state_change_event
    ),
    (binding_module, "async_dispatcher_send"): binding_module.async_dispatcher_send,
    (binding_module, "async_dispatcher_connect"): (
        binding_module.async_dispatcher_connect
    ),
    (binding_module, "Script"): binding_module.Script,
    (binding_module, "async_validate_actions_config"): (
        binding_module.async_validate_actions_config
    ),
    (binding_module, "async_extract_referenced_entity_ids"): (
        binding_module.async_extract_referenced_entity_ids
    ),
    (coordinator_module, "async_dispatcher_send"): (
        coordinator_module.async_dispatcher_send
    ),
    (coordinator_module, "async_call_later"): coordinator_module.async_call_later,
    (coordinator_module, "GestureEngine"): coordinator_module.GestureEngine,
    (matter_core_module, "time"): matter_core_module.time,
    (matter_core_module, "async_track_time_interval"): (
        matter_core_module.async_track_time_interval
    ),
}


def _drift() -> list[str]:
    drift = [
        f"{module.__name__}.{name}"
        for (module, name), original in _PRISTINE.items()
        if getattr(module, name) is not original
    ]
    if time.monotonic is not _REAL_MONOTONIC:
        drift.append("time.monotonic")
    return drift


@pytest.fixture(autouse=True)
def pristine_modules() -> Iterator[None]:
    """Every test starts with the production modules unpatched.

    A patch that leaked from one test would otherwise make the next one depend
    on order. This turns such a leak into a loud failure at the next test.
    """
    drift = _drift()
    if drift:
        raise LabSafetyViolation(f"a previous test left a patch behind: {drift}")
    yield


@pytest.fixture(autouse=True, scope="session")
def pristine_after_the_last_test() -> Iterator[None]:
    """The same check once more after the very last test has been torn down."""
    yield
    drift = _drift()
    if drift:
        raise LabSafetyViolation(f"the lab left a production module patched: {drift}")


@pytest.fixture(autouse=True)
def network_attempts() -> Iterator[list[str]]:
    """Refuse every non-loopback network operation; yield what was tried."""
    attempts: list[str] = []
    guard = NetworkGuard(attempts)
    guard.install()
    try:
        yield attempts
    finally:
        not_restored = guard.uninstall()
    if not_restored:
        raise LabSafetyViolation(f"the network guard was not removed: {not_restored}")
    if attempts:
        raise LabSafetyViolation(f"the lab tried to reach {attempts}")


@pytest.fixture
def lab(monkeypatch: pytest.MonkeyPatch) -> Iterator[LabHarness]:
    harness = LabHarness(monkeypatch)
    yield harness
    harness.close()
    left = harness.leftovers_at_close
    if left != {"timers": [], "subscribers": 0, "state_listeners": 0, "tasks": 0}:
        raise LabSafetyViolation(f"the shutdown left something running: {left}")
    if harness.safety.unacknowledged:
        raise LabSafetyViolation(
            f"unacknowledged safety events: {harness.safety.unacknowledged}"
        )
