"""Panel lifecycle: static asset registration and the sidebar entry.

**This is the `0.5.8` Phase 0 technical spike, not the panel.** Its only job is
to answer the question `PANEL_ROADMAP.md` says must be answered before any
production frontend work: can this integration register, serve, cache-bust and
unregister one local asset on the supported Home Assistant, through the same
HACS install path, without breaking setup when it fails?

The asset it serves is deliberately a stub. Nothing here should survive into the
real panel unchanged.

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
PANEL_ICON = "mdi:knob"

STATIC_URL_PATH = "/ikea_bilresa_frontend"
FRONTEND_DIR = "frontend"
PANEL_FILENAME = "ikea_bilresa_panel.js"

_STATIC_REGISTERED = f"{DOMAIN}_static_registered"


def _panel_asset_path(hass: HomeAssistant) -> Path:
    return Path(hass.config.path("custom_components", DOMAIN, FRONTEND_DIR)) / (
        PANEL_FILENAME
    )


async def async_setup_panel(hass: HomeAssistant) -> bool:
    """Serve the panel asset and add the sidebar entry.

    Returns whether the panel is now registered. Never raises: a panel that
    cannot be served must degrade to "no panel", never to a failed integration
    setup. Gesture processing and bindings do not depend on any of this.
    """
    try:
        asset = _panel_asset_path(hass)
        # Path.is_file() hits the filesystem; never do that on the event loop.
        if not await hass.async_add_executor_job(asset.is_file):
            _LOGGER.warning(
                "BILRESA panel asset is missing at %s; continuing without a "
                "panel. Wheels, bindings and events are unaffected",
                asset,
            )
            return False

        if not hass.data.get(_STATIC_REGISTERED):
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        STATIC_URL_PATH,
                        str(asset.parent),
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
