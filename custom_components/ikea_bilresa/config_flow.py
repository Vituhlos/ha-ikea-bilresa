"""Config flow for the IKEA BILRESA (smooth scroll) integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant

from .const import CONF_URL, DEFAULT_MATTER_URL, DOMAIN


def _matter_server_url(hass: HomeAssistant) -> str:
    for entry in hass.config_entries.async_entries("matter"):
        if url := entry.data.get("url"):
            return url
    return DEFAULT_MATTER_URL


class BilresaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Single-instance config flow. Auto-detects the Matter Server URL."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="IKEA BILRESA", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_URL, default=_matter_server_url(self.hass)
                ): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
