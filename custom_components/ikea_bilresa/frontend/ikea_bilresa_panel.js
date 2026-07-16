/**
 * BILRESA panel — Phase 3 frontend shell and overview grid.
 *
 * Layout is the two-layer model in PANEL_DESIGN.md: a grid of wheel cards as the
 * landing layer. The wheel detail and its 256px rail are Phase 4 and are not
 * here; a card opens a placeholder that says so.
 *
 * ## Why this looks like Home Assistant and not like a design
 *
 * It is built from Home Assistant's own design tokens, read from the frontend
 * source rather than guessed:
 *
 *   --ha-space-1..20      4px..80px in 4px steps. HA's own styling guidance
 *                         forbids hard-coded pixels in spacing; every gap,
 *                         padding and inset below is a token.
 *   --ha-font-size-*      xs 10 / s 12 / m 14 / l 16 / xl 20 / 2xl 24 ...
 *   --ha-font-weight-*    light 300 / normal 400 / medium 500 / bold 700
 *   --ha-line-height-*    condensed 1.2 / normal 1.6 / expanded 2
 *   --ha-card-*           border-radius, border-width, border-color
 *
 * Every one of these carries a fallback, because a custom theme may not define
 * the newer tokens and a panel that collapses on an old theme is worse than one
 * that is slightly off.
 *
 * Note what is NOT here: no gradient, no invented icon, no decorative bar, no
 * chosen font. PANEL_DESIGN.md rejects all of it, and the earlier mockups were
 * thrown out for exactly that. A panel that looks designed looks foreign.
 *
 * ## The colour rule, which is not cosmetic
 *
 * **Accent carries state, never text.** HA's own accent tokens fail WCAG AA as
 * text on a light card: --primary-color is 2.63:1, --success-color 3.30:1,
 * --warning-color 1.96:1. Measured, not assumed; PANEL_DESIGN.md has the table.
 * So colour lives on the status dot and the card border, and every word is
 * --primary-text-color. --secondary-text-color clears AA by only 0.31, so it
 * may sit on an untinted card surface and nowhere else.
 *
 * ## Shadow DOM
 *
 * Styles are scoped to the component, per HA's guidance. Custom properties
 * inherit through the boundary, so themes still reach in. `hass-toggle-menu`
 * must be `composed` to get out.
 */

const OVERVIEW = "ikea_bilresa/overview";
const OVERVIEW_SUBSCRIBE = "ikea_bilresa/overview/subscribe";

// Only icons whose Material Design Icons paths are certain. mdi:knob, which
// event.py uses for the wheel, is deliberately absent rather than approximated:
// PANEL_DESIGN.md requires standard MDI, and an invented path is not one.
// Resolving real icons needs ha-svg-icon or the @mdi/js package — an open Phase
// 3 decision, not something to fake in the meantime.
const ICON = {
  menu: "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z",
  chevron: "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
  alert:
    "M13,13H11V7H13M13,17H11V15H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",
  refresh:
    "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z",
};

