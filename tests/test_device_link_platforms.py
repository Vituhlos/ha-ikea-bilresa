"""The entity platforms on real registries: where the entities end up.

`test_device_link_registry.py` covers the registry bookkeeping on its own.
These tests run the real `event`, `number` and `switch` platform setup, so they
also cover what only Home Assistant's entity platform decides: which device an
entity is registered on, and whether a device of our own gets created.
"""

from __future__ import annotations

from types import SimpleNamespace

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import Entity
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockEntityPlatform,
)

from custom_components.ikea_bilresa import event, number, switch
from custom_components.ikea_bilresa.const import (
    DOMAIN,
    ROLE_BUTTON,
    ROLE_SCROLL_DOWN,
    ROLE_SCROLL_UP,
)
from custom_components.ikea_bilresa.coordinator import BilresaCoordinator
from custom_components.ikea_bilresa.model import BilresaWheel, SwitchEndpoint

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

MATTER_URL = "ws://matter:5580/ws"
SERVER_INFO = {"compressed_fabric_id": 2}
WHEEL_NODE = 13
BUTTON_NODE = 15
WHEEL_SERIAL = ("matter", "serial_WHEEL0001")
BUTTON_SERIAL = ("matter", "serial_BUTTON0001")

PLATFORMS = {"event": event, "number": number, "switch": switch}


def _wheel() -> BilresaWheel:
    endpoints: dict[int, SwitchEndpoint] = {}
    for channel in (1, 2, 3):
        base = (channel - 1) * 3
        endpoints[base + 1] = SwitchEndpoint(base + 1, channel, ROLE_SCROLL_UP, 18)
        endpoints[base + 2] = SwitchEndpoint(base + 2, channel, ROLE_SCROLL_DOWN, 18)
        endpoints[base + 3] = SwitchEndpoint(base + 3, channel, ROLE_BUTTON, 3)
    return BilresaWheel(
        node_id=WHEEL_NODE,
        name="BILRESA scroll wheel",
        product_name="BILRESA scroll wheel",
        serial="WHEEL0001",
        endpoints=endpoints,
    )


def _dual_button() -> BilresaWheel:
    return BilresaWheel(
        node_id=BUTTON_NODE,
        name="BILRESA dual button",
        product_name="BILRESA dual button",
        serial="BUTTON0001",
        endpoints={
            1: SwitchEndpoint(1, None, ROLE_BUTTON, 2),
            2: SwitchEndpoint(2, None, ROLE_BUTTON, 2),
        },
    )


class _Instance:
    """A config entry with a real coordinator, minus the Matter connection."""

    def __init__(
        self, hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, *wheels
    ) -> None:
        self.hass = hass
        self.matter = MockConfigEntry(domain="matter", data={"url": MATTER_URL})
        self.matter.add_to_hass(hass)
        self.entry = MockConfigEntry(domain=DOMAIN)
        self.entry.add_to_hass(hass)
        self.devices = dr.async_get(hass)
        self.entities = er.async_get(hass)
        monkeypatch.setattr(
            "custom_components.ikea_bilresa.coordinator.CoreMatterEventSource",
            lambda *_args: SimpleNamespace(source="core", server_info=SERVER_INFO),
        )
        self.coordinator = BilresaCoordinator(hass, MATTER_URL)
        self.coordinator.connected = True
        for wheel in wheels:
            self.coordinator.wheels[wheel.node_id] = wheel
        self.entry.runtime_data = self.coordinator
        self._links_started = False

    def matter_device(self, identifier: tuple[str, str], name: str) -> dr.DeviceEntry:
        return self.devices.async_get_or_create(
            config_entry_id=self.matter.entry_id,
            identifiers={identifier},
            manufacturer="IKEA of Sweden",
            model="BILRESA",
            name=name,
        )

    async def setup_platforms(self) -> None:
        """Run each platform's real setup through a real entity platform.

        The device link starts here, as it does in `async_setup_entry`: after
        the registries are loaded and before any platform is forwarded.
        """
        if not self._links_started:
            self.coordinator.async_setup_device_links(self.entry)
            self._links_started = True
        for domain, module in PLATFORMS.items():
            platform = MockEntityPlatform(
                self.hass, domain=domain, platform_name=DOMAIN
            )
            platform.config_entry = self.entry
            # Home Assistant loads these before a platform adds entities;
            # entity names and entity IDs are built from them.
            await platform.platform_data.async_load_translations()
            added: list[Entity] = []
            await module.async_setup_entry(self.hass, self.entry, added.extend)
            await platform.async_add_entities(added)
        await self.hass.async_block_till_done()

    def ours(self) -> list[er.RegistryEntry]:
        return er.async_entries_for_config_entry(self.entities, self.entry.entry_id)

    def own_devices(self) -> list[dr.DeviceEntry]:
        return dr.async_entries_for_config_entry(self.devices, self.entry.entry_id)


