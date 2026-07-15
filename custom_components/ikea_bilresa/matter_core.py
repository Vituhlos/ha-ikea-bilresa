"""Adapter for reusing Home Assistant's active Matter client.

The core Matter integration already owns a connected ``MatterClient`` and its
``start_listening`` subscription. This adapter consumes that client's supported
``subscribe_events`` callback instead of opening another WebSocket. All access
is feature-detected so older/incompatible Home Assistant versions can fall back
to the integration's standalone passive listener.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

EventCallback = Callable[[str, Any], None]
UnavailableCallback = Callable[[str], None]
_CLIENT_CHECK_INTERVAL = timedelta(seconds=5)
_UNAVAILABLE_CHECKS_BEFORE_FALLBACK = 2


class CoreMatterUnavailable(RuntimeError):
    """Raised when the loaded core Matter client cannot be reused safely."""


def _as_mapping(value: Any) -> dict[str, Any]:
    """Convert Matter client dataclasses to the mapping used by the decoder."""
    if isinstance(value, dict):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    try:
        return dict(vars(value))
    except TypeError as err:
        raise CoreMatterUnavailable(
            f"Unsupported Matter client data type: {type(value).__name__}"
        ) from err


class CoreMatterEventSource:
    """Expose core MatterClient events through the local listener interface."""

    source = "core_matter_client"

    def __init__(
        self,
        hass: HomeAssistant,
        configured_url: str,
        on_event: EventCallback,
        on_unavailable: UnavailableCallback | None = None,
    ) -> None:
        self._hass = hass
        self._configured_url = configured_url.rstrip("/")
        self._on_event = on_event
        self._on_unavailable = on_unavailable
        self._matter_client: Any = None
        self._unsubscribe: Callable[[], None] | None = None
        self._monitor_unsubscribe: Callable[[], None] | None = None
        self._connected = False
        self._unavailable_checks = 0

    @property
    def server_info(self) -> dict[str, Any] | None:
        """Return Matter Server information from the reused client."""
        if self._matter_client is None:
            return None
        info = getattr(self._matter_client, "server_info", None)
        return _as_mapping(info) if info is not None else None

    async def start(self) -> None:
        """Subscribe to the already-running core Matter client."""
        try:
            self._attach_client(self._get_loaded_client())
        except (AttributeError, IndexError, RuntimeError, TypeError) as err:
            self._unsubscribe_safely()
            self._matter_client = None
            raise CoreMatterUnavailable(
                "Home Assistant's loaded Matter client is not reusable"
            ) from err

        self._monitor_unsubscribe = async_track_time_interval(
            self._hass, self._check_client, _CLIENT_CHECK_INTERVAL
        )
        _LOGGER.info("Reusing Home Assistant's existing Matter client event stream")

    async def stop(self) -> None:
        """Unsubscribe without stopping the core-owned Matter client."""
        if self._monitor_unsubscribe is not None:
            self._monitor_unsubscribe()
            self._monitor_unsubscribe = None
        self._unsubscribe_safely()
        self._matter_client = None
        self._set_connected(False)

    def _get_loaded_client(self) -> Any:
        entries = self._hass.config_entries.async_loaded_entries("matter")
        entry = entries[0]
        core_url = entry.data.get("url")
        if (
            not isinstance(core_url, str)
            or core_url.rstrip("/") != self._configured_url
        ):
            raise RuntimeError("Core Matter entry uses a different server URL")
        runtime_data = entry.runtime_data
        matter_client = runtime_data.adapter.matter_client
        if not callable(matter_client.subscribe_events) or not callable(
            matter_client.get_nodes
        ):
            raise TypeError("Matter client event API is not callable")
        return matter_client

    @callback
    def _attach_client(self, matter_client: Any) -> None:
        self._matter_client = matter_client
        self._unsubscribe = matter_client.subscribe_events(callback=self._handle_event)
        nodes = [self._node_to_mapping(node) for node in matter_client.get_nodes()]
        self._set_connected(True)
        self._unavailable_checks = 0
        self._on_event("__nodes__", nodes)

    @callback
    def _check_client(self, _now: Any) -> None:
        """Reattach after the core Matter config entry reloads."""
        try:
            matter_client = self._get_loaded_client()
        except (AttributeError, IndexError, RuntimeError, TypeError) as err:
            if self._matter_client is not None:
                self._unsubscribe_safely()
                self._matter_client = None
                self._set_connected(False)
            self._unavailable_checks += 1
            if (
                self._on_unavailable is not None
                and self._unavailable_checks >= _UNAVAILABLE_CHECKS_BEFORE_FALLBACK
            ):
                self._on_unavailable(str(err))
            return
        if matter_client is self._matter_client:
            return
        self._unsubscribe_safely()
        self._matter_client = None
        self._set_connected(False)
        try:
            self._attach_client(matter_client)
        except (AttributeError, RuntimeError, TypeError) as err:
            self._unsubscribe_safely()
            self._matter_client = None
            _LOGGER.warning("Failed to reattach to core Matter client: %s", err)
            if self._on_unavailable is not None:
                self._on_unavailable(str(err))

    @callback
    def _handle_event(self, event_type: Any, data: Any) -> None:
        event_name = getattr(event_type, "value", event_type)
        if event_name in ("node_added", "node_updated"):
            self._on_event("node_added", self._node_to_mapping(data))
        elif event_name == "node_removed":
            self._on_event("node_removed", data)
        elif event_name == "node_event":
            self._on_event("node_event", _as_mapping(data))
        elif event_name == "server_shutdown":
            self._set_connected(False)

    @staticmethod
    def _node_to_mapping(node: Any) -> dict[str, Any]:
        node_data = getattr(node, "node_data", node)
        return _as_mapping(node_data)

    @callback
    def _unsubscribe_safely(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    @callback
    def _set_connected(self, connected: bool) -> None:
        if self._connected == connected:
            return
        self._connected = connected
        self._on_event("__connected__" if connected else "__disconnected__", None)
