"""Unit tests for per-wheel settings and dial math (pure logic, no HA)."""

from __future__ import annotations

from custom_components.ikea_bilresa.channel_controls import (
    DEFAULT_SETTINGS,
    ScrollAccelerator,
    WheelSettings,
    apply_rotation,
)
from custom_components.ikea_bilresa.const import (
    CONF_CHANNEL_ENABLED,
    CONF_NODE_ID,
    DIRECTION_DOWN,
    DIRECTION_UP,
)


def _clock(*values: float):
    """A monotonic clock that yields the given values in order."""
    iterator = iter(values)
    return lambda: next(iterator)


# --- WheelSettings ------------------------------------------------------


def test_defaults_enable_every_channel() -> None:
    settings = WheelSettings.from_data({})
    assert settings.node_id is None
    assert settings.disabled_channels == frozenset()
    assert settings.step == 2.0
    assert settings.acceleration == 0.0
    assert DEFAULT_SETTINGS.channel_enabled(1)


def test_node_id_parses_from_the_panel_string() -> None:
    # The panel addresses wheels by an opaque key resolved to a string node id.
    assert WheelSettings.from_data({CONF_NODE_ID: "12"}).node_id == 12


def test_unparseable_node_id_is_dropped_rather_than_raising() -> None:
    assert WheelSettings.from_data({CONF_NODE_ID: "not-a-node"}).node_id is None


def test_only_explicitly_false_channels_are_disabled() -> None:
    settings = WheelSettings.from_data({CONF_CHANNEL_ENABLED: {"1": True, "3": False}})
    assert settings.disabled_channels == frozenset({3})
    assert settings.channel_enabled(1)
    assert settings.channel_enabled(2)  # absent means enabled
    assert not settings.channel_enabled(3)


def test_a_dual_buttons_channelless_action_is_never_disabled() -> None:
    settings = WheelSettings.from_data({CONF_CHANNEL_ENABLED: {"1": False}})
    assert settings.channel_enabled(None)


# --- dial math ----------------------------------------------------------


def test_rotation_up_and_down_move_by_step_times_notches() -> None:
    assert apply_rotation(50.0, 3, up=True, step=2.0) == 56.0
    assert apply_rotation(50.0, 3, up=False, step=2.0) == 44.0


def test_rotation_clamps_to_both_ends() -> None:
    assert apply_rotation(99.0, 10, up=True, step=2.0) == 100.0
    assert apply_rotation(3.0, 5, up=False, step=2.0) == 1.0


# --- ScrollAccelerator --------------------------------------------------


def test_zero_acceleration_is_the_identity() -> None:
    accelerator = ScrollAccelerator(0, clock=_clock(0.0, 1.0))
    assert accelerator.accelerate(6, DIRECTION_UP) == 6
    assert not accelerator.enabled


def test_a_single_sample_cannot_establish_a_velocity() -> None:
    # One batch has no elapsed interval to divide by, however large it is.
    accelerator = ScrollAccelerator(100, clock=_clock(0.0))
    assert accelerator.accelerate(20, DIRECTION_UP) == 20


def test_velocity_comes_from_elapsed_time_not_the_first_batch_size() -> None:
    accelerator = ScrollAccelerator(100, clock=_clock(0.0, 1.0))
    assert accelerator.accelerate(20, DIRECTION_UP) == 20
    # 6 notches over 1 s is below the floor of 2/s? No: 6/s sits mid-scale,
    # so the multiplier lands between 1x and the 3x cap.
    assert accelerator.accelerate(6, DIRECTION_UP) == 12


def test_a_large_batch_cannot_exceed_the_multiplier_cap() -> None:
    """The property the batch-size formula lacks: a bounded worst case.

    A 14-notch batch is the largest recorded on the physical E2490. Scaled
    quadratically by batch size it would be 196 notches; the velocity model
    caps it at three times the raw count.
    """
    accelerator = ScrollAccelerator(100, clock=_clock(0.0, 0.1))
    accelerator.accelerate(14, DIRECTION_UP)
    assert accelerator.accelerate(14, DIRECTION_UP) <= 14 * 3


def test_direction_change_restarts_the_measurement() -> None:
    accelerator = ScrollAccelerator(100, clock=_clock(0.0, 1.0, 1.1))
    accelerator.accelerate(6, DIRECTION_UP)
    accelerator.accelerate(6, DIRECTION_UP)
    # Reversing discards the samples, so the first notch back is unscaled.
    assert accelerator.accelerate(6, DIRECTION_DOWN) == 6


def test_an_idle_gap_restarts_the_measurement() -> None:
    accelerator = ScrollAccelerator(100, clock=_clock(0.0, 1.0, 5.0))
    accelerator.accelerate(6, DIRECTION_UP)
    accelerator.accelerate(6, DIRECTION_UP)
    assert accelerator.accelerate(6, DIRECTION_UP) == 6


def test_reset_forgets_the_measured_velocity() -> None:
    accelerator = ScrollAccelerator(100, clock=_clock(0.0, 1.0, 1.1))
    accelerator.accelerate(6, DIRECTION_UP)
    accelerator.reset()
    assert accelerator.accelerate(6, DIRECTION_UP) == 6
