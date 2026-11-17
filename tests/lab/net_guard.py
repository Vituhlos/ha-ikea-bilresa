"""A cross-platform, fail-closed guard against outbound network use.

The lab never talks to a network. The Home Assistant test plugin blocks sockets
on Linux, but a local Windows run switches that off, so the lab brings its own
guard, independent of it. It is layered over whatever guard is already there.

Inventory of the outbound entry points it covers (CPython 3.14):

* socket objects: ``connect``, ``connect_ex``, ``sendto``, ``sendmsg``. The
  ``socket.socket`` name is replaced by a guarded subclass, so every object made
  through it (``socket.socketpair``, ``socket.create_connection``, ``dup``,
  ``accept``, asyncio's own sockets) is guarded. ``send`` and ``sendall`` need a
  connected socket, and a connection is refused before it exists.
* name resolution: ``getaddrinfo``, ``gethostbyname``, ``gethostbyname_ex``,
  ``gethostbyaddr``, ``getnameinfo``, on ``socket`` and on the C module
  ``_socket`` they come from (``getfqdn`` and ``create_connection`` go through
  them).
* asyncio, because the Windows Proactor loop connects without ever calling
  ``socket.connect``: ``create_connection``, ``create_datagram_endpoint``,
  ``sock_connect``, ``sock_sendto``. ``open_connection`` goes through the first.

What stays allowed: loopback (IPv4 ``127.0.0.0/8``, IPv6 ``::1``, ``localhost``)
and Unix sockets, which the event loop itself needs.

What it cannot cover: a raw ``_socket.socket`` object made directly, because
that C type cannot be patched. Nothing in the lab does that, and no test here
tries it, because trying it would send a packet.

Every refusal raises ``LabSafetyViolation`` and is appended to ``attempts``,
before any packet or DNS query exists.
"""

from __future__ import annotations

import _socket
import asyncio
from collections.abc import Callable
import importlib
import ipaddress
import socket
from typing import Any

from .service_spy import LabSafetyViolation

_LOOPBACK_NAMES = {"localhost"}
# Bind-style wildcards are fine for a lookup (nothing is resolved), never as a
# destination.
_LOOKUP_ONLY = {"", "0.0.0.0", "::"}

RESOLVERS = (
    "getaddrinfo",
    "gethostbyname",
    "gethostbyname_ex",
    "gethostbyaddr",
    "getnameinfo",
)
SOCKET_METHODS = ("connect", "connect_ex", "sendto", "sendmsg")
LOOP_METHODS = (
    "create_connection",
    "create_datagram_endpoint",
    "sock_connect",
    "sock_sendto",
)


def _text(host: Any) -> str | None:
    if host is None:
        return None
    if isinstance(host, bytes | bytearray):
        return bytes(host).decode("ascii", "replace")
    return str(host)


def host_allowed(host: Any, *, lookup: bool) -> bool:
    """Whether ``host`` is loopback (or, for a lookup, a local wildcard)."""
    text = _text(host)
    if text is None:
        return lookup
    if lookup and text in _LOOKUP_ONLY:
        return True
    text = text.partition("%")[0].strip("[]")
    if text.lower() in _LOOPBACK_NAMES:
        return True
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return address.ipv4_mapped.is_loopback
    return address.is_loopback


def address_allowed(address: Any) -> bool:
    """Whether a socket address is loopback or a Unix socket path."""
    if address is None:
        return True
    if isinstance(address, tuple):
        return bool(address) and host_allowed(address[0], lookup=False)
    return True  # a str/bytes path is an AF_UNIX address


