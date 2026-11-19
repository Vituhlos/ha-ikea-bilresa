"""RC7: a press must not lose to a rotation that is still waiting to be sent.

The statement under test is the ``0.7.0-rc.7`` changelog (GitHub issue #63 and
pull request #59), not the binding's code:

* a fast scroll leaves a brightness command queued for a moment (the first notch
  goes out at once, the rest wait for the command interval); a press that is
  really sent, a scene or a run of actions cancels the queued rotation, so the
  light is not switched on again behind the press;
* a press that cannot run leaves the queue alone;
* a mute or playback press keeps a queued volume, a power press cancels it;
* the same holds when *another* binding of the same light does the pressing
  (two channels of one wheel, or two wheels);
* two bindings that only scroll one light behave as before: neither cancels
  the other.

The queued command of a burst is deterministic here: a gesture of five notches
sends the first at once and the other four 0.18 s later (the command interval),
so a press in between is exactly the case the changelog describes.
"""

from __future__ import annotations

from typing import Any

import pytest

from .fake_matter import E2490_ENDPOINTS, Wire, e2490_node
from .harness import LabHarness
from .targets import LightTarget, MediaPlayerTarget

NODE = 14
OTHER_NODE = 15
UP1 = E2490_ENDPOINTS[1]["up"]
BTN1 = E2490_ENDPOINTS[1]["button"]
DOWN2 = E2490_ENDPOINTS[2]["down"]
BTN2 = E2490_ENDPOINTS[2]["button"]
LIGHT = "light.lab"
SPEAKER = "media_player.lab_speaker"


def _channel_binding(
    node: int, channel: int, target: str, mode: str, **extra: Any
) -> dict[str, Any]:
    return {
        "node_id": node,
        "channel": channel,
        "target": target,
        "mode": mode,
        "step": 3 if mode == "brightness" else 10,
        "step_curve": "linear",
        "transition": 0.0,
        **extra,
    }


def _burst(lab: LabHarness, node: int, endpoint: int, when: float) -> None:
    """Five notches in one gesture: one sent now, four queued for 0.18 s."""
    wire = Wire(node)
    lab.play([(when, e) for e in wire.scroll(endpoint, ongoing=(5,), complete=5)])


def _click(lab: LabHarness, node: int, endpoint: int, when: float) -> None:
    wire = Wire(node)
    lab.play([(when, e) for e in wire.click(endpoint, 1)])


def _brightness_intents(lab: LabHarness) -> list[tuple[float, str, Any]]:
    return [
        (i["t"], i["service"], i["data"].get("brightness"))
        for i in lab.spy.intents
        if i["entity_id"] == LIGHT
    ]


# -- one binding, one light --------------------------------------------------------


def press_cancels_the_queued_rotation(lab: LabHarness) -> None:
    """Scroll burst at 0 s, a press that switches the light off at 0.05 s."""
    lab.add_target(LightTarget(LIGHT, brightness=100))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(
        _channel_binding(
            NODE, 1, LIGHT, "brightness", click_action="toggle", click_target=LIGHT
        )
    )
    _burst(lab, NODE, UP1, 0.0)
    assert [t for t, _, _ in _brightness_intents(lab)] == [0.0], "the rest is queued"
    _click(lab, NODE, BTN1, 0.05)
    lab.advance(2.0)

    sent = [(t, s) for t, s, _ in _brightness_intents(lab)]
    assert sent == [(0.0, "turn_on"), (0.05, "toggle")], "nothing is sent behind it"
    assert lab.registry.target(LIGHT).requested()["state"] == "off"
    seen = lab.registry.get(LIGHT)
    assert seen is not None and seen.state == "off"


def test_a_press_cancels_the_rotation_still_waiting_to_be_sent(lab) -> None:
    press_cancels_the_queued_rotation(lab)


