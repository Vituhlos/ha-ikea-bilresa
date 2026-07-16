/**
 * BILRESA panel — Phase 0 technical spike. NOT the panel.
 *
 * This file exists to answer four questions in a running Home Assistant, and
 * then to be deleted:
 *
 *   1. does HA fetch and execute a module served by this integration?
 *   2. does it inject `hass`, `narrow` and `panel` into the custom element?
 *   3. does an authenticated read-only WebSocket request reach the integration?
 *   4. does a subscription push, and does it stop when the panel is closed?
 *
 * It is deliberately hand-written, dependency-free and ugly. The real panel is
 * TypeScript + Lit bundled by Vite, per PANEL_ROADMAP.md, and its layout is the
 * two-layer model in PANEL_DESIGN.md — a grid of wheel cards, with a 256px rail
 * inside the wheel detail. None of that is here. Do not grow this file into it.
 *
 * No wheel names, areas, node IDs or serials are requested or rendered. The
 * spike's WebSocket reply is three scalars.
 */

class IkeaBilresaPanel extends HTMLElement {
  constructor() {
    super();
    this._unsub = null;
    this._info = null;
    this._pushes = 0;
    this._error = null;
    this._rendered = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this._rendered = true;
      this._render();
      this._probe();
    }
  }

  set panel(panel) {
    this._panel = panel;
  }

  set narrow(narrow) {
    this._narrow = narrow;
  }

  async _probe() {
    try {
      this._info = await this._hass.callWS({ type: "ikea_bilresa/spike/info" });
      this._render();
    } catch (err) {
      this._error = String(err && err.message ? err.message : err);
      this._render();
      return;
    }

    try {
      this._unsub = await this._hass.connection.subscribeMessage(
        () => {
          this._pushes += 1;
          this._render();
        },
        { type: "ikea_bilresa/spike/subscribe" },
      );
    } catch (err) {
      this._error = String(err && err.message ? err.message : err);
      this._render();
    }
  }

  /**
   * HA calls this when the panel is removed from the DOM. If the subscription
   * is not torn down here it outlives the view, which is exactly the leak the
   * roadmap's "unsubscribe on view close" rule is about.
   */
  disconnectedCallback() {
    if (this._unsub) {
      this._unsub();
      this._unsub = null;
    }
  }

  /**
   * Every dynamic value goes in through textContent, never innerHTML — the
   * error string in particular is an exception message this code did not
   * author. PANEL_ROADMAP.md's frontend floor requires "no unsafe HTML
   * rendering", and the real panel will be interpolating device and area names
   * that users chose. Whatever this file does, that one will copy.
   */
  /**
   * A custom panel owns its whole viewport, including the app header. Home
   * Assistant does not draw one for you.
   *
   * On a narrow screen the sidebar is collapsed and its only door is the
   * header's menu button. A panel without a header therefore TRAPS the user:
   * in the companion app there is no way back out except a system back gesture.
   * Found the hard way on a real phone, and invisible on a desktop where the
   * sidebar is already on screen.
   *
   * `hass-toggle-menu` is the event Home Assistant's own `ha-menu-button`
   * fires; it must bubble and cross the shadow boundary to reach the listener.
   */
  _header() {
    const bar = document.createElement("header");
    bar.className = "bilresa-panel-header";

    const menu = document.createElement("button");
    menu.type = "button";
    menu.className = "bilresa-panel-menu";
    menu.setAttribute("aria-label", "Open Home Assistant sidebar");
    menu.innerHTML =
      '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24">' +
      '<path d="M3 6h18v2H3V6m0 5h18v2H3v-2m0 5h18v2H3v-2Z"/></svg>';
    menu.addEventListener("click", () => {
      this.dispatchEvent(
        new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }),
      );
    });

    const title = document.createElement("div");
    title.textContent = "IKEA BILRESA";
    title.setAttribute("style", "font-size:20px;font-weight:400");

    bar.appendChild(menu);
    bar.appendChild(title);
    return bar;
  }

  _render() {
    const el = (tag, text, style) => {
      const node = document.createElement(tag);
      if (text !== undefined) node.textContent = text;
      if (style) node.setAttribute("style", style);
      return node;
    };

    const page = el("div", undefined, "font-family:Roboto,sans-serif");
    const style = document.createElement("style");
    style.textContent = `
      /* The companion app's WebView extends under the status bar, so on a
         notched iPhone a header with a plain 56px height puts its menu button
         behind the notch or Dynamic Island -- reachable in theory, unusable in
         practice. The safe-area insets are the fix, and they must be added to
         the height rather than eating into it, or the bar just gets shorter.
         The left/right insets matter in landscape, where the notch takes a
         side. env() resolves to 0px everywhere else, so this costs nothing on
         a desktop. Verify on real hardware: a narrow desktop window has no
         insets and will look fine either way. */
      ikea-bilresa-panel .bilresa-panel-header {
        display: flex;
        align-items: center;
        gap: 8px;
        box-sizing: content-box;
        height: 56px;
        padding-block: env(safe-area-inset-top, 0px) 0;
        padding-inline:
          max(4px, env(safe-area-inset-left, 0px))
          max(4px, env(safe-area-inset-right, 0px));
        border-bottom: 1px solid var(--divider-color);
        background: var(--app-header-background-color, var(--primary-color));
        color: var(--app-header-text-color, var(--text-primary-color));
      }
      ikea-bilresa-panel .bilresa-panel-menu {
        display: grid;
        place-items: center;
        flex: 0 0 48px;
        inline-size: 48px;
        block-size: 48px;
        padding: 0;
        border: 0;
        border-radius: 50%;
        cursor: pointer;
        background: transparent;
        color: inherit;
      }
      ikea-bilresa-panel .bilresa-panel-menu:hover {
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
      }
      ikea-bilresa-panel .bilresa-panel-menu:active {
        background: var(--divider-color);
      }
      ikea-bilresa-panel .bilresa-panel-menu:focus-visible {
        outline: 2px solid currentColor;
        outline-offset: -4px;
      }
      ikea-bilresa-panel .bilresa-panel-menu svg {
        inline-size: 24px;
        block-size: 24px;
        fill: currentColor;
      }
    `;
    page.appendChild(style);
    page.appendChild(this._header());

    const root = el(
      "div",
      undefined,
      "padding:24px;color:var(--primary-text-color)",
    );
    root.appendChild(
      el("h1", "BILRESA panel — Phase 0 spike", "font-size:20px;font-weight:500"),
    );
    root.appendChild(
      el(
        "p",
        "This is not the panel. It proves the delivery path works. If every row " +
          "below is populated, the spike passed and this file's job is done.",
        "color:var(--secondary-text-color);max-width:60ch",
      ),
    );

    if (this._error) {
      root.appendChild(
        el("div", `WebSocket failed: ${this._error}`, "color:var(--error-color)"),
      );
    } else if (!this._info) {
      root.appendChild(el("div", "calling WebSocket…"));
    } else {
      const table = document.createElement("table");
      const rows = [
        ["module loaded", "yes"],
        ["hass injected", this._hass ? "yes" : "no"],
        [
          "panel config",
          this._panel ? JSON.stringify(this._panel.config) : "missing",
        ],
        ["narrow", String(this._narrow)],
        ["ws request", "ok"],
        ["integration loaded", String(this._info.loaded)],
        ["matter connected", String(this._info.connected)],
        ["wheels discovered", String(this._info.wheel_count)],
        ["subscription pushes", String(this._pushes)],
      ];
      for (const [key, value] of rows) {
        const tr = document.createElement("tr");
        tr.appendChild(
          el(
            "td",
            key,
            "padding:4px 16px 4px 0;color:var(--secondary-text-color)",
          ),
        );
        const td = el("td", undefined, "padding:4px 0");
        td.appendChild(el("b", value));
        tr.appendChild(td);
        table.appendChild(tr);
      }
      root.appendChild(table);
    }

    page.appendChild(root);
    this.replaceChildren(page);
  }
}

// Home Assistant can import a cache-busted panel module into a document that
// still owns the previous release's custom-element registration. The browser
// does not allow redefining that name, so keep registration idempotent. A full
// page reload then picks up the new class from the new module URL.
if (!customElements.get("ikea-bilresa-panel")) {
  customElements.define("ikea-bilresa-panel", IkeaBilresaPanel);
}