class NetworkGuard:
    """Installs the guards and records every refusal."""

    def __init__(self, attempts: list[str], *, skip: frozenset[str] = frozenset()):
        # ``skip`` exists only so a test can build a deliberately incomplete
        # guard and prove the probes notice (see ``uncovered``).
        self.attempts = attempts
        self._skip = skip
        self._saved: list[tuple[Any, str, Any]] = []
        # While probing, a call that gets past the guard returns at once instead
        # of reaching the real function: a probe can never cause network I/O.
        self._probing = False
        self._socket_class: type[socket.socket] | None = None

    # -- decisions -------------------------------------------------------

    def refuse(self, kind: str, target: Any) -> None:
        host = target[0] if isinstance(target, tuple) and target else target
        self.attempts.append(f"{kind}:{_text(host)}")
        raise LabSafetyViolation(f"the lab refused {kind} to {target!r}")

    def check_address(self, kind: str, address: Any) -> None:
        if not address_allowed(address):
            self.refuse(kind, address)

    def check_host(self, kind: str, host: Any) -> None:
        if not host_allowed(host, lookup=True):
            self.refuse(kind, host)

    # -- install / restore ----------------------------------------------

    def _swap(self, owner: Any, name: str, value: Any) -> None:
        self._saved.append((owner, name, getattr(owner, name)))
        setattr(owner, name, value)

    def install(self) -> None:
        self._install_socket_class()
        self._install_resolvers()
        self._install_loop_methods()

    def uninstall(self) -> list[str]:
        """Restore everything; return the names that did not come back."""
        for owner, name, original in reversed(self._saved):
            setattr(owner, name, original)
        broken = [
            f"{getattr(owner, '__name__', owner)}.{name}"
            for owner, name, original in self._saved
            if getattr(owner, name) is not original
        ]
        self._saved.clear()
        return broken

    def _install_socket_class(self) -> None:
        guard = self
        base = socket.socket

        class GuardedLabSocket(base):  # type: ignore[valid-type, misc]
            def connect(self, address: Any) -> Any:
                if "connect" not in guard._skip:
                    guard.check_address("connect", address)
                return super().connect(address)

            def connect_ex(self, address: Any) -> Any:
                if "connect_ex" not in guard._skip:
                    guard.check_address("connect_ex", address)
                return super().connect_ex(address)

            def sendto(self, data: Any, *args: Any) -> Any:
                if "sendto" not in guard._skip:
                    guard.check_address("sendto", args[-1] if args else None)
                return super().sendto(data, *args)

            def sendmsg(self, buffers: Any, *args: Any) -> Any:
                if "sendmsg" not in guard._skip:
                    guard.check_address("sendmsg", args[2] if len(args) > 2 else None)
                return super().sendmsg(buffers, *args)

        self._socket_class = GuardedLabSocket
        self._swap(socket, "socket", GuardedLabSocket)

    def _install_resolvers(self) -> None:
        for name in RESOLVERS:
            for module in (socket, _socket):
                original = getattr(module, name, None)
                if original is None:
                    continue
                self._swap(module, name, self._wrap_resolver(name, original))

    def _wrap_resolver(self, name: str, original: Callable[..., Any]) -> Any:
        guard = self

        def guarded(*args: Any, **kwargs: Any) -> Any:
            if name == "getnameinfo":
                sockaddr = args[0] if args else kwargs.get("sockaddr")
                host = sockaddr[0] if isinstance(sockaddr, tuple) and sockaddr else None
            else:
                host = args[0] if args else kwargs.get("host", kwargs.get("hostname"))
            if name not in guard._skip:
                guard.check_host(name, host)
            if guard._probing:
                return None
            return original(*args, **kwargs)

        guarded.__name__ = name
        return guarded

    def _install_loop_methods(self) -> None:
        for cls in self._loop_classes():
            for name in LOOP_METHODS:
                if name not in vars(cls):
                    continue
                self._swap(cls, name, self._wrap_loop_method(name, vars(cls)[name]))

    def _wrap_loop_method(self, name: str, original: Callable[..., Any]) -> Any:
        guard = self

        async def guarded(loop: Any, *args: Any, **kwargs: Any) -> Any:
            if name not in guard._skip:
                for target in _loop_destinations(name, args, kwargs):
                    guard.check_address(name, target)
            if guard._probing:
                return None
            return await original(loop, *args, **kwargs)

        guarded.__name__ = name
        return guarded

    # -- probes ----------------------------------------------------------

    def uncovered(self) -> list[str]:
        """Probe every synchronous path with inert arguments; list the ones that
        did not refuse. Nothing here creates a socket or touches the network:
        methods are called on a stand-in object and refuse before using it.
        """
        assert self._socket_class is not None
        sock: Any = self._socket_class  # methods called on a stand-in, unbound
        stand_in = object()
        far = ("192.0.2.1", 5580)
        far6 = ("2001:db8::1", 5580, 0, 0)
        probes: dict[str, Callable[[], Any]] = {
            "connect": lambda: sock.connect(stand_in, far),
            "connect_ex": lambda: sock.connect_ex(stand_in, far6),
            "sendto": lambda: sock.sendto(stand_in, b"x", far),
            "sendmsg": lambda: sock.sendmsg(stand_in, [b"x"], [], 0, far),
            "getaddrinfo": lambda: socket.getaddrinfo("matter-server.invalid", 5580),
            "gethostbyname": lambda: socket.gethostbyname("matter-server.invalid"),
            "gethostbyname_ex": lambda: socket.gethostbyname_ex(
                "matter-server.invalid"
            ),
            "gethostbyaddr": lambda: socket.gethostbyaddr("192.0.2.1"),
            "getnameinfo": lambda: socket.getnameinfo(far, 0),
        }
        missed = []
        self._probing = True
        try:
            for name, probe in probes.items():
                try:
                    probe()
                except LabSafetyViolation:
                    continue
                except Exception:  # noqa: BLE001 - something else answered
                    pass
                missed.append(name)
        finally:
            self._probing = False
        return missed

    async def uncovered_async(self) -> list[str]:
        """The same for the asyncio entry points, called on a stand-in loop."""
        stand_in = object()
        far = ("192.0.2.1", 5580)
        calls: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {
            "create_connection": ((asyncio.Protocol, "192.0.2.1", 5580), {}),
            "create_datagram_endpoint": (
                (asyncio.DatagramProtocol,),
                {"remote_addr": far},
            ),
            "sock_connect": ((object(), far), {}),
            "sock_sendto": ((object(), b"x", far), {}),
        }
        missed = []
        self._probing = True
        try:
            for name, (args, kwargs) in calls.items():
                for cls in self._loop_classes():
                    if name not in vars(cls):
                        continue
                    try:
                        await getattr(cls, name)(stand_in, *args, **kwargs)
                    except LabSafetyViolation:
                        continue
                    except Exception:  # noqa: BLE001
                        pass
                    missed.append(f"{cls.__name__}.{name}")
        finally:
            self._probing = False
        return missed

    @staticmethod
    def _loop_classes() -> list[type]:
        classes: list[type] = [
            asyncio.base_events.BaseEventLoop,
            asyncio.selector_events.BaseSelectorEventLoop,
        ]
        try:
            proactor = importlib.import_module("asyncio.proactor_events")
        except ImportError:  # pragma: no cover
            return classes
        return [*classes, proactor.BaseProactorEventLoop]


def _loop_destinations(name: str, args: tuple[Any, ...], kwargs: dict[str, Any]):
    """The destinations an asyncio call would connect or send to."""
    if name == "create_connection":
        host = args[1] if len(args) > 1 else kwargs.get("host")
        port = args[2] if len(args) > 2 else kwargs.get("port")
        if kwargs.get("sock") is not None or host is None:
            return []
        return [(host, port)]
    if name == "create_datagram_endpoint":
        remote = kwargs.get("remote_addr")
        return [remote] if remote else []
    if name in ("sock_connect", "sock_sendto"):
        address = args[-1] if args else kwargs.get("address")
        return [address]
    return []
