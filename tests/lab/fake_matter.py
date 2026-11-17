"""Synthetic Matter nodes and Switch events, written as literal wire facts.

Everything below is taken from the Matter specification and from
``docs/DEVICE_REFERENCE.md`` / ``docs/DEVICE_REFERENCE_BUTTON.md``, and it is
deliberately *not* read from ``custom_components/ikea_bilresa/const.py``: the
production constants must be able to disagree with it and fail a test, or the
lab would only ever agree with itself.

Provenance of what is built here:

* ``e2490_node``: ``synthetic_spec``. Endpoint layout and MultiPressMax are from
  the documented node structure; the TagList shape is the one ``test_model.py``
  uses. No raw E2490 node dump is committed to the repository (UNKNOWN).
* ``e2489_node``: ``recorded_derived``. The sanitized node shape captured from a
  real E2489 and kept in ``tests/fixtures/bilresa_dual_button_node.json``.
* events: ``synthetic_spec``, in the order the documented raw streams show.
"""

from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
from typing import Any

SWITCH_CLUSTER = 59

EVENT_ID = {
    "initial_press": 1,
    "long_press": 2,
    "short_release": 3,
    "long_release": 4,
    "multi_press_ongoing": 5,
    "multi_press_complete": 6,
}

# docs/DEVICE_REFERENCE.md, "Matter node structure": channel -> endpoints.
E2490_ENDPOINTS = {
    1: {"up": 1, "down": 2, "button": 3},
    2: {"up": 4, "down": 5, "button": 6},
    3: {"up": 7, "down": 8, "button": 9},
}
E2490_SCROLL_MAX = 18
E2490_BUTTON_MAX = 3

_DUAL_BUTTON_FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "bilresa_dual_button_node.json"
)


def e2490_node(node_id: int = 14, *, scroll_max: int = E2490_SCROLL_MAX) -> dict:
    """A three-channel scroll wheel, as the Matter Server would list it."""
    attributes: dict[str, Any] = {
        "0/40/3": "BILRESA scroll wheel",
        "0/40/15": "SYNTHETIC-E2490",
        "0/29/3": list(range(1, 10)),
    }
    for channel, endpoints in E2490_ENDPOINTS.items():
        label = str(channel)
        for role, endpoint in endpoints.items():
            attributes[f"{endpoint}/59/65532"] = 30 if role == "button" else 22
            attributes[f"{endpoint}/59/2"] = (
                E2490_BUTTON_MAX if role == "button" else scroll_max
            )
        # TagList entries use TLV field numbers as string keys:
        # "1" namespace, "2" tag, "3" label.
        position = {"1": 8, "2": 6, "3": label}
        attributes[f"{endpoints['up']}/29/4"] = [position, {"1": 67, "2": 3}]
        attributes[f"{endpoints['down']}/29/4"] = [position, {"1": 67, "2": 4}]
        attributes[f"{endpoints['button']}/29/4"] = [
            position,
            {"1": 67, "2": 8, "3": "button"},
        ]
    return {"node_id": node_id, "attributes": attributes}


def e2489_node(node_id: int = 9001) -> dict:
    """The two-button remote, from the sanitized real capture."""
    node = copy.deepcopy(json.loads(_DUAL_BUTTON_FIXTURE.read_text(encoding="utf-8")))
    node["node_id"] = node_id
    return node


class Wire:
    """Builds ``node_event`` messages for one node, numbered like the server's."""

    def __init__(self, node_id: int) -> None:
        self.node_id = node_id
        self._numbers = itertools.count(1)

    def event(
        self, endpoint: int, name: str, *, count: int | None = None
    ) -> dict[str, Any]:
        if name in ("initial_press", "long_press"):
            data: dict[str, Any] = {"newPosition": 1}
        elif name in ("short_release", "long_release"):
            data = {"previousPosition": 1}
        elif name == "multi_press_ongoing":
            data = {"newPosition": 1}
            if count is not None:
                data["currentNumberOfPressesCounted"] = count
        elif name == "multi_press_complete":
            data = {"previousPosition": 0}
            if count is not None:
                data["totalNumberOfPressesCounted"] = count
        else:
            raise ValueError(name)
        return self.raw(endpoint, EVENT_ID[name], data)

    def raw(
        self,
        endpoint: int | None,
        event_id: int | None,
        data: Any,
        *,
        cluster_id: int = SWITCH_CLUSTER,
        node_id: int | None = None,
    ) -> dict[str, Any]:
        """Any event at all, including malformed ones, for the rejection tests."""
        message: dict[str, Any] = {
            "node_id": self.node_id if node_id is None else node_id,
            "cluster_id": cluster_id,
            "event_number": next(self._numbers),
            "priority": 1,
            "timestamp": 0,
            "timestamp_type": 0,
            "data": data,
        }
        if endpoint is not None:
            message["endpoint_id"] = endpoint
        if event_id is not None:
            message["event_id"] = event_id
        return message

    def scroll(
        self,
        endpoint: int,
        *,
        ongoing: tuple[int, ...] = (),
        complete: int | None = None,
        initial: bool = True,
    ) -> list[dict[str, Any]]:
        """One scroll gesture in the documented order.

        ``initial_press``, the cumulative ``multi_press_ongoing`` reports, a
        ``short_release``, then ``multi_press_complete`` with the total.
        """
        events: list[dict[str, Any]] = []
        if initial:
            events.append(self.event(endpoint, "initial_press"))
        events.extend(
            self.event(endpoint, "multi_press_ongoing", count=count)
            for count in ongoing
        )
        events.append(self.event(endpoint, "short_release"))
        if complete is not None:
            events.append(self.event(endpoint, "multi_press_complete", count=complete))
        return events

    def click(self, endpoint: int, presses: int) -> list[dict[str, Any]]:
        """One button click of ``presses`` presses, as the raw stream shows it.

        A double press is ``initial_press, short_release, initial_press,
        multi_press_ongoing(2), short_release, multi_press_complete(2)``
        (docs/DEVICE_REFERENCE_BUTTON.md, Matter Server 9.1.0 stream).
        """
        events: list[dict[str, Any]] = []
        for number in range(1, presses + 1):
            events.append(self.event(endpoint, "initial_press"))
            if number >= 2:
                events.append(self.event(endpoint, "multi_press_ongoing", count=number))
            events.append(self.event(endpoint, "short_release"))
        events.append(self.event(endpoint, "multi_press_complete", count=presses))
        return events
