"""Phase 0 spike: panel registration must be safe, idempotent and removable."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from custom_components.ikea_bilresa.panel import (
    PANEL_URL_PATH,
    STATIC_URL_PATH,
    async_remove_panel,
    async_setup_panel,
)


def _hass(*, asset_exists: bool = True) -> SimpleNamespace:
    async def _add_executor_job(func, *args):
        return func(*args)

    return SimpleNamespace(
        data={},
        config=SimpleNamespace(path=lambda *parts: "/config/" + "/".join(parts)),
        http=SimpleNamespace(async_register_static_paths=AsyncMock()),
        async_add_executor_job=_add_executor_job,
        _asset_exists=asset_exists,
    )


def _patch(monkeypatch, hass, *, register=None) -> MagicMock:
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel.Path.is_file",
        lambda _self: hass._asset_exists,
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel.async_get_integration",
        AsyncMock(return_value=SimpleNamespace(version="9.9.9")),
    )
    registrar = register or AsyncMock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel.panel_custom.async_register_panel",
        registrar,
    )
    return registrar


async def test_registers_panel_with_a_cache_busted_module_url(monkeypatch) -> None:
    """An upgrade must change the URL, or browsers keep the old bundle."""
    hass = _hass()
    registrar = _patch(monkeypatch, hass)

    assert await async_setup_panel(hass) is True

    kwargs = registrar.await_args.kwargs
    assert kwargs["module_url"] == f"{STATIC_URL_PATH}/ikea_bilresa_panel.js?v=9.9.9"
    assert kwargs["frontend_url_path"] == PANEL_URL_PATH
    assert kwargs["require_admin"] is True


async def test_missing_asset_does_not_break_setup(monkeypatch) -> None:
    """A panel that cannot be served degrades to no panel, never to a failure."""
    hass = _hass(asset_exists=False)
    registrar = _patch(monkeypatch, hass)

    assert await async_setup_panel(hass) is False

    registrar.assert_not_awaited()
    hass.http.async_register_static_paths.assert_not_awaited()


async def test_registration_failure_does_not_break_setup(monkeypatch) -> None:
    """Setup must survive any frontend API change or breakage."""
    hass = _hass()
    _patch(monkeypatch, hass, register=AsyncMock(side_effect=RuntimeError("boom")))

    assert await async_setup_panel(hass) is False


async def test_static_path_is_registered_only_once(monkeypatch) -> None:
    """Static paths cannot be unregistered; a reload must not re-add the route."""
    hass = _hass()
    _patch(monkeypatch, hass)

    await async_setup_panel(hass)
    await async_setup_panel(hass)

    hass.http.async_register_static_paths.assert_awaited_once()


async def test_reload_re_registers_the_panel_itself(monkeypatch) -> None:
    """The panel, unlike the static path, must come back after a reload."""
    hass = _hass()
    registrar = _patch(monkeypatch, hass)

    await async_setup_panel(hass)
    await async_setup_panel(hass)

    assert registrar.await_count == 2


def test_remove_is_quiet_when_the_panel_never_registered(monkeypatch) -> None:
    """Unload runs even when registration was skipped or failed."""
    remover = MagicMock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel.frontend.async_remove_panel", remover
    )

    async_remove_panel(_hass())

    remover.assert_called_once()
    assert remover.call_args.kwargs["warn_if_unknown"] is False


def test_panel_asset_has_an_accessible_mobile_exit() -> None:
    """The custom viewport must never trap companion-app users."""
    asset = (
        Path(__file__).parents[1]
        / "custom_components"
        / "ikea_bilresa"
        / "frontend"
        / "ikea_bilresa_panel.js"
    ).read_text(encoding="utf-8")

    assert 'document.createElement("header")' in asset
    assert 'menu.type = "button"' in asset
    assert 'aria-label", "Open Home Assistant sidebar"' in asset
    assert 'aria-hidden="true" focusable="false"' in asset
    assert (
        'new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true })'
        in asset
    )
    assert "inline-size: 48px" in asset
    assert "block-size: 48px" in asset
    assert ".bilresa-panel-menu:focus-visible" in asset


def test_panel_asset_registration_is_browser_idempotent() -> None:
    """A cache-busted upgrade must not redefine an element in an open tab."""
    asset = (
        Path(__file__).parents[1]
        / "custom_components"
        / "ikea_bilresa"
        / "frontend"
        / "ikea_bilresa_panel.js"
    ).read_text(encoding="utf-8")

    guard = 'if (!customElements.get("ikea-bilresa-panel")) {'
    registration = 'customElements.define("ikea-bilresa-panel", IkeaBilresaPanel);'
    assert guard in asset
    assert asset.index(guard) < asset.index(registration)
