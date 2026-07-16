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


def _asset() -> str:
    return (
        Path(__file__).parents[1]
        / "custom_components"
        / "ikea_bilresa"
        / "frontend"
        / "ikea_bilresa_panel.js"
    ).read_text(encoding="utf-8")


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

    assert 'el("header")' in asset
    assert 'menu.type = "button"' in asset
    # the label itself lives in panel_strings.py; assert it is wired, not spelled
    assert 'menu.setAttribute("aria-label", this._t("menu"))' in asset
    assert (
        'new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true })'
        in asset
    )
    # HA's own ha-menu-button hides itself when the sidebar is already on screen;
    # rendering a second hamburger next to HA's own is what rc.9 did.
    assert "_showMenuButton()" in asset
    assert 'dockedSidebar === "always_hidden"' in asset
    # a 48px target, and a focus ring so it is reachable without a touchscreen
    assert "inline-size: 48px" in asset
    assert "block-size: 48px" in asset
    assert ".icon-button:focus-visible" in asset
    # decorative icons must stay out of the accessibility tree
    assert 'setAttribute("aria-hidden", "true")' in asset
    assert 'setAttribute("focusable", "false")' in asset


def test_panel_header_clears_the_notch() -> None:
    """A 48px target under a Dynamic Island is not a target.

    The companion app's WebView runs under the status bar, so the header must
    add the safe-area inset to its height rather than let the notch overlap it.
    A narrow desktop window reports no insets and will not catch a regression.
    """
    asset = (
        Path(__file__).parents[1]
        / "custom_components"
        / "ikea_bilresa"
        / "frontend"
        / "ikea_bilresa_panel.js"
    ).read_text(encoding="utf-8")

    assert "padding-block: env(safe-area-inset-top, 0px) 0;" in asset
    assert "env(safe-area-inset-left, 0px)" in asset
    assert "env(safe-area-inset-right, 0px)" in asset
    # content-box keeps the inset additive; border-box would eat the 56px bar
    assert "box-sizing: content-box;" in asset


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


def test_panel_asset_uses_home_assistant_design_tokens() -> None:
    """It must look like Home Assistant because it IS Home Assistant's system.

    HA's own frontend styling guidance forbids hard-coded pixels in spacing and
    raw hex in component styles. Every value here should come from a token, with
    a fallback so a theme predating the token rename still renders.
    """
    asset = _asset()

    for token in (
        "--ha-space-",
        "--ha-font-size-",
        "--ha-font-weight-",
        "--ha-line-height-",
        "--ha-card-border-color",
        "--ha-card-border-radius",
    ):
        assert token in asset, token
    # every alias carries a fallback
    assert "var(--ha-space-4, 16px)" in asset
    assert "var(--primary-text-color, #212121)" in asset


def test_panel_asset_keeps_accent_off_text() -> None:
    """Measured, not stylistic: HA's accents fail AA as text on a light card.

    --primary-color is 2.63:1 and --warning-color 1.96:1. Colour may carry state
    on a dot, a border or a stripe; the words must be --primary-text-color. A
    regression here is invisible on screen and fails the Phase 3 gate.
    """
    asset = _asset()

    # the status label sits on the ink colour, with the dot beside it
    assert ".status {" in asset
    assert '.dot[data-state="connected"]' in asset
    # the warning banner colours its stripe and icon, never its text
    assert "border-inline-start: 4px solid var(--warning-color" in asset
    assert "fill: var(--warning-color" in asset


def test_panel_asset_never_renders_user_strings_as_html() -> None:
    """Wheel names, areas and target labels are strings the user chose."""
    asset = _asset()

    assert "innerHTML" not in asset
    assert "node.textContent = text" in asset


def test_panel_asset_unsubscribes_when_the_view_closes() -> None:
    """A subscription that outlives the panel keeps pushing into a dead view."""
    asset = _asset()

    assert "disconnectedCallback()" in asset
    assert "this._unsub()" in asset


def test_panel_asset_grid_does_not_leave_a_phantom_column() -> None:
    """auto-fill keeps empty tracks alive; beside two wheels that reads broken."""
    asset = _asset()

    assert "repeat(auto-fit," in asset
    # the declaration, not the word: the comment above it explains why auto-fill
    # was rejected, and a bare substring check would fail on its own reasoning
    assert "repeat(auto-fill," not in asset
