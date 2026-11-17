"""B11: media player volume, and the contract of PR #73 (``max_volume``).

Three groups, kept apart on purpose:

* runs today on this branch: the 0-100 % volume arithmetic;
* the PR #73 contract, written against the config key that PR adds
  (``max_volume``, a percent, default 100). On a branch without that feature
  the limit tests carry ``known_issues.MISSING_FEATURE_MAX_VOLUME``
  (``xfail(strict=True)``). Once PR #73 is merged the marker's condition turns
  false by itself and the same tests must pass;
* what happens when the volume is already above the limit lives in
  ``test_volume_modes.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from .catalog import covers
from .fake_matter import E2490_ENDPOINTS, Wire, e2490_node
from .known_issues import HAS_MAX_VOLUME, MISSING_FEATURE_MAX_VOLUME
from .targets import MediaPlayerTarget

NODE = 14
UP1 = E2490_ENDPOINTS[1]["up"]
DOWN1 = E2490_ENDPOINTS[1]["down"]
SPEAKER = "media_player.lab_speaker"

BLOCKED_BY_73 = MISSING_FEATURE_MAX_VOLUME


def _setup(lab, volume: float, **extra: Any) -> Wire:
    lab.add_target(MediaPlayerTarget(SPEAKER, volume=volume))
    lab.load(e2490_node(NODE))
    lab.setup_bindings(
        {
            "node_id": NODE,
            "channel": 1,
            "target": SPEAKER,
            "mode": "volume",
            "step": 10,
            "transition": 0.0,
            **extra,
        }
    )
    return Wire(NODE)


def _levels(lab) -> list[float]:
    return [i["data"]["volume_level"] for i in lab.spy.intents]


def _notch(lab, wire: Wire, endpoint: int, when: float = 0.0) -> None:
    lab.play([(when, event) for event in wire.scroll(endpoint, complete=1)])


# -- runs today ---------------------------------------------------------------


@covers("mode:volume", "conf:step")
def test_one_notch_is_ten_percent_of_the_scale(lab) -> None:
    wire = _setup(lab, 0.5)
    _notch(lab, wire, UP1)

    assert _levels(lab) == [0.6]
    assert lab.spy.intents[0]["domain"] == "media_player"
    assert lab.spy.intents[0]["service"] == "volume_set"


def test_a_batch_adds_up(lab) -> None:
    """0.2 + one eager notch = 0.3, then two more arrive together: 0.5."""
    wire = _setup(lab, 0.2)
    lab.play([(0.0, e) for e in wire.scroll(UP1, ongoing=(3,), complete=3)])
    lab.advance(1.0)

    assert _levels(lab) == [0.3, 0.5]


def test_the_scale_ends_at_zero_and_one(lab) -> None:
    wire = _setup(lab, 0.95)
    _notch(lab, wire, UP1)
    assert _levels(lab) == [1.0]

    wire = Wire(NODE)
    _notch(lab, wire, UP1, 1.0)
    assert _levels(lab) == [1.0], "at the top nothing more is sent"


def test_the_bottom_is_zero_and_then_quiet(lab) -> None:
    wire = _setup(lab, 0.05)
    _notch(lab, wire, DOWN1)
    _notch(lab, wire, DOWN1, 1.0)

    assert _levels(lab) == [0.0]


def test_without_the_setting_the_limit_is_one_hundred_percent(lab) -> None:
    """The compatible default: a binding saved before PR #73 keeps its range."""
    wire = _setup(lab, 0.95)
    _notch(lab, wire, UP1)

    assert _levels(lab) == [1.0]


# -- the PR #73 contract ------------------------------------------------------


def test_an_explicit_limit_of_one_hundred_is_the_default(lab) -> None:
    wire = _setup(lab, 0.95, max_volume=100)
    _notch(lab, wire, UP1)

    assert _levels(lab) == [1.0]


@BLOCKED_BY_73
def test_a_limit_of_forty_percent_stops_the_scroll_at_forty(lab) -> None:
    """0.35 + 0.1 = 0.45 is above the limit: sent as 0.4, then nothing more."""
    wire = _setup(lab, 0.35, max_volume=40)
    _notch(lab, wire, UP1)
    _notch(lab, wire, UP1, 1.0)

    assert _levels(lab) == [0.4]


@BLOCKED_BY_73
def test_a_fast_scroll_cannot_overshoot_the_limit(lab) -> None:
    """From 0.3, five notches would be 0.8; the limit is 0.4."""
    wire = _setup(lab, 0.3, max_volume=40)
    lab.play([(0.0, e) for e in wire.scroll(UP1, ongoing=(5,), complete=5)])
    lab.advance(1.0)

    assert _levels(lab) == [0.4]
    assert lab.registry.target(SPEAKER).value() == 0.4


# -- what this branch does today, pinned ---------------------------------------


@pytest.mark.skipif(
    HAS_MAX_VOLUME, reason="PR #73 is on this branch: the limit exists and is tested"
)
def test_observed_without_pr_73_a_limit_setting_is_ignored(lab) -> None:
    """A stored ``max_volume`` is ignored today: 0.35 + 0.1 goes to 0.45.

    Proves the xfail tests above fail because the feature is absent, not
    because of the harness. Delete when PR #73 is merged.
    """
    wire = _setup(lab, 0.35, max_volume=40)
    _notch(lab, wire, UP1)

    assert _levels(lab) == [0.45]
