"""Static guard: no device registry API that Home Assistant is removing.

Home Assistant 2026.8 made every device belong to one config entry and
scheduled the shared-device API for removal in 2027.8 to 2027.10. The runtime
guard in `test_device_link_registry.py` only sees code a test executes; this
one reads every source file.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

SOURCES = sorted(
    (Path(__file__).parent.parent / "custom_components" / "ikea_bilresa").glob("*.py")
)

# Each pattern is the deprecated spelling; the comment names its replacement.
BANNED = {
    # async_get_device_by_identifier / async_get_device_by_connection
    "DeviceRegistry.async_get_device": re.compile(r"\.async_get_device\("),
    # new_config_entry_id, or async_remove_device
    "add_config_entry_id": re.compile(r"\badd_config_entry_id\b"),
    "remove_config_entry_id": re.compile(r"\bremove_config_entry_id\b"),
    "add_config_subentry_id": re.compile(r"\badd_config_subentry_id\b"),
    "remove_config_subentry_id": re.compile(r"\bremove_config_subentry_id\b"),
    # new_identifiers / new_connections with the full set
    "merge_identifiers": re.compile(r"\bmerge_identifiers\b"),
    "merge_connections": re.compile(r"\bmerge_connections\b"),
    # DeviceEntry.config_entry_id / config_subentry_id
    # (`hass.config_entries` and the `homeassistant.config_entries` module are
    # the config entry manager, not this property.)
    "DeviceEntry.config_entries": re.compile(
        r"(?<!hass)(?<!homeassistant)\.config_entries\b"
    ),
    "DeviceEntry.config_entries_subentries": re.compile(
        r"\.config_entries_subentries\b"
    ),
    "DeviceEntry.primary_config_entry": re.compile(r"\.primary_config_entry\b"),
    # via_device_id
    "via_device": re.compile(r"\bvia_device\b(?!_id)"),
    # name / model / manufacturer
    "default_name": re.compile(r"\bdefault_(name|model|manufacturer)\b"),
    # Entity.device_entry
    "async_device_info_to_link": re.compile(r"\basync_device_info_to_link_from_"),
    # iterate DeviceRegistry.devices, look up with async_get
    "DeviceRegistry.devices mapping": re.compile(
        r"\.devices\.(get|values|keys|items)\("
    ),
    "DeviceRegistry.deleted_devices": re.compile(r"\.deleted_devices\b"),
}


def test_sources_were_found() -> None:
    assert len(SOURCES) > 20


@pytest.mark.parametrize("name", sorted(BANNED))
def test_no_deprecated_device_registry_api(name: str) -> None:
    pattern = BANNED[name]
    hits = [
        f"{source.name}:{number}: {line.strip()}"
        for source in SOURCES
        for number, line in enumerate(
            source.read_text(encoding="utf-8").splitlines(), start=1
        )
        if pattern.search(line)
    ]
    assert hits == [], f"{name} is scheduled for removal:\n" + "\n".join(hits)
