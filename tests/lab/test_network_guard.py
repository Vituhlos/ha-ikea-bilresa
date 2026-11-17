"""The network guard: every outbound path is refused before any I/O.

Nothing here can reach a network. Methods are called on a stand-in object or
through the guarded name before the real function; destinations are the
documentation ranges (192.0.2.0/24, 2001:db8::/32) and a name under the reserved
``.invalid`` TLD. The probes of a deliberately incomplete guard never call the
real function either (see ``NetworkGuard._probing``).

The autouse ``network_attempts`` fixture installs the guard; these tests read its
record, then clear it so the fixture's own teardown stays quiet.
"""

from __future__ import annotations

import _socket
import asyncio
import socket
from typing import Any

import pytest

from .net_guard import (
    DATAGRAM_SEND,
    LOOP_METHODS,
    RESOLVERS,
    NetworkGuard,
    address_allowed,
    host_allowed,
)
from .service_spy import LabSafetyViolation

FAR4 = ("192.0.2.1", 5580)
FAR6 = ("2001:db8::1", 5580, 0, 0)
NAME = "matter-server.invalid"


def _stand_in() -> Any:
    """Not a socket: any attempt to really use it raises TypeError."""
    return object()


# -- what is allowed and what is not -------------------------------------------


@pytest.mark.parametrize(
    ("host", "lookup", "allowed"),
    [
        ("127.0.0.1", False, True),
        ("127.0.0.2", False, True),
        ("::1", False, True),
        ("[::1]", False, True),
        ("::ffff:127.0.0.1", False, True),
        ("localhost", False, True),
        ("LOCALHOST", False, True),
        (b"127.0.0.1", False, True),
        ("0.0.0.0", True, True),  # a wildcard is fine to look up, never to reach
        ("0.0.0.0", False, False),
        (None, True, True),
        (None, False, False),
        ("192.0.2.1", False, False),
        ("192.0.2.1", True, False),
        ("10.0.0.1", False, False),
        ("2001:db8::1", False, False),
        ("fe80::1%eth0", False, False),
        ("::ffff:192.0.2.1", False, False),
        (NAME, False, False),
        ("example.com", True, False),
        ("localhost.evil.example", False, False),
    ],
)
def test_which_hosts_are_allowed(host: Any, lookup: bool, allowed: bool) -> None:
    assert host_allowed(host, lookup=lookup) is allowed


def test_which_socket_addresses_are_allowed() -> None:
    assert address_allowed(("127.0.0.1", 80)) is True
    assert address_allowed(("::1", 80, 0, 0)) is True
    assert address_allowed("/tmp/unix.sock") is True  # an AF_UNIX path
    assert address_allowed(b"\0abstract") is True
    assert address_allowed(None) is True  # a connected socket: already checked
    assert address_allowed(FAR4) is False
    assert address_allowed(FAR6) is False
    assert address_allowed((NAME, 5580)) is False
    assert address_allowed(()) is False


# -- socket objects: TCP and UDP, IPv4 and IPv6 ---------------------------------


def test_the_installed_socket_class_is_the_guard() -> None:
    assert socket.socket.__name__ == "GuardedLabSocket"


@pytest.mark.parametrize("address", [FAR4, FAR6, (NAME, 5580)])
def test_tcp_connect_and_connect_ex_are_refused(
    address: Any, network_attempts: list[str]
) -> None:
    with pytest.raises(LabSafetyViolation):
        socket.socket.connect(_stand_in(), address)
    with pytest.raises(LabSafetyViolation):
        socket.socket.connect_ex(_stand_in(), address)

    host = address[0]
    assert network_attempts == [f"connect:{host}", f"connect_ex:{host}"]
    network_attempts.clear()


@pytest.mark.parametrize("address", [FAR4, FAR6, (NAME, 5353)])
def test_udp_sendto_and_sendmsg_are_refused(
    address: Any, network_attempts: list[str]
) -> None:
    with pytest.raises(LabSafetyViolation):
        socket.socket.sendto(_stand_in(), b"x", address)  # sendto(data, address)
    with pytest.raises(LabSafetyViolation):
        socket.socket.sendto(_stand_in(), b"x", 0, address)  # (data, flags, address)
    with pytest.raises(LabSafetyViolation):
        getattr(socket.socket, "sendmsg")(_stand_in(), [b"x"], [], 0, address)  # noqa: B009

    host = address[0]
    assert network_attempts == [f"sendto:{host}", f"sendto:{host}", f"sendmsg:{host}"]
    network_attempts.clear()


