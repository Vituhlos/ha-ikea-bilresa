"""Config flow for the IKEA BILRESA (smooth scroll) integration.

A single parent config entry holds the Matter Server connection. Light bindings
are added through **config subentries** — one per wheel channel — configured
entirely in the UI.
"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
import voluptuous as vol

from .const import (
    BINDING_PROFILE_CLIMATE,
    BINDING_PROFILE_COVER,
    BINDING_PROFILE_LIGHT,
    BINDING_PROFILE_MEDIA,
    BINDING_PROFILE_SCENES,
    BINDING_PROFILES,
    CLICK_ACTIONS,
    CLICK_NONE,
    CONF_ACCELERATION,
    CONF_BINDING_PROFILE,
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_CLICK_TARGET,
    CONF_COPY_FROM,
    CONF_DOUBLE_TARGET,
    CONF_HOLD_ACTION,
    CONF_HOLD_TARGET,
    CONF_MAX_BRIGHTNESS,
    CONF_MIN_BRIGHTNESS,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_SCENES,
    CONF_STEP,
    CONF_TARGET,
    CONF_TRANSITION,
    CONF_TRIPLE_TARGET,
    CONF_URL,
    DEFAULT_ACCELERATION,
    DEFAULT_CLICK_ACTION,
    DEFAULT_HOLD_ACTION,
    DEFAULT_MATTER_URL,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MODE,
    DEFAULT_STEP,
    DEFAULT_TRANSITION,
    DOMAIN,
    HOLD_ACTIONS,
    MODE_BRIGHTNESS,
    MODE_COVER,
    MODE_TEMPERATURE,
    MODE_VOLUME,
    MODES,
    SUBENTRY_BINDING,
    TARGET_DOMAINS,
)
from .matter_ws import MatterWSIncompatible, validate_server_info
from .presentation import generated_binding_title


def _matter_server_url(hass: HomeAssistant) -> str:
    for entry in hass.config_entries.async_entries("matter"):
        if url := entry.data.get("url"):
            return url
    return DEFAULT_MATTER_URL


async def _async_can_connect(hass: HomeAssistant, url: str) -> bool:
    """Return True if a Matter Server answers with a ServerInfo message."""
    session = async_get_clientsession(hass)
    try:
        async with (
            asyncio.timeout(10),
            session.ws_connect(url, heartbeat=None) as ws,
        ):
            message = await ws.receive_json()
            validate_server_info(message)
    except (
        TimeoutError,
        OSError,
        aiohttp.ClientError,
        MatterWSIncompatible,
        ValueError,
        TypeError,
    ):
        return False
    return True


class BilresaConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Single-instance parent flow. Auto-detects the Matter Server URL."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            if await _async_can_connect(self.hass, user_input[CONF_URL]):
                return self.async_create_entry(title="IKEA BILRESA", data=user_input)
            errors["base"] = "cannot_connect"

        default_url = (user_input or {}).get(CONF_URL) or _matter_server_url(self.hass)
        schema = vol.Schema({vol.Required(CONF_URL, default=default_url): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the Matter Server URL of an existing entry."""
        entry = self._get_reconfigure_entry()
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_mismatch()

        errors: dict[str, str] = {}
        if user_input is not None:
            if await _async_can_connect(self.hass, user_input[CONF_URL]):
                return self.async_update_and_abort(
                    entry,
                    data_updates={CONF_URL: user_input[CONF_URL]},
                )
            errors["base"] = "cannot_connect"

        default_url = (user_input or {}).get(CONF_URL) or entry.data.get(
            CONF_URL, DEFAULT_MATTER_URL
        )
        schema = vol.Schema({vol.Required(CONF_URL, default=default_url): str})
        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_supported_subentry_types(
        config_entry,
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_BINDING: BindingSubentryFlowHandler}