const STYLES = `
  :host {
    display: block;
    /* Local aliases so every fallback is written once. A custom theme that
       predates HA's token rename must still render a usable panel. */
    --_bg: var(--primary-background-color, #fafafa);
    --_card: var(--ha-card-background, var(--card-background-color, #fff));
    --_border: var(--ha-card-border-color, var(--divider-color, #e0e0e0));
    --_radius: var(--ha-card-border-radius, var(--ha-border-radius-lg, 12px));
    --_ink: var(--primary-text-color, #212121);
    --_ink-dim: var(--secondary-text-color, #727272);
    --_divider: var(--divider-color, rgba(0, 0, 0, 0.12));
    --_space-1: var(--ha-space-1, 4px);
    --_space-2: var(--ha-space-2, 8px);
    --_space-3: var(--ha-space-3, 12px);
    --_space-4: var(--ha-space-4, 16px);
    --_space-6: var(--ha-space-6, 24px);
    --_font: var(--ha-font-family-body, Roboto, Noto, sans-serif);
    --_fast: var(--ha-animation-duration-fast, 120ms);

    font-family: var(--_font);
    color: var(--_ink);
    background: var(--_bg);
    min-block-size: 100%;
  }

  /* The panel owns its app header; HA draws none. Without it a narrow screen
     has no way back to the sidebar. The safe-area inset is ADDED to the bar
     (content-box) — subtracting it would just shorten the bar and leave the
     button under an iPhone's notch. Both learned on a real phone. */
  header {
    display: flex;
    align-items: center;
    gap: var(--_space-2);
    box-sizing: content-box;
    block-size: 56px;
    padding-block: env(safe-area-inset-top, 0px) 0;
    padding-inline:
      max(var(--_space-1), env(safe-area-inset-left, 0px))
      max(var(--_space-4), env(safe-area-inset-right, 0px));
    background: var(--app-header-background-color, var(--primary-color, #03a9f4));
    color: var(--app-header-text-color, var(--text-primary-color, #fff));
    position: sticky;
    inset-block-start: 0;
    z-index: 1;
  }
  header h1 {
    margin: 0;
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: var(--ha-font-weight-normal, 400);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  /* With no menu button the title would sit against the edge; the button's own
     box is what spaces it on narrow screens. */
  header h1:first-child { padding-inline-start: var(--_space-3); }

  .icon-button {
    flex: 0 0 auto;
    inline-size: 48px;
    block-size: 48px;
    display: grid;
    place-items: center;
    padding: 0;
    border: 0;
    border-radius: 50%;
    background: transparent;
    color: inherit;
    cursor: pointer;
  }
  .icon-button:hover { background: rgba(255, 255, 255, 0.12); }
  .icon-button:focus-visible {
    outline: 2px solid currentColor;
    outline-offset: -4px;
  }
  .icon-button svg { inline-size: 24px; block-size: 24px; fill: currentColor; }

  main { padding: var(--_space-4); }
  @media (max-width: 600px) { main { padding: var(--_space-2); } }

  /* Summary. Small and quiet: PANEL_DESIGN.md wants it actionable, not a
     dashboard of its own. */
  .summary {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--_space-2);
    margin-block-end: var(--_space-4);
    padding-inline: var(--_space-1);
    font-size: var(--ha-font-size-m, 14px);
    color: var(--_ink-dim);
  }
  .summary .sep { opacity: 0.4; }

  .banner {
    display: flex;
    align-items: flex-start;
    gap: var(--_space-3);
    margin-block-end: var(--_space-4);
    padding: var(--_space-3) var(--_space-4);
    border: var(--ha-card-border-width, 1px) solid var(--_border);
    border-inline-start: 4px solid var(--warning-color, #ffa600);
    border-radius: var(--_radius);
    background: var(--_card);
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.6);
  }
  /* The stripe carries the warning; the words stay readable. HA's warning
     orange is 1.96:1 on a light card and cannot be text. */
  .banner svg {
    flex: 0 0 auto;
    inline-size: 20px;
    block-size: 20px;
    margin-block-start: 2px;
    fill: var(--warning-color, #ffa600);
  }

  /* auto-FIT, not auto-fill: auto-fill keeps empty tracks alive and leaves a
     phantom card-shaped hole beside two wheels on a wide screen, which reads as
     a failed load. The max stops two cards stretching into slabs. */
  .grid {
    display: grid;
    gap: var(--_space-4);
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 400px));
    justify-content: start;
  }

  .wheel {
    display: flex;
    flex-direction: column;
    inline-size: 100%;
    padding: 0;
    border: var(--ha-card-border-width, 1px) solid var(--_border);
    border-radius: var(--_radius);
    background: var(--_card);
    box-shadow: var(--ha-card-box-shadow, none);
    color: inherit;
    font: inherit;
    text-align: start;
    cursor: pointer;
    transition: border-color var(--_fast) ease-in-out;
  }
  .wheel:hover { border-color: var(--primary-color, #03a9f4); }
  .wheel:focus-visible {
    outline: 2px solid var(--primary-color, #03a9f4);
    outline-offset: 2px;
  }
  @media (prefers-reduced-motion: reduce) { .wheel { transition: none; } }

  .wheel-head {
    display: flex;
    align-items: baseline;
    gap: var(--_space-2);
    padding: var(--_space-4) var(--_space-4) var(--_space-3);
  }
  .wheel-name {
    font-size: var(--ha-font-size-l, 16px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  .wheel-sub {
    margin-block-start: var(--_space-1);
    font-size: var(--ha-font-size-s, 12px);
    color: var(--_ink-dim);
  }
  .status {
    display: inline-flex;
    align-items: center;
    gap: var(--_space-2);
    margin-inline-start: auto;
    flex: 0 0 auto;
    font-size: var(--ha-font-size-s, 12px);
    /* The dot is the colour. The word is readable. */
    color: var(--_ink);
  }
  .dot {
    inline-size: 8px;
    block-size: 8px;
    border-radius: 50%;
    background: var(--_ink-dim);
  }
  .dot[data-state="connected"] { background: var(--success-color, #43a047); }
  .dot[data-state="unavailable"] { background: var(--_ink-dim); }
  .dot[data-state="unknown"] {
    background: transparent;
    border: 2px solid var(--_ink-dim);
    box-sizing: border-box;
  }

  .channels { border-block-start: 1px solid var(--_divider); }
  .channel {
    display: flex;
    align-items: center;
    gap: var(--_space-3);
    padding: var(--_space-2) var(--_space-4);
    border-block-end: 1px solid var(--_divider);
  }
  .channel:last-child { border-block-end: 0; }
  .channel-n {
    flex: 0 0 auto;
    inline-size: 22px;
    block-size: 22px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    /* NOT --secondary-background-color: it is #202020 against a #1c1c1c card in
       the dark theme, i.e. 1.05:1, and the badge vanishes. */
    background: color-mix(in srgb, var(--_ink) 16%, var(--_card));
    font-size: var(--ha-font-size-xs, 10px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .channel-text { min-inline-size: 0; flex: 1; }
  .channel-behaviour {
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-condensed, 1.2);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .channel-target {
    font-size: var(--ha-font-size-s, 12px);
    color: var(--_ink-dim);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .channel[data-state="empty"] .channel-behaviour {
    color: var(--_ink-dim);
    font-style: italic;
  }
  .channel-warn {
    flex: 0 0 auto;
    inline-size: 16px;
    block-size: 16px;
    fill: var(--warning-color, #ffa600);
  }
  .channel > svg:last-child {
    flex: 0 0 auto;
    inline-size: 18px;
    block-size: 18px;
    fill: var(--_ink-dim);
  }

  .placeholder {
    display: grid;
    place-items: center;
    gap: var(--_space-3);
    padding: var(--_space-6) var(--_space-4);
    text-align: center;
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.6);
  }
  .placeholder .title {
    color: var(--_ink);
    font-size: var(--ha-font-size-l, 16px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .placeholder button {
    display: inline-flex;
    align-items: center;
    gap: var(--_space-2);
    min-block-size: 40px;
    padding-inline: var(--_space-4);
    border: 1px solid var(--_border);
    border-radius: var(--ha-border-radius-md, 8px);
    background: transparent;
    color: var(--_ink);
    font: inherit;
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    cursor: pointer;
  }
  .placeholder button:hover { background: var(--_divider); }
  .placeholder button:focus-visible {
    outline: 2px solid var(--primary-color, #03a9f4);
    outline-offset: 2px;
  }
  .placeholder button svg {
    inline-size: 18px;
    block-size: 18px;
    fill: var(--state-icon-color, #44739e);
  }

  /* Skeletons, not a spinner: the grid's shape is known before its data, so
     hold the layout rather than flashing an empty screen and reflowing. */
  .skeleton {
    border: var(--ha-card-border-width, 1px) solid var(--_border);
    border-radius: var(--_radius);
    background: var(--_card);
    block-size: 168px;
    opacity: 0.5;
  }
`;

