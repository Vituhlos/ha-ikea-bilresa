"""Phase 1: the read models must be deterministic, bounded and leak nothing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.ikea_bilresa.const import (
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_HOLD_ACTION,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_SCENES,
    CONF_TARGET,
    CONF_TRIPLE_TARGET,
    HOLD_RAMP,
    MODE_BRIGHTNESS,
    MODE_VOLUME,
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


def _dual_button(node_id: int) -> BilresaWheel:
    """The E2489: two button endpoints, no rotary channels."""
    return BilresaWheel(
        node_id=node_id,
        name="BILRESA dual button",
        product_name="BILRESA dual button",
        serial=SERIAL,
        endpoints={
            1: SwitchEndpoint(endpoint_id=1, channel=None, role="button"),
            2: SwitchEndpoint(endpoint_id=2, channel=None, role="button"),
        },
    )


def _subentry(node_id: int, channel: int, **data) -> SimpleNamespace:
    """A subentry shaped like the ones Home Assistant actually stores.

    node_id and channel are **strings** here on purpose: they come from
    config-flow selectors, and a live diagnostics dump shows `"channel": "1"`.
    The first version of these fixtures used ints, matched the code's wrong
    assumption, and let a grid ship that reported every configured channel as
    empty. Fixtures that agree with the code prove nothing.
    """
    return SimpleNamespace(
        subentry_id=f"binding-{node_id}-{channel}",
        subentry_type=SUBENTRY_BINDING,
        title=f"Wheel · Channel {channel}",
        data={CONF_NODE_ID: str(node_id), CONF_CHANNEL: str(channel), **data},
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


def _hass(states=None, language="en") -> SimpleNamespace:
    store = states or {}
    return SimpleNamespace(
        states=SimpleNamespace(get=lambda eid: store.get(eid)),
        # Real hass always has this. The fixture did not, and the production code
        # reading hass.config.language blew up on every test at once.
        config=SimpleNamespace(language=language),
    )


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


def test_snapshot_excludes_the_dual_button(monkeypatch) -> None:
    """A dual button is not a wheel and must not render as a zero-channel card."""
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))

    result = async_overview_snapshot(
        _hass(), _entry([_wheel(NODE_A), _dual_button(15)])
    )

    assert len(result["wheels"]) == 1
    assert result["wheels"][0]["key"] == wheel_key(NODE_A)


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
        [_subentry(NODE_A, 1, **{CONF_MODE: MODE_BRIGHTNESS, CONF_TARGET: "light.a"})],
    )

    channels = async_overview_snapshot(_hass(), entry)["wheels"][0]["channels"]

    assert channels[0]["profile"] == MODE_BRIGHTNESS
    assert channels[0]["binding"]["id"] == f"binding-{NODE_A}-1"
    assert channels[0]["binding"]["data"][CONF_MODE] == MODE_BRIGHTNESS
    assert CONF_NODE_ID not in channels[0]["binding"]["data"]
    assert CONF_CHANNEL not in channels[0]["binding"]["data"]
    assert channels[1]["profile"] is None
    assert channels[1]["behaviour"] is None
    assert channels[1]["binding"] is None


def test_a_binding_for_another_wheel_is_not_borrowed(monkeypatch) -> None:
    """Subentries are keyed by node; channel 1 exists on every wheel."""
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A), _wheel(NODE_B)],
        [_subentry(NODE_B, 1, **{CONF_MODE: MODE_VOLUME, CONF_TARGET: "m.b"})],
    )

    result = async_overview_snapshot(_hass(), entry)
    by_key = {w["key"]: w for w in result["wheels"]}

    assert by_key[wheel_key(NODE_A)]["channels"][0]["profile"] is None
    assert by_key[wheel_key(NODE_B)]["channels"][0]["profile"] == MODE_VOLUME


def test_missing_target_is_flagged(monkeypatch) -> None:
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [
            _subentry(
                NODE_A, 1, **{CONF_MODE: MODE_BRIGHTNESS, CONF_TARGET: "light.gone"}
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
                    CONF_MODE: MODE_BRIGHTNESS,
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


def test_detail_actions_mirror_the_stored_binding(monkeypatch) -> None:
    """The detail describes runtime inputs without importing or executing it."""
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [
            _subentry(
                NODE_A,
                1,
                **{
                    CONF_MODE: MODE_BRIGHTNESS,
                    CONF_TARGET: "light.main",
                    CONF_CLICK_ACTION: "off",
                    CONF_CLICK_TARGET: "switch.click",
                    CONF_DOUBLE_TARGET: "switch.double",
                    CONF_TRIPLE_TARGET: "switch.triple",
                    CONF_HOLD_ACTION: HOLD_RAMP,
                },
            )
        ],
    )
    hass = _hass(
        {
            "light.main": _state("on", "Main light"),
            "switch.click": _state("on", "Bedside switch"),
            "switch.double": _state("off", "Reading switch"),
            "switch.triple": _state("off", "Movie switch"),
        }
    )

    actions = async_overview_snapshot(hass, entry)["wheels"][0]["channels"][0][
        "actions"
    ]
    by_gesture = {action["gesture"]: action for action in actions}

    assert list(by_gesture) == [
        "rotation",
        "short_press",
        "double_press",
        "triple_press",
        "hold",
        "release",
    ]
    assert by_gesture["rotation"]["action_label"] == "Adjust target"
    assert by_gesture["rotation"]["target_label"] == "Main light"
    assert by_gesture["short_press"]["action_label"] == "Turn off"
    assert by_gesture["short_press"]["target_label"] == "Bedside switch"
    assert by_gesture["double_press"]["target_label"] == "Reading switch"
    assert by_gesture["triple_press"]["target_label"] == "Movie switch"
    assert by_gesture["hold"]["action_label"] == "Ramp target"
    assert by_gesture["release"]["action_label"] == "Stop ramp"


def test_missing_secondary_action_target_flags_the_channel(monkeypatch) -> None:
    """Unavailable double/triple/hold targets must not hide in the detail."""
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [
            _subentry(
                NODE_A,
                1,
                **{
                    CONF_MODE: MODE_BRIGHTNESS,
                    CONF_TARGET: "light.ok",
                    CONF_DOUBLE_TARGET: "switch.gone",
                },
            )
        ],
    )
    hass = _hass({"light.ok": _state("on", "Main light")})

    channel = async_overview_snapshot(hass, entry)["wheels"][0]["channels"][0]
    double = next(
        action for action in channel["actions"] if action["gesture"] == "double_press"
    )

    assert channel["target_missing"] is True
    assert double["target_missing"] is True
    assert double["target_label"] == "switch.gone"


def test_scene_binding_reports_its_count(monkeypatch) -> None:
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [
            _subentry(
                NODE_A,
                2,
                **{
                    CONF_MODE: MODE_BRIGHTNESS,
                    CONF_TARGET: "light.a",
                    CONF_SCENES: ["scene.a", "scene.b", "scene.c"],
                },
            )
        ],
    )
    hass = _hass(
        {
            "light.a": _state("on", "Lamp"),
            "scene.a": _state("scening", "Evening"),
            "scene.b": _state("scening", "Reading"),
            "scene.c": _state("scening", "Movie"),
        }
    )

    channels = async_overview_snapshot(hass, entry)["wheels"][0]["channels"]

    assert channels[1]["behaviour"] == "Scenes (3)"
    short_press = channels[1]["actions"][1]
    assert short_press["gesture"] == "short_press"
    assert short_press["action_label"] == "Cycle scenes"
    assert short_press["target_label"] == "Evening / Reading / Movie"


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


# -- regressions from the first live deploy --------------------------------


def test_string_typed_subentry_still_matches_its_wheel(monkeypatch) -> None:
    """The exact shape a live diagnostics dump showed, verbatim.

    Home Assistant stored `"channel": "1"` and a string node_id. The grid
    compared them against an int wheel.node_id, matched nothing, and reported
    four configured channels as "not configured" on a real user's screen.
    """
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    live = SimpleNamespace(
        subentry_type=SUBENTRY_BINDING,
        data={
            "node_id": str(NODE_A),
            "channel": "1",
            "mode": "brightness",
            "target": "light.main",
            "step": 3,
            "click_action": "toggle",
            "button_response": "fast",
        },
    )
    hass = _hass({"light.main": _state("on", "Main light")})

    channels = async_overview_snapshot(hass, _entry([_wheel(NODE_A)], [live]))[
        "wheels"
    ][0]["channels"]

    assert channels[0]["profile"] == "brightness"
    assert channels[0]["behaviour"] == "Smooth dimming"
    assert channels[0]["target_label"] == "Main light"


def test_behaviour_comes_from_the_stored_mode(monkeypatch) -> None:
    """binding_profile is a config-flow field and is never written to storage."""
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [
            _subentry(NODE_A, 1, **{CONF_MODE: MODE_VOLUME, CONF_TARGET: "media.a"}),
            _subentry(NODE_A, 2, **{CONF_MODE: "cover_position", CONF_TARGET: "c.a"}),
        ],
    )
    hass = _hass(
        {"media.a": _state("playing", "Speaker"), "c.a": _state("open", "Blind")}
    )

    channels = async_overview_snapshot(hass, entry)["wheels"][0]["channels"]

    assert channels[0]["behaviour"] == "Volume"
    assert channels[1]["behaviour"] == "Cover position"


def test_a_binding_with_an_unknown_mode_is_not_called_unconfigured(
    monkeypatch,
) -> None:
    """ "Configured but odd" and "not configured" are different claims."""
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [_subentry(NODE_A, 1, **{CONF_MODE: "something_new", CONF_TARGET: "x.y"})],
    )
    hass = _hass({"x.y": _state("on", "Thing")})

    channels = async_overview_snapshot(hass, entry)["wheels"][0]["channels"]

    assert channels[0]["behaviour"] == "something_new"
    assert channels[0]["profile"] is not None


def test_a_nonsense_channel_is_skipped_not_crashed(monkeypatch) -> None:
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [
            SimpleNamespace(
                subentry_type=SUBENTRY_BINDING,
                data={"node_id": str(NODE_A), "channel": "not-a-number"},
            )
        ],
    )

    channels = async_overview_snapshot(_hass(), entry)["wheels"][0]["channels"]

    assert all(c["profile"] is None for c in channels)


def test_behaviour_labels_follow_the_instance_language(monkeypatch) -> None:
    """The grid shipped English to a Czech owner; this is the regression.

    The language comes from hass.config.language, which is the instance's and not
    each user's — Home Assistant offers a WebSocket handler no per-user locale.
    """
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [_subentry(NODE_A, 1, **{CONF_MODE: MODE_BRIGHTNESS, CONF_TARGET: "light.a"})],
    )
    states = {"light.a": _state("on", "Lampa")}

    czech = async_overview_snapshot(_hass(states, language="cs"), entry)
    english = async_overview_snapshot(_hass(states, language="en"), entry)

    assert czech["wheels"][0]["channels"][0]["behaviour"] == "Plynulé stmívání"
    assert english["wheels"][0]["channels"][0]["behaviour"] == "Smooth dimming"
    # the entity's own name is the user's and is never translated
    assert czech["wheels"][0]["channels"][0]["target_label"] == "Lampa"
    assert czech["wheels"][0]["channels"][0]["actions"][0]["action_label"] == (
        "Upravit cíl"
    )
    assert english["wheels"][0]["channels"][0]["actions"][0]["action_label"] == (
        "Adjust target"
    )


def test_an_unknown_instance_language_falls_back_to_english(monkeypatch) -> None:
    _patch(monkeypatch, device=SimpleNamespace(id="d", name_by_user="A", area_id=None))
    entry = _entry(
        [_wheel(NODE_A)],
        [_subentry(NODE_A, 1, **{CONF_MODE: MODE_BRIGHTNESS, CONF_TARGET: "light.a"})],
    )

    snapshot = async_overview_snapshot(_hass(language="de"), entry)

    assert snapshot["wheels"][0]["channels"][0]["behaviour"] == "Smooth dimming"