class BindingSubentryFlowHandler(ConfigSubentryFlow):
    """Add or reconfigure a wheel-channel -> light binding, all in the UI."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if hasattr(self, "_pending_defaults"):
            return await self._async_step_form("user", user_input)
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=self._setup_schema()
            )
        self._pending_defaults = self._creation_defaults(user_input)
        return await self._async_step_form("user", None)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_step_form("reconfigure", user_input)

    async def _async_step_form(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> SubentryFlowResult:
        wheel_options = self._wheel_options()
        if not wheel_options:
            return self.async_abort(reason="no_wheels")

        if user_input is not None:
            title = self._title(user_input)
            if step_id == "reconfigure":
                return self.async_update_and_abort(
                    self._get_entry(),
                    self._get_reconfigure_subentry(),
                    title=title,
                    data=user_input,
                )
            return self.async_create_entry(title=title, data=user_input)

        defaults = (
            self._get_reconfigure_subentry().data
            if step_id == "reconfigure"
            else getattr(self, "_pending_defaults", {})
        )
        return self.async_show_form(
            step_id=step_id,
            data_schema=self._schema(wheel_options, defaults),
        )

    @callback
    def _setup_schema(self) -> vol.Schema:
        schema: dict[Any, Any] = {
            vol.Required(
                CONF_BINDING_PROFILE, default=BINDING_PROFILE_LIGHT
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=BINDING_PROFILES,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="binding_profile",
                )
            )
        }
        copy_options = [
            selector.SelectOptionDict(value=subentry.subentry_id, label=subentry.title)
            for subentry in self._get_entry().subentries.values()
            if subentry.subentry_type == SUBENTRY_BINDING
        ]
        if copy_options:
            schema[vol.Optional(CONF_COPY_FROM)] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=copy_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        return vol.Schema(schema)

    @callback
    def _creation_defaults(self, user_input: dict[str, Any]) -> dict[str, Any]:
        if copy_from := user_input.get(CONF_COPY_FROM):
            subentry = self._get_entry().subentries.get(copy_from)
            if subentry is not None and subentry.subentry_type == SUBENTRY_BINDING:
                return dict(subentry.data)

        profile = user_input[CONF_BINDING_PROFILE]
        defaults: dict[str, Any] = {}
        if profile == BINDING_PROFILE_LIGHT:
            defaults[CONF_MODE] = MODE_BRIGHTNESS
        elif profile == BINDING_PROFILE_MEDIA:
            defaults[CONF_MODE] = MODE_VOLUME
        elif profile == BINDING_PROFILE_COVER:
            defaults[CONF_MODE] = MODE_COVER
        elif profile == BINDING_PROFILE_CLIMATE:
            defaults[CONF_MODE] = MODE_TEMPERATURE
        elif profile == BINDING_PROFILE_SCENES:
            defaults[CONF_MODE] = MODE_BRIGHTNESS
            defaults[CONF_CLICK_ACTION] = CLICK_NONE
        return defaults

    @callback
    def _wheel_options(self) -> list[selector.SelectOptionDict]:
        coordinator = self._get_entry().runtime_data
        device_registry = async_get_device_registry(self.hass)
        options: list[selector.SelectOptionDict] = []
        for node_id, wheel in coordinator.wheels.items():
            label = wheel.name
            if wheel.serial:
                device = device_registry.async_get_device(
                    identifiers={("matter", f"serial_{wheel.serial}")}
                )
                if device:
                    label = device.name_by_user or device.name or label
            options.append(
                selector.SelectOptionDict(
                    value=str(node_id), label=f"{label} (node {node_id})"
                )
            )
        return options

    @callback
    def _schema(
        self,
        wheel_options: list[selector.SelectOptionDict],
        defaults: dict[str, Any],
    ) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_NODE_ID, default=defaults.get(CONF_NODE_ID)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=wheel_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_CHANNEL, default=defaults.get(CONF_CHANNEL, "1")
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["1", "2", "3"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_TARGET, default=defaults.get(CONF_TARGET)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=TARGET_DOMAINS)
                ),
                vol.Required(
                    CONF_MODE, default=defaults.get(CONF_MODE, DEFAULT_MODE)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=MODES,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="scroll_mode",
                    )
                ),
                vol.Required(
                    CONF_STEP, default=defaults.get(CONF_STEP, DEFAULT_STEP)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=25,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                    )
                ),
                vol.Required(
                    CONF_ACCELERATION,
                    default=defaults.get(CONF_ACCELERATION, DEFAULT_ACCELERATION),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=100,
                        step=5,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                    )
                ),
                vol.Required(
                    CONF_MIN_BRIGHTNESS,
                    default=defaults.get(CONF_MIN_BRIGHTNESS, DEFAULT_MIN_BRIGHTNESS),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=50,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                    )
                ),
                vol.Required(
                    CONF_MAX_BRIGHTNESS,
                    default=defaults.get(CONF_MAX_BRIGHTNESS, DEFAULT_MAX_BRIGHTNESS),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=100,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                    )
                ),
                vol.Required(
                    CONF_TRANSITION,
                    default=defaults.get(CONF_TRANSITION, DEFAULT_TRANSITION),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=5,
                        step=0.1,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="s",
                    )
                ),
                vol.Required(
                    CONF_CLICK_ACTION,
                    default=defaults.get(CONF_CLICK_ACTION, DEFAULT_CLICK_ACTION),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=CLICK_ACTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="click_action",
                    )
                ),
                vol.Optional(
                    CONF_CLICK_TARGET,
                    description={"suggested_value": defaults.get(CONF_CLICK_TARGET)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["light", "switch"])
                ),
                vol.Optional(
                    CONF_DOUBLE_TARGET,
                    description={"suggested_value": defaults.get(CONF_DOUBLE_TARGET)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["light", "switch"])
                ),
                vol.Optional(
                    CONF_TRIPLE_TARGET,
                    description={"suggested_value": defaults.get(CONF_TRIPLE_TARGET)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["light", "switch"])
                ),
                vol.Optional(
                    CONF_HOLD_TARGET,
                    description={"suggested_value": defaults.get(CONF_HOLD_TARGET)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["light", "switch"])
                ),
                vol.Required(
                    CONF_HOLD_ACTION,
                    default=defaults.get(CONF_HOLD_ACTION, DEFAULT_HOLD_ACTION),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=HOLD_ACTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="hold_action",
                    )
                ),
                vol.Optional(
                    CONF_SCENES,
                    description={"suggested_value": defaults.get(CONF_SCENES)},
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="scene", multiple=True)
                ),
            }
        )

    @callback
    def _title(self, user_input: dict[str, Any]) -> str:
        node_id = user_input[CONF_NODE_ID]
        channel = user_input[CONF_CHANNEL]
        label = next(
            (o["label"] for o in self._wheel_options() if o["value"] == node_id),
            f"node {node_id}",
        )
        # Trim the "(node N)" suffix for a cleaner subentry title.
        label = label.rsplit(" (node", 1)[0]
        return generated_binding_title(label, channel)
