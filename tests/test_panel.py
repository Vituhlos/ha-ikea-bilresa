"""Panel delivery and frontend-contract regression tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from custom_components.ikea_bilresa.panel import (
    ICONSET_FILENAME,
    PANEL_ICON,
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


def _iconset_asset() -> str:
    return (
        Path(__file__).parents[1]
        / "custom_components"
        / "ikea_bilresa"
        / "frontend"
        / ICONSET_FILENAME
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
    hass._add_extra_js_url = MagicMock()
    hass._remove_extra_js_url = MagicMock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel.frontend.add_extra_js_url",
        hass._add_extra_js_url,
    )
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel.frontend.remove_extra_js_url",
        hass._remove_extra_js_url,
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
    assert kwargs["sidebar_icon"] == PANEL_ICON == "bilresa:scroll-wheel"
    assert kwargs["require_admin"] is True
    hass._add_extra_js_url.assert_called_once_with(
        hass,
        f"{STATIC_URL_PATH}/{ICONSET_FILENAME}?v=9.9.9",
    )


async def test_missing_asset_does_not_break_setup(monkeypatch) -> None:
    """A panel that cannot be served degrades to no panel, never to a failure."""
    hass = _hass(asset_exists=False)
    registrar = _patch(monkeypatch, hass)

    assert await async_setup_panel(hass) is False

    registrar.assert_not_awaited()
    hass.http.async_register_static_paths.assert_not_awaited()
    hass._add_extra_js_url.assert_not_called()


async def test_registration_failure_does_not_break_setup(monkeypatch) -> None:
    """Setup must survive any frontend API change or breakage."""
    hass = _hass()
    _patch(monkeypatch, hass, register=AsyncMock(side_effect=RuntimeError("boom")))

    assert await async_setup_panel(hass) is False
    hass._remove_extra_js_url.assert_called_once_with(
        hass,
        f"{STATIC_URL_PATH}/{ICONSET_FILENAME}?v=9.9.9",
    )


async def test_static_path_is_registered_only_once(monkeypatch) -> None:
    """Static paths cannot be unregistered; a reload must not re-add the route."""
    hass = _hass()
    _patch(monkeypatch, hass)

    await async_setup_panel(hass)
    await async_setup_panel(hass)

    hass.http.async_register_static_paths.assert_awaited_once()
    hass._add_extra_js_url.assert_called_once()


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


async def test_remove_stops_advertising_the_icon_provider(monkeypatch) -> None:
    """Unload removes the extra module URL as well as the sidebar entry."""
    hass = _hass()
    _patch(monkeypatch, hass)
    remover = MagicMock()
    monkeypatch.setattr(
        "custom_components.ikea_bilresa.panel.frontend.async_remove_panel", remover
    )

    await async_setup_panel(hass)
    async_remove_panel(hass)

    remover.assert_called_once()
    hass._remove_extra_js_url.assert_called_once_with(
        hass,
        f"{STATIC_URL_PATH}/{ICONSET_FILENAME}?v=9.9.9",
    )


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


def test_bilresa_icon_provider_uses_the_selected_v2_geometry() -> None:
    """The sidebar provider must expose the approved two-path product glyph."""
    iconset = _iconset_asset()
    panel = _asset()

    assert "window.customIcons.bilresa = { getIcon, getIconList };" in iconset
    assert "window.customIconsets.bilresa = getIcon;" in iconset
    assert 'name === "scroll-wheel"' in iconset
    assert "secondaryPath:" in iconset
    assert "M13.05 1.35" in iconset
    # Same distinctive source geometry in the panel prevents identity drift.
    assert "M11.3 1.4" in iconset
    assert "M11.3 1.4" in panel
    assert ".secondary-path { opacity: 0.32; }" in panel


def test_panel_uses_distinct_material_rounded_gestures() -> None:
    """Press count belongs in the glyph; release is the end of a hold sequence."""
    asset = _asset()

    assert 'const MATERIAL_VIEWBOX = "0 -960 960 960";' in asset
    for gesture in (
        "rotate_left",
        "rotate_right",
        "short_press",
        "double_press",
        "triple_press",
        "hold",
    ):
        assert f"{gesture}: {{" in asset
    assert 'el("li", "channel-action gesture-sequence")' in asset
    assert 'el("span", "gesture-sequence-end")' in asset
    assert "gestureGlyph(action.gesture)" in asset


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
    # HA's warning token fails even the 3:1 non-text threshold on a light card.
    # The warning is carried by the alert shape and explicit copy, both in the
    # readable ink colour, rather than by orange words or a decorative stripe.
    assert ".banner svg" in asset
    assert "fill: currentColor;" in asset
    assert "border-inline-start:" not in asset


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


def test_panel_detail_keeps_the_measured_rail_and_pane_breakpoints() -> None:
    """The rail width and pane threshold came from measured layout evidence."""
    asset = _asset()

    assert "--_rail-width: 256px;" in asset
    assert "grid-template-columns: var(--_rail-width) minmax(0, 1fr);" in asset
    assert "@media (max-width: 619px)" in asset
    assert ".rail { display: none; }" in asset
    # This must be a container query on the detail pane, never a window query.
    assert ".detail-pane { min-inline-size: 0; container-type: inline-size; }" in asset
    assert "@container (max-width: 700px)" in asset
    assert "@media (max-width: 700px)" not in asset


def test_panel_detail_puts_desktop_back_navigation_inside_the_rail() -> None:
    """The desktop detail must not create a third column before the wheel title."""
    asset = _asset()
    rail = asset.split("  _rail() {", 1)[1].split("  _statusDot(", 1)[0]
    back_rule = asset.split("  .back-button {", 1)[1].split("  .back-button:hover", 1)[
        0
    ]

    assert 'el("button", "rail-back")' in rail
    assert "this._backToOverview()" in rail
    assert ".back-button {\n    display: none;" in asset
    assert "display: inline-flex;" not in back_rule
    assert "@media (max-width: 619px)" in asset
    assert ".back-button { display: inline-flex; }" in asset


def test_panel_channel_detail_is_card_list_not_a_table_grid() -> None:
    """The detail needs to scan as channel cards, not as a spreadsheet."""
    asset = _asset()
    channel = asset.split("  _channelDetail(wheel, channel) {", 1)[1].split(
        "  _channelsView(wheel) {", 1
    )[0]

    assert 'el("div", "channel-grid")' in asset
    assert 'el("ul", "channel-action-list")' in channel
    assert 'el("li", "channel-action")' in channel
    assert 'el("div", "gesture-grid")' not in channel
    assert 'el("div", "channel-detail-footer")' in channel


def test_overview_rows_do_not_promise_per_channel_navigation() -> None:
    """Only the wheel card opens detail, so channel rows must not draw chevrons."""
    asset = _asset()
    channel = asset.split("  _overviewChannel(channel) {", 1)[1].split(
        "  _wheel(wheel) {", 1
    )[0]
    wheel = asset.split("  _wheel(wheel) {", 1)[1].split(
        "  _activityLabel(wheel) {", 1
    )[0]

    assert "ICON.chevron" not in channel
    assert 'svg(ICON.chevron, "wheel-open")' in wheel


def test_panel_detail_tabs_follow_the_aria_keyboard_contract() -> None:
    """Tabs need roles, relationships, roving focus and arrow-key navigation."""
    asset = _asset()

    assert 'setAttribute("role", "tablist")' in asset
    assert 'setAttribute("role", "tab")' in asset
    assert 'setAttribute("role", "tabpanel")' in asset
    assert 'setAttribute("aria-selected", String(this._view === view))' in asset
    assert 'setAttribute("aria-controls", `panel-${wheel.key}-${view}`)' in asset
    assert 'setAttribute("aria-labelledby", `tab-${wheel.key}-${this._view}`)' in asset
    for key in ("ArrowRight", "ArrowLeft", "Home", "End"):
        assert f'event.key === "{key}"' in asset


def test_live_activity_is_opt_in_bounded_and_unsubscribed() -> None:
    """Only the Live test view may listen, and leaving it must stop immediately."""
    asset = _asset()

    assert 'const ACTIVITY_SUBSCRIBE = "ikea_bilresa/activity/subscribe";' in asset
    assert 'this._view !== "live"' in asset
    assert "{ type: ACTIVITY_SUBSCRIBE }" in asset
    assert ".slice(0, ACTIVITY_LIMIT)" in asset
    assert 'if (this._view === "live") this._stopActivity();' in asset
    assert "this._activityUnsub();" in asset
    assert "this._activityEpoch += 1;" in asset


def test_live_test_leads_with_result_and_hides_synthetic_controls() -> None:
    """Physical feedback is primary; target-changing panel tests are secondary."""
    asset = _asset()

    assert 'el("section", "detail-card live-output")' in asset
    assert 'el("div", "live-result", result)' in asset
    assert 'el("section", "detail-card live-channels")' in asset
    assert 'el("details", "detail-card test-panel")' in asset
    assert 'el("summary", null, this._t("test_controls_heading"))' in asset


def test_diagnostics_hides_internal_contract_under_technical_details() -> None:
    """The default diagnostic surface stays human-readable."""
    asset = _asset()
    diagnostics = asset.split("  _diagnosticsView(wheel) {", 1)[1].split(
        "  _detailPanel(wheel) {", 1
    )[0]

    assert 'el("section", "detail-card health-hero")' in diagnostics
    assert 'el("details", "detail-card technical-details")' in diagnostics
    assert 'this._t("diagnostic_technical_details")' in diagnostics
    assert 'this._t("diagnostic_contract")' in diagnostics


def test_live_activity_renders_structured_runtime_outcomes_without_call_service() -> (
    None
):
    """Binding results come from the backend; the browser never bypasses it."""
    asset = _asset()

    assert 'this._t("result_unavailable")' in asset
    assert "result.before" in asset
    assert "result.after" in asset
    assert "activity.dispatch_status" in asset
    assert "dispatch_accepted" in asset
    assert "dispatch_pending" in asset
    assert "binding.py" not in asset
    assert "callService" not in asset


def test_binding_editor_uses_revision_checked_websocket_mutations() -> None:
    """Panel writes stay inside the narrow binding API."""
    asset = _asset()

    assert 'const BINDING_SAVE = "ikea_bilresa/binding/save";' in asset
    assert 'const BINDING_DELETE = "ikea_bilresa/binding/delete";' in asset
    assert 'const BINDING_TEST = "ikea_bilresa/binding/test";' in asset
    assert "expected_revision: this._editorBinding?.revision" in asset
    assert "binding_id: this._editorBinding?.id" in asset
    assert 'this._t("binding_conflict")' in asset
    assert 'this._t("delete_binding_confirm")' in asset


def test_panel_detail_has_a_back_path_at_every_width() -> None:
    """The rail may disappear on mobile; the back control may not."""
    asset = _asset()

    assert 'back.id = "back-to-overview"' in asset
    assert 'back.type = "button"' in asset
    assert "back.appendChild(svg(ICON.back))" in asset
    assert "this._backToOverview()" in asset


def test_panel_preserves_focus_across_live_renders() -> None:
    """A new physical event must not silently throw keyboard focus away."""
    asset = _asset()

    assert "const focused = this.shadowRoot.activeElement?.id || null;" in asset
    assert "getElementById(focused)?.focus({ preventScroll: true })" in asset


def test_channel_detail_uses_the_versioned_read_model_actions() -> None:
    """Gesture rows come from panel_models, never from frontend guesses."""
    asset = _asset()

    assert "const summaries = channel.actions || [];" in asset
    assert "const action = summaries[index];" in asset
    assert "action.gesture_label" in asset
    assert "action.action_label" in asset
    assert "action.target_missing" in asset
