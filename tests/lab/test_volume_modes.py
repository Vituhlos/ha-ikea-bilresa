"""Volume above the limit: the two behaviours the owner asked for (PR #73 follow-up).

A binding of a media player may have a ``max_volume`` (PR #73). The owner wants
the behaviour for a volume that is *already above* that limit to be chosen per
binding. The contract below uses this proposed key and these values:

``volume_over_limit_behavior``
    ``"clamp"`` (the default; also what a binding stored before the setting
    existed does) or ``"gradual"``.

All numbers: limit 40 %, step 5 percentage points (config ``step`` 5 is 5 % of
the 0-1 scale), so a step is 0.05.

``clamp``: a turn down from 80 % goes to 40 % at once; a turn up never takes the
volume above 40 %.
``gradual``: turning down from 80 % goes 75, 70, ... 40 % one step at a time; a
turn up while above the limit sends nothing at all; at and below the limit it is
the normal stepping, capped at 40 %.

Nothing here implements either behaviour. The tests drive the production
binding, so they fail until the production binding does it:

* ``clamp`` tests need PR #73 (``MISSING_FEATURE_MAX_VOLUME``);
* ``gradual`` tests need the setting too (``MISSING_FEATURE_VOLUME_OVER_LIMIT``),
  and are expected failures, not passes, until then.
"""

from __future__ import annotations

from typing import Any

import pytest

from .fake_matter import E2490_ENDPOINTS, Wire
from .known_issues import (
    MISSING_FEATURE_MAX_VOLUME,
    MISSING_FEATURE_VOLUME_OVER_LIMIT,
)
from .test_volume import SPEAKER, _levels, _notch, _setup

UP1 = E2490_ENDPOINTS[1]["up"]
DOWN1 = E2490_ENDPOINTS[1]["down"]

LIMIT = 0.4
CLAMP_SETTINGS = [{}, {"volume_over_limit_behavior": "clamp"}]
GRADUAL = {"volume_over_limit_behavior": "gradual"}


def _wheel(lab, volume: float, **settings: Any) -> Wire:
    return _setup(lab, volume, max_volume=40, step=5, **settings)


def _notches(lab, wire: Wire, endpoint: int, count: int, *, start: float = 0.0) -> None:
    """``count`` separate single notches, half a second apart."""
    for index in range(count):
        _notch(lab, wire, endpoint, start + 0.5 * index)


# -- behaviour that is the same in every mode, so it is not an expected failure --
#
# Below the limit and at the ends nothing depends on the over-limit setting, so
# these pass on this branch already (a stored limit and behaviour are simply
# ignored today). They guard that the future feature does not change them.

EVERY_MODE = [{}, {"volume_over_limit_behavior": "clamp"}, GRADUAL]


@pytest.mark.parametrize("settings", EVERY_MODE)
def test_below_the_limit_the_stepping_is_normal(lab, settings) -> None:
    """0.20 up 0.05 is 0.25, and down again is 0.20."""
    wire = _wheel(lab, 0.2, **settings)
    _notch(lab, wire, UP1)
    _notch(lab, wire, DOWN1, 1.0)

    assert _levels(lab) == [0.25, 0.2]


@pytest.mark.parametrize("settings", EVERY_MODE)
def test_zero_stays_zero(lab, settings) -> None:
    wire = _wheel(lab, 0.0, **settings)
    _notch(lab, wire, DOWN1)

    assert _levels(lab) == []


@MISSING_FEATURE_MAX_VOLUME
@pytest.mark.parametrize("settings", EVERY_MODE)
def test_up_stops_at_the_limit_and_then_stays(lab, settings) -> None:
    """From below the limit, in every mode: 0.30 -> 0.35 -> 0.40, then nothing."""
    wire = _wheel(lab, 0.3, **settings)
    _notches(lab, wire, UP1, 3)

    assert _levels(lab) == [0.35, LIMIT]


# -- clamp: the PR #73 design, and the default --------------------------------


@MISSING_FEATURE_MAX_VOLUME
@pytest.mark.parametrize("settings", CLAMP_SETTINGS)
def test_clamp_a_turn_down_above_the_limit_goes_straight_to_it(lab, settings) -> None:
    wire = _wheel(lab, 0.8, **settings)
    _notch(lab, wire, DOWN1)

    assert _levels(lab) == [LIMIT]
    assert lab.registry.target(SPEAKER).value() == LIMIT


@MISSING_FEATURE_MAX_VOLUME
@pytest.mark.parametrize("settings", CLAMP_SETTINGS)
def test_clamp_a_turn_up_above_the_limit_never_raises_the_volume(lab, settings) -> None:
    wire = _wheel(lab, 0.8, **settings)
    _notch(lab, wire, UP1)

    assert _levels(lab) in ([], [LIMIT])
    assert lab.registry.target(SPEAKER).value() <= LIMIT


@MISSING_FEATURE_MAX_VOLUME
@pytest.mark.parametrize("settings", CLAMP_SETTINGS)
def test_clamp_the_limit_is_a_ceiling_for_steps_and_for_a_batch(lab, settings) -> None:
    """0.35 + 0.05 is exactly the limit, then nothing; a batch from 0.30 stops there.

    A batch of five notches from 0.30 is one eager notch (0.35) and four more
    held for 0.18 s (0.55 uncapped), so the second command is the capped 0.40.
    """
    wire = _wheel(lab, 0.35, **settings)
    _notch(lab, wire, UP1)
    _notch(lab, wire, UP1, 1.0)
    assert _levels(lab) == [LIMIT]


