"""Fixtures for the lab: a harness that cleans up and checks its own safety.

Two guards run around every test in this directory:

* a network tripwire: any connection or name lookup that is not loopback is
  refused and recorded, whatever the platform's socket plugin does;
* the harness teardown: no refusal may be left unacknowledged, and the
  coordinator's shutdown must leave no timer, subscription or task behind.
"""

from __future__ import annotations

from collections.abc import Iterator
import socket
import time
from typing import Any

import pytest

from custom_components.ikea_bilresa import binding as binding_module
from custom_components.ikea_bilresa import coordinator as coordinator_module

from .harness import LabHarness
from .service_spy import LabSafetyViolation

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}

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
    """Every test starts and ends with the production modules unpatched.

    A patch that leaked from one test would otherwise make the next one depend
    on order. This turns such a leak into a loud failure at the next test.
    """
    assert _drift() == [], "a previous test left a patch behind"
    yield


@pytest.fixture(autouse=True, scope="session")
def pristine_after_the_last_test() -> Iterator[None]:
    """The same check once more after the very last test has been torn down."""
    yield
    assert _drift() == [], "the lab left a production module patched"


@pytest.fixture(autouse=True)
def network_attempts(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    """Refuse every non-loopback connection or lookup; yield what was tried."""
    attempts: list[str] = []
    real_connect = socket.socket.connect
    real_getaddrinfo = socket.getaddrinfo

    def _host(address: Any) -> str | None:
        return address[0] if isinstance(address, tuple) and address else None

    def connect(self: socket.socket, address: Any) -> Any:
        host = _host(address)
        if host is not None and host not in _LOOPBACK:
            attempts.append(str(host))
            raise LabSafetyViolation(f"lab refused a connection to {host}")
        return real_connect(self, address)

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        if host is not None and str(host) not in _LOOPBACK:
            attempts.append(str(host))
            raise LabSafetyViolation(f"lab refused a lookup of {host}")
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    yield attempts
    assert not attempts, f"the lab tried to reach {attempts}"


@pytest.fixture
def lab(monkeypatch: pytest.MonkeyPatch) -> Iterator[LabHarness]:
    harness = LabHarness(monkeypatch)
    yield harness
    harness.close()
    assert harness.leftovers_at_close == {
        "timers": [],
        "subscribers": 0,
        "state_listeners": 0,
        "tasks": 0,
    }, "the shutdown left something running"
    assert not harness.safety.unacknowledged, harness.safety.unacknowledged
