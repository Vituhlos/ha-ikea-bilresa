"""Named BILRESA triggers for automations.

One trigger per gesture, aimed at this integration's event entities. Home
Assistant offers a trigger wherever its target entities are, not by who owns
the device, so these appear on the core Matter device the entities sit on.
That is what the retired device triggers could not do once a device belonged
to a single config entry.

Each trigger watches the `event_type` an event entity reports, so it fires on
exactly what the event entity and the `ikea_bilresa_event` bus event report.
The gesture details stay on the entity: `trigger.to_state.attributes.notches`
for a rotation, `.presses` for a press.
"""

from __future__ import annotations

from typing import override

from homeassistant.components.event import ATTR_EVENT_TYPE
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.automation import DomainSpec
from homeassistant.helpers.trigger import (
    NotTriggeredReasonReporter,
    StatelessEntityTriggerBase,
    Trigger,
)

from .const import (
    DOMAIN,
    ET_DOUBLE_PRESS,
    ET_HOLD,
    ET_PRESS,
    ET_RELEASE,
    ET_ROTATE_DOWN,
    ET_ROTATE_UP,
    ET_TRIPLE_PRESS,
)


class BilresaGestureTrigger(StatelessEntityTriggerBase):
    """Fires when a BILRESA event entity reports one particular gesture."""

    _domain_specs = {Platform.EVENT: DomainSpec()}
    _event_type: str

    @override
    def entity_filter(self, entities: set[str]) -> set[str]:
        """Keep this integration's event entities only.

        A target naming the whole device also covers core Matter's own event
        entities for the same wheel; those report different event types and
        are none of this trigger's business.
        """
        registry = er.async_get(self._hass)
        return {
            entity_id
            for entity_id in super().entity_filter(entities)
            if (entry := registry.async_get(entity_id)) is not None
            and entry.platform == DOMAIN
        }

    @override
    def is_valid_state(
        self,
        state: State,
        report_not_triggered: NotTriggeredReasonReporter,
    ) -> bool:
        """Check that the entity's latest event is this trigger's gesture."""
        return state.attributes.get(ATTR_EVENT_TYPE) == self._event_type


def _gesture_trigger(event_type: str) -> type[BilresaGestureTrigger]:
    class GestureTrigger(BilresaGestureTrigger):
        _event_type = event_type

    GestureTrigger.__name__ = GestureTrigger.__qualname__ = (
        f"Bilresa{event_type.title().replace('_', '')}Trigger"
    )
    return GestureTrigger


# Trigger key -> the event type it watches. The keys are public: automations
# store them as `ikea_bilresa.<key>`.
GESTURES: dict[str, str] = {
    "rotated_up": ET_ROTATE_UP,
    "rotated_down": ET_ROTATE_DOWN,
    "pressed": ET_PRESS,
    "double_pressed": ET_DOUBLE_PRESS,
    "triple_pressed": ET_TRIPLE_PRESS,
    "held": ET_HOLD,
    "released": ET_RELEASE,
}

TRIGGERS: dict[str, type[Trigger]] = {
    key: _gesture_trigger(event_type) for key, event_type in GESTURES.items()
}


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type[Trigger]]:
    """Return the BILRESA triggers."""
    return TRIGGERS
