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


async def test_panel_ships_every_language_so_it_can_follow_the_user(
    monkeypatch,
) -> None:
    """A user's language lives in their browser; the panel picks from all of them.

    Until 0.6.0 only the instance language shipped, so a user who set English in
    their profile on a Czech instance saw a Czech panel inside an English UI.
    """
    hass = _hass()
    hass.config.language = "cs"
    registrar = _patch(monkeypatch, hass)

    assert await async_setup_panel(hass) is True

    config = registrar.await_args.kwargs["config"]
    assert set(config["labels_by_language"]) == {"en", "cs"}
    assert (
        config["labels_by_language"]["en"]["add_binding"]
        != (config["labels_by_language"]["cs"]["add_binding"])
    )
    # Kept for a panel script cached from before this key existed.
    assert config["language"] == "cs"
    assert config["labels"] == config["labels_by_language"]["cs"]


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
    assert 'el("span", "gesture-sequence-end")' in asset
    assert "gestureGlyph(row.gesture)" in asset


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

    # Only the part of the notch that the theme's inset does not already
    # clear is added, or the bar sits a notch too low.
    assert (
        "padding-block: max(0px, calc(env(safe-area-inset-top, 0px)"
        " - var(--_frame-start))) 0;"
    ) in asset
    assert "max(env(safe-area-inset-top, 0px), var(--_frame-start))" in asset
    assert "env(safe-area-inset-left, 0px)" in asset
    assert "env(safe-area-inset-right, 0px)" in asset
    # content-box keeps the inset additive; border-box would eat the 56px bar
    assert "box-sizing: content-box;" in asset
    # The strip above the bar is the bar's colour, never the page's, so a
    # padded theme does not show a band of page colour over the header.
    strip = asset.split("header::before {", 1)[1].split("}", 1)[0]
    assert "background: inherit;" in strip
    assert "_frame-bg" not in asset


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


def test_panel_detail_collapses_on_its_own_width_not_the_window() -> None:
    """Two columns collapse on the width of the card or page they sit in."""
    asset = _asset()

    # Container queries, never a window query: a channel card is narrower than
    # the window, and the page is narrower than the window beside the sidebar.
    assert "@container (max-width: 700px)" in asset
    assert "@media (max-width: 700px)" not in asset
    assert ".control-card {" in asset
    card = asset.split("  .control-card {", 1)[1].split("  }", 1)[0]
    assert "container-type: inline-size;" in card
    # The live test and diagnostics measure the page itself.
    assert (
        ".detail-inner.subpage { margin-inline: auto; container-type: inline-size; }"
        in asset
    )
    # The detail needs the overview's ceiling too: without it a wide window
    # drags a fact's label and its value to opposite ends of the screen.
    assert "--_detail-max: 880px;" in asset
    assert ".detail-inner { inline-size: min(100%, var(--_detail-max)); }" in asset


def test_panel_detail_is_a_home_assistant_subpage() -> None:
    """A back arrow and the device name in the bar; no second sidebar.

    HACS, the KNX panel, Alarmo and Home Assistant's own device pages are built
    this way. The 256 px rail beside Home Assistant's sidebar was the main
    reason the panel did not read as part of Home Assistant (2026-10-18).
    """
    asset = _asset()
    header = asset.split("  _header() {", 1)[1].split("  _summaryItem(", 1)[0]

    assert 'back.id = "header-back"' in header
    assert "back.appendChild(svg(ICON.back))" in header
    assert "this._backToOverview()" in header
    assert 'el("h1", null, device.name)' in header
    for gone in (
        "_rail()",
        "--_rail-width",
        ".rail-wheel",
        "_mobileBack()",
        "_detailTop(",
    ):
        assert gone not in asset


