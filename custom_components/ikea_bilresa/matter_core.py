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
import time
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

EventCallback = Callable[[str, Any], None]
UnavailableCallback = Callable[[str], None]
_CLIENT_CHECK_INTERVAL = timedelta(seconds=5)
# The paths of a node's Switch.CurrentPosition values are looked up again at least
# this often, plus up to this much more per node so that the nodes do not all fall
# due in one update. A table changed in place with the same number of attributes
# is the one change the cache cannot see; this bounds how long it stays unseen.
_POSITION_PATH_MAX_AGE = 30.0
_POSITION_PATH_JITTER = 30
# A Matter Server app restart temporarily unloads the core Matter config entry.
# Keep preferring the supported core client for one minute before treating a
# runtime outage as permanent enough to require the compatibility WebSocket.
_UNAVAILABLE_CHECKS_BEFORE_FALLBACK = 12
_SWITCH_CLUSTER_ID = 0x003B
_SWITCH_CURRENT_POSITION_ATTRIBUTE_ID = 0


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
        self._switch_positions: dict[tuple[int, str], Any] = {}
        # Where each node keeps its Switch.CurrentPosition values, found once.
        # The key is the node id; the value is the attribute table the paths
        # were read from, its length then, the paths and when they were found. See
        # _current_switch_positions for when it is read again.
        self._position_paths: dict[
            int, tuple[dict[str, Any], int, tuple[str, ...], float]
        ] = {}

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
        self._switch_positions.clear()
        self._position_paths.clear()
        self._set_connected(False)

    def _get_loaded_client(self) -> Any:
        entries = self._hass.config_entries.async_loaded_entries("matter")
        if not entries:
            raise RuntimeError("Core Matter config entry is temporarily not loaded")
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
        self._position_paths.clear()
        self._switch_positions = self._current_switch_positions()
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
        except (AttributeError, IndexError, RuntimeError, TypeError) as err:
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
            self._forget_node(data)
            self._on_event("node_removed", data)
        elif event_name == "node_event":
            self._on_event("node_event", _as_mapping(data))
        elif event_name == "attribute_updated":
            # The Python client's catch-all callback intentionally supplies
            # only the new value. Its node cache is updated before callbacks,
            # so compare the cached Switch.CurrentPosition paths and restore
            # the full wire tuple expected by the local listener interface.
            self._forward_switch_position_updates()
        elif event_name == "server_shutdown":
            self._set_connected(False)

    @callback
    def _forget_node(self, node: Any) -> None:
        """Drop what the position lookup holds for a node that is gone.

        Each cache entry keeps the node's whole attribute table alive, so it must
        not wait for a later attribute update to be pruned: on a quiet install
        that update may not come, and repeated removals would pile tables up.
        """
        node_id = getattr(node, "node_id", node)
        if not isinstance(node_id, int) or isinstance(node_id, bool):
            return
        self._position_paths.pop(node_id, None)
        self._switch_positions = {
            key: value
            for key, value in self._switch_positions.items()
            if key[0] != node_id
        }

    @staticmethod
    def _is_switch_position_path(path: Any) -> bool:
        """Whether an attribute path is endpoint/0x3B/0, Switch.CurrentPosition."""
        if not isinstance(path, str):
            return False
        parts = path.split("/")
        if len(parts) != 3:
            return False
        try:
            _endpoint, cluster, attribute = (int(part) for part in parts)
        except ValueError:
            return False
        return (
            cluster == _SWITCH_CLUSTER_ID
            and attribute == _SWITCH_CURRENT_POSITION_ATTRIBUTE_ID
        )

    @staticmethod
    def _node_fields(node: Any) -> tuple[int, dict[str, Any]] | None:
        """A node's id and its live attribute table, without copying either.

        The table is read as it is: converting a node to a mapping copies every
        attribute recursively, and a house with many Matter devices has tens of
        thousands of them.
        """
        node_data = getattr(node, "node_data", node)
        if isinstance(node_data, dict):
            node_id = node_data.get("node_id")
            attributes = node_data.get("attributes")
        else:
            node_id = getattr(node_data, "node_id", None)
            attributes = getattr(node_data, "attributes", None)
        if not isinstance(node_id, int) or not isinstance(attributes, dict):
            return None
        return node_id, attributes

    @callback
    def _current_switch_positions(self) -> dict[tuple[int, str], Any]:
        """Read every node's Switch.CurrentPosition values from the live cache.

        An attribute update names only its new value, not the node or the path
        it belongs to, so every node's positions have to be read after each one.
        What must not be repeated is finding them: walking every attribute of
        every node took a minute or two of the Home Assistant event loop on an
        install with 63 nodes. The paths are found once per attribute table and
        read again when the table is another object or has another size, which is
        when a node was interviewed again or gained an attribute, and in any case
        every 30 to 60 seconds, so that a table changed in place without changing
        its size (the one change those two checks cannot see) is noticed soon.
        """
        positions: dict[tuple[int, str], Any] = {}
        seen: set[int] = set()
        now = time.monotonic()
        for node in self._matter_client.get_nodes():
            fields = self._node_fields(node)
            if fields is None:
                continue
            node_id, attributes = fields
            seen.add(node_id)
            cached = self._position_paths.get(node_id)
            if (
                cached is None
                or cached[0] is not attributes
                or cached[1] != len(attributes)
                or now - cached[3]
                > _POSITION_PATH_MAX_AGE + node_id % _POSITION_PATH_JITTER
            ):
                paths = tuple(
                    path for path in attributes if self._is_switch_position_path(path)
                )
                cached = (attributes, len(attributes), paths, now)
                self._position_paths[node_id] = cached
            for path in cached[2]:
                if path in attributes:
                    positions[(node_id, path)] = attributes[path]
        for node_id in self._position_paths.keys() - seen:
            del self._position_paths[node_id]
        return positions

    @callback
    def _forward_switch_position_updates(self) -> None:
        """Forward changed CurrentPosition values with node and path context."""
        if self._matter_client is None:
            return
        current = self._current_switch_positions()
        for key, value in current.items():
            if self._switch_positions.get(key) == value:
                continue
            node_id, path = key
            self._on_event("attribute_updated", [node_id, path, value])
        self._switch_positions = current

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
