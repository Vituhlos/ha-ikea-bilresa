"""Phase 1: the read models must be deterministic, bounded and leak nothing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.ikea_bilresa.const import (
    CONF_BINDING_PROFILE,
    CONF_CHANNEL,
    CONF_CLICK_TARGET,
    CONF_NODE_ID,
    CONF_SCENES,
    CONF_TARGET,
    SUBENTRY_BINDING,
)
from custom_components.ikea_bilresa.device_link import MatterDeviceLink
from custom_components.ikea_bilresa.model import BilresaWheel, SwitchEndpoint
from custom_components.ikea_bilresa.panel_models import (
    CONTRACT_VERSION,
    async_overview_snapshot,
    wheel_key,
)

NODE_A = 13
NODE_B = 14
SERIAL = "household-serial"


def _wheel(node_id: int, channels: tuple[int, ...] = (1, 2, 3)) -> BilresaWheel:
    endpoints = {}
    ep = 1
    for channel in channels:
        for role in ("scroll_up", "scroll_down", "button"):
            endpoints[ep] = SwitchEndpoint(endpoint_id=ep, channel=channel, role=role)
            ep += 1
    return BilresaWheel(
        node_id=node_id,
        name="BILRESA scroll wheel",
        product_name="BILRESA scroll wheel",
        serial=SERIAL,
        endpoints=endpoints,
    )


def _subentry(node_id: int, channel: int, **data) -> SimpleNamespace:
    return SimpleNamespace(
        subentry_type=SUBENTRY_BINDING,
        data={CONF_NODE_ID: node_id, CONF_CHANNEL: channel, **data},
    )


def _entry(wheels, subentries=()) -> SimpleNamespace:
    coordinator = SimpleNamespace(
        url="ws://matter/ws",
        wheels={w.node_id: w for w in wheels},
        matter_server_info={"compressed_fabric_id": 2},
        connected=True,
        event_source="core_matter_client",
    )
    return SimpleNamespace(
        subentries={str(i): s for i, s in enumerate(subentries)},
        runtime_data=coordinator,
    )


def _hass(states=None) -> SimpleNamespace:
    store = states or {}
    return SimpleNamespace(states=SimpleNamespace(get=lambda eid: store.get(eid)))


def _state(value, friendly_name=None) -> SimpleNamespace:
    return SimpleNamespace(
        state=value,
        attributes={"friendly_name": friendly_name} if friendly_name else {},
    )


def _patch(
    monkeypatch,
    *,
    device=None,
    availability="connected",
    area="Living room",
    entity_ids=None,
) -> None:
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_models.resolve_matter_device",
        lambda _hass, **_kw: MatterDeviceLink(device, frozenset()),
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_models.wheel_availability",
        lambda _hass, _device: availability,
    )
    registry = MagicMock()
    registry.async_get_entity_id.side_effect = lambda _d, _p, unique: (
        entity_ids or {}
    ).get(unique)
    registry.async_get.return_value = None
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_models.er.async_get",
        lambda _hass: registry,
    )
    area_registry = MagicMock()
    area_registry.async_get_area.return_value = (
        SimpleNamespace(name=area) if area else None
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel_models.ar.async_get",
        lambda _hass: area_registry,
    )


# -- the opaque key --------------------------------------------------------


def test_key_is_stable_and_hides_the_node_id() -> None:
    """It must survive a reload, and never be the node ID."""
    assert wheel_key(NODE_A) == wheel_key(NODE_A)
    assert wheel_key(NODE_A) != wheel_key(NODE_B)
    assert str(NODE_A) not in wheel_key(NODE_A)


# -- the snapshot ----------------------------------------------------------


def test_snapshot_uses_the_user_name_not_the_product_name(monkeypatch) -> None:
    """model.py sets wheel.name to the product name, identical for every wheel."""
    device = SimpleNamespace(
        id="dev", name_by_user="Kolecko obyvak", name="Matter device", area_id="area-1"
    )
    _patch(monkeypatch, device=device)

    result = async_overview_snapshot(_hass(), _entry([_wheel(NODE_A)]))

    assert result["wheels"][0]["name"] == "Kolecko obyvak"
    assert result["wheels"][0]["area"] == "Living room"


def test_snapshot_leaks_no_identifiers(monkeypatch) -> None:
    """No node ID, no serial, no product name, no Matter URL."""
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))

    result = async_overview_snapshot(_hass(), _entry([_wheel(NODE_A)]))

    rendered = str(result)
    assert SERIAL not in rendered
    assert "ws://matter/ws" not in rendered
    assert "BILRESA scroll wheel" not in rendered
    assert f"'{NODE_A}'" not in rendered
    assert result["contract_version"] == CONTRACT_VERSION


def test_channels_come_from_the_device_not_a_hard_coded_three(monkeypatch) -> None:
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))

    result = async_overview_snapshot(_hass(), _entry([_wheel(NODE_A, channels=(1, 2))]))

    assert [c["channel"] for c in result["wheels"][0]["channels"]] == [1, 2]


def test_unconfigured_channel_is_reported_not_omitted(monkeypatch) -> None:
    """The grid must be able to show 'not configured' and offer a binding."""
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [
            _subentry(
                NODE_A, 1, **{CONF_BINDING_PROFILE: "light", CONF_TARGET: "light.a"}
            )
        ],
    )

    channels = async_overview_snapshot(_hass(), entry)["wheels"][0]["channels"]

    assert channels[0]["profile"] == "light"
    assert channels[1]["profile"] is None
    assert channels[1]["behaviour"] is None


def test_a_binding_for_another_wheel_is_not_borrowed(monkeypatch) -> None:
    """Subentries are keyed by node; channel 1 exists on every wheel."""
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A), _wheel(NODE_B)],
        [_subentry(NODE_B, 1, **{CONF_BINDING_PROFILE: "media", CONF_TARGET: "m.b"})],
    )

    result = async_overview_snapshot(_hass(), entry)
    by_key = {w["key"]: w for w in result["wheels"]}

    assert by_key[wheel_key(NODE_A)]["channels"][0]["profile"] is None
    assert by_key[wheel_key(NODE_B)]["channels"][0]["profile"] == "media"


def test_missing_target_is_flagged(monkeypatch) -> None:
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [
            _subentry(
                NODE_A, 1, **{CONF_BINDING_PROFILE: "light", CONF_TARGET: "light.gone"}
            )
        ],
    )

    channels = async_overview_snapshot(_hass(), entry)["wheels"][0]["channels"]

    assert channels[0]["target_missing"] is True


def test_a_dead_click_target_flags_the_channel(monkeypatch) -> None:
    """A binding can dim one entity and toggle another; either can vanish."""
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [
            _subentry(
                NODE_A,
                1,
                **{
                    CONF_BINDING_PROFILE: "light",
                    CONF_TARGET: "light.ok",
                    CONF_CLICK_TARGET: "switch.gone",
                },
            )
        ],
    )
    hass = _hass({"light.ok": _state("on", "Main light")})

    channels = async_overview_snapshot(hass, entry)["wheels"][0]["channels"]

    assert channels[0]["target_label"] == "Main light"
    assert channels[0]["target_missing"] is True


def test_scene_binding_reports_its_count(monkeypatch) -> None:
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [
            _subentry(
                NODE_A,
                2,
                **{
                    CONF_BINDING_PROFILE: "scenes",
                    CONF_TARGET: "light.a",
                    CONF_SCENES: ["scene.a", "scene.b", "scene.c"],
                },
            )
        ],
    )
    hass = _hass({"light.a": _state("on", "Lamp")})

    channels = async_overview_snapshot(hass, entry)["wheels"][0]["channels"]

    assert channels[1]["behaviour"] == "Scenes (3)"


# -- last activity ---------------------------------------------------------


def test_last_activity_picks_the_newest_channel(monkeypatch) -> None:
    _patch(
        monkeypatch,
        device=SimpleNamespace(id="d", name_by_user="A", area_id=None),
        entity_ids={
            f"{NODE_A}_ch1": "event.a_ch1",
            f"{NODE_A}_ch2": "event.a_ch2",
        },
    )
    hass = _hass(
        {
            "event.a_ch1": _state("2026-07-16T10:00:00+00:00"),
            "event.a_ch2": _state("2026-07-16T11:00:00+00:00"),
        }
    )

    wheel = async_overview_snapshot(hass, _entry([_wheel(NODE_A)]))["wheels"][0]

    assert wheel["last_activity"] == "2026-07-16T11:00:00+00:00"
    assert wheel["last_active_channel"] == 2


def test_no_activity_after_restart_is_none_not_a_fault(monkeypatch) -> None:
    """EventEntity does not restore state. Empty means 'nothing yet'."""
    _patch(
        monkeypatch,
        device=SimpleNamespace(id="d", name_by_user="A", area_id=None),
        entity_ids={f"{NODE_A}_ch1": "event.a_ch1"},
    )
    hass = _hass({"event.a_ch1": _state("unknown")})

    wheel = async_overview_snapshot(hass, _entry([_wheel(NODE_A)]))["wheels"][0]

    assert wheel["last_activity"] is None
    assert wheel["last_active_channel"] is None
    # and the wheel itself is still reported, not dropped
    assert wheel["availability"] == "connected"


# -- degraded and malformed ------------------------------------------------


def test_unlinked_wheel_still_appears(monkeypatch) -> None:
    """A wheel that never linked is degraded, not invisible."""
    _patch(monkeypatch, device=None, availability="unknown")

    wheel = async_overview_snapshot(_hass(), _entry([_wheel(NODE_A)]))["wheels"][0]

    assert wheel["linked_to_matter"] is False
    assert wheel["availability"] == "unknown"
    assert wheel["area"] is None


def test_no_wheels_is_an_empty_snapshot_not_an_error(monkeypatch) -> None:
    _patch(monkeypatch)

    result = async_overview_snapshot(_hass(), _entry([]))

    assert result["wheels"] == []
    assert result["matter_connected"] is True


def test_malformed_subentry_does_not_raise(monkeypatch) -> None:
    """A channel that is not an int must be skipped, not crash the panel."""
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [
            SimpleNamespace(
                subentry_type=SUBENTRY_BINDING,
                data={CONF_NODE_ID: NODE_A, CONF_CHANNEL: "one"},
            ),
            SimpleNamespace(subentry_type="something_else", data={}),
        ],
    )

    channels = async_overview_snapshot(_hass(), entry)["wheels"][0]["channels"]

    assert all(c["profile"] is None for c in channels)


def test_snapshot_is_deterministic(monkeypatch) -> None:
    """Same state in, same bytes out — wheels sorted, not dict-ordered."""
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry([_wheel(NODE_B), _wheel(NODE_A)])
    hass = _hass()

    first = async_overview_snapshot(hass, entry)
    second = async_overview_snapshot(hass, entry)

    assert first == second
    assert [w["key"] for w in first["wheels"]] == [wheel_key(NODE_A), wheel_key(NODE_B)]