def test_the_tab_strip_does_not_scroll_itself() -> None:
    """The owner found a scrollbar on a row of three short tabs.

    `overflow-x: auto` is a real safety net — a long translation must not push
    the page sideways — but it costs more than it looks. Per CSS Overflow, when
    one axis is not `visible` the other's `visible` computes to `auto`, so the
    tab strip scrolls in BOTH axes whether or not we asked. Anything overhanging
    it vertically then becomes a scrollbar or gets clipped:

    * an underline at `inset-block-end: -1px` (ported from a prototype whose tab
      strip had no `overflow-x`) made 1px of scrollable height, so a vertical
      scrollbar appeared beside three short tabs;
    * a tab fills the strip's height exactly, so an outset focus ring is clipped
      top and bottom.

    Hence: the rule is painted inside as a shadow, the underline sits at 0, and
    the tabs' ring is inset. Measured after the fix: 0px overflow on both axes.
    """
    asset = _asset()
    styles = asset.split("const STYLES = `", 1)[1].split("`;", 1)[0]
    tabs_rule = styles.split("  .tabs {", 1)[1].split("  }", 1)[0]

    # the divider is painted inside, never hung off the border edge
    assert "box-shadow: inset 0 -1px 0 var(--_divider);" in tabs_rule
    assert "border-block-end" not in tabs_rule
    # nothing may overhang the scroll container
    assert "inset-block-end: -1px;" not in styles
    assert (
        '.tab[aria-selected="true"]::after {\n'
        '    content: "";\n'
        "    position: absolute;\n"
        "    inset-inline: 0;\n"
        "    inset-block-end: 0;" in styles
    )
    # a ring on a full-height tab must be inset or the container clips it
    assert ".tab:focus-visible { outline-offset: -2px; }" in styles


def test_glanceable_times_are_relative_and_keep_the_exact_stamp() -> None:
    """ "2 hours ago" is read; "16. 7. 2026 9:54" has to be subtracted from now.

    Diagnostics is the exception and keeps the absolute stamp: it is a surface
    for reading facts, not for glancing.
    """
    asset = _asset()
    activity = asset.split("  _activityLabel(wheel) {", 1)[1].split(
        "  _formatDate(value) {", 1
    )[0]
    diagnostics = asset.split("  _diagnosticsView(wheel) {", 1)[1].split(
        "  _detailPanel(wheel) {", 1
    )[0]

    assert "Intl.RelativeTimeFormat" in asset
    assert "this._formatRelative(when)" in activity
    assert "this._formatDate(" not in activity
    # the precise time stays one hover away rather than being thrown away
    assert "sub.title = this._formatDate(wheel.last_activity)" in asset
    assert "copy.title = this._formatDate(wheel.last_activity)" in asset
    assert "this._formatDate(wheel.last_activity)" in diagnostics


def test_every_channel_is_its_own_card_on_one_page() -> None:
    """Nothing to navigate, so no spine and no paragraph explaining one."""
    asset = _asset()
    stacked = asset.split("  _stackedControls(wheel) {", 1)[1].split(
        "  _channelsView(wheel) {", 1
    )[0]
    view = asset.split("  _channelsView(wheel) {", 1)[1].split(
        "  _gestureLabel(activity) {", 1
    )[0]
    channel = asset.split("  _channelDetail(wheel, channel) {", 1)[1].split(
        "  _isNoAction(action) {", 1
    )[0]

    assert 'el("section", "control-card")' in stacked
    assert "for (const control of this._controlsFor(wheel))" in stacked
    assert "this._stackedControls(wheel)" in view
    assert 'el("ul", "channel-action-list")' in channel
    assert 'el("li", "channel-action")' in channel
    for gone in (
        "channel-spine",
        "channel-workbench",
        "channel-position",
        "_openChannelAt",
    ):
        assert gone not in asset
    # A switched-off channel says so on its card.
    assert 'card.dataset.state = "off"' in stacked
    # ...in its header, on the summary's line, so the card keeps its height.
    assert '"channel_off_note"' in channel
    # Its switch sits on its card; there is no separate "Active channels" card.
    assert "tools.appendChild(this._channelSwitch(wheel, channel))" in channel
    assert "_activeChannelsSection" not in asset


def test_an_unconfigured_channel_stays_lighter_than_a_configured_one() -> None:
    """PANEL_DESIGN.md: an empty channel must not carry a full channel's weight.

    The shipped grid stretched every channel to the tallest sibling, so two
    empty channels rendered as two large blank rectangles beside one real one.
    """
    asset = _asset()

    # One compact head, like a configured channel's, with no ledger under it:
    # the 0.6.1-rc.1 heading, paragraph and primary button were a poster.
    assert "channel-empty" not in asset
    # ...until its editor opens, when the form's line needs the usual gap.
    empty_head = (
        '.channel-detail[data-state="empty"]:not([data-editing="true"])'
        " .channel-detail-head {\n    margin-block-end: 0;"
    )
    assert empty_head in asset
    assert "min-block-size: 100%;" not in asset

    # Dimmed, never italic: HA does not italicise state, and an italic label is
    # a reliable generated-UI tell.
    assert "font-style: italic" not in asset
    # --disabled-text-color is 2.8:1 on a light card and fails the AA gate this
    # project measured. "Empty" is said with --_ink-dim (secondary text, 4.81:1).
    styles = asset.split("const STYLES = `", 1)[1].split("`;", 1)[0]
    assert "var(--disabled-text-color" not in styles
    assert (
        '.channel[data-state="empty"] .channel-primary { color: var(--_ink-dim); }'
        in styles
    )


