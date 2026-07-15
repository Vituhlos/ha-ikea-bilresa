"""Minimal, dependency-free WebSocket client for the Matter Server add-on.

This is intentionally tiny: it is a *passive listener*. It connects to the
Matter Server WebSocket, issues a single ``start_listening`` command and then
forwards every event message to a callback. It never sends device commands,
so it cannot interfere with the core Matter integration that shares the same
server.

Protocol (python-matter-server / matter.js server, schema 11):
  * On connect the server sends a ServerInfo message.
  * The client sends ``{"message_id": id, "command": "start_listening",
    "args": {}}``.
  * The server replies with ``{"message_id": id, "result": [<all nodes>]}``.
  * Afterwards the server streams ``{"event": "<type>", "data": <payload>}``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
import logging
from typing import Any

from aiohttp import ClientSession, WSMsgType

_LOGGER = logging.getLogger(__name__)

# on_event(event_type: str, data: Any) -> None
#   event_type == "__nodes__"  -> data is the initial list of nodes
#   event_type == "node_event" -> data is a MatterNodeEvent dict
EventCallback = Callable[[str, Any], None]

_RECONNECT_MAX = 60


class MatterWSClient:
    """A resilient, read-only WebSocket listener for the Matter Server."""

    def __init__(
        self, url: str, session: ClientSession, on_event: EventCallback
    ) -> None:
        self._url = url
        self._session = session
        self._on_event = on_event
        self._task: asyncio.Task | None = None
        self._closing = False
        self._msg_id = 0
        self.server_info: dict[str, Any] | None = None

    async def start(self) -> None:
        """Start the background connection loop."""
        self._closing = False
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the client and close the connection."""
        self._closing = True
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    def _next_id(self) -> str:
        self._msg_id += 1
        return str(self._msg_id)

    async def _run_loop(self) -> None:
        backoff = 1
        while not self._closing:
            try:
                await self._connect_and_listen()
                backoff = 1
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - resilience is the point
                _LOGGER.warning(
                    "Matter WS connection dropped (%s); reconnecting in %ss",
                    err,
                    backoff,
                )
            if self._closing:
                break
            try:
                await asyncio.sleep(backoff)
            except asyncio.CancelledError:
                raise
            backoff = min(backoff * 2, _RECONNECT_MAX)

    async def _connect_and_listen(self) -> None:
        _LOGGER.debug("Connecting to Matter Server at %s", self._url)
        pending: dict[str, asyncio.Future] = {}
        async with self._session.ws_connect(
            self._url, heartbeat=30, max_msg_size=0
        ) as ws:
            # First message is always the ServerInfo message.
            self.server_info = await ws.receive_json()
            _LOGGER.debug(
                "Matter Server connected: %s",
                (self.server_info or {}).get("sdk_version"),
            )
            self._on_event("__connected__", None)

            # Kick off start_listening; its result (the node dump) is delivered
            # via the read loop below and dispatched from the done-callback.
            listen_id = self._next_id()
            loop = asyncio.get_running_loop()
            listen_future: asyncio.Future = loop.create_future()
            pending[listen_id] = listen_future

            def _deliver_nodes(fut: asyncio.Future) -> None:
                if fut.cancelled() or fut.exception():
                    return
                self._on_event("__nodes__", fut.result())

            listen_future.add_done_callback(_deliver_nodes)
            await ws.send_json(
                {"message_id": listen_id, "command": "start_listening", "args": {}}
            )

            try:
                async for msg in ws:
                    if msg.type == WSMsgType.TEXT:
                        self._handle_message(msg.json(), pending)
                    elif msg.type in (
                        WSMsgType.CLOSE,
                        WSMsgType.CLOSING,
                        WSMsgType.CLOSED,
                        WSMsgType.ERROR,
                    ):
                        break
            finally:
                # Connection ended: fail pending futures and signal a disconnect.
                for fut in pending.values():
                    if not fut.done():
                        fut.set_exception(ConnectionError("Matter WS closed"))
                self._on_event("__disconnected__", None)

    def _handle_message(
        self, data: dict[str, Any], pending: dict[str, asyncio.Future]
    ) -> None:
        # Event message (streamed) — no message_id, has "event".
        if "event" in data:
            self._on_event(data["event"], data.get("data"))
            return

        # Command result — correlate by message_id.
        msg_id = data.get("message_id")
        future = pending.pop(msg_id, None) if msg_id is not None else None
        if future is None or future.done():
            return
        if "error_code" in data or "errorCode" in data or "error" in data:
            future.set_exception(RuntimeError(f"Matter command error: {data}"))
        else:
            future.set_result(data.get("result"))
