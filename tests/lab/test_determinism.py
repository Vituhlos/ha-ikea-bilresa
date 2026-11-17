"""Determinism: the same scenario, seed and code give the same normalized run.

The record compared here is everything a scenario produces: the decoded
actions, the service intents with their times, the target's requested and
reported timeline, the binding's activity and the rejection counters. Random
ids (``action_id``) and wall-clock time are not part of it.

The generated gestures also carry an oracle that does not come from the code
under test: by the Matter Switch contract the notches of one gesture add up to
its final cumulative count, whatever the batching.
"""

from __future__ import annotations

import json
import random

import pytest

from .fake_matter import E2490_ENDPOINTS, Wire, e2490_node
from .harness import LabHarness
from .targets import LightTarget

NODE = 14
UP1 = E2490_ENDPOINTS[1]["up"]
SEEDS = range(40)


def random_gesture(seed: int) -> tuple[list[int], int]:
    """Cumulative ongoing counts and the final count of one fast gesture.

    Counts never go down, may repeat, start at 2 (the first count is paid by
    InitialPress) and stop at 18, the E2490 MultiPressMax.
    """
    rng = random.Random(seed)
    total = 1
    ongoing: list[int] = []
    for _ in range(rng.randint(1, 5)):
        total = min(18, max(2, total + rng.randint(0, 6)))
        ongoing.append(total)
    return ongoing, ongoing[-1]


def run_seed(seed: int) -> tuple[dict, str, int, int]:
    """One seeded gesture on a delayed-echo light; returns record, digest, ..."""
    rng = random.Random(f"timing-{seed}")
    ongoing, complete = random_gesture(seed)
    with pytest.MonkeyPatch.context() as patch:
        lab = LabHarness(patch)
        lab.add_target(LightTarget("light.lab", brightness=100, echo_delay=0.3))
        lab.load(e2490_node(NODE))
        lab.setup_bindings(
            {
                "node_id": NODE,
                "channel": 1,
                "target": "light.lab",
                "mode": "brightness",
                "step": 3,
                "step_curve": "linear",
                "transition": 0.0,
            }
        )
        wire = Wire(NODE)
        events = wire.scroll(UP1, ongoing=tuple(ongoing), complete=complete)
        when = 0.0
        timeline = []
        for event in events:
            timeline.append((round(when, 3), event))
            when += rng.choice([0.05, 0.2, 0.5])
        lab.play(timeline)
        lab.advance(5.0)
        notches = sum(n for _, _, n in lab.rotations())
        record, digest = lab.record(), lab.digest()
        lab.close()
    return record, digest, notches, complete


@pytest.mark.parametrize("seed", SEEDS)
def test_a_seeded_gesture_adds_up_and_repeats_exactly(seed: int) -> None:
    record, digest, notches, complete = run_seed(seed)
    again_record, again_digest, _, _ = run_seed(seed)

    assert notches == complete, "the notches of a gesture add up to its final count"
    assert digest == again_digest
    assert record == again_record
    assert record["safety"] == []
    assert "action_id" not in json.dumps(record)


def test_different_seeds_really_differ() -> None:
    """A digest that never changed would prove nothing."""
    digests = {run_seed(seed)[1] for seed in SEEDS}
    assert len(digests) > 10


def test_a_changed_input_changes_the_digest() -> None:
    first = run_seed(3)[1]
    with pytest.MonkeyPatch.context() as patch:
        lab = LabHarness(patch)
        lab.add_target(LightTarget("light.lab", brightness=100, echo_delay=0.3))
        lab.load(e2490_node(NODE))
        lab.setup_bindings(
            {
                "node_id": NODE,
                "channel": 1,
                "target": "light.lab",
                "mode": "brightness",
                "step": 4,  # the only difference
                "step_curve": "linear",
                "transition": 0.0,
            }
        )
        wire = Wire(NODE)
        ongoing, complete = random_gesture(3)
        lab.play(
            [
                (0.0, e)
                for e in wire.scroll(UP1, ongoing=tuple(ongoing), complete=complete)
            ]
        )
        lab.advance(5.0)
        other = lab.digest()
        lab.close()
    assert other != first
