"""The device link against Home Assistant's real device and entity registries.

Every state these tests start from was observed in the field: a clean install,
the standalone device of 0.5.0, and the duplicate Home Assistant 2026.8 forked
for each wheel when a device could no longer be shared between config entries.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ikea_bilresa.const import DOMAIN
from custom_components.ikea_bilresa.device_link import (
    DeviceLinkManager,
    MatterDeviceLink,
    reconcile_wheel_device,
    resolve_matter_device,
)
from custom_components.ikea_bilresa.model import BilresaWheel

MATTER_URL = "ws://matter:5580/ws"
NODE_ID = 13
SERIAL = "TESTSERIAL0001"
SERVER_INFO = {"compressed_fabric_id": 2}
SERIAL_IDENTIFIER = ("matter", f"serial_{SERIAL}")
OPERATIONAL_IDENTIFIER = (
    "matter",
    "deviceid_0000000000000002-000000000000000D-MatterNodeDevice",
)
CUSTOM_IDENTIFIER = (DOMAIN, str(NODE_ID))


def _wheel(serial: str | None = SERIAL, node_id: int = NODE_ID) -> BilresaWheel:
    return BilresaWheel(
        node_id=node_id,
        name="BILRESA scroll wheel",
        product_name="BILRESA scroll wheel",
        serial=serial,
        endpoints={},
    )


class _World:
    """Two config entries and the registries, as a running instance has them."""

    def __init__(self, hass: HomeAssistant, matter_url: str = MATTER_URL) -> None:
        self.hass = hass
        self.matter = MockConfigEntry(domain="matter", data={"url": matter_url})
        self.matter.add_to_hass(hass)
        self.ours = MockConfigEntry(domain=DOMAIN)
        self.ours.add_to_hass(hass)
        self.devices = dr.async_get(hass)
        self.entities = er.async_get(hass)

    def matter_device(
        self, identifiers: set[tuple[str, str]] | None = None
    ) -> dr.DeviceEntry:
        return self.devices.async_get_or_create(
            config_entry_id=self.matter.entry_id,
            identifiers=identifiers or {SERIAL_IDENTIFIER, OPERATIONAL_IDENTIFIER},
            manufacturer="IKEA of Sweden",
            model="BILRESA scroll wheel",
            name="Wheel",
        )

    def own_device(self, identifiers: set[tuple[str, str]]) -> dr.DeviceEntry:
        return self.devices.async_get_or_create(
            config_entry_id=self.ours.entry_id, identifiers=identifiers
        )

    def entity(
        self, domain: str, unique_id: str, device: dr.DeviceEntry | None
    ) -> er.RegistryEntry:
        return self.entities.async_get_or_create(
            domain,
            DOMAIN,
            unique_id,
            config_entry=self.ours,
            device_id=device.id if device else None,
        )

    def reconcile(self, wheel: BilresaWheel | None = None) -> MatterDeviceLink:
        return reconcile_wheel_device(
            self.hass,
            config_entry_id=self.ours.entry_id,
            matter_url=MATTER_URL,
            server_info=SERVER_INFO,
            wheel=wheel or _wheel(),
        )

    def device_of(self, entity: er.RegistryEntry) -> str | None:
        current = self.entities.async_get(entity.entity_id)
        assert current is not None, f"{entity.entity_id} was removed"
        return current.device_id

    def own_devices(self) -> list[dr.DeviceEntry]:
        return dr.async_entries_for_config_entry(self.devices, self.ours.entry_id)


@pytest.fixture
def world(hass: HomeAssistant) -> _World:
    return _World(hass)


def _snapshot(world: _World) -> Any:
    """Everything a reconcile may change, for idempotence checks."""
    entry_ids = (world.matter.entry_id, world.ours.entry_id)
    return (
        sorted(
            (device.id, device.config_entry_id, sorted(device.identifiers))
            for entry_id in entry_ids
            for device in dr.async_entries_for_config_entry(world.devices, entry_id)
        ),
        sorted(
            (entity.entity_id, entity.device_id)
            for entity in er.async_entries_for_config_entry(
                world.entities, world.ours.entry_id
            )
        ),
    )


# -- resolution ------------------------------------------------------------


async def test_resolves_by_serial_and_operational_identifier(world: _World) -> None:
    device = world.matter_device()

    link = resolve_matter_device(
        world.hass, matter_url=MATTER_URL, server_info=SERVER_INFO, wheel=_wheel()
    )

    assert link.device is not None and link.device.id == device.id


async def test_resolves_missing_serial_by_operational_identifier(
    world: _World,
) -> None:
    """Firmware 1.8.7 reports no serial number."""
    device = world.matter_device({OPERATIONAL_IDENTIFIER})

    link = resolve_matter_device(
        world.hass, matter_url=MATTER_URL, server_info=SERVER_INFO, wheel=_wheel(None)
    )

    assert link.device is not None and link.device.id == device.id


async def test_does_not_link_to_a_different_matter_server(hass: HomeAssistant) -> None:
    world = _World(hass, matter_url="ws://another-server:5580/ws")
    world.matter_device()

    assert world.reconcile().device is None


async def test_trailing_slash_in_the_server_url_still_matches(
    hass: HomeAssistant,
) -> None:
    world = _World(hass, matter_url=MATTER_URL + "/")
    device = world.matter_device()

    link = world.reconcile()

    assert link.device is not None and link.device.id == device.id


async def test_conflicting_serial_and_operational_matches_stay_separate(
    world: _World, caplog: pytest.LogCaptureFixture
) -> None:
    world.matter_device({SERIAL_IDENTIFIER})
    world.matter_device({OPERATIONAL_IDENTIFIER})
    entity = world.entity("event", f"{NODE_ID}_ch1", None)

    link = world.reconcile()

    assert link.device is None
    assert world.device_of(entity) is None
    assert "resolve to different devices" in caplog.text


async def test_never_resolves_to_a_device_of_this_integration(world: _World) -> None:
    """The forked duplicate carries the Matter identifiers too."""
    world.own_device({SERIAL_IDENTIFIER, OPERATIONAL_IDENTIFIER, CUSTOM_IDENTIFIER})

    assert world.reconcile().device is None


# -- reconciliation and migration ------------------------------------------


async def test_clean_install_creates_no_device_of_our_own(world: _World) -> None:
    device = world.matter_device()

    link = world.reconcile()

    assert link.device is not None and link.device.id == device.id
    assert world.own_devices() == []
    assert link.device.config_entry_id == world.matter.entry_id


async def test_migrates_the_duplicate_forked_by_home_assistant_2026_8(
    world: _World,
) -> None:
    """The layout found on a live 2026.9.4 instance running rc.13."""
    matter = world.matter_device(
        {SERIAL_IDENTIFIER, OPERATIONAL_IDENTIFIER, CUSTOM_IDENTIFIER}
    )
    duplicate = world.own_device(
        {SERIAL_IDENTIFIER, OPERATIONAL_IDENTIFIER, CUSTOM_IDENTIFIER}
    )
    assert duplicate.id != matter.id
    on_matter = [
        world.entity("event", f"{NODE_ID}_ch{channel}", matter) for channel in (1, 2, 3)
    ] + [
        world.entity("number", f"{NODE_ID}_ch{channel}_dial", matter)
        for channel in (1, 2, 3)
    ]
    on_duplicate = [
        world.entity("switch", f"{NODE_ID}_ch{channel}_button", duplicate)
        for channel in (1, 2, 3)
    ]
    entity_ids = sorted(e.entity_id for e in on_matter + on_duplicate)

    link = world.reconcile()
    await world.hass.async_block_till_done()

    assert link.device is not None and link.device.id == matter.id
    for entity in on_matter + on_duplicate:
        assert world.device_of(entity) == matter.id
    assert world.devices.async_get(duplicate.id) is None
    assert world.own_devices() == []
    assert (
        sorted(
            e.entity_id
            for e in er.async_entries_for_config_entry(
                world.entities, world.ours.entry_id
            )
        )
        == entity_ids
    )
    # Our identifier is gone from the device we do not own; Matter's stay.
    assert link.device.identifiers == {SERIAL_IDENTIFIER, OPERATIONAL_IDENTIFIER}
    assert link.device.config_entry_id == world.matter.entry_id


async def test_migrates_the_standalone_device_of_0_5_0(world: _World) -> None:
    matter = world.matter_device()
    standalone = world.own_device({CUSTOM_IDENTIFIER})
    entities = [
        world.entity("event", f"{NODE_ID}_ch{channel}", standalone)
        for channel in (1, 2, 3)
    ]

    world.reconcile()
    await world.hass.async_block_till_done()

    for entity in entities:
        assert world.device_of(entity) == matter.id
    assert world.devices.async_get(standalone.id) is None


async def test_disabled_entities_are_moved_too(world: _World) -> None:
    matter = world.matter_device()
    standalone = world.own_device({CUSTOM_IDENTIFIER})
    entity = world.entity("number", f"{NODE_ID}_ch1_dial", standalone)
    world.entities.async_update_entity(
        entity.entity_id, disabled_by=er.RegistryEntryDisabler.USER
    )

    world.reconcile()
    await world.hass.async_block_till_done()

    assert world.device_of(entity) == matter.id
    assert world.devices.async_get(standalone.id) is None


async def test_a_device_still_carrying_an_entity_is_not_removed(
    world: _World, caplog: pytest.LogCaptureFixture
) -> None:
    """A helper the user attached there would lose its device otherwise."""
    matter = world.matter_device()
    standalone = world.own_device({CUSTOM_IDENTIFIER})
    ours = world.entity("event", f"{NODE_ID}_ch1", standalone)
    helper_entry = MockConfigEntry(domain="derivative")
    helper_entry.add_to_hass(world.hass)
    helper = world.entities.async_get_or_create(
        "sensor",
        "derivative",
        "helper-1",
        config_entry=helper_entry,
        device_id=standalone.id,
    )

    world.reconcile()
    await world.hass.async_block_till_done()

    assert world.device_of(ours) == matter.id
    assert world.devices.async_get(standalone.id) is not None
    assert world.device_of(helper) == standalone.id
    assert "still has entities attached" in caplog.text


async def test_entities_of_another_node_are_left_alone(world: _World) -> None:
    """Node 1 must not match node 13's `13_` prefix, nor the other way round."""
    matter = world.matter_device()
    other = world.own_device({(DOMAIN, "1")})
    other_entity = world.entity("event", "1_ch1", other)
    lookalike = world.entity("event", "130_ch1", other)

    world.reconcile()
    await world.hass.async_block_till_done()

    assert world.device_of(other_entity) == other.id
    assert world.device_of(lookalike) == other.id
    assert world.devices.async_get(other.id) is not None
    assert world.devices.async_get(matter.id) is not None


