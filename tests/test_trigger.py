"""The named BILRESA triggers, run through Home Assistant's automation engine."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from homeassistant.const import EVENT_COMPONENT_LOADED
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.loader import async_get_integration
from homeassistant.setup import ATTR_COMPONENT, async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockEntityPlatform,
    async_capture_events,
)
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.ikea_bilresa.const import DOMAIN, WHEEL_EVENT_TYPES
from custom_components.ikea_bilresa.device_link import MatterDeviceLink
from custom_components.ikea_bilresa.event import BilresaChannelEvent
from custom_components.ikea_bilresa.trigger import GESTURES, TRIGGERS

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

FIRED = "bilresa_test_fired"


class _Home:
    """A Matter device carrying our event entities and one of Matter's own."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._tick = 0
        matter = MockConfigEntry(domain="matter")
        matter.add_to_hass(hass)
        ours = MockConfigEntry(domain=DOMAIN)
        ours.add_to_hass(hass)
        self.device = dr.async_get(hass).async_get_or_create(
            config_entry_id=matter.entry_id, identifiers={("matter", "serial_T")}
        )
        registry = er.async_get(hass)
        self.channel_1 = registry.async_get_or_create(
            "event", DOMAIN, "13_ch1", config_entry=ours, device_id=self.device.id
        ).entity_id
        self.channel_2 = registry.async_get_or_create(
            "event", DOMAIN, "13_ch2", config_entry=ours, device_id=self.device.id
        ).entity_id
        self.matter_button = registry.async_get_or_create(
            "event",
            "matter",
            "matter-ep3",
            config_entry=matter,
            device_id=self.device.id,
        ).entity_id
        for entity_id in (self.channel_1, self.channel_2, self.matter_button):
            hass.states.async_set(entity_id, "unknown")

    async def gesture(self, entity_id: str, event_type: str, **attributes: Any) -> None:
        """Report one event the way an event entity does: a new timestamp."""
        self._tick += 1
        self.hass.states.async_set(
            entity_id,
            f"2026-10-03T10:00:{self._tick:02d}.000+00:00",
            {"event_type": event_type, **attributes},
        )
        await self.hass.async_block_till_done()

    async def automation(self, trigger: str, target: dict[str, Any]) -> list[Event]:
        fired = async_capture_events(self.hass, FIRED)
        assert await async_setup_component(
            self.hass,
            "automation",
            {
                "automation": {
                    "alias": f"on {trigger}",
                    "triggers": [{"trigger": f"{DOMAIN}.{trigger}", "target": target}],
                    "actions": [
                        {
                            "event": FIRED,
                            "event_data": {
                                "entity_id": "{{ trigger.entity_id }}",
                                "notches": (
                                    "{{ trigger.to_state.attributes.notches"
                                    " | default(none) }}"
                                ),
                            },
                        }
                    ],
                }
            },
        )
        await self.hass.async_block_till_done()
        return fired


def test_one_trigger_per_wheel_gesture() -> None:
    assert sorted(GESTURES.values()) == sorted(WHEEL_EVENT_TYPES)
    assert set(TRIGGERS) == set(GESTURES)
    assert len({trigger.__name__ for trigger in TRIGGERS.values()}) == len(TRIGGERS)


@pytest.mark.parametrize(("trigger", "event_type"), sorted(GESTURES.items()))
async def test_trigger_fires_for_its_gesture_and_no_other(
    hass: HomeAssistant, trigger: str, event_type: str
) -> None:
    home = _Home(hass)
    fired = await home.automation(trigger, {"entity_id": home.channel_1})

    for other in WHEEL_EVENT_TYPES:
        await home.gesture(home.channel_1, other)

    assert len(fired) == 1
    assert fired[0].data["entity_id"] == home.channel_1


async def test_repeating_the_same_gesture_fires_every_time(
    hass: HomeAssistant,
) -> None:
    """Fast rotation is many `rotate_up` events in a row, not a state change."""
    home = _Home(hass)
    fired = await home.automation("rotated_up", {"entity_id": home.channel_1})

    for notches in (1, 5, 2):
        await home.gesture(home.channel_1, "rotate_up", notches=notches)

    assert [event.data["notches"] for event in fired] == [1, 5, 2]


async def test_trigger_ignores_other_channels(hass: HomeAssistant) -> None:
    home = _Home(hass)
    fired = await home.automation("pressed", {"entity_id": home.channel_1})

    await home.gesture(home.channel_2, "press")

    assert fired == []


async def test_device_target_covers_our_entities_but_not_core_matters(
    hass: HomeAssistant,
) -> None:
    """The reason the triggers exist: aim at the Matter device, get our gestures."""
    home = _Home(hass)
    fired = await home.automation("rotated_up", {"device_id": home.device.id})

    await home.gesture(home.channel_1, "rotate_up")
    await home.gesture(home.channel_2, "rotate_up")
    # Core Matter's entity sits on the same device; even reporting the very
    # same event type it is not ours to react to.
    await home.gesture(home.matter_button, "rotate_up")

    assert [event.data["entity_id"] for event in fired] == [
        home.channel_1,
        home.channel_2,
    ]


async def test_unavailable_entity_does_not_fire(hass: HomeAssistant) -> None:
    home = _Home(hass)
    fired = await home.automation("pressed", {"entity_id": home.channel_1})

    hass.states.async_set(home.channel_1, "unavailable", {"event_type": "press"})
    await hass.async_block_till_done()

    assert fired == []


async def test_triggers_are_offered_for_the_matter_device(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """What the automation editor asks when the user picks the wheel's device.

    Uses a live entity: Home Assistant decides what to offer from the entities
    actually running on the target, not from the registry.
    """
    matter = MockConfigEntry(domain="matter")
    matter.add_to_hass(hass)
    ours = MockConfigEntry(domain=DOMAIN)
    ours.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=matter.entry_id, identifiers={("matter", "serial_OFFER")}
    )
    platform = MockEntityPlatform(hass, domain="event", platform_name=DOMAIN)
    platform.config_entry = ours
    await platform.platform_data.async_load_translations()
    await platform.async_add_entities(
        [
            BilresaChannelEvent(
                SimpleNamespace(connected=True),
                SimpleNamespace(node_id=13, name="Wheel"),
                1,
                MatterDeviceLink(device),
            )
        ]
    )
    assert await async_setup_component(hass, "automation", {})
    # The integration is not set up in this test (that needs a Matter Server);
    # announce it the way a finished setup does, so its trigger platform loads.
    await async_get_integration(hass, DOMAIN)
    hass.config.components.add(DOMAIN)
    hass.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: DOMAIN})
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "get_triggers_for_target", "target": {"device_id": [device.id]}}
    )
    response = await client.receive_json()

    assert response["success"], response
    assert {f"{DOMAIN}.{trigger}" for trigger in GESTURES} <= set(response["result"])
    # The device itself still belongs to core Matter alone.
    assert device.config_entry_id == matter.entry_id