def test_overview_rows_do_not_promise_per_channel_navigation() -> None:
    """Only the wheel card opens detail, so channel rows must not draw chevrons."""
    asset = _asset()
    channel = asset.split("  _overviewControl(device, control) {", 1)[1].split(
        "  _wheel(wheel) {", 1
    )[0]
    wheel = asset.split("  _wheel(wheel) {", 1)[1].split(
        "  _activityLabel(wheel) {", 1
    )[0]

    assert "ICON.chevron" not in channel
    assert 'svg(ICON.chevron, "wheel-open")' in wheel


def test_dual_button_reuses_the_panel_shell_with_two_button_controls() -> None:
    """B3 is a variant of the existing panel, not a second application."""
    asset = _asset()
    buttons = asset.split("  _buttonsView(wheel) {", 1)[1].split(
        "  _gestureLabel(activity) {", 1
    )[0]
    views = asset.split("  _viewsFor(device) {", 1)[1].split(
        "  _controlsFor(device) {", 1
    )[0]
    form = asset.split("  _bindingForm(wheel, control) {", 1)[1].split(
        "  _channelDetail(wheel, channel) {", 1
    )[0]

    assert "this._stackedControls(wheel)" in buttons
    assert "_openButtonAt" not in asset
    assert '"button-list"' not in asset
    assert '"button-surface"' not in asset
    assert '["buttons", "live", "diagnostics"]' in views
    # Scene cycling and triple press exist only on the wheel.
    assert '? ["toggle", "on", "off", "none"]' in form
    assert ': ["toggle", "on", "off", "scenes", "none"]' in form
    assert '? ["double_press"]' in form
    assert ': ["double_press", "triple_press"]' in form
    assert '"ramp_direction"' in form


def test_binding_editor_offers_three_truthful_response_points() -> None:
    asset = _asset()
    form = asset.split("  _bindingForm(wheel, control) {", 1)[1].split(
        "  _channelDetail(wheel, channel) {", 1
    )[0]

    assert '["multi_press", "fast", "instant"]' in form


def _binding_form_source() -> str:
    return (
        _asset()
        .split("  _bindingForm(wheel, control) {", 1)[1]
        .split("  _channelDetail(wheel, channel) {", 1)[0]
    )


def test_every_press_gesture_is_edited_beside_the_others() -> None:
    """No catch-all "advanced" group: every field sits with what it belongs to.

    The gesture ledger presents equal gestures, and a disclosure at the foot
    of the form read as the heading of the buttons below it.
    """
    form = _binding_form_source()

    assert 'el("details", "advanced")' not in form
    for field in (
        '"click_action"',
        '"click_target"',
        '"double_press"',
        '"triple_press"',
        '"hold_action"',
        '"hold_target"',
    ):
        assert field in form, field


def test_the_editor_follows_the_gesture_ledger_order() -> None:
    form = _binding_form_source()
    order = [
        '"mode"',
        '"target"',
        '"click_action"',
        '"double_press"',
        '"triple_press"',
        '"hold_action"',
    ]
    positions = [form.index(field) for field in order]

    assert positions == sorted(positions)


def test_set_once_options_sit_in_the_section_they_belong_to() -> None:
    """Rotation limits behind Rotation's own toggle; the response by short press.

    The response decides when a short press runs and which gestures exist, so
    it sits with the short press rather than in a disclosure.
    """
    form = _binding_form_source()
    rotation = form.split('this._t("rotation_more")', 1)[1].split(
        'this._formSection(sections, "short_press")', 1
    )[0]
    short_press = form.split('this._formSection(sections, "short_press")', 1)[1]

    # Adjacent in source order, so the two-column grid keeps the pair together.
    minimum = rotation.index('"min_brightness"')
    maximum = rotation.index('"max_brightness"')
    acceleration = rotation.index('"acceleration"')
    assert minimum < maximum < acceleration
    assert '"step_curve"' in rotation
    assert '"button_response"' in short_press


