"""Privacy contract tests for downloadable diagnostics."""

from custom_components.ikea_bilresa.const import (
    CONF_CLICK_TARGET,
    CONF_DOUBLE_TARGET,
    CONF_HOLD_TARGET,
    CONF_NODE_ID,
    CONF_TARGET,
    CONF_TRIPLE_TARGET,
    CONF_URL,
)
from custom_components.ikea_bilresa.diagnostics import TO_REDACT


def test_household_identifiers_are_redacted() -> None:
    assert {
        CONF_URL,
        CONF_NODE_ID,
        CONF_TARGET,
        CONF_CLICK_TARGET,
        CONF_DOUBLE_TARGET,
        CONF_TRIPLE_TARGET,
        CONF_HOLD_TARGET,
        "serial",
        "compressed_fabric_id",
        "name",
        "title",
    } <= TO_REDACT