async def test_linked_entities_register_on_the_matter_device(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance = _Instance(hass, monkeypatch, _wheel(), _dual_button())
    wheel_device = instance.matter_device(WHEEL_SERIAL, "Living room wheel")
    button_device = instance.matter_device(BUTTON_SERIAL, "Hall button")

    await instance.setup_platforms()

    by_device: dict[str | None, list[str]] = {}
    for entity in instance.ours():
        by_device.setdefault(entity.device_id, []).append(entity.unique_id)
    assert sorted(by_device[wheel_device.id]) == sorted(
        [f"{WHEEL_NODE}_ch{c}" for c in (1, 2, 3)]
        + [f"{WHEEL_NODE}_ch{c}_dial" for c in (1, 2, 3)]
        + [f"{WHEEL_NODE}_ch{c}_button" for c in (1, 2, 3)]
    )
    assert sorted(by_device[button_device.id]) == [
        f"{BUTTON_NODE}_ep1",
        f"{BUTTON_NODE}_ep2",
    ]
    assert set(by_device) == {wheel_device.id, button_device.id}
    # Nothing of ours in the device registry, and Matter still owns its own.
    assert instance.own_devices() == []
    for device in (wheel_device, button_device):
        current = instance.devices.async_get(device.id)
        assert current is not None
        assert current.config_entry_id == instance.matter.entry_id
        assert current.identifiers == device.identifiers
    # The Matter device's name leads the entity name, as it did before.
    state = hass.states.get("event.living_room_wheel_channel_1")
    assert state is not None
    assert state.attributes["friendly_name"] == "Living room wheel Channel 1"


async def test_unlinked_wheel_gets_one_described_standalone_device(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance = _Instance(hass, monkeypatch, _wheel(), _dual_button())

    await instance.setup_platforms()

    devices = {
        next(iter(d.identifiers)): d for d in instance.own_devices() if d.identifiers
    }
    assert set(devices) == {(DOMAIN, str(WHEEL_NODE)), (DOMAIN, str(BUTTON_NODE))}
    wheel_device = devices[(DOMAIN, str(WHEEL_NODE))]
    assert wheel_device.manufacturer == "IKEA of Sweden"
    assert wheel_device.model == "BILRESA scroll wheel"
    assert wheel_device.name == "BILRESA scroll wheel"
    assert wheel_device.identifiers == {(DOMAIN, str(WHEEL_NODE))}
    assert devices[(DOMAIN, str(BUTTON_NODE))].model == "BILRESA dual button"
    assert {e.device_id for e in instance.ours()} == {d.id for d in devices.values()}
    assert instance.coordinator.device_links.device_id(WHEEL_NODE) == wheel_device.id


async def test_upgrade_from_the_rc13_layout_on_home_assistant_2026_9(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Start from the registries a live instance had, then start the platforms."""
    instance = _Instance(hass, monkeypatch, _wheel())
    custom = (DOMAIN, str(WHEEL_NODE))
    matter = instance.devices.async_get_or_create(
        config_entry_id=instance.matter.entry_id,
        identifiers={WHEEL_SERIAL, custom},
        name="Living room wheel",
    )
    duplicate = instance.devices.async_get_or_create(
        config_entry_id=instance.entry.entry_id, identifiers={WHEEL_SERIAL, custom}
    )
    before: dict[str, str] = {}
    for channel in (1, 2, 3):
        for domain, suffix, device in (
            ("event", "", matter),
            ("number", "_dial", matter),
            ("switch", "_button", duplicate),
        ):
            unique_id = f"{WHEEL_NODE}_ch{channel}{suffix}"
            entry = instance.entities.async_get_or_create(
                domain,
                DOMAIN,
                unique_id,
                config_entry=instance.entry,
                device_id=device.id,
                suggested_object_id=f"legacy_{unique_id}",
            )
            before[unique_id] = entry.entity_id

    await instance.setup_platforms()

    after = {entity.unique_id: entity for entity in instance.ours()}
    assert {uid: entity.entity_id for uid, entity in after.items()} == before
    assert {entity.device_id for entity in after.values()} == {matter.id}
    assert instance.devices.async_get(duplicate.id) is None
    assert instance.own_devices() == []
    current = instance.devices.async_get(matter.id)
    assert current is not None and current.identifiers == {WHEEL_SERIAL}
    # Every entity is live, not just present in the registry.
    for entity_id in before.values():
        assert hass.states.get(entity_id) is not None
    assert instance.coordinator.device_links.device_id(WHEEL_NODE) == matter.id


async def test_live_entities_follow_a_matter_device_created_later(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance = _Instance(hass, monkeypatch, _wheel())
    await instance.setup_platforms()
    (standalone,) = instance.own_devices()

    matter = instance.matter_device(WHEEL_SERIAL, "Living room wheel")
    await hass.async_block_till_done()

    assert {e.device_id for e in instance.ours()} == {matter.id}
    assert instance.devices.async_get(standalone.id) is None
    assert len(instance.ours()) == 9
    for entity in instance.ours():
        assert hass.states.get(entity.entity_id) is not None
    assert instance.coordinator.device_links.device_id(WHEEL_NODE) == matter.id


async def test_second_sync_adds_and_moves_nothing(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance = _Instance(hass, monkeypatch, _wheel())
    matter = instance.matter_device(WHEEL_SERIAL, "Living room wheel")
    await instance.setup_platforms()
    first = sorted((e.entity_id, e.device_id) for e in instance.ours())

    await instance.setup_platforms()

    assert sorted((e.entity_id, e.device_id) for e in instance.ours()) == first
    assert instance.own_devices() == []
    assert instance.devices.async_get(matter.id) is not None