def test_every_gesture_is_its_own_section() -> None:
    """Rotation and each press gesture are peers, named once, as in the ledger.

    A scene list and its "add" control must read as part of the short press,
    not as siblings of the gesture after it.
    """
    form = _binding_form_source()

    assert 'this._formSection(sections, "rotation")' in form
    assert 'this._formSection(sections, "short_press")' in form
    assert "this._formSection(sections, press)" in form
    assert 'this._formSection(sections, "hold")' in form
    assert form.count('this._t("gesture_action")') == 3


def test_an_empty_wheel_short_press_target_says_what_it_falls_back_to() -> None:
    """The ledger reports the rotation target, so the field must agree.

    A wheel binding with no explicit short-press target uses the rotation
    target at runtime. Labelling the empty option "no target configured"
    contradicted the gesture row rendered directly above it.
    """
    form = _binding_form_source()
    declaration = form.split('"click_target"', 1)[1].split("      ),", 1)[0]

    assert 'this._t("target_same_as_rotation")' in declaration
    # A dual button has no rotation to fall back to, so it keeps the plain
    # placeholder and its own required-target behaviour.
    assert "isButton ? undefined :" in declaration


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
    assert 'el("div", "live-result", this._liveResult(latest))' in asset
    assert 'el("section", "detail-card live-channels")' in asset
    assert "this._liveControls(wheel)" in asset
    assert 'el("details", "detail-card test-panel")' in asset
    assert 'el("summary", null, this._t("test_controls_heading"))' in asset


def test_live_test_turns_an_unconfigured_gesture_into_a_useful_empty_state() -> None:
    """Recognized hardware is success even when no target has been configured."""
    asset = _asset()

    assert '"result_gesture_press"' in asset
    assert '"result_not_configured_button_detail"' in asset
    assert 'this._t(isButton ? "live_setup_button" : "live_setup_channel"' in asset
    assert "this._configureFromLive(wheel, latest)" in asset
    assert 'not_configured: [\n        "unknown",' in asset


def test_recent_live_events_form_a_keyboard_scroll_region() -> None:
    """A burst stays bounded on screen and remains reachable without a pointer."""
    asset = _asset()

    assert ".recent ol {" in asset
    assert "max-block-size: 320px;" in asset
    assert "overflow-y: auto;" in asset
    assert "overscroll-behavior: contain;" in asset
    assert "scrollbar-gutter: stable;" in asset
    assert "list.tabIndex = 0;" in asset
    assert 'list.setAttribute("aria-labelledby", recentHeading.id);' in asset
    assert ".recent ol:focus-visible {" in asset


def test_the_detent_strip_is_scaled_to_observed_hardware() -> None:
    """The strip is a measured scale, not decoration.

    Eighteen is the highest rotary count DEVICE_REFERENCE.md has ever recorded,
    so the strip shows one batch against what this firmware can actually emit.
    A round number chosen because it looked nice would be a lie about hardware.
    """
    asset = _asset()
    strip = asset.split("  _detentStrip(notches) {", 1)[1].split(
        "  _liveView(wheel) {", 1
    )[0]

    assert "const total = 18;" in strip
    assert "Math.min(Math.abs(Number(notches) || 0), total)" in strip
    assert 'el("span", "detent")' in strip
    # only a rotation has notches to show
    assert 'if (latest.gesture === "rotate") {' in asset


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
    # Fact groups are sections on the page, not cards inside the page. A
    # bordered box per group, each with its own boxed heading, is the
    # card-in-card tell that made the panel read as a wireframe.
    assert 'el("section", "diagnostic-section")' in diagnostics
    assert diagnostics.count('el("section", "detail-card")') == 0


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
    assert '"delete_binding_confirm"' in asset
    assert '"delete_button_binding_confirm"' in asset


def test_panel_detail_has_a_back_path_at_every_width() -> None:
    """The way back lives in the bar, so it exists on a phone and a desktop alike."""
    asset = _asset()
    header = asset.split("  _header() {", 1)[1].split("  _summaryItem(", 1)[0]

    assert 'back.type = "button"' in header
    assert 'back.setAttribute("aria-label", this._t("back"))' in header
    # Nothing hides the bar's back arrow at any width.
    assert "#header-back { display: none" not in asset


def test_panel_preserves_focus_across_live_renders() -> None:
    """A new physical event must not silently throw keyboard focus away."""
    asset = _asset()

    assert "const focused = this.shadowRoot.activeElement?.id || null;" in asset
    assert "getElementById(focused)?.focus({ preventScroll: true })" in asset