const svg = (path, cls) => {
  const node = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  node.setAttribute("viewBox", "0 0 24 24");
  node.setAttribute("aria-hidden", "true");
  node.setAttribute("focusable", "false");
  if (cls) node.setAttribute("class", cls);
  const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
  p.setAttribute("d", path);
  node.appendChild(p);
  return node;
};

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  // Always textContent. Wheel names, areas and target labels are strings the
  // user chose; PANEL_ROADMAP.md's frontend floor forbids rendering them as HTML.
  if (text !== undefined) node.textContent = text;
  return node;
};

class IkeaBilresaPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._snapshot = null;
    this._error = null;
    this._unsub = null;
    this._started = false;
    this._open = null;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._started) {
      this._started = true;
      this._render();
      this._connect();
    }
  }

  set narrow(narrow) {
    // HA re-sets this on every resize across the breakpoint, and the menu button
    // appears and disappears with it. Storing it without re-rendering leaves a
    // desktop-sized header on a phone until something else happens to repaint.
    const changed = this._narrow !== narrow;
    this._narrow = narrow;
    if (changed && this._started) this._render();
  }

  set panel(panel) {
    this._panel = panel;
  }

  async _connect() {
    this._error = null;
    try {
      this._snapshot = await this._hass.callWS({ type: OVERVIEW });
      this._render();
    } catch (err) {
      this._fail(err);
      return;
    }
    try {
      this._unsub = await this._hass.connection.subscribeMessage(
        (snapshot) => {
          this._snapshot = snapshot;
          this._render();
        },
        { type: OVERVIEW_SUBSCRIBE },
      );
    } catch (err) {
      // A failed subscription is degraded, not fatal: the snapshot already
      // rendered, it just will not update itself.
      this._error = this._message(err);
      this._render();
    }
  }

  _fail(err) {
    this._error = this._message(err);
    this._snapshot = null;
    this._render();
  }

  _message(err) {
    return String(err && err.message ? err.message : err);
  }

  async _retry() {
    if (this._unsub) {
      this._unsub();
      this._unsub = null;
    }
    this._snapshot = null;
    this._error = null;
    this._render();
    await this._connect();
  }

  /**
   * HA removes the element when the panel is left. Without this the overview
   * subscription outlives the view and a closed panel keeps receiving pushes —
   * the leak PANEL_ROADMAP.md's "unsubscribe on view close" rule is about.
   */
  disconnectedCallback() {
    if (this._unsub) {
      this._unsub();
      this._unsub = null;
    }
    this._started = false;
  }

  /**
   * Home Assistant's own ha-menu-button shows itself only when
   *
   *   kioskMode === false && (narrow || dockedSidebar === "always_hidden")
   *
   * On a desktop with the sidebar on screen it renders nothing, because HA's
   * sidebar already has its own collapse control — a second hamburger is one
   * button too many, which is exactly how this looked on first deploy.
   *
   * The button is still mandatory when it IS narrow: the sidebar is collapsed
   * there and this is its only door.
   *
   * Kiosk mode is not checked. It lives in a private frontend store with no
   * public API, and a stray button under kiosk is a smaller problem than a
   * trapped user without one.
   */
  _showMenuButton() {
    return Boolean(this._narrow) || this._hass?.dockedSidebar === "always_hidden";
  }

  _header() {
    const bar = el("header");
    if (this._showMenuButton()) {
      const menu = el("button", "icon-button");
      menu.type = "button";
      menu.setAttribute("aria-label", "Open Home Assistant sidebar");
      menu.appendChild(svg(ICON.menu));
      menu.addEventListener("click", () =>
        this.dispatchEvent(
          new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }),
        ),
      );
      bar.appendChild(menu);
    }
    bar.appendChild(el("h1", null, "IKEA BILRESA"));
    return bar;
  }

  _summary() {
    const s = this._snapshot;
    const wrap = el("div", "summary");
    const connected = s.wheels.filter(
      (w) => w.availability === "connected",
    ).length;
    const unknown = s.wheels.filter((w) => w.availability === "unknown").length;

    wrap.appendChild(el("span", null, `${connected} connected`));
    const away = s.wheels.length - connected - unknown;
    if (away > 0) {
      wrap.appendChild(el("span", "sep", "·"));
      wrap.appendChild(el("span", null, `${away} unavailable`));
    }
    if (unknown > 0) {
      wrap.appendChild(el("span", "sep", "·"));
      wrap.appendChild(el("span", null, `${unknown} not reporting`));
    }
    wrap.appendChild(el("span", "sep", "·"));
    wrap.appendChild(
      el("span", null, s.matter_connected ? "Matter connected" : "Matter offline"),
    );
    return wrap;
  }

  _banner(text) {
    const b = el("div", "banner");
    b.appendChild(svg(ICON.alert));
    b.appendChild(el("span", null, text));
    return b;
  }

  _channel(channel) {
    const configured = channel.profile !== null && channel.profile !== undefined;
    const row = el("div", "channel");
    row.dataset.state = configured ? "ok" : "empty";
    row.appendChild(el("span", "channel-n", String(channel.channel)));

    const text = el("span", "channel-text");
    const behaviour = el(
      "div",
      "channel-behaviour",
      channel.behaviour || (configured ? channel.profile : "Not configured"),
    );
    text.appendChild(behaviour);
    text.appendChild(
      el(
        "div",
        "channel-target",
        channel.target_missing
          ? `${channel.target_label || "Target"} — unavailable`
          : channel.target_label || "Add a control binding",
      ),
    );
    row.appendChild(text);
    if (channel.target_missing) row.appendChild(svg(ICON.alert, "channel-warn"));
    row.appendChild(svg(ICON.chevron));
    return row;
  }

  _wheel(wheel) {
    const card = el("button", "wheel");
    card.type = "button";
    card.setAttribute(
      "aria-label",
      `${wheel.name}${wheel.area ? `, ${wheel.area}` : ""}`,
    );
    card.addEventListener("click", () => {
      this._open = wheel.key;
      this._render();
    });

    const head = el("div", "wheel-head");
    const names = el("span");
    names.appendChild(el("div", "wheel-name", wheel.name));
    const meta = [wheel.area, this._activityLabel(wheel)].filter(Boolean);
    names.appendChild(el("div", "wheel-sub", meta.join(" · ")));
    head.appendChild(names);

    const status = el("span", "status");
    const dot = el("span", "dot");
    dot.dataset.state = wheel.availability;
    status.appendChild(dot);
    status.appendChild(
      el(
        "span",
        null,
        {
          connected: "Connected",
          unavailable: "Unavailable",
          unknown: "Not reporting",
        }[wheel.availability] || "Unknown",
      ),
    );
    head.appendChild(status);
    card.appendChild(head);

    const channels = el("div", "channels");
    for (const channel of wheel.channels) channels.appendChild(this._channel(channel));
    card.appendChild(channels);
    return card;
  }

  /**
   * EventEntity does not restore state, so a wheel that has not been touched
   * since Home Assistant restarted has no last activity. That is "no activity
   * yet" and must never read as a fault.
   */
  _activityLabel(wheel) {
    if (!wheel.last_activity) return "No activity yet";
    const when = new Date(wheel.last_activity);
    if (Number.isNaN(when.getTime())) return null;
    const label = this._hass?.localize
      ? null
      : when.toLocaleString(this._hass?.language || undefined);
    const suffix =
      wheel.last_active_channel !== null && wheel.last_active_channel !== undefined
        ? ` · last on channel ${wheel.last_active_channel}`
        : "";
    return `${label || when.toLocaleString()}${suffix}`;
  }

  _placeholder(title, body, retry) {
    const wrap = el("div", "placeholder");
    wrap.appendChild(el("div", "title", title));
    wrap.appendChild(el("div", null, body));
    if (retry) {
      const button = el("button", null);
      button.type = "button";
      button.appendChild(svg(ICON.refresh));
      button.appendChild(el("span", null, "Try again"));
      button.addEventListener("click", () => this._retry());
      wrap.appendChild(button);
    }
    return wrap;
  }

  _body() {
    if (this._error && !this._snapshot) {
      return this._placeholder(
        "Cannot reach the integration",
        this._error,
        true,
      );
    }
    if (!this._snapshot) {
      const grid = el("div", "grid");
      for (let i = 0; i < 2; i++) grid.appendChild(el("div", "skeleton"));
      return grid;
    }
    if (this._open) {
      // Phase 4 builds the detail and its 256px wheel rail. Navigation exists
      // now so the grid's job is complete and testable; the destination is not
      // pretending to be finished.
      const wheel = this._snapshot.wheels.find((w) => w.key === this._open);
      const wrap = el("div");
      const back = el("button", null);
      back.type = "button";
      back.textContent = "← Back to all wheels";
      back.addEventListener("click", () => {
        this._open = null;
        this._render();
      });
      wrap.appendChild(
        this._placeholder(
          wheel ? wheel.name : "Wheel",
          "Channels, live test and diagnostics arrive in the next package.",
          false,
        ),
      );
      const row = el("div", "placeholder");
      row.appendChild(back);
      wrap.appendChild(row);
      return wrap;
    }
    if (!this._snapshot.wheels.length) {
      return this._placeholder(
        "No BILRESA wheels found",
        this._snapshot.matter_connected
          ? "The integration is connected but has not discovered a wheel yet."
          : "Home Assistant is not connected to Matter, so no wheel can be seen.",
        true,
      );
    }

    const wrap = el("div");
    if (!this._snapshot.matter_connected) {
      wrap.appendChild(
        this._banner(
          "Matter is disconnected. The wheels below show their last known state.",
        ),
      );
    } else if (this._error) {
      wrap.appendChild(
        this._banner("Live updates stopped. The view may be out of date."),
      );
    }
    const missing = this._snapshot.wheels.filter((w) =>
      w.channels.some((c) => c.target_missing),
    );
    if (missing.length) {
      wrap.appendChild(
        this._banner(
          `A control binding points at something Home Assistant can no longer find (${missing.length} ${missing.length === 1 ? "wheel" : "wheels"}).`,
        ),
      );
    }
    wrap.appendChild(this._summary());
    const grid = el("div", "grid");
    for (const wheel of this._snapshot.wheels) grid.appendChild(this._wheel(wheel));
    wrap.appendChild(grid);
    return wrap;
  }

  _render() {
    const style = document.createElement("style");
    style.textContent = STYLES;
    const main = el("main");
    main.appendChild(this._body());
    this.shadowRoot.replaceChildren(style, this._header(), main);
  }
}

if (!customElements.get("ikea-bilresa-panel")) {
  customElements.define("ikea-bilresa-panel", IkeaBilresaPanel);
}