async def test_reconcile_is_idempotent(world: _World) -> None:
    matter = world.matter_device(
        {SERIAL_IDENTIFIER, OPERATIONAL_IDENTIFIER, CUSTOM_IDENTIFIER}
    )
    duplicate = world.own_device({SERIAL_IDENTIFIER, CUSTOM_IDENTIFIER})
    world.entity("event", f"{NODE_ID}_ch1", matter)
    world.entity("switch", f"{NODE_ID}_ch1_button", duplicate)

    world.reconcile()
    await world.hass.async_block_till_done()
    after_first = _snapshot(world)
    world.reconcile()
    world.reconcile()
    await world.hass.async_block_till_done()

    assert _snapshot(world) == after_first


async def test_standalone_wheel_is_left_untouched(hass: HomeAssistant) -> None:
    """No Matter config entry for this server: our own device stays ours."""
    world = _World(hass, matter_url="ws://another-server:5580/ws")
    standalone = world.own_device({CUSTOM_IDENTIFIER})
    entity = world.entity("event", f"{NODE_ID}_ch1", standalone)
    before = _snapshot(world)

    link = world.reconcile()

    assert link.device is None
    assert world.device_of(entity) == standalone.id
    assert _snapshot(world) == before


# -- the manager while running ---------------------------------------------


