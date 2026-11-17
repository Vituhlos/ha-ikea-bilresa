"""Every expected failure in the lab, in one place.

Each marker is ``xfail(strict=True, raises=AssertionError)``:

* ``strict``: when the behaviour is fixed or the feature appears, the test turns
  into an XPASS and fails, which forces the marker out;
* ``raises=AssertionError``: only a failed *assertion* counts as the expected
  failure. Any other exception (a harness error, a bad input, and also
  ``LabSafetyViolation``, which is not an ``AssertionError``) is an ordinary
  failure and is never hidden.

Three kinds are kept apart, and the reason text always names the reference, what
is wrong or missing, and when the marker goes:

* KNOWN DEFECT: reproduced here, with the observed wrong value pinned by a
  separate characterization test;
* MISSING FEATURE: not on this branch, and the test is the executable contract;
* SUSPECTED DEFECT: a mismatch with an authoritative source whose effect on real
  hardware is not proven.
"""

from __future__ import annotations

import pytest

from custom_components.ikea_bilresa import const

HAS_MAX_VOLUME = hasattr(const, "CONF_MAX_VOLUME")
# Proposed contract for the follow-up to PR #73: a per-binding behaviour when the
# volume is already above the limit, stored under this constant and key.
HAS_VOLUME_OVER_LIMIT = hasattr(const, "CONF_VOLUME_OVER_LIMIT_BEHAVIOR")


def _expected_failure(reason: str, *, condition: bool = True) -> pytest.MarkDecorator:
    return pytest.mark.xfail(
        condition, raises=AssertionError, strict=True, reason=reason
    )


KNOWN_DEFECT_71 = _expected_failure(
    "KNOWN DEFECT (reproduced) | PR #71, https://github.com/Vituhlos/ha-ikea-bilresa/pull/71"
    " | binding.py _rotate_number / _rotate_temperature read a bound with"
    " `_as_float(x) or default`, so a valid min/max of 0 counts as missing"
    " | remove when PR #71 (or an equivalent fix) is on this branch; the pinned"
    " observed values in test_observed_defect_71_* fail then and go with it"
)

MISSING_FEATURE_MAX_VOLUME = _expected_failure(
    "MISSING FEATURE | PR #73, https://github.com/Vituhlos/ha-ikea-bilresa/pull/73"
    " | no `max_volume` binding setting on this branch (const.CONF_MAX_VOLUME)"
    " | the condition turns false by itself once PR #73 is merged; nothing to edit",
    condition=not HAS_MAX_VOLUME,
)

MISSING_FEATURE_VOLUME_OVER_LIMIT = _expected_failure(
    "MISSING FEATURE (contract proposed, no PR yet) | follow-up to PR #73"
    " | no `volume_over_limit_behavior` binding setting"
    " (const.CONF_VOLUME_OVER_LIMIT_BEHAVIOR = 'volume_over_limit_behavior',"
    " values 'clamp' | 'gradual') | the condition turns false once PR #73 and"
    " that constant exist; nothing to edit",
    condition=not (HAS_MAX_VOLUME and HAS_VOLUME_OVER_LIMIT),
)

SUSPECTED_CURRENT_POSITION = _expected_failure(
    "SUSPECTED DEFECT (spec mismatch; real hardware impact not proven)"
    " | Matter Switch cluster 0x003B: NumberOfPositions is 0x0000 and"
    " CurrentPosition is 0x0001 (project-chip/connectedhomeip data_model/1.3 and"
    " 1.4 Switch.xml; matter.js switch.element.ts) | const.py"
    " ATTR_SWITCH_CURRENT_POSITION is 0, so the coordinator and the core Matter"
    " source follow attribute 0x0000 and ignore 0x0001"
    " | remove when the constant (and matter_core._SWITCH_CURRENT_POSITION_"
    "ATTRIBUTE_ID) follow the specification, or a raw capture shows the device"
    " really reports its position at attribute 0"
)