# -- name resolution ------------------------------------------------------------


@pytest.mark.parametrize("module", [socket, _socket], ids=["socket", "_socket"])
def test_every_resolver_refuses_before_any_dns_query(
    module: Any, network_attempts: list[str]
) -> None:
    """The Python names and the C module they are built on."""
    calls = {
        "getaddrinfo": (NAME, 5580),
        "gethostbyname": (NAME,),
        "gethostbyname_ex": (NAME,),
        "gethostbyaddr": ("192.0.2.1",),
        "getnameinfo": (FAR4, 0),
    }
    assert set(calls) == set(RESOLVERS)
    for name, args in calls.items():
        with pytest.raises(LabSafetyViolation):
            getattr(module, name)(*args)

    assert network_attempts == [
        "getaddrinfo:" + NAME,
        "gethostbyname:" + NAME,
        "gethostbyname_ex:" + NAME,
        "gethostbyaddr:192.0.2.1",
        "getnameinfo:192.0.2.1",
    ]
    network_attempts.clear()


def test_an_ip_literal_is_not_looked_up_either(network_attempts: list[str]) -> None:
    for host in ("192.0.2.1", "2001:db8::1"):
        with pytest.raises(LabSafetyViolation):
            socket.getaddrinfo(host, 5580)

    assert network_attempts == ["getaddrinfo:192.0.2.1", "getaddrinfo:2001:db8::1"]
    network_attempts.clear()


def test_higher_level_helpers_end_in_the_same_refusal(
    network_attempts: list[str],
) -> None:
    """``create_connection`` and ``getfqdn`` resolve first, and are refused there."""
    with pytest.raises(LabSafetyViolation):
        socket.create_connection((NAME, 5580), timeout=0.1)
    with pytest.raises(LabSafetyViolation):
        socket.create_connection(("2001:db8::1", 5580), timeout=0.1)
    with pytest.raises(LabSafetyViolation):
        socket.getfqdn("192.0.2.1")

    assert network_attempts == [
        "getaddrinfo:" + NAME,
        "getaddrinfo:2001:db8::1",
        "gethostbyaddr:192.0.2.1",
    ]
    network_attempts.clear()


# -- another socket object does not get around it ------------------------------


def test_every_way_of_making_a_socket_gives_a_guarded_one() -> None:
    """``socketpair`` (what the event loop itself uses) and ``dup`` return the guard.

    Both are loopback / Unix only, so they are allowed on every platform and
    create no outside traffic. The sockets are closed at once.
    """
    first, second = socket.socketpair()
    try:
        duplicate = first.dup()
        try:
            for made in (first, second, duplicate):
                assert type(made) is socket.socket
        finally:
            duplicate.close()
    finally:
        first.close()
        second.close()


# -- asyncio ----------------------------------------------------------------------


async def test_asyncio_connections_are_refused_before_a_socket_exists(
    network_attempts: list[str],
) -> None:
    """The Windows Proactor loop connects without ``socket.connect``: guarded too."""
    loop = asyncio.get_running_loop()
    for host in ("192.0.2.1", "2001:db8::1", NAME):
        with pytest.raises(LabSafetyViolation):
            await loop.create_connection(asyncio.Protocol, host, 5580)
    with pytest.raises(LabSafetyViolation):
        await asyncio.open_connection("192.0.2.1", 5580)

    assert network_attempts == [
        "create_connection:192.0.2.1",
        "create_connection:2001:db8::1",
        "create_connection:" + NAME,
        "create_connection:192.0.2.1",
    ]
    network_attempts.clear()


async def test_asyncio_datagrams_and_raw_socket_calls_are_refused(
    network_attempts: list[str],
) -> None:
    loop = asyncio.get_running_loop()
    with pytest.raises(LabSafetyViolation):
        await loop.create_datagram_endpoint(
            asyncio.DatagramProtocol, remote_addr=("192.0.2.1", 5353)
        )
    with pytest.raises(LabSafetyViolation):
        await loop.sock_connect(_stand_in(), FAR4)
    with pytest.raises(LabSafetyViolation):
        await loop.sock_sendto(_stand_in(), b"x", FAR6)

    assert network_attempts == [
        "create_datagram_endpoint:192.0.2.1",
        "sock_connect:192.0.2.1",
        "sock_sendto:2001:db8::1",
    ]
    network_attempts.clear()


async def test_asyncio_name_lookups_are_refused_in_the_executor(
    network_attempts: list[str],
) -> None:
    with pytest.raises(LabSafetyViolation):
        await asyncio.get_running_loop().getaddrinfo(NAME, 5580)

    assert network_attempts == ["getaddrinfo:" + NAME]
    network_attempts.clear()