def _manager(world: _World, wheels: dict[int, BilresaWheel]) -> DeviceLinkManager:
    source = SimpleNamespace(
        url=MATTER_URL, wheels=wheels, matter_server_info=SERVER_INFO
    )
    return DeviceLinkManager(world.hass, world.ours.entry_id, source)


async def test_manager_reports_the_matter_device(world: _World) -> None:
    matter = world.matter_device()
    manager = _manager(world, {NODE_ID: _wheel()})

    link = manager.link_for(_wheel())

    assert link.device is not None and link.device.id == matter.id
    assert manager.device_id(NODE_ID) == matter.id


async def test_manager_reports_our_standalone_device(world: _World) -> None:
    manager = _manager(world, {NODE_ID: _wheel()})
    assert manager.link_for(_wheel()).device is None
    assert manager.device_id(NODE_ID) is None

    standalone = world.own_device({CUSTOM_IDENTIFIER})

    assert manager.device_id(NODE_ID) == standalone.id


async def test_matter_device_created_later_is_picked_up(world: _World) -> None:
    """A wheel commissioned while running can reach us before core Matter."""
    manager = _manager(world, {NODE_ID: _wheel()})
    unsubscribe = manager.async_start()
    assert manager.link_for(_wheel()).device is None
    standalone = world.own_device({CUSTOM_IDENTIFIER})
    entity = world.entity("event", f"{NODE_ID}_ch1", standalone)
    assert manager.device_id(NODE_ID) == standalone.id

    matter = world.matter_device()
    await world.hass.async_block_till_done()

    assert world.device_of(entity) == matter.id
    assert world.devices.async_get(standalone.id) is None
    assert manager.device_id(NODE_ID) == matter.id
    unsubscribe()


