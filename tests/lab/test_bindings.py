"""B: the production ``LightBinding`` driven by synthetic Matter events.

The expected values are plain arithmetic from the binding's documented settings
(a 3 % step of the 0-255 brightness range is 7.65 units, a 20 % minimum is 51),
never a call into the binding's own functions. The binding is attached through
``BilresaCoordinator.async_setup_bindings`` from its stored config data.
"""

from __future__ import annotations

from typing import Any

from .fake_matter import E2490_ENDPOINTS, Wire, e2489_node, e2490_node
from .targets import LightTarget

NODE = 14
UP1 = E2490_ENDPOINTS[1]["up"]
DOWN1 = E2490_ENDPOINTS[1]["down"]
BTN1 = E2490_ENDPOINTS[1]["button"]


def light_binding(**extra: Any) -> dict[str, Any]:
    """Channel 1 of the wheel, brightness mode, 3 % linear steps, no fade."""
    return {
        "node_id": NODE,
        "channel": 1,
        "target": "light.lab",
        "mode": "brightness",
        "step": 3,
        "step_curve": "linear",
        "transition": 0.0,
        **extra,
    }


def _notch(lab, wire: Wire, when: float, endpoint: int) -> None:
    """One physical notch at ``when`` seconds (the documented single-notch stream)."""
    lab.play([(when, event) for event in wire.scroll(endpoint, complete=1)])


def _sent(lab) -> list[tuple[float, str, dict[str, Any], str]]:
    return [(i["t"], i["service"], i["data"], i["status"]) for i in lab.spy.intents]


def _setup(lab, light: LightTarget, **binding: Any) -> Wire:
    lab.add_target(light)
    lab.load(e2490_node(NODE))
    lab.setup_bindings(light_binding(**binding))
    return Wire(NODE)


# -- B01 / B02: brightness ---------------------------------------------------


def test_b01_a_light_that_is_off_starts_at_the_first_step(lab) -> None:
    """Off, one notch up: 3 % of 255 = 7.65, sent as the integer 8."""
    wire = _setup(lab, LightTarget("light.lab", on=False, brightness=0))
    _notch(lab, wire, 0.0, UP1)

    assert _sent(lab) == [
        (0.0, "turn_on", {"brightness": 8, "transition": 0.0}, "accepted")
    ]
    assert lab.registry.target("light.lab").value() == 8


def test_b01_the_first_step_is_never_below_the_minimum(lab) -> None:
    """A 20 % minimum is 51 of 255: the first step from off lands there, not at 8."""
    wire = _setup(
        lab, LightTarget("light.lab", on=False, brightness=0), min_brightness=20
    )
    _notch(lab, wire, 0.0, UP1)

    assert _sent(lab)[0][2]["brightness"] == 51


def test_b01_scrolling_down_never_switches_a_dark_light_on(lab) -> None:
    wire = _setup(lab, LightTarget("light.lab", on=False, brightness=0))
    _notch(lab, wire, 0.0, DOWN1)

    assert lab.spy.intents == []
    assert [a["reason"] for a in lab.dispatcher.activity if a["reason"]] == [
        "light_already_off"
    ]


def test_b02_the_top_is_clamped_and_then_unchanged(lab) -> None:
    """250 + 7.65 = 257.65 is clamped to 255; at 255 nothing is sent again."""
    wire = _setup(lab, LightTarget("light.lab", brightness=250))
    _notch(lab, wire, 0.0, UP1)
    _notch(lab, wire, 1.0, UP1)

    assert _sent(lab) == [
        (0.0, "turn_on", {"brightness": 255, "transition": 0.0}, "accepted")
    ]
    assert "target_unchanged" in [a["reason"] for a in lab.dispatcher.activity]


def test_b02_the_minimum_is_a_floor_when_it_is_above_zero(lab) -> None:
    """55 - 7.65 = 47.35 is below the 51 floor: sent as 51, then unchanged."""
    wire = _setup(lab, LightTarget("light.lab", brightness=55), min_brightness=20)
    _notch(lab, wire, 0.0, DOWN1)
    _notch(lab, wire, 1.0, DOWN1)

    assert _sent(lab) == [
        (0.0, "turn_on", {"brightness": 51, "transition": 0.0}, "accepted")
    ]


def test_b02_a_zero_minimum_switches_the_light_off(lab) -> None:
    """With a minimum of 0 %, going below it is "off", as the checklist says."""
    wire = _setup(lab, LightTarget("light.lab", brightness=5), min_brightness=0)
    _notch(lab, wire, 0.0, DOWN1)

    assert _sent(lab) == [(0.0, "turn_off", {"transition": 0.0}, "accepted")]
    assert lab.registry.target("light.lab").value() == 0