# -- the probes, and a guard that has a hole --------------------------------------


def test_a_complete_guard_leaves_no_synchronous_path_uncovered() -> None:
    guard = NetworkGuard([])
    guard.install()
    try:
        assert guard.uncovered() == []
    finally:
        assert guard.uninstall() == []


async def test_a_complete_guard_leaves_no_asyncio_path_uncovered() -> None:
    guard = NetworkGuard([])
    guard.install()
    try:
        assert await guard.uncovered_async() == []
    finally:
        assert guard.uninstall() == []


@pytest.mark.parametrize(
    "hole",
    ["connect", "connect_ex", "sendto", "sendmsg", DATAGRAM_SEND, *RESOLVERS],
)
def test_a_guard_with_a_hole_is_caught_by_the_probes(hole: str) -> None:
    """Mutation: leave one path unguarded; the probes must name exactly that path."""
    guard = NetworkGuard([], skip=frozenset({hole}))
    guard.install()
    try:
        assert guard.uncovered() == [hole]
    finally:
        assert guard.uninstall() == []


@pytest.mark.parametrize("hole", LOOP_METHODS)
async def test_an_asyncio_guard_with_a_hole_is_caught(hole: str) -> None:
    guard = NetworkGuard([], skip=frozenset({hole}))
    guard.install()
    try:
        missed = await guard.uncovered_async()
    finally:
        assert guard.uninstall() == []
    assert missed and all(entry.endswith("." + hole) for entry in missed)


def test_with_no_guard_at_all_every_path_is_reported() -> None:
    """Mutation: the whole guard switched off (every path skipped)."""
    everything = frozenset(
        {
            "connect",
            "connect_ex",
            "sendto",
            "sendmsg",
            DATAGRAM_SEND,
            *RESOLVERS,
            *LOOP_METHODS,
        }
    )
    guard = NetworkGuard([], skip=everything)
    guard.install()
    try:
        assert len(guard.uncovered()) == 10
    finally:
        assert guard.uninstall() == []


# -- cleanup ----------------------------------------------------------------------


def test_installing_and_removing_the_guard_restores_everything() -> None:
    before = {
        "socket": socket.socket,
        **{name: getattr(socket, name) for name in RESOLVERS},
        **{f"_{name}": getattr(_socket, name) for name in RESOLVERS},
    }
    guard = NetworkGuard([])
    guard.install()
    assert socket.socket is not before["socket"]
    assert guard.uninstall() == []

    assert socket.socket is before["socket"]
    for name in RESOLVERS:
        assert getattr(socket, name) is before[name]
        assert getattr(_socket, name) is before[f"_{name}"]


# -- findings of the review of 26d1210 ------------------------------------------


@pytest.mark.parametrize("address", [FAR4, FAR6, (NAME, 5353)])
def test_an_unconnected_datagram_transport_cannot_send_outside(
    address: Any, network_attempts: list[str]
) -> None:
    """``transport.sendto(data, addr)`` of an endpoint made with ``local_addr`` only.

    Called on a stand-in transport for every datagram transport class (selector
    and Proactor), so nothing is sent; the guard refuses before the send.
    """
    from .net_guard import NetworkGuard as _Guard

    classes = _Guard._datagram_transports()
    assert classes, "no datagram transport class found"
    for cls in classes:
        with pytest.raises(LabSafetyViolation):
            vars(cls)["sendto"](_stand_in(), b"x", address)

    host = address[0]
    assert network_attempts == [f"{DATAGRAM_SEND}:{host}"] * len(classes)
    network_attempts.clear()


async def test_asyncio_raw_socket_calls_are_checked_when_the_address_is_a_keyword(
    network_attempts: list[str],
) -> None:
    """``address=`` given by keyword next to positional arguments is still checked."""
    loop = asyncio.get_running_loop()
    with pytest.raises(LabSafetyViolation):
        await loop.sock_sendto(_stand_in(), b"x", address=FAR4)
    with pytest.raises(LabSafetyViolation):
        await loop.sock_connect(_stand_in(), address=FAR6)
    with pytest.raises(LabSafetyViolation):
        await loop.sock_connect(_stand_in(), address=(NAME, 5580))

    assert network_attempts == [
        "sock_sendto:192.0.2.1",
        "sock_connect:2001:db8::1",
        "sock_connect:" + NAME,
    ]
    network_attempts.clear()
