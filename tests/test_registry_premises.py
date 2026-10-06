"""Premises about Home Assistant's registries that the device link relies on.

These test Home Assistant, not this integration. They pin the behaviour
`docs/DEVICE_REGISTRY_PLAN.md` is built on, so a Home Assistant release that
changes one of them fails here, by name, instead of somewhere inside the
device link.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ikea_bilresa.const import DOMAIN

MATTER_IDENTIFIER = ("matter", "serial_TEST0001")


def _entries(hass: HomeAssistant) -> tuple[MockConfigEntry, MockConfigEntry]:
    matter = MockConfigEntry(domain="matter", data={"url": "ws://matter:5580/ws"})
    matter.add_to_hass(hass)
    ours = MockConfigEntry(domain=DOMAIN)
    ours.add_to_hass(hass)
    return matter, ours


async def test_shared_identifier_yields_one_device_per_config_entry(
    hass: HomeAssistant,
) -> None:
    """Describing another entry's device by its identifiers forks a duplicate."""
    matter, ours = _entries(hass)
    registry = dr.async_get(hass)

    matter_device = registry.async_get_or_create(
        config_entry_id=matter.entry_id, identifiers={MATTER_IDENTIFIER}
    )
    duplicate = registry.async_get_or_create(
        config_entry_id=ours.entry_id, identifiers={MATTER_IDENTIFIER}
    )

    assert duplicate.id != matter_device.id
    assert matter_device.config_entry_id == matter.entry_id
    assert duplicate.config_entry_id == ours.entry_id


async def test_identifier_lookup_is_scoped_to_one_config_entry(
    hass: HomeAssistant,
) -> None:
    matter, ours = _entries(hass)
    registry = dr.async_get(hass)
    matter_device = registry.async_get_or_create(
        config_entry_id=matter.entry_id, identifiers={MATTER_IDENTIFIER}
    )

    found = registry.async_get_device_by_identifier(MATTER_IDENTIFIER, matter.entry_id)
    assert found is not None and found.id == matter_device.id
    assert (
        registry.async_get_device_by_identifier(MATTER_IDENTIFIER, ours.entry_id)
        is None
    )
    assert [
        device.id
        for device in registry.async_get_devices(
            identifiers={MATTER_IDENTIFIER}, config_entry_id=matter.entry_id
        )
    ] == [matter_device.id]


async def test_entity_can_sit_on_another_config_entrys_device(
    hass: HomeAssistant,
) -> None:
    matter, ours = _entries(hass)
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    matter_device = device_registry.async_get_or_create(
        config_entry_id=matter.entry_id, identifiers={MATTER_IDENTIFIER}
    )

    entity = entity_registry.async_get_or_create(
        "event", DOMAIN, "13_ch1", config_entry=ours, device_id=matter_device.id
    )

    assert entity.device_id == matter_device.id
    assert entity.config_entry_id == ours.entry_id
    # Attaching the entity must not make this integration a co-owner.
    refreshed = device_registry.async_get(matter_device.id)
    assert refreshed is not None
    assert refreshed.config_entry_id == matter.entry_id


async def test_removing_a_device_detaches_foreign_entities_and_removes_own(
    hass: HomeAssistant,
) -> None:
    """Why a duplicate may only be removed once none of our entities is on it."""
    matter, ours = _entries(hass)
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    matter_device = device_registry.async_get_or_create(
        config_entry_id=matter.entry_id, identifiers={MATTER_IDENTIFIER}
    )
    own_device = device_registry.async_get_or_create(
        config_entry_id=ours.entry_id, identifiers={(DOMAIN, "13")}
    )
    on_matter = entity_registry.async_get_or_create(
        "event", DOMAIN, "13_ch1", config_entry=ours, device_id=matter_device.id
    )
    on_own = entity_registry.async_get_or_create(
        "switch", DOMAIN, "13_ch1_button", config_entry=ours, device_id=own_device.id
    )

    device_registry.async_remove_device(own_device.id)
    device_registry.async_remove_device(matter_device.id)
    await hass.async_block_till_done()

    assert entity_registry.async_get(on_own.entity_id) is None
    survivor = entity_registry.async_get(on_matter.entity_id)
    assert survivor is not None
    assert survivor.device_id is None
