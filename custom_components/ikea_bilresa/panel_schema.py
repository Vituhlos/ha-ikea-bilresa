"""The editable fields of a binding, described once for validation and the panel.

The panel used to keep its own copy of every range, unit and choice list, next
to the copies in the validation schema. Three copies drift. The ranges live
here; ``binding_config`` and the settings command validate against them, and
the panel receives the same numbers in its registration config.

Nothing here is per-household: it is static, so it travels in the panel config
rather than in the overview snapshot.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import voluptuous as vol

from .const import (
    CONF_ACCELERATION,
    CONF_MAX_BRIGHTNESS,
    CONF_MIN_BRIGHTNESS,
    CONF_STEP,
    CONF_TRANSITION,
    MODE_TARGET_DOMAINS,
)

SCHEMA_VERSION = 1

# Entity domains a press, double press, triple press or hold may toggle.
PRESS_TARGET_DOMAINS = ("light", "switch")
# A hold that ramps changes brightness, so it needs a light.
RAMP_TARGET_DOMAINS = ("light",)


@dataclass(frozen=True, slots=True)
class NumberField:
    """The accepted range of one numeric field and how a control presents it."""

    min: float
    max: float
    step: float
    unit: str | None = None

    def validator(self) -> Any:
        """Return the voluptuous validator for this field."""
        return vol.All(vol.Coerce(float), vol.Range(min=self.min, max=self.max))


BINDING_NUMBERS: dict[str, NumberField] = {
    CONF_STEP: NumberField(1, 25, 1, "%"),
    CONF_ACCELERATION: NumberField(0, 100, 5, "%"),
    CONF_MIN_BRIGHTNESS: NumberField(0, 50, 1, "%"),
    CONF_MAX_BRIGHTNESS: NumberField(1, 100, 1, "%"),
    CONF_TRANSITION: NumberField(0, 5, 0.1, "s"),
}

# The dial is the 1-100 number entity each channel carries; its step is in the
# dial's own units, not a percentage of a target.
SETTINGS_NUMBERS: dict[str, NumberField] = {
    "step": NumberField(1, 25, 1),
    "acceleration": NumberField(0, 100, 5, "%"),
}


def panel_schema() -> dict[str, Any]:
    """Return the form description the panel builds its editor from."""
    return {
        "version": SCHEMA_VERSION,
        "binding_numbers": {
            name: asdict(field) for name, field in BINDING_NUMBERS.items()
        },
        "settings_numbers": {
            name: asdict(field) for name, field in SETTINGS_NUMBERS.items()
        },
        "mode_domains": {
            mode: sorted(domains) for mode, domains in MODE_TARGET_DOMAINS.items()
        },
        "press_target_domains": list(PRESS_TARGET_DOMAINS),
        "ramp_target_domains": list(RAMP_TARGET_DOMAINS),
    }
