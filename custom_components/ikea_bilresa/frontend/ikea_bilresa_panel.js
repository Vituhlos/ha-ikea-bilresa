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
  _render() {
    const el = (tag, text, style) => {
      const node = document.createElement(tag);
      if (text !== undefined) node.textContent = text;
      if (style) node.setAttribute("style", style);
      return node;
    };

    const root = el(
      "div",
      undefined,
      "padding:24px;font-family:Roboto,sans-serif;color:var(--primary-text-color)",
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

    this.replaceChildren(root);
  }
}

customElements.define("ikea-bilresa-panel", IkeaBilresaPanel);