async def test_unrelated_matter_devices_trigger_no_work(world: _World) -> None:
    manager = _manager(world, {NODE_ID: _wheel()})
    unsubscribe = manager.async_start()
    standalone = world.own_device({CUSTOM_IDENTIFIER})
    entity = world.entity("event", f"{NODE_ID}_ch1", standalone)

    world.matter_device({("matter", "serial_SOME_LAMP")})
    await world.hass.async_block_till_done()

    assert world.device_of(entity) == standalone.id
    assert manager.device_id(NODE_ID) == standalone.id
    unsubscribe()


async def test_removed_matter_device_detaches_without_error(world: _World) -> None:
    matter = world.matter_device()
    manager = _manager(world, {NODE_ID: _wheel()})
    unsubscribe = manager.async_start()
    entity = world.entity("event", f"{NODE_ID}_ch1", matter)
    manager.link_for(_wheel())

    world.devices.async_remove_device(matter.id)
    await world.hass.async_block_till_done()

    assert world.device_of(entity) is None
    assert manager.device_id(NODE_ID) is None
    unsubscribe()


async def test_forgotten_node_has_no_device(world: _World) -> None:
    world.matter_device()
    manager = _manager(world, {NODE_ID: _wheel()})
    manager.link_for(_wheel())

    manager.forget(NODE_ID)

    assert manager.device_id(NODE_ID) is None


# -- the 2027 guard ---------------------------------------------------------


async def test_reconcile_uses_no_api_scheduled_for_removal(
    world: _World, caplog: pytest.LogCaptureFixture
) -> None:
    """Home Assistant reports every deprecated registry call it sees."""
    caplog.set_level(logging.WARNING)
    matter = world.matter_device(
        {SERIAL_IDENTIFIER, OPERATIONAL_IDENTIFIER, CUSTOM_IDENTIFIER}
    )
    duplicate = world.own_device({SERIAL_IDENTIFIER, CUSTOM_IDENTIFIER})
    world.entity("event", f"{NODE_ID}_ch1", matter)
    world.entity("switch", f"{NODE_ID}_ch1_button", duplicate)
    manager = _manager(world, {NODE_ID: _wheel()})
    unsubscribe = manager.async_start()

    manager.link_for(_wheel())
    manager.device_id(NODE_ID)
    await world.hass.async_block_till_done()
    unsubscribe()

    reports = [
        record.getMessage()
        for record in caplog.records
        if "deprecated" in record.getMessage().lower()
        or "stop working" in record.getMessage().lower()
    ]
    assert reports == []