def test_a_press_that_cannot_run_leaves_the_queue_alone(lab) -> None:
    """With no short-press action the press does nothing, and the burst completes:
    100 + 5 x 7.65 = 138.25, sent as 138 at 0.18 s after the eager 108.
    """
    lab.add_target(LightTarget(LIGHT, brightness=100))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(
        _channel_binding(
            NODE, 1, LIGHT, "brightness", click_action="none", click_target=LIGHT
        )
    )
    _burst(lab, NODE, UP1, 0.0)
    _click(lab, NODE, BTN1, 0.05)
    lab.advance(2.0)

    assert _brightness_intents(lab) == [
        (0.0, "turn_on", 108),
        (0.18, "turn_on", 138),
    ]


def test_a_scene_press_cancels_the_queued_rotation(lab) -> None:
    """A scene may change the light, so an older queued value must not follow it."""
    lab.add_target(LightTarget(LIGHT, brightness=100))
    lab.add_target(_Scene("scene.evening"))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(
        _channel_binding(
            NODE, 1, LIGHT, "brightness", scenes=["scene.evening"], click_target=LIGHT
        )
    )
    _burst(lab, NODE, UP1, 0.0)
    _click(lab, NODE, BTN1, 0.05)
    lab.advance(2.0)

    assert [i["service"] for i in lab.spy.intents] == ["turn_on", "turn_on"]
    assert [i["entity_id"] for i in lab.spy.intents] == [LIGHT, "scene.evening"]
    assert _brightness_intents(lab) == [(0.0, "turn_on", 108)]


# -- another binding presses ---------------------------------------------------------


def _two_channels(lab: LabHarness) -> None:
    lab.add_target(LightTarget(LIGHT, brightness=100))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(
        _channel_binding(NODE, 1, LIGHT, "brightness"),
        _channel_binding(
            NODE,
            2,
            LIGHT,
            "brightness",
            click_action="toggle",
            click_target=LIGHT,
        ),
    )


def another_binding_press_cancels_the_queued_rotation(lab: LabHarness) -> None:
    """Channel 1 scrolls, channel 2 of the same wheel presses the same light."""
    _two_channels(lab)
    _burst(lab, NODE, UP1, 0.0)
    _click(lab, NODE, BTN2, 0.05)
    lab.advance(2.0)

    assert [(t, s) for t, s, _ in _brightness_intents(lab)] == [
        (0.0, "turn_on"),
        (0.05, "toggle"),
    ]
    assert lab.registry.target(LIGHT).requested()["state"] == "off"


def test_a_press_of_another_binding_cancels_a_queued_rotation_of_this_one(lab) -> None:
    another_binding_press_cancels_the_queued_rotation(lab)


def test_a_press_of_another_wheel_cancels_it_too(lab) -> None:
    lab.add_target(LightTarget(LIGHT, brightness=100))
    lab.load(e2490_node(NODE), e2490_node(OTHER_NODE))
    lab.setup_bindings(
        _channel_binding(NODE, 1, LIGHT, "brightness"),
        _channel_binding(
            OTHER_NODE,
            1,
            LIGHT,
            "brightness",
            click_action="toggle",
            click_target=LIGHT,
        ),
    )
    _burst(lab, NODE, UP1, 0.0)
    _click(lab, OTHER_NODE, BTN1, 0.05)
    lab.advance(2.0)

    assert [(t, s) for t, s, _ in _brightness_intents(lab)] == [
        (0.0, "turn_on"),
        (0.05, "toggle"),
    ]
    assert lab.registry.target(LIGHT).requested()["state"] == "off"


def test_two_bindings_that_only_scroll_one_light_do_not_cancel_each_other(lab) -> None:
    """Before and after rc.7: a rotation sends no signal. Channel 1 queues 138;
    channel 2 turns one notch down at 0.05 s from the light's 108 (100.35, sent as
    100); channel 1's queued value still goes out at 0.18 s.
    """
    lab.add_target(LightTarget(LIGHT, brightness=100))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(
        _channel_binding(NODE, 1, LIGHT, "brightness"),
        _channel_binding(NODE, 2, LIGHT, "brightness"),
    )
    _burst(lab, NODE, UP1, 0.0)
    wire = Wire(NODE)
    lab.play([(0.05, e) for e in wire.scroll(DOWN2, complete=1)])
    lab.advance(2.0)

    assert _brightness_intents(lab) == [
        (0.0, "turn_on", 108),
        (0.05, "turn_on", 100),
        (0.18, "turn_on", 138),
    ]


