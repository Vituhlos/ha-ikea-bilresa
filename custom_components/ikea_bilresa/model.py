"""Decode the BILRESA Matter node structure and switch events.

Everything here is derived from the node's *own* Matter descriptors, so the
integration adapts to any BILRESA regardless of endpoint numbering or channel
count. Nothing is hard-coded to a specific device.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from .const import (
    ATTR_BASIC_PRODUCT_NAME,
    ATTR_DESCRIPTOR_PARTS_LIST,
    ATTR_DESCRIPTOR_TAGLIST,
    ATTR_SWITCH_MULTI_PRESS_MAX,
    BILRESA_PRODUCT_MATCH,
    CLUSTER_BASIC_INFO,
    CLUSTER_DESCRIPTOR,
    CLUSTER_SWITCH,
    DATA_CURRENT_COUNT,
    DATA_TOTAL_COUNT,
    NS_SWITCHES,
    ROLE_BUTTON,
    ROLE_SCROLL_DOWN,
    ROLE_SCROLL_UP,
    SWITCH_EVENT_NAMES,
    SWTAG_DOWN,
    SWTAG_UP,
    TAG_KEY_LABEL,
    TAG_KEY_NAMESPACE,
    TAG_KEY_TAG,
    VARIANT_DUAL_BUTTON,
    VARIANT_WHEEL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SwitchEndpoint:
    """One Switch endpoint of the wheel (a scroll direction or a button)."""

    endpoint_id: int
    channel: int | None
    role: str  # ROLE_SCROLL_UP / ROLE_SCROLL_DOWN / ROLE_BUTTON
    multi_press_max: int | None = None  # Switch.MultiPressMax, if the node reports it


def _is_dual_button_shape(endpoints: dict[int, SwitchEndpoint]) -> bool:
    """Return whether endpoint structure matches the two-button E2489.

    The real E2489 labels its two physical buttons with the Matter semantic
    tags ``up`` and ``down``. Those tags describe the face of the remote; they
    do not make the device a rotary wheel. The stable structural distinction is
    that both endpoints lack the wheel's numeric channel label.

    Requiring exactly two endpoints keeps a partial or malformed wheel dump
    from being promoted to a supported dual button.
    """
    return len(endpoints) == 2 and all(
        endpoint.channel is None for endpoint in endpoints.values()
    )


@dataclass(slots=True)
class BilresaWheel:
    """A discovered BILRESA device (a scroll wheel or the dual button).

    The class name is historical: it also carries the button-only variant. The
    device kind is derived from endpoint shape via `variant`, never stored, so it
    can never disagree with the endpoints it is computed from.
    """

    node_id: int
    name: str
    product_name: str
    serial: str | None
    endpoints: dict[int, SwitchEndpoint]  # endpoint_id -> SwitchEndpoint

    @property
    def variant(self) -> str:
        """Return the device variant from endpoint shape (wheel vs dual button)."""
        if _is_dual_button_shape(self.endpoints):
            return VARIANT_DUAL_BUTTON
        return VARIANT_WHEEL

    @property
    def is_dual_button(self) -> bool:
        """Whether this is the button-only BILRESA (E2489), not a scroll wheel."""
        return self.variant == VARIANT_DUAL_BUTTON


def _attr(attrs: dict[str, Any], ep: int, cluster: int, attr: int) -> Any:
    return attrs.get(f"{ep}/{cluster}/{attr}")


def _has_cluster(attrs: dict[str, Any], ep: int, cluster: int) -> bool:
    prefix = f"{ep}/{cluster}/"
    return any(key.startswith(prefix) for key in attrs)


def parse_taglist(taglist: Any) -> tuple[int | None, str]:
    """Return (channel, role) from an endpoint's Descriptor TagList."""
    channel: int | None = None
    has_up = has_down = False
    for tag in taglist or []:
        if not isinstance(tag, dict):
            continue
        namespace = tag.get(TAG_KEY_NAMESPACE)
        value = tag.get(TAG_KEY_TAG)
        label = tag.get(TAG_KEY_LABEL)
        if label is not None and str(label).isdigit():
            channel = int(label)
        if namespace == NS_SWITCHES:
            if value == SWTAG_UP:
                has_up = True
            elif value == SWTAG_DOWN:
                has_down = True
    if has_up:
        role = ROLE_SCROLL_UP
    elif has_down:
        role = ROLE_SCROLL_DOWN
    else:
        role = ROLE_BUTTON
    return channel, role