def test_b02_a_batch_is_one_sum_not_five_steps(lab) -> None:
    """From 100, five notches (1 eager + 4) are 100 + 5 x 7.65 = 138.25 -> 138.

    The first notch is sent at once (107.65 -> 108); the other four arrive in
    the same instant, inside the 0.18 s command interval, so they are held and
    sent once at 0.18 s, from the tracked 107.65 + 4 x 7.65 = 138.25.
    """
    wire = _setup(lab, LightTarget("light.lab", brightness=100))
    gesture = wire.scroll(UP1, ongoing=(5,), complete=5)
    lab.play([(0.0, event) for event in gesture])
    lab.advance(1.0)

    assert [(t, d["brightness"]) for t, _, d, _ in _sent(lab)] == [
        (0.0, 108),
        (0.18, 138),
    ]
    assert lab.registry.target("light.lab").value() == 138


def test_b_a_delayed_echo_does_not_pull_the_next_step_back(lab) -> None:
    """The light reports each value 0.4 s late; the next notch continues from
    the binding's own target (107.65 + 7.65 = 115.3, then 122.95), not from the
    stale report.
    """
    wire = _setup(lab, LightTarget("light.lab", brightness=100, echo_delay=0.4))
    _notch(lab, wire, 0.0, UP1)
    _notch(lab, wire, 0.1, UP1)
    _notch(lab, wire, 2.0, UP1)
    lab.advance(1.0)

    assert [d["brightness"] for _, _, d, _ in _sent(lab)] == [108, 115, 123]
    requested = [h for h in lab.registry.history if h["event"] == "requested"]
    reported = [h for h in lab.registry.history if h["event"] == "reported"]
    assert [h["brightness"] for h in requested] == [108, 115, 123]
    assert [h["value"] for h in reported] == [108, 115, 123]
    # Requested versus reported: every report arrives 0.4 s after its request.
    assert [
        round(r["t"] - q["t"], 3) for q, r in zip(requested, reported, strict=True)
    ] == [
        0.4,
        0.4,
        0.4,
    ]


def test_b_the_first_notch_is_never_faded(lab) -> None:
    """With a 1 s transition configured, the first notch of a scroll is sent
    with transition 0.0 (the eager response; see ``_smoothing_transition``).
    """
    wire = _setup(lab, LightTarget("light.lab", brightness=100), transition=1.0)
    _notch(lab, wire, 0.0, UP1)

    assert lab.spy.intents[0]["data"] == {"brightness": 108, "transition": 0.0}
    assert lab.registry.target("light.lab").value() == 108


def test_b_a_fade_reports_the_new_level_only_when_it_ends(lab) -> None:
    """The second notch of the same scroll is sent with the whole 1 s transition,
    so the light keeps reporting the old level for 1 s and then the new one:
    request at 0.5 s (107.65 + 7.65 = 115.3 -> 115), report at 1.5 s.
    """
    wire = _setup(lab, LightTarget("light.lab", brightness=100), transition=1.0)
    _notch(lab, wire, 0.0, UP1)
    _notch(lab, wire, 0.5, UP1)

    assert [d for _, _, d, _ in _sent(lab)] == [
        {"brightness": 108, "transition": 0.0},
        {"brightness": 115, "transition": 1.0},
    ]
    lab.at(1.4)
    assert lab.registry.target("light.lab").value() == 108, "still fading"
    lab.at(1.6)
    assert lab.registry.target("light.lab").value() == 115, "the fade has ended"


# -- buttons ----------------------------------------------------------------


def test_e2490_single_press_toggles_the_target_once(lab) -> None:
    lab.add_target(LightTarget("light.lab", on=True, brightness=120))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(
        {
            "node_id": NODE,
            "channel": 1,
            "target": "light.lab",
            "mode": "brightness",
            "click_action": "toggle",
            "click_target": "light.lab",
        }
    )
    wire = Wire(NODE)
    lab.play([(0.0, event) for event in wire.click(BTN1, 1)])

    # gesture_verbs sends a toggle through the ``homeassistant`` domain.
    assert [(i["domain"], i["service"], i["status"]) for i in lab.spy.intents] == [
        ("homeassistant", "toggle", "accepted")
    ]
    assert lab.registry.target("light.lab").value() == 0


def test_e2489_overflow_never_clicks_and_the_next_single_still_works(lab) -> None:
    """Complete(0) after three rapid taps leaves the light alone; a normal
    single press afterwards toggles it exactly once.
    """
    lab.add_target(LightTarget("light.lab", on=True, brightness=120))
    lab.load(e2489_node(9001))
    lab.setup_bindings(
        {
            "node_id": 9001,
            "endpoint": 1,
            "target": "light.lab",
            "mode": "brightness",
            "click_action": "toggle",
            "click_target": "light.lab",
        }
    )
    wire = Wire(9001)
    overflow = [
        wire.event(1, "initial_press"),
        wire.event(1, "short_release"),
        wire.event(1, "initial_press"),
        wire.event(1, "multi_press_ongoing", count=2),
        wire.event(1, "short_release"),
        wire.event(1, "multi_press_complete", count=0),
    ]
    lab.play([(0.0, event) for event in overflow])
    assert lab.spy.intents == []

    lab.play([(2.0, event) for event in wire.click(1, 1)])
    assert [(i["service"], i["status"]) for i in lab.spy.intents] == [
        ("toggle", "accepted")
    ]