@MISSING_FEATURE_MAX_VOLUME
@pytest.mark.parametrize("settings", CLAMP_SETTINGS)
def test_clamp_a_fast_batch_cannot_overshoot(lab, settings) -> None:
    wire = _wheel(lab, 0.3, **settings)
    lab.play([(0.0, e) for e in wire.scroll(UP1, ongoing=(5,), complete=5)])
    lab.advance(1.0)

    assert _levels(lab) == [0.35, LIMIT]


@MISSING_FEATURE_MAX_VOLUME
@pytest.mark.parametrize("settings", CLAMP_SETTINGS)
def test_clamp_a_fast_batch_down_from_above_goes_to_the_limit_then_on(
    lab, settings
) -> None:
    """From 0.80, four notches down: the first lands on the limit, three more
    follow it down: 0.40, then 0.40 - 3 x 0.05 = 0.25.
    """
    wire = _wheel(lab, 0.8, **settings)
    lab.play([(0.0, e) for e in wire.scroll(DOWN1, ongoing=(4,), complete=4)])
    lab.advance(1.0)

    assert _levels(lab) == [LIMIT, 0.25]


@MISSING_FEATURE_MAX_VOLUME
@pytest.mark.parametrize("settings", CLAMP_SETTINGS)
def test_clamp_an_outside_change_above_the_limit_is_pulled_back(lab, settings) -> None:
    """Somebody sets 90 % from outside while the wheel is idle: the next turn
    down goes to the limit, a turn up afterwards sends nothing more.
    """
    wire = _wheel(lab, 0.3, **settings)
    _notch(lab, wire, UP1)
    lab.at(10.0)
    lab.registry.external_change(SPEAKER, 0.9)
    lab.settle()
    _notch(lab, wire, DOWN1, 11.0)
    _notch(lab, wire, UP1, 12.0)

    assert _levels(lab) == [0.35, LIMIT]


# -- gradual: the behaviour that does not exist yet ---------------------------


@MISSING_FEATURE_VOLUME_OVER_LIMIT
def test_gradual_turning_down_above_the_limit_steps_one_notch_at_a_time(lab) -> None:
    """80 -> 75 -> 70 -> ... -> 40 %, and one more notch goes below the limit.

    A turn up comes first: above the limit it sends nothing. Without it this
    would be indistinguishable from a branch that has no limit at all.
    """
    wire = _wheel(lab, 0.8, **GRADUAL)
    _notch(lab, wire, UP1)
    _notches(lab, wire, DOWN1, 9, start=1.0)

    assert _levels(lab) == [0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45, 0.4, 0.35]


@MISSING_FEATURE_VOLUME_OVER_LIMIT
def test_gradual_a_turn_up_above_the_limit_sends_nothing(lab) -> None:
    wire = _wheel(lab, 0.8, **GRADUAL)
    _notches(lab, wire, UP1, 3)

    assert lab.spy.intents == []
    assert lab.registry.target(SPEAKER).value() == 0.8


@MISSING_FEATURE_VOLUME_OVER_LIMIT
def test_gradual_a_batch_down_above_the_limit_is_still_stepwise(lab) -> None:
    """From 0.80 four notches are 0.75 (eager) and then 0.75 - 3 x 0.05 = 0.60,
    never a jump to the limit. A first turn up sends nothing.
    """
    wire = _wheel(lab, 0.8, **GRADUAL)
    _notch(lab, wire, UP1)
    lab.play([(2.0, e) for e in wire.scroll(DOWN1, ongoing=(4,), complete=4)])
    lab.advance(1.0)

    assert _levels(lab) == [0.75, 0.6]


@MISSING_FEATURE_VOLUME_OVER_LIMIT
def test_gradual_a_batch_that_crosses_the_limit_goes_on_below_it(lab) -> None:
    """From 0.45, three notches down: 0.40, then 0.40 - 2 x 0.05 = 0.30.

    A first turn up sends nothing (0.45 is above the limit).
    """
    wire = _wheel(lab, 0.45, **GRADUAL)
    _notch(lab, wire, UP1)
    lab.play([(2.0, e) for e in wire.scroll(DOWN1, ongoing=(3,), complete=3)])
    lab.advance(1.0)

    assert _levels(lab) == [LIMIT, 0.3]


@MISSING_FEATURE_VOLUME_OVER_LIMIT
def test_gradual_an_outside_change_above_the_limit_is_followed_down(lab) -> None:
    """90 % set from outside: the next turn down is 85 %, a turn up sends nothing."""
    wire = _wheel(lab, 0.3, **GRADUAL)
    _notch(lab, wire, UP1)
    lab.at(10.0)
    lab.registry.external_change(SPEAKER, 0.9)
    lab.settle()
    _notch(lab, wire, DOWN1, 11.0)
    _notch(lab, wire, UP1, 12.0)

    assert _levels(lab) == [0.35, 0.85]
