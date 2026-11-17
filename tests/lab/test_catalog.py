"""The coverage guard: the lab cannot silently fall behind the integration.

The features come from the production code, the claims from the ``@covers``
decorators of the lab's tests, the excuses from ``coverage_gaps``. See
``catalog`` for the rules. The mutation tests below feed the same checker an
altered world and prove it complains, so a guard that stopped guarding would
fail here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .catalog import covers, declared, features, problems
from .coverage_gaps import GAPS

KINDS = {"conf", "mode", "hold", "ramp", "curve", "response", "gesture", "verb"}


def test_every_feature_is_covered_or_a_reasoned_gap() -> None:
    assert problems(features(), declared(), GAPS) == []


def test_the_catalogue_reads_every_kind_from_production() -> None:
    kinds = {feature.split(":", 1)[0] for feature in features()}
    assert kinds == KINDS


def test_the_guard_sees_the_tests_that_name_a_feature() -> None:
    named = declared()
    assert "mode:brightness" in named
    assert any(
        test.startswith("test_bindings.py::") for test in named["mode:brightness"]
    )


def test_covers_needs_a_feature() -> None:
    with pytest.raises(ValueError):
        covers()


# -- mutations: the guard must notice ------------------------------------------


def test_mutation_a_new_feature_without_a_test_or_a_reason_is_caught() -> None:
    world = {**features(), "mode:teleport": "const.MODE_TARGET_DOMAINS"}

    wrong = problems(world, declared(), GAPS)

    assert len(wrong) == 1
    assert "mode:teleport" in wrong[0]
    assert "neither covered" in wrong[0]


def test_mutation_a_gap_that_has_been_covered_is_caught() -> None:
    named = {**declared(), "mode:color": ["test_x.py::test_colour"]}

    wrong = problems(features(), named, GAPS)

    assert any("'mode:color'" in line and "remove it" in line for line in wrong)


def test_mutation_a_test_that_names_a_missing_feature_is_caught() -> None:
    named = {**declared(), "mode:brightnes": ["test_x.py::test_typo"]}

    wrong = problems(features(), named, GAPS)

    assert any("mode:brightnes" in line and "no such feature" in line for line in wrong)


def test_mutation_a_gap_without_a_reason_is_caught() -> None:
    gaps = {**GAPS, "mode:color": "  "}

    assert any(
        "needs a reason" in line for line in problems(features(), declared(), gaps)
    )


def test_mutation_a_removed_feature_leaves_its_test_unmatched(tmp_path: Path) -> None:
    (tmp_path / "test_one.py").write_text(
        "from tests.lab.catalog import covers\n\n"
        '@covers("mode:brightness", "mode:gone")\n'
        "def test_a():\n    pass\n",
        encoding="utf-8",
    )

    named = declared(tmp_path)

    assert named == {
        "mode:brightness": ["test_one.py::test_a"],
        "mode:gone": ["test_one.py::test_a"],
    }
    assert any("mode:gone" in line for line in problems(features(), named, GAPS))