def parse_node(node: dict[str, Any]) -> BilresaWheel | None:
    """Return a BilresaWheel if the node is a BILRESA, else None."""
    if not isinstance(node, dict):
        return None
    attrs = node.get("attributes") or {}
    if not isinstance(attrs, dict):
        return None

    product = str(_attr(attrs, 0, CLUSTER_BASIC_INFO, ATTR_BASIC_PRODUCT_NAME) or "")
    if BILRESA_PRODUCT_MATCH not in product.lower():
        return None

    node_id = node.get("node_id")
    if node_id is None:
        return None

    parts = _attr(attrs, 0, CLUSTER_DESCRIPTOR, ATTR_DESCRIPTOR_PARTS_LIST) or []
    endpoints: dict[int, SwitchEndpoint] = {}
    for ep in parts:
        if not _has_cluster(attrs, ep, CLUSTER_SWITCH):
            continue
        taglist = _attr(attrs, ep, CLUSTER_DESCRIPTOR, ATTR_DESCRIPTOR_TAGLIST)
        channel, role = parse_taglist(taglist)
        raw_max = _attr(attrs, ep, CLUSTER_SWITCH, ATTR_SWITCH_MULTI_PRESS_MAX)
        multi_press_max = (
            raw_max
            if isinstance(raw_max, int) and not isinstance(raw_max, bool)
            else None
        )
        endpoints[ep] = SwitchEndpoint(
            endpoint_id=ep,
            channel=channel,
            role=role,
            multi_press_max=multi_press_max,
        )

    if not endpoints:
        return None

    if _is_dual_button_shape(endpoints):
        # E2489 uses the semantic up/down tags for its two physical buttons.
        # Normalize both endpoints here so every downstream consumer (gesture
        # engine, event entities, device triggers, bindings and panel) sees the
        # button semantics that the hardware actually exposes.
        for endpoint in endpoints.values():
            endpoint.role = ROLE_BUTTON

    serial = node.get("attributes", {}).get(f"0/{CLUSTER_BASIC_INFO}/15")
    return BilresaWheel(
        node_id=node_id,
        name=product or f"BILRESA {node_id}",
        product_name=product,
        serial=serial,
        endpoints=endpoints,
    )


def decode_event(
    wheel: BilresaWheel, node_event: dict[str, Any]
) -> dict[str, Any] | None:
    """Decode a Matter Switch node event into a structured wheel action."""
    if node_event.get("cluster_id") != CLUSTER_SWITCH:
        return None
    endpoint_id = node_event.get("endpoint_id")
    if endpoint_id is None:
        return None
    switch = wheel.endpoints.get(endpoint_id)
    if switch is None:
        return None

    event_id = node_event.get("event_id")
    if event_id is None:
        return None
    data = node_event.get("data") or {}
    if not isinstance(data, dict):
        data = {}

    event_type = SWITCH_EVENT_NAMES.get(event_id, f"event_{event_id}")
    count = data.get(DATA_CURRENT_COUNT)
    if count is None:
        count = data.get(DATA_TOTAL_COUNT)

    return {
        "node_id": wheel.node_id,
        "wheel_name": wheel.name,
        "endpoint_id": endpoint_id,
        "channel": switch.channel,
        "role": switch.role,  # scroll_up / scroll_down / button
        "event_type": event_type,  # initial_press / multi_press_ongoing / ...
        "count": count,  # number of notches for multi-press events
        "raw": data,
    }
