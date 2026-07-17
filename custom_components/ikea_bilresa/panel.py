"""Panel lifecycle: frontend assets, custom icon provider and sidebar entry.

Two Home Assistant constraints shaped this module, and both are easy to trip on:

- **Static paths cannot be unregistered.** `async_register_static_paths` adds
  aiohttp routes for the life of the process; there is no removal API. Reloading
  the config entry must therefore not re-register the path, or the second
  attempt raises on the duplicate route. The panel itself *can* be removed and
  re-added, so only the static path is guarded.
- **`async_register_built_in_panel` and `async_remove_panel` are `@callback`,
  not coroutines**, despite the `async_` prefix. `panel_custom.async_register_panel`
  genuinely is a coroutine. Do not await the first two.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .panel_strings import panel_strings, resolve_language

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = "ikea-bilresa"
PANEL_WEBCOMPONENT = "ikea-bilresa-panel"
PANEL_TITLE = "IKEA BILRESA"
PANEL_ICON = "bilresa:scroll-wheel"

STATIC_URL_PATH = "/ikea_bilresa_frontend"
FRONTEND_DIR = "frontend"
PANEL_FILENAME = "ikea_bilresa_panel.js"
ICONSET_FILENAME = "bilresa_icons.js"

_STATIC_REGISTERED = f"{DOMAIN}_static_registered"
_ICONSET_URL = f"{DOMAIN}_iconset_url"


def _frontend_asset_path(hass: HomeAssistant, filename: str) -> Path:
    return Path(hass.config.path("custom_components", DOMAIN, FRONTEND_DIR, filename))


def _remove_iconset_url(hass: HomeAssistant) -> None:
    """Stop advertising the global icon module without breaking unload."""
    if not (iconset_url := hass.data.pop(_ICONSET_URL, None)):
        return
    try:
        frontend.remove_extra_js_url(hass, iconset_url)
    except Exception:  # noqa: BLE001 - frontend cleanup must never break unload
        _LOGGER.exception("Failed to remove the BILRESA icon provider URL")


async def async_setup_panel(hass: HomeAssistant) -> bool:
    """Serve the panel asset and add the sidebar entry.

    Returns whether the panel is now registered. Never raises: a panel that
    cannot be served must degrade to "no panel", never to a failed integration
    setup. Gesture processing and bindings do not depend on any of this.
    """
    try:
        panel_asset = _frontend_asset_path(hass, PANEL_FILENAME)
        iconset_asset = _frontend_asset_path(hass, ICONSET_FILENAME)
        # Path.is_file() hits the filesystem; never do that on the event loop.
        assets_exist = await hass.async_add_executor_job(
            lambda: panel_asset.is_file() and iconset_asset.is_file()
        )
        if not assets_exist:
            _LOGGER.warning(
                "BILRESA frontend assets are incomplete at %s; continuing "
                "without a panel. Wheels, bindings and events are unaffected",
                panel_asset.parent,
            )
            return False

        if not hass.data.get(_STATIC_REGISTERED):
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        STATIC_URL_PATH,
                        str(panel_asset.parent),
                        # Safe to cache hard: the module URL carries the
                        # integration version, so an upgrade changes the URL.
                        cache_headers=True,
                    )
                ]
            )
            hass.data[_STATIC_REGISTERED] = True

        integration = await async_get_integration(hass, DOMAIN)
        language = resolve_language(getattr(hass.config, "language", None))
        # Cache-busting. Without this an upgrade leaves browsers on the old
        # bundle until a hard refresh, which looks exactly like a broken panel.
        module_url = f"{STATIC_URL_PATH}/{PANEL_FILENAME}?v={integration.version}"
        iconset_url = f"{STATIC_URL_PATH}/{ICONSET_FILENAME}?v={integration.version}"

        # The sidebar is rendered before the panel module is opened. Register a
        # small global module first so bilresa:scroll-wheel can resolve there.
        if hass.data.get(_ICONSET_URL) != iconset_url:
            _remove_iconset_url(hass)
            frontend.add_extra_js_url(hass, iconset_url)
            hass.data[_ICONSET_URL] = iconset_url

        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_WEBCOMPONENT,
            module_url=module_url,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            # Admin-only for now. PANEL_ROADMAP.md: if per-device permission
            # filtering cannot be done safely in the first package, restrict to
            # administrators and record the decision rather than over-serving.
            require_admin=True,
            # The panel's own vocabulary travels in its config: Home Assistant has
            # no translation category a custom panel could use, and the frontend
            # would not fetch one. See panel_strings for why both languages live
            # in a single Python file rather than two JSON files.
            #
            # Resolved once at registration, so a language change needs a reload.
            # Acceptable: HA reloads the integration on a core config change.
            config={
                "version": str(integration.version),
                "language": language,
                "labels": panel_strings(language),
            },
        )
    except Exception:  # noqa: BLE001 - a panel must never break setup
        _remove_iconset_url(hass)
        _LOGGER.exception("Failed to register the BILRESA panel; continuing without it")
        return False

    _LOGGER.debug("Registered the BILRESA panel at /%s", PANEL_URL_PATH)
    return True


def async_remove_panel(hass: HomeAssistant) -> None:
    """Remove the sidebar entry on unload.

    The static path stays registered; Home Assistant offers no way to remove it,
    and leaving it costs one route. `warn_if_unknown=False` because unload runs
    even when registration was skipped or failed.
    """
    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
    _remove_iconset_url(hass)
