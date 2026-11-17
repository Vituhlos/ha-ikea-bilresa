"""The catalogue of everything the integration offers, and who tests it.

The point of the lab is to need the real devices less. That only works if it is
known, and checked, what the lab does *not* test yet. So the list of features is
**read from the production code**, not typed here, and ``test_catalog.py`` fails
when:

* a feature exists in production and no lab test names it, and it is not on the
  ledger of known gaps (``coverage_gaps.py``): a new mode, setting, verb or
  gesture cannot be added without a lab test or an explicit, reasoned gap;
* a gap on the ledger has since been covered: the entry must go;
* a test names a feature that does not exist (a typo, or a removed feature).

A feature id is ``<kind>:<value>``:

========  ==========================================================
kind      source in production
========  ==========================================================
conf      every ``CONF_*`` setting key of a binding (``const``)
mode      the rotation modes (``const.MODE_TARGET_DOMAINS``)
hold      the hold actions (``const.HOLD_ACTIONS``)
ramp      the ramp directions (``const.RAMP_DIRECTIONS``)
curve     the brightness step curves (``const.STEP_CURVES``)
response  how soon a single press acts (``const.BUTTON_RESPONSES``)
gesture   the event types a channel reports (``const.WHEEL_EVENT_TYPES``)
verb      ``<domain>.<verb>``, what a press can do to a kind of entity
          (``gesture_verbs.VERBS``, without the legacy ones)
========  ==========================================================

"Covered" means a test states and checks the behaviour of that feature, through
the production objects. It is evidence of logic, not of hardware: the lab never
proves what a real device sends.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
import fnmatch
from pathlib import Path
from typing import TypeVar

from custom_components.ikea_bilresa import const, gesture_verbs

F = TypeVar("F", bound=Callable[..., object])

LAB_DIR = Path(__file__).resolve().parent


def covers(*features: str) -> Callable[[F], F]:
    """Say which features a test checks. It changes nothing at run time.

    The guard reads these calls from the source text (``declared``), so it works
    the same when only some of the tests are run.
    """
    if not features:
        raise ValueError("covers() needs at least one feature id")

    def mark(test: F) -> F:
        return test

    return mark


def features() -> dict[str, str]:
    """Every feature id the production code offers, with where it comes from."""
    found: dict[str, str] = {}

    def add(kind: str, value: object, source: str) -> None:
        found[f"{kind}:{value}"] = source

    for name, value in vars(const).items():
        if name.startswith("CONF_") and isinstance(value, str):
            add("conf", value, f"const.{name}")
    for mode in const.MODE_TARGET_DOMAINS:
        add("mode", mode, "const.MODE_TARGET_DOMAINS")
    for action in const.HOLD_ACTIONS:
        add("hold", action, "const.HOLD_ACTIONS")
    for direction in const.RAMP_DIRECTIONS:
        add("ramp", direction, "const.RAMP_DIRECTIONS")
    for curve in const.STEP_CURVES:
        add("curve", curve, "const.STEP_CURVES")
    for response in const.BUTTON_RESPONSES:
        add("response", response, "const.BUTTON_RESPONSES")
    for event_type in const.WHEEL_EVENT_TYPES:
        add("gesture", event_type, "const.WHEEL_EVENT_TYPES")
    for domain, verbs in gesture_verbs.VERBS.items():
        for verb in verbs:
            if (domain, verb) not in gesture_verbs._LEGACY:
                add("verb", f"{domain}.{verb}", "gesture_verbs.VERBS")
    return found


def declared(directory: Path = LAB_DIR) -> dict[str, list[str]]:
    """Feature id -> the tests that name it, read from the lab's source files."""
    named: dict[str, list[str]] = {}
    for path in sorted(directory.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for decorator in node.decorator_list:
                if not (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "covers"
                ):
                    continue
                for argument in decorator.args:
                    if isinstance(argument, ast.Constant) and isinstance(
                        argument.value, str
                    ):
                        named.setdefault(argument.value, []).append(
                            f"{path.name}::{node.name}"
                        )
    return named


def problems(
    available: dict[str, str],
    named: dict[str, list[str]],
    gaps: dict[str, str],
) -> list[str]:
    """What is wrong with the lab's coverage of ``available``; empty when sound.

    ``named`` is what the tests declare (``declared``) and ``gaps`` the ledger of
    known, reasoned gaps (pattern -> reason, ``fnmatch`` style).
    """
    wrong: list[str] = []
    uncovered = sorted(set(available) - set(named))

    for feature in sorted(set(named) - set(available)):
        wrong.append(
            f"{feature}: named by {named[feature]} but production has no such feature"
        )

    allowed = [pattern for pattern in gaps if pattern]
    for feature in uncovered:
        if not any(fnmatch.fnmatchcase(feature, pattern) for pattern in allowed):
            wrong.append(
                f"{feature}: offered by {available[feature]} and neither covered"
                " by a lab test nor on the ledger of known gaps"
            )

    for pattern, reason in gaps.items():
        if not reason.strip():
            wrong.append(f"gap {pattern!r}: a gap needs a reason")
        if not any(fnmatch.fnmatchcase(feature, pattern) for feature in uncovered):
            wrong.append(
                f"gap {pattern!r}: nothing it matches is uncovered any more;"
                " remove it from the ledger"
            )
    return wrong