def test_channel_detail_uses_the_versioned_read_model_actions() -> None:
    """Gesture rows come from panel_models, never from frontend guesses."""
    asset = _asset()

    assert "this._ledgerRows(channel.actions || [])" in asset
    assert "const action = summaries[index];" in asset
    assert "action.gesture_label" in asset
    assert "action.action_label" in asset
    assert "this._targetText(action)" in asset
    assert 'targetState(action) === "missing"' in asset


def test_the_community_tool_is_linked_in_one_place_without_data() -> None:
    """BILRESA-5: a plain external link in the info row, nothing embedded.

    The address is one constant used once, so it cannot be assembled from
    anything about the installation; the link leaves in a new tab without
    handing the panel's window to the other site.
    """
    asset = _asset()

    assert 'const COMMUNITY_TOOL_URL = "https://bilresa.marcel1.com/";' in asset
    assert asset.count("COMMUNITY_TOOL_URL") == 2  # declaration and one use
    assert "link.href = COMMUNITY_TOOL_URL;" in asset
    assert 'link.target = "_blank";' in asset
    assert 'link.rel = "noopener noreferrer";' in asset
    # No query string or fragment is ever appended.
    assert "COMMUNITY_TOOL_URL +" not in asset
    assert "${COMMUNITY_TOOL_URL" not in asset
    # Nothing is embedded or fetched from the other site.
    assert "<iframe" not in asset
    assert 'createElement("iframe")' not in asset
    assert 'el("iframe"' not in asset
    # It sits in the info row above the tabs, which both device pages share
    # (the wheel's and the dual button's), and no longer at the foot of either.
    channels = asset.split("_channelsView(wheel) {", 1)[1].split("_buttonsView", 1)[0]
    buttons = asset.split("_buttonsView(wheel) {", 1)[1].split("_gestureLabel", 1)[0]
    assert "_communityLink" not in channels
    assert "_communityLink" not in buttons
    detail = asset.split("_subpageDetail(wheel) {", 1)[1].split("_detail(wheel) {", 1)[
        0
    ]
    assert "meta.appendChild(this._communityLink());" in detail
    assert detail.index("_communityLink") < detail.index("this._tabs(wheel)")
    assert asset.count("this._communityLink()") == 1


def test_the_community_card_is_outlined_and_has_hover_and_focus() -> None:
    """It must not read as one more control: outlined, slim in a narrow pane,
    and visible to the keyboard and the pointer."""
    asset = _asset()
    card = asset.split(".resource-link {", 1)[1].split("}", 1)[0]

    assert "background: transparent;" in card
    # At the right end of the info row, and a slim full-width row under the
    # info text in a narrow pane, where the second part of the note is not drawn
    # but stays for a screen reader.
    assert "flex: 0 1 auto;" in card
    narrow = asset.split("@container (max-width: 560px) {", 1)[1].split("\n  }\n", 1)[0]
    assert ".subpage-meta { flex-wrap: wrap; }" in narrow
    assert ".resource-link { flex: 1 1 100%; max-inline-size: none; }" in narrow
    assert ".resource-new {" in narrow
    assert "clip-path: inset(50%);" in narrow
    assert "display: none" not in narrow
    # A tinted round icon, with the words in the link rather than hidden.
    assert ".resource-badge {" in asset
    assert (
        "border-radius: 50%;" in asset.split(".resource-badge {", 1)[1].split("}", 1)[0]
    )
    assert "visually-hidden" not in asset
    assert 'aria-hidden", "true"' in asset
    # Pointer, press and keyboard states, and no animation when it is not wanted.
    assert ".resource-link:hover {" in asset
    assert ".resource-link:active {" in asset
    assert ".resource-link:focus-visible {" in asset
    assert (
        "prefers-reduced-motion: reduce"
        in asset.split(".resource-link:focus-visible {", 1)[1]
    )


def test_the_community_tool_texts_exist_in_both_languages() -> None:
    from custom_components.ikea_bilresa.panel_strings import STRINGS

    for language in ("en", "cs"):
        strings = STRINGS[language]
        for key in (
            "community_tool_link",
            "community_tool_note",
            "community_tool_new_window",
        ):
            assert strings[key].strip(), (language, key)
    # It must say whose tool it is, so it is not read as part of the integration.
    assert "Liquidmasl" in STRINGS["en"]["community_tool_note"]
    assert "Liquidmasl" in STRINGS["cs"]["community_tool_note"]
