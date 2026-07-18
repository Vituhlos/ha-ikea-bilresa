"""Config flow for the IKEA BILRESA (smooth scroll) integration.

A single parent config entry holds the Matter Server connection. Control
bindings are added through **config subentries** — one per wheel channel or
dual-button endpoint — configured entirely in the UI.
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
import voluptuous as vol

from .binding_config import binding_errors, normalize_binding_data
from .const import (
    BINDING_PROFILE_CLIMATE,
    BINDING_PROFILE_COVER,
    BINDING_PROFILE_LIGHT,
    BINDING_PROFILE_MEDIA,
    BINDING_PROFILE_SCENES,
    BINDING_PROFILES,
    BUTTON_RESPONSE_FAST,
    BUTTON_RESPONSES,
    CLICK_ACTIONS,
    CLICK_NONE,
    CONF_ACCELERATION,
    CONF_BINDING_PROFILE,
    CONF_BUTTON_RESPONSE,
    CONF_CHANNEL,
    CONF_CLICK_ACTION,
    CONF_CLICK_TARGET,
    CONF_COPY_FROM,
    CONF_DOUBLE_TARGET,
    CONF_ENDPOINT,
    CONF_HOLD_ACTION,
    CONF_HOLD_TARGET,
    CONF_MAX_BRIGHTNESS,
    CONF_MIN_BRIGHTNESS,
    CONF_MODE,
    CONF_NODE_ID,
    CONF_RAMP_DIRECTION,
    CONF_SCENES,
    CONF_STEP,
    CONF_TARGET,
    CONF_TRANSITION,
    CONF_TRIPLE_TARGET,
    CONF_URL,
    DEFAULT_ACCELERATION,
    DEFAULT_BUTTON_RESPONSE,
    DEFAULT_CLICK_ACTION,
    DEFAULT_HOLD_ACTION,
    DEFAULT_MATTER_URL,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MODE,
    DEFAULT_RAMP_DIRECTION,
    DEFAULT_STEP,
    DEFAULT_TRANSITION,
    DOMAIN,
    HOLD_ACTIONS,
    MODE_BRIGHTNESS,
    MODE_COVER,
    MODE_TEMPERATURE,
    MODE_VOLUME,
    MODES,
    RAMP_DIRECTIONS,
    ROLE_BUTTON,
    SUBENTRY_BINDING,
    TARGET_DOMAINS,
)
from .device_link import resolve_matter_device
from .matter_ws import MatterWSIncompatible, validate_server_info
from .model import BilresaWheel
from .presentation import generated_binding_title, generated_button_binding_title


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
    """Add or reconfigure a wheel channel or button endpoint binding."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if hasattr(self, "_pending_defaults"):
            return await self._async_step_form("user", user_input)
        device_options = self._device_options()
        if not device_options:
            return self.async_abort(reason="no_devices")
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=self._setup_schema(device_options)
            )

        self._pending_node_id = str(user_input[CONF_NODE_ID])
        copied = self._copy_defaults(user_input.get(CONF_COPY_FROM))
        if copied is not None:
            self._pending_defaults = {
                **copied,
                CONF_NODE_ID: self._pending_node_id,
            }
            return await self._async_step_form("user", None)
        if self._is_dual_button(self._pending_node_id):
            self._pending_defaults = {
                CONF_NODE_ID: self._pending_node_id,
                CONF_BUTTON_RESPONSE: DEFAULT_BUTTON_RESPONSE,
            }
            return await self._async_step_form("user", None)
        return await self.async_step_profile()

    async def async_step_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Choose wheel defaults only after the source variant is known."""
        if user_input is None:
            return self.async_show_form(
                step_id="profile", data_schema=self._profile_schema()
            )
        self._pending_defaults = {
            CONF_NODE_ID: self._pending_node_id,
            **self._creation_defaults(user_input),
        }
        return await self._async_step_form("user", None)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        self._pending_defaults = dict(self._get_reconfigure_subentry().data)
        self._pending_node_id = str(self._pending_defaults[CONF_NODE_ID])
        return await self._async_step_form("reconfigure", user_input)

    async def _async_step_form(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        normalized: dict[str, Any] | None = None
        if user_input is not None:
            candidate = {CONF_NODE_ID: self._pending_node_id, **user_input}
            normalized, errors = self._normalize_and_validate(candidate)
            if normalized is not None and CONF_ENDPOINT in normalized:
                device = self._device(str(normalized[CONF_NODE_ID]))
                endpoint = (
                    device.endpoints.get(int(normalized[CONF_ENDPOINT]))
                    if device is not None
                    else None
                )
                if endpoint is None or endpoint.role != ROLE_BUTTON:
                    normalized = None
                    errors = {CONF_ENDPOINT: "invalid_value"}
        if normalized is not None and not errors:
            title = self._title(normalized)
            if step_id == "reconfigure":
                return self.async_update_and_abort(
                    self._get_entry(),
                    self._get_reconfigure_subentry(),
                    title=title,
                    data=normalized,
                )
            return self.async_create_entry(title=title, data=normalized)

        defaults = (
            {CONF_NODE_ID: self._pending_node_id, **user_input}
            if user_input is not None
            else self._pending_defaults
        )
        return self.async_show_form(
            step_id=step_id,
            data_schema=self._schema(defaults, include_device=step_id == "reconfigure"),
            errors=errors,
        )

    @staticmethod
    @callback
    def _validate_binding(user_input: dict[str, Any]) -> dict[str, str]:
        """Reject response policies whose configured actions cannot run."""
        normalized, errors = BindingSubentryFlowHandler._normalize_and_validate(
            user_input
        )
        return errors if normalized is None else binding_errors(normalized)

    @staticmethod
    @callback
    def _normalize_and_validate(
        user_input: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, dict[str, str]]:
        """Normalize one variant without allowing rotary fields onto a button."""
        try:
            normalized = normalize_binding_data(
                user_input,
                node_id=user_input.get(CONF_NODE_ID, "0"),
                channel=(
                    None
                    if CONF_ENDPOINT in user_input
                    else user_input.get(CONF_CHANNEL, "1")
                ),
                endpoint=user_input.get(CONF_ENDPOINT),
            )
        except vol.Invalid as err:
            path = str(err.path[-1]) if err.path else "base"
            return None, {path: "invalid_value"}
        errors = binding_errors(normalized)
        return (None, errors) if errors else (normalized, {})

    @callback
    def _setup_schema(
        self, device_options: list[selector.SelectOptionDict]
    ) -> vol.Schema:
        schema: dict[Any, Any] = {
            vol.Required(CONF_NODE_ID): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=device_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }
        copy_options = self._copy_options()
        if copy_options:
            schema[vol.Optional(CONF_COPY_FROM)] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=copy_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        return vol.Schema(schema)

    @staticmethod
    @callback
    def _profile_schema() -> vol.Schema:
        return vol.Schema(
            {
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
        )

    @callback
    def _copy_options(self) -> list[selector.SelectOptionDict]:
        return [
            selector.SelectOptionDict(value=subentry.subentry_id, label=subentry.title)
            for subentry in self._get_entry().subentries.values()
            if subentry.subentry_type == SUBENTRY_BINDING
        ]

    @callback
    def _copy_defaults(self, copy_from: str | None) -> dict[str, Any] | None:
        if not copy_from:
            return None
        subentry = self._get_entry().subentries.get(copy_from)
        if subentry is None or subentry.subentry_type != SUBENTRY_BINDING:
            return None
        return dict(subentry.data)

    @staticmethod
    @callback
    def _creation_defaults(user_input: dict[str, Any]) -> dict[str, Any]:
        profile = user_input[CONF_BINDING_PROFILE]
        defaults: dict[str, Any] = {CONF_BUTTON_RESPONSE: BUTTON_RESPONSE_FAST}
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
    def _device_options(self) -> list[selector.SelectOptionDict]:
        coordinator = self._get_entry().runtime_data
        options: list[selector.SelectOptionDict] = []
        for node_id, wheel in coordinator.wheels.items():
            label = wheel.name
            link = resolve_matter_device(
                self.hass,
                matter_url=coordinator.url,
                server_info=coordinator.matter_server_info,
                wheel=wheel,
            )
            if link.device:
                label = link.device.name_by_user or link.device.name or label
            options.append(
                selector.SelectOptionDict(
                    value=str(node_id), label=f"{label} (node {node_id})"
                )
            )
        return options

    @callback
    def _same_variant_device_options(
        self, node_id: str
    ) -> list[selector.SelectOptionDict]:
        is_dual_button = self._is_dual_button(node_id)
        return [
            option
            for option in self._device_options()
            if self._is_dual_button(str(option["value"])) == is_dual_button
        ]

    @callback
    def _device(self, node_id: str) -> BilresaWheel | None:
        try:
            return self._get_entry().runtime_data.wheels.get(int(node_id))
        except (TypeError, ValueError):
            return None

    @callback
    def _is_dual_button(self, node_id: str) -> bool:
        device = self._device(node_id)
        return bool(device is not None and device.is_dual_button)

    @callback
    def _button_options(self, node_id: str) -> list[selector.SelectOptionDict]:
        device = self._device(node_id)
        if device is None:
            return []
        endpoints = sorted(
            endpoint_id
            for endpoint_id, endpoint in device.endpoints.items()
            if endpoint.role == ROLE_BUTTON
        )
        return [
            selector.SelectOptionDict(value=str(endpoint_id), label=str(index))
            for index, endpoint_id in enumerate(endpoints, start=1)
        ]

    @callback
    def _schema(
        self, defaults: dict[str, Any], *, include_device: bool = False
    ) -> vol.Schema:
        node_id = str(defaults[CONF_NODE_ID])
        device_options = (
            self._same_variant_device_options(node_id) if include_device else None
        )
        if self._is_dual_button(node_id):
            return self._button_schema(node_id, defaults, device_options=device_options)
        return self._wheel_schema(defaults, device_options=device_options)

    @callback
    def _wheel_schema(
        self,
        defaults: dict[str, Any],
        *,
        device_options: list[selector.SelectOptionDict] | None = None,
    ) -> vol.Schema:
        schema: dict[Any, Any] = {}
        if device_options is not None:
            schema[vol.Required(CONF_NODE_ID, default=str(defaults[CONF_NODE_ID]))] = (
                selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=device_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            )
        schema.update(
            {
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
                **self._button_action_fields(defaults, wheel=True),
            }
        )
        return vol.Schema(schema)

    @callback
    def _button_schema(
        self,
        node_id: str,
        defaults: dict[str, Any],
        *,
        device_options: list[selector.SelectOptionDict] | None = None,
    ) -> vol.Schema:
        endpoint_options = self._button_options(node_id)
        default_endpoint = defaults.get(CONF_ENDPOINT)
        if default_endpoint is None and endpoint_options:
            default_endpoint = endpoint_options[0]["value"]
        schema: dict[Any, Any] = {}
        if device_options is not None:
            schema[vol.Required(CONF_NODE_ID, default=str(defaults[CONF_NODE_ID]))] = (
                selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=device_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            )
        schema.update(
            {
                vol.Required(
                    CONF_ENDPOINT, default=default_endpoint
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=endpoint_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                **self._button_action_fields(defaults, wheel=False),
            }
        )
        return vol.Schema(schema)

    @staticmethod
    @callback
    def _button_action_fields(
        defaults: dict[str, Any], *, wheel: bool
    ) -> dict[Any, Any]:
        fields: dict[Any, Any] = {
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
            vol.Required(
                CONF_BUTTON_RESPONSE,
                default=defaults.get(CONF_BUTTON_RESPONSE, DEFAULT_BUTTON_RESPONSE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=BUTTON_RESPONSES,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key=(
                        "button_response" if wheel else "dual_button_response"
                    ),
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
        }
        if wheel:
            fields[
                vol.Optional(
                    CONF_TRIPLE_TARGET,
                    description={"suggested_value": defaults.get(CONF_TRIPLE_TARGET)},
                )
            ] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["light", "switch"])
            )
            fields[
                vol.Optional(
                    CONF_SCENES,
                    description={"suggested_value": defaults.get(CONF_SCENES)},
                )
            ] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="scene", multiple=True)
            )
        else:
            fields[
                vol.Required(
                    CONF_RAMP_DIRECTION,
                    default=defaults.get(CONF_RAMP_DIRECTION, DEFAULT_RAMP_DIRECTION),
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=RAMP_DIRECTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="ramp_direction",
                )
            )
        return fields

    @callback
    def _title(self, user_input: dict[str, Any]) -> str:
        node_id = str(user_input[CONF_NODE_ID])
        label = next(
            (o["label"] for o in self._device_options() if o["value"] == node_id),
            f"node {node_id}",
        )
        label = label.rsplit(" (node", 1)[0]
        if CONF_ENDPOINT in user_input:
            endpoint = str(user_input[CONF_ENDPOINT])
            button_index = next(
                (
                    option["label"]
                    for option in self._button_options(node_id)
                    if option["value"] == endpoint
                ),
                endpoint,
            )
            return generated_button_binding_title(label, button_index)
        return generated_binding_title(label, str(user_input[CONF_CHANNEL]))