# -- volume: mute and playback keep the queue, power cancels it -----------------------


def _volume_world(lab: LabHarness, click_action: str) -> None:
    lab.add_target(MediaPlayerTarget(SPEAKER, volume=0.5))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(
        _channel_binding(
            NODE, 1, SPEAKER, "volume", click_action=click_action, click_target=SPEAKER
        )
    )
    _burst(lab, NODE, UP1, 0.0)
    _click(lab, NODE, BTN1, 0.05)
    lab.advance(2.0)


def _levels(lab: LabHarness) -> list[float]:
    return [
        i["data"]["volume_level"]
        for i in lab.spy.intents
        if i["service"] == "volume_set"
    ]


@pytest.mark.parametrize("action", ["mute_toggle", "play_pause"])
def test_a_mute_or_playback_press_keeps_a_queued_volume(lab, action: str) -> None:
    """Volume 0.50, step 10 %: eager 0.60, then the four queued notches cap at 1.0."""
    _volume_world(lab, action)

    assert _levels(lab) == [0.6, 1.0]
    target = lab.registry.target(SPEAKER)
    assert target.requested() == {"volume_level": 1.0}
    assert (target.muted, target.playing) == (
        (True, True) if action == "mute_toggle" else (False, False)
    )


def test_a_power_press_cancels_a_queued_volume(lab) -> None:
    _volume_world(lab, "off")

    assert _levels(lab) == [0.6], "the queued 1.0 is not sent behind a power-off"
    assert lab.registry.target(SPEAKER).power is False


# -- mutations: the scenarios must fail if the cancelling is removed -----------


class _Scene(LightTarget):
    """A scene entity: it can only be run (``scene.turn_on``)."""

    def services(self) -> frozenset[tuple[str, str]]:
        return frozenset({("scene", "turn_on")})

    def apply(self, service: str, data: dict[str, Any]):
        return self._applied, 0.0


def test_mutation_without_cancelling_the_queue_the_press_scenarios_fail(
    lab, monkeypatch
) -> None:
    """Make the cancel a no-op inside this test only: the light comes back on.

    This patches the production class for the duration of the test (undone by
    ``monkeypatch``); no file changes.
    """
    from custom_components.ikea_bilresa.binding import LightBinding

    monkeypatch.setattr(LightBinding, "_cancel_pending_command", lambda self: None)
    with pytest.raises(AssertionError):
        press_cancels_the_queued_rotation(lab)


def test_mutation_the_cross_binding_scenario_also_fails_without_it(
    lab, monkeypatch
) -> None:
    from custom_components.ikea_bilresa.binding import LightBinding

    monkeypatch.setattr(LightBinding, "_cancel_pending_command", lambda self: None)
    with pytest.raises(AssertionError):
        another_binding_press_cancels_the_queued_rotation(lab)


def test_mutation_a_mute_press_that_cancels_the_volume_queue_is_caught(
    lab, monkeypatch
) -> None:
    """If mute counted as a call that changes the volume, the queued 1.0 would be
    dropped: the scenario that expects ``[0.6, 1.0]`` must notice.
    """
    from custom_components.ikea_bilresa.binding import LightBinding

    monkeypatch.setattr(LightBinding, "_keeps_volume", lambda self, d, s: False)
    with pytest.raises(AssertionError):
        _volume_world(lab, "mute_toggle")
        assert _levels(lab) == [0.6, 1.0]


def _digest(scenario: Any) -> str:
    with pytest.MonkeyPatch.context() as patch:
        lab = LabHarness(patch)
        scenario(lab)
        digest = lab.digest()
        lab.close()
    return digest


@pytest.mark.parametrize(
    "scenario",
    [
        press_cancels_the_queued_rotation,
        another_binding_press_cancels_the_queued_rotation,
    ],
)
def test_the_press_scenarios_repeat_exactly(scenario: Any) -> None:
    assert _digest(scenario) == _digest(scenario)
