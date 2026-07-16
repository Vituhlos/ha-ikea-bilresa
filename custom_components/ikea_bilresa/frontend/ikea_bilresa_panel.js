/**
 * BILRESA panel — wheel overview, live activity and binding editor.
 *
 * The layout follows PANEL_DESIGN.md's two-layer model: the landing view is a
 * grid of every wheel, while an opened wheel gets a measured 256px switcher rail
 * plus Channels, Live test and Diagnostics views. The rail disappears below
 * 620px and the detail's two-column content collapses on its own 700px pane
 * width, not on the window width.
 *
 * This file deliberately stays dependency-free. It uses Home Assistant tokens,
 * authenticated WebSocket commands and textContent only. Binding mutations are
 * narrow, admin-only and revision-checked; the browser never connects to Matter.
 *
 * Accent carries state, never words. Home Assistant's default accent tokens do
 * not pass WCAG AA as normal text on a light card, so labels stay on the primary
 * text colour and state is paired with dots, borders, weight and explicit copy.
 */

const OVERVIEW = "ikea_bilresa/overview";
const OVERVIEW_SUBSCRIBE = "ikea_bilresa/overview/subscribe";
const ACTIVITY_SUBSCRIBE = "ikea_bilresa/activity/subscribe";
const BINDING_SAVE = "ikea_bilresa/binding/save";
const BINDING_DELETE = "ikea_bilresa/binding/delete";
const BINDING_TEST = "ikea_bilresa/binding/test";
const ACTIVITY_LIMIT = 8;

const MODE_DOMAINS = {
  brightness: ["light"],
  color_temp: ["light"],
  color: ["light"],
  volume: ["media_player"],
  cover_position: ["cover"],
  temperature: ["climate"],
  fan_speed: ["fan"],
  number: ["number", "input_number"],
};

const DEFAULT_BINDING = {
  mode: "brightness",
  step: 3,
  acceleration: 0,
  min_brightness: 1,
  max_brightness: 100,
  transition: 1,
  click_action: "toggle",
  button_response: "multi_press",
  hold_action: "toggle",
  scenes: [],
};

// Material Design Icons paths already used as standard chrome. The product icon
// remains absent rather than approximated with an invented path.
const ICON = {
  menu: "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z",
  chevron: "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
  back: "M20,11H7.83L13.42,5.41L12,4L4,12L12,20L13.42,18.59L7.83,13H20V11Z",
  check: "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
  alert:
    "M13,13H11V7H13M13,17H11V15H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",
  refresh:
    "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z",
};

const STYLES = `
  :host {
    display: block;
    --_bg: var(--primary-background-color, #fafafa);
    --_card: var(--ha-card-background, var(--card-background-color, #fff));
    --_border: var(--ha-card-border-color, var(--divider-color, #e0e0e0));
    --_radius: var(--ha-card-border-radius, var(--ha-border-radius-lg, 12px));
    --_ink: var(--primary-text-color, #212121);
    --_ink-dim: var(--secondary-text-color, #727272);
    --_divider: var(--divider-color, rgba(0, 0, 0, 0.12));
    --_surface-subtle: var(
      --secondary-background-color,
      color-mix(in srgb, var(--_ink) 4%, var(--_card))
    );
    --_selected: var(
      --secondary-background-color,
      color-mix(in srgb, var(--_ink) 8%, var(--_card))
    );
    --_space-1: var(--ha-space-1, 4px);
    --_space-2: var(--ha-space-2, 8px);
    --_space-3: var(--ha-space-3, 12px);
    --_space-4: var(--ha-space-4, 16px);
    --_space-5: var(--ha-space-5, 20px);
    --_space-6: var(--ha-space-6, 24px);
    --_space-8: var(--ha-space-8, 32px);
    --_font: var(--ha-font-family-body, Roboto, Noto, sans-serif);
    --_fast: var(--ha-animation-duration-fast, 120ms);
    --_rail-width: 256px;
    --_overview-max: 1120px;

    min-block-size: 100vh;
    min-block-size: 100dvh;
    background: var(--_bg);
    color: var(--_ink);
    font-family: var(--_font);
  }

  *, *::before, *::after { box-sizing: border-box; }

  /* The safe-area inset is added to the 56px bar. A border-box header would
     consume the inset and put the exit control under an iPhone notch. */
  header {
    position: sticky;
    inset-block-start: 0;
    z-index: 2;
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
  }
  header h1 {
    margin: 0;
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: var(--ha-font-weight-normal, 400);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  header h1:first-child { padding-inline-start: var(--_space-3); }

  button { font-family: inherit; }
  button:focus-visible {
    outline: 2px solid var(--_ink);
    outline-offset: 2px;
  }
  summary:focus-visible {
    outline: 2px solid var(--_ink);
    outline-offset: -3px;
  }

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
    outline-color: var(--_ink);
    outline-offset: -4px;
    background: var(--_card);
    color: var(--_ink);
  }
  .icon-button svg { inline-size: 24px; block-size: 24px; fill: currentColor; }

  main {
    padding-block: var(--_space-4) max(var(--_space-4), env(safe-area-inset-bottom, 0px));
    padding-inline:
      max(var(--_space-4), env(safe-area-inset-left, 0px))
      max(var(--_space-4), env(safe-area-inset-right, 0px));
  }
  @media (max-width: 600px) {
    main {
      padding-inline:
        max(var(--_space-2), env(safe-area-inset-left, 0px))
        max(var(--_space-2), env(safe-area-inset-right, 0px));
    }
  }

  .summary {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--_space-2);
    margin-block-end: var(--_space-4);
    padding-inline: var(--_space-1);
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
  }
  .summary .sep { opacity: 0.4; }

  .overview {
    max-inline-size: var(--_overview-max);
    margin-inline: auto;
  }

  .banner {
    display: flex;
    align-items: flex-start;
    gap: var(--_space-3);
    margin-block-end: var(--_space-4);
    padding: var(--_space-3) var(--_space-4);
    border: var(--ha-card-border-width, 1px) solid var(--_border);
    border-radius: var(--_radius);
    background: var(--_card);
    color: var(--_ink);
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.6);
  }
  .banner svg {
    flex: 0 0 auto;
    inline-size: 20px;
    block-size: 20px;
    margin-block-start: 2px;
    fill: currentColor;
  }

  .grid {
    display: grid;
    gap: var(--_space-4);
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 400px), 1fr));
  }

  .wheel {
    display: flex;
    flex-direction: column;
    inline-size: 100%;
    overflow: hidden;
    padding: 0;
    border: var(--ha-card-border-width, 1px) solid var(--_border);
    border-radius: var(--_radius);
    background: var(--_card);
    box-shadow: var(--ha-card-box-shadow, none);
    color: inherit;
    font: inherit;
    text-align: start;
    cursor: pointer;
    transition:
      border-color var(--_fast) ease-in-out,
      background-color var(--_fast) ease-in-out;
  }
  .wheel:hover {
    border-color: var(--_ink);
    background: var(--_surface-subtle);
  }

  .wheel-head {
    display: flex;
    align-items: center;
    gap: var(--_space-3);
    min-block-size: 88px;
    padding: var(--_space-5) var(--_space-6);
  }
  .wheel-head > span:first-child { min-inline-size: 0; }
  .wheel-name {
    display: block;
    min-inline-size: 0;
    overflow-wrap: anywhere;
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  .wheel-sub {
    display: block;
    margin-block-start: var(--_space-2);
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
  }

  .status {
    display: inline-flex;
    align-items: center;
    gap: var(--_space-2);
    margin-inline-start: auto;
    flex: 0 0 auto;
    color: var(--_ink);
    font-size: var(--ha-font-size-m, 14px);
  }
  .dot {
    inline-size: 8px;
    block-size: 8px;
    flex: 0 0 auto;
    border-radius: 50%;
    background: var(--_ink-dim);
  }
  .dot[data-state="connected"],
  .dot[data-state="success"] { background: var(--success-color, #43a047); }
  .dot[data-state="unavailable"],
  .dot[data-state="failed"] { background: var(--_ink-dim); }
  .dot[data-state="unknown"] {
    border: 2px solid var(--_ink-dim);
    background: transparent;
  }

  .channels {
    display: block;
    border-block-start: 1px solid var(--_divider);
  }
  .channel {
    display: flex;
    align-items: center;
    gap: var(--_space-3);
    min-block-size: 64px;
    padding: var(--_space-3) var(--_space-6);
    border-block-end: 1px solid var(--_divider);
    background: var(--_card);
  }
  .channel:last-child { border-block-end: 0; }
  .channel-n {
    flex: 0 0 auto;
    inline-size: 28px;
    block-size: 28px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    background: color-mix(in srgb, var(--_ink) 16%, var(--_card));
    font-size: var(--ha-font-size-s, 12px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .channel-text { min-inline-size: 0; flex: 1; }
  .channel-behaviour,
  .channel-target {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .channel-behaviour {
    font-size: var(--ha-font-size-l, 16px);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  .channel-target {
    margin-block-start: var(--_space-1);
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
  }
  .channel[data-state="empty"] .channel-behaviour {
    color: var(--_ink-dim);
    font-style: italic;
  }
  .channel-warn,
  .wheel-open {
    flex: 0 0 auto;
    inline-size: 20px;
    block-size: 20px;
    fill: var(--_ink);
  }

  .detail-shell {
    display: grid;
    grid-template-columns: var(--_rail-width) minmax(0, 1fr);
    gap: var(--_space-4);
    align-items: start;
  }
  .rail {
    position: sticky;
    inset-block-start: calc(56px + env(safe-area-inset-top, 0px) + var(--_space-4));
    max-block-size: calc(100dvh - 56px - env(safe-area-inset-top, 0px) - var(--_space-8));
    overflow: auto;
    border: var(--ha-card-border-width, 1px) solid var(--_border);
    border-radius: var(--_radius);
    background: var(--_card);
  }
  .rail-back {
    inline-size: 100%;
    min-block-size: 52px;
    display: flex;
    align-items: center;
    gap: var(--_space-2);
    padding-inline: var(--_space-4);
    border: 0;
    border-block-end: 1px solid var(--_divider);
    background: transparent;
    color: var(--_ink);
    text-align: start;
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    cursor: pointer;
  }
  .rail-back:hover { background: var(--_surface-subtle); }
  .rail-back svg {
    inline-size: 20px;
    block-size: 20px;
    fill: currentColor;
  }
  .rail-title {
    padding: var(--_space-4) var(--_space-4) var(--_space-2);
    border-block-end: 1px solid var(--_divider);
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .rail ul { margin: 0; padding: var(--_space-2); list-style: none; }
  .rail li + li { margin-block-start: var(--_space-1); }
  .rail-wheel {
    inline-size: 100%;
    min-block-size: 48px;
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: var(--_space-2);
    padding: var(--_space-2) var(--_space-3);
    border: 0;
    border-radius: var(--ha-border-radius-md, 8px);
    background: transparent;
    color: var(--_ink);
    text-align: start;
    cursor: pointer;
  }
  .rail-wheel:hover { background: color-mix(in srgb, var(--_ink) 6%, transparent); }
  .rail-wheel[aria-current="page"] {
    background: var(--_selected);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .rail-copy { min-inline-size: 0; }
  .rail-name,
  .rail-area {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .rail-name { font-size: var(--ha-font-size-m, 14px); }
  .rail-area {
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-s, 12px);
    font-weight: var(--ha-font-weight-normal, 400);
  }
  .rail-wheel[aria-current="page"] .rail-area { color: var(--_ink); }
  .rail-check { inline-size: 18px; block-size: 18px; fill: var(--_ink); }

  .detail-pane { min-inline-size: 0; container-type: inline-size; }
  .detail-top {
    display: flex;
    align-items: flex-start;
    gap: var(--_space-3);
    min-block-size: 72px;
    margin-block-end: var(--_space-2);
  }
  .back-button {
    display: none;
    min-block-size: 44px;
    align-items: center;
    gap: var(--_space-2);
    padding-inline: var(--_space-3);
    border: 0;
    border-radius: var(--ha-border-radius-md, 8px);
    background: transparent;
    color: var(--_ink);
    font-size: var(--ha-font-size-m, 14px);
    cursor: pointer;
  }
  .back-button:hover { background: color-mix(in srgb, var(--_ink) 6%, transparent); }
  .back-button svg { inline-size: 20px; block-size: 20px; fill: currentColor; }
  .detail-heading { min-inline-size: 0; padding-block-start: var(--_space-2); }
  .detail-heading h2 {
    margin: 0;
    overflow-wrap: anywhere;
    font-size: var(--ha-font-size-3xl, 30px);
    font-weight: var(--ha-font-weight-normal, 400);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  .detail-meta {
    margin-block-start: var(--_space-2);
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
  }

  .tabs {
    display: flex;
    gap: var(--_space-1);
    overflow-x: auto;
    margin-block-end: var(--_space-4);
    border-block-end: 1px solid var(--_divider);
  }
  .tab {
    position: relative;
    min-block-size: 44px;
    flex: 0 0 auto;
    padding-inline: var(--_space-4);
    border: 0;
    background: transparent;
    color: var(--_ink);
    font-size: var(--ha-font-size-m, 14px);
    cursor: pointer;
  }
  .tab:hover { background: color-mix(in srgb, var(--_ink) 6%, transparent); }
  .tab[aria-selected="true"] { font-weight: var(--ha-font-weight-medium, 500); }
  .tab[aria-selected="true"]::after {
    content: "";
    position: absolute;
    inset-inline: var(--_space-3);
    inset-block-end: 0;
    block-size: 3px;
    background: var(--primary-color, #03a9f4);
  }
  .tab-panel { min-inline-size: 0; }

  .section-head { margin-block-end: var(--_space-4); }
  .section-head h3 {
    margin: 0;
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  .section-head p {
    max-inline-size: 70ch;
    margin: var(--_space-1) 0 0;
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.6);
  }

  .diagnostic-grid,
  .live-layout {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--_space-4);
  }
  .channel-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--_space-4);
  }
  .channel-detail {
    display: flex;
    flex-direction: column;
    min-inline-size: 0;
    min-block-size: 100%;
    overflow: hidden;
    border: var(--ha-card-border-width, 1px) solid var(--_border);
    border-radius: var(--_radius);
    background: var(--_card);
    box-shadow: var(--ha-card-box-shadow, none);
  }
  .channel-detail-head {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: start;
    gap: var(--_space-3);
    padding: var(--_space-4);
  }
  .channel-detail-number {
    inline-size: 32px;
    block-size: 32px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    background: var(--_selected);
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .channel-detail-copy { min-inline-size: 0; }
  .channel-detail-title {
    font-size: var(--ha-font-size-l, 16px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .channel-detail-summary {
    margin-block-start: var(--_space-1);
    overflow-wrap: anywhere;
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
  }
  .channel-detail[data-state="warning"] .channel-detail-summary {
    color: var(--_ink);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .channel-action-list {
    display: grid;
    gap: 0;
    margin: 0;
    padding: 0;
    border-block-start: 1px solid var(--_divider);
    list-style: none;
  }
  .channel-action {
    display: grid;
    grid-template-columns: minmax(9ch, 0.9fr) minmax(0, 1.5fr);
    gap: var(--_space-3);
    align-items: start;
    min-inline-size: 0;
    padding: var(--_space-3) var(--_space-4);
    background: var(--_card);
  }
  .channel-action + .channel-action { border-block-start: 1px solid var(--_divider); }
  .channel-action-label {
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-s, 12px);
    line-height: var(--ha-line-height-normal, 1.4);
  }
  .channel-action-value {
    overflow-wrap: anywhere;
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.45);
  }
  .channel-action[data-state="warning"] .channel-action-value {
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .channel-detail-footer {
    margin-block-start: auto;
    padding: var(--_space-3) var(--_space-4);
    border-block-start: 1px solid var(--_divider);
  }
  .channel-detail-footer .action-button { inline-size: 100%; justify-content: center; }
  .channel-detail .binding-form {
    border-block-start: 1px solid var(--_divider);
  }
  .detail-card {
    min-inline-size: 0;
    border: var(--ha-card-border-width, 1px) solid var(--_border);
    border-radius: var(--_radius);
    background: var(--_card);
    box-shadow: var(--ha-card-box-shadow, none);
  }
  .detail-card h4 {
    margin: 0;
    padding: var(--_space-4);
    border-block-end: 1px solid var(--_divider);
    font-size: var(--ha-font-size-l, 16px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .facts { margin: 0; padding: var(--_space-2) var(--_space-4); }
  .fact {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(0, 3fr);
    gap: var(--_space-3);
    padding-block: var(--_space-2);
  }
  .fact + .fact { border-block-start: 1px solid var(--_divider); }
  .fact dt { color: var(--_ink-dim); font-size: var(--ha-font-size-s, 12px); }
  .fact dd {
    min-inline-size: 0;
    margin: 0;
    overflow-wrap: anywhere;
    text-align: end;
    font-size: var(--ha-font-size-m, 14px);
  }
  .fact dd[data-state="warning"] { font-weight: var(--ha-font-weight-medium, 500); }

  .card-actions,
  .form-actions,
  .test-actions,
  .delete-confirm {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--_space-2);
    padding: var(--_space-3) var(--_space-4);
    border-block-start: 1px solid var(--_divider);
  }
  .action-button {
    min-block-size: 44px;
    padding-inline: var(--_space-4);
    border: 1px solid var(--_border);
    border-radius: var(--ha-border-radius-md, 8px);
    background: transparent;
    color: var(--_ink);
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    cursor: pointer;
  }
  .action-button:hover { background: var(--_selected); }
  .action-button[data-primary="true"] {
    border-color: var(--primary-color, var(--_ink));
    background: var(--primary-color, var(--_ink));
    color: var(--text-primary-color, var(--_card));
  }
  .action-button[data-danger="true"] {
    border-color: var(--error-color, var(--_ink));
    color: var(--error-color, var(--_ink));
  }
  .action-button:disabled { cursor: wait; opacity: 0.65; }

  .binding-form {
    display: grid;
    gap: var(--_space-4);
    padding: var(--_space-4);
  }
  .form-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--_space-4);
  }
  .field {
    min-inline-size: 0;
    display: grid;
    align-content: start;
    gap: var(--_space-1);
  }
  .field[data-wide="true"] { grid-column: 1 / -1; }
  .field label,
  .field-label {
    color: var(--_ink);
    font-size: var(--ha-font-size-s, 12px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .field input,
  .field select {
    min-inline-size: 0;
    inline-size: 100%;
    min-block-size: 44px;
    padding: var(--_space-2) var(--_space-3);
    border: 1px solid var(--_border);
    border-radius: var(--ha-border-radius-md, 8px);
    background: var(--_card);
    color: var(--_ink);
    font: inherit;
  }
  .field select[multiple] { min-block-size: 132px; }
  .field input:focus-visible,
  .field select:focus-visible {
    outline: 2px solid var(--_ink);
    outline-offset: 2px;
  }
  .field-help,
  .field-error,
  .form-message {
    font-size: var(--ha-font-size-s, 12px);
    line-height: var(--ha-line-height-normal, 1.6);
  }
  .field-help { color: var(--_ink-dim); }
  .field-error { color: var(--_ink); font-weight: var(--ha-font-weight-medium, 500); }
  .form-message {
    margin: 0;
    padding: var(--_space-3);
    border: 1px solid var(--_border);
    border-radius: var(--ha-border-radius-md, 8px);
  }
  .advanced {
    border-block-start: 1px solid var(--_divider);
    padding-block-start: var(--_space-3);
  }
  .advanced summary {
    min-block-size: 44px;
    display: flex;
    align-items: center;
    cursor: pointer;
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .advanced .form-grid { padding-block-start: var(--_space-3); }
  .delete-confirm { color: var(--_ink); }
  .delete-confirm span { flex: 1 1 220px; }
  .test-panel {
    grid-column: 1 / -1;
    overflow: hidden;
  }
  .test-panel > summary {
    min-block-size: 56px;
    display: flex;
    align-items: center;
    padding: var(--_space-3) var(--_space-4);
    cursor: pointer;
    font-size: var(--ha-font-size-l, 16px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .test-panel > summary:hover { background: var(--_surface-subtle); }
  .test-panel p {
    margin: 0;
    padding: var(--_space-4);
    border-block-start: 1px solid var(--_divider);
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.6);
  }

  .live-layout {
    grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
    align-items: start;
  }
  .live-output {
    min-block-size: 360px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: var(--_space-8);
  }
  .live-status {
    display: inline-flex;
    align-items: center;
    gap: var(--_space-2);
    margin-block-end: var(--_space-6);
    color: var(--_ink);
    font-size: var(--ha-font-size-s, 12px);
  }
  .live-result {
    overflow-wrap: anywhere;
    font-size: var(--ha-font-size-4xl, 36px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  .live-explanation {
    max-inline-size: 62ch;
    margin-block-start: var(--_space-2);
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.6);
  }
  .dispatch {
    display: flex;
    align-items: center;
    gap: var(--_space-2);
    margin-block-start: var(--_space-5);
    font-size: var(--ha-font-size-l, 16px);
  }
  .gesture-caption {
    margin-block-start: var(--_space-4);
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-s, 12px);
  }
  .waiting-title {
    font-size: var(--ha-font-size-2xl, 24px);
    font-weight: var(--ha-font-weight-medium, 500);
  }

  .live-side {
    display: grid;
    gap: var(--_space-4);
  }
  .live-channels { overflow: hidden; }
  .live-channel {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
    gap: var(--_space-3);
    min-block-size: 64px;
    padding: var(--_space-3) var(--_space-4);
  }
  .live-channel + .live-channel { border-block-start: 1px solid var(--_divider); }
  .live-channel-copy { min-inline-size: 0; }
  .live-channel-title {
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .live-channel-summary {
    margin-block-start: var(--_space-1);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-s, 12px);
  }
  .recent h4 { padding-block-end: var(--_space-3); }
  .recent ol { margin: 0; padding: 0; list-style: none; }
  .recent li {
    padding: var(--_space-3) var(--_space-4);
    font-size: var(--ha-font-size-m, 14px);
  }
  .recent li + li { border-block-start: 1px solid var(--_divider); }
  .recent time {
    display: block;
    margin-block-start: var(--_space-1);
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-s, 12px);
  }

  .health-hero {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    gap: var(--_space-3);
    padding: var(--_space-5);
  }
  .health-hero .dot {
    inline-size: 12px;
    block-size: 12px;
  }
  .health-copy { min-inline-size: 0; }
  .health-title {
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .health-body {
    margin-block-start: var(--_space-1);
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
  }
  .recovery { grid-column: 1 / -1; }
  .recovery p {
    margin: 0;
    padding: var(--_space-4);
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.6);
  }
  .technical-details {
    grid-column: 1 / -1;
    overflow: hidden;
  }
  .technical-details > summary {
    min-block-size: 52px;
    display: flex;
    align-items: center;
    padding-inline: var(--_space-4);
    cursor: pointer;
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .technical-details > summary:hover { background: var(--_surface-subtle); }

  .placeholder {
    display: grid;
    place-items: center;
    gap: var(--_space-3);
    padding: var(--_space-6) var(--_space-4);
    color: var(--_ink-dim);
    text-align: center;
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.6);
  }
  .placeholder .title {
    color: var(--_ink);
    font-size: var(--ha-font-size-l, 16px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .placeholder button {
    min-block-size: 44px;
    display: inline-flex;
    align-items: center;
    gap: var(--_space-2);
    padding-inline: var(--_space-4);
    border: 1px solid var(--_border);
    border-radius: var(--ha-border-radius-md, 8px);
    background: transparent;
    color: var(--_ink);
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    cursor: pointer;
  }
  .placeholder button:hover { background: var(--_divider); }
  .placeholder button svg { inline-size: 18px; block-size: 18px; fill: currentColor; }

  .skeleton {
    block-size: 168px;
    border: var(--ha-card-border-width, 1px) solid var(--_border);
    border-radius: var(--_radius);
    background: var(--_card);
    opacity: 0.5;
  }

  @container (max-width: 700px) {
    .diagnostic-grid,
    .live-layout,
    .form-grid { grid-template-columns: minmax(0, 1fr); }
    .channel-grid { grid-template-columns: minmax(0, 1fr); }
    .field[data-wide="true"] { grid-column: auto; }
  }

  @media (max-width: 619px) {
    .detail-shell { grid-template-columns: minmax(0, 1fr); }
    .rail { display: none; }
    .detail-top { display: block; }
    .back-button { display: inline-flex; }
    .detail-heading { padding: var(--_space-2) var(--_space-3) 0; }
    .detail-heading h2 { font-size: var(--ha-font-size-xl, 20px); }
    .wheel-head { padding-inline: var(--_space-4); }
    .channel { padding-inline: var(--_space-4); }
    .channel-detail-head {
      grid-template-columns: auto minmax(0, 1fr);
      padding-inline: var(--_space-4);
    }
    .channel-action { grid-template-columns: minmax(0, 1fr); }
    .live-output {
      min-block-size: 280px;
      padding: var(--_space-6) var(--_space-4);
    }
    .live-result { font-size: var(--ha-font-size-3xl, 30px); }
  }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
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
  // Names, areas and targets are user-controlled. Never interpret them as HTML.
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
    this._view = "channels";
    this._activities = [];
    this._activityUnsub = null;
    this._activityPending = false;
    this._activityError = false;
    this._activityEpoch = 0;
    this._editingChannel = null;
    this._editorData = null;
    this._editorBinding = null;
    this._editorErrors = {};
    this._editorBusy = false;
    this._editorMessage = null;
    this._deleteConfirm = false;
    this._testBusy = false;
    this._testMessage = null;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._started) {
      this._started = true;
      this._render();
      this._connect();
      if (this._view === "live" && this._open) this._startActivity();
    }
  }

  set narrow(narrow) {
    const changed = this._narrow !== narrow;
    this._narrow = narrow;
    if (changed && this._started) this._render();
  }

  set panel(panel) {
    this._panel = panel;
  }

  _t(key, placeholders) {
    const labels = this._panel?.config?.labels || {};
    let value = labels[key];
    if (value === undefined) return key;
    if (placeholders) {
      for (const [name, replacement] of Object.entries(placeholders)) {
        value = value.replace(`{${name}}`, String(replacement));
      }
    }
    return value;
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
          if (
            this._open &&
            !snapshot.wheels.some((wheel) => wheel.key === this._open)
          ) {
            this._stopActivity();
          }
          this._render();
        },
        { type: OVERVIEW_SUBSCRIBE },
      );
    } catch (err) {
      // The existing snapshot remains useful; only its automatic updates stopped.
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
    this._stopActivity();
    this._snapshot = null;
    this._error = null;
    this._render();
    await this._connect();
  }

  disconnectedCallback() {
    if (this._unsub) {
      this._unsub();
      this._unsub = null;
    }
    this._stopActivity();
    this._started = false;
  }

  async _startActivity() {
    if (
      this._activityUnsub ||
      this._activityPending ||
      this._view !== "live" ||
      !this._open
    ) {
      return;
    }

    const epoch = ++this._activityEpoch;
    this._activityPending = true;
    this._activityError = false;
    this._render();
    try {
      const unsub = await this._hass.connection.subscribeMessage(
        (activity) => {
          if (
            epoch !== this._activityEpoch ||
            this._view !== "live" ||
            activity.wheel !== this._open
          ) {
            return;
          }
          const receivedAt = new Date().toISOString();
          const index = activity.action_id
            ? this._activities.findIndex(
                (item) => item.action_id === activity.action_id,
              )
            : -1;
          if (index >= 0) {
            const current = this._activities[index];
            this._activities = [
              {
                ...current,
                ...activity,
                received_at: current.received_at || receivedAt,
                updated_at: receivedAt,
              },
              ...this._activities.filter((_, itemIndex) => itemIndex !== index),
            ].slice(0, ACTIVITY_LIMIT);
          } else {
            this._activities = [
              { ...activity, received_at: receivedAt, updated_at: receivedAt },
              ...this._activities,
            ].slice(0, ACTIVITY_LIMIT);
          }
          this._render();
        },
        { type: ACTIVITY_SUBSCRIBE },
      );

      if (
        epoch !== this._activityEpoch ||
        this._view !== "live" ||
        !this._open
      ) {
        unsub();
        return;
      }
      this._activityUnsub = unsub;
    } catch (_err) {
      if (epoch === this._activityEpoch) this._activityError = true;
    } finally {
      if (epoch === this._activityEpoch) {
        this._activityPending = false;
        this._render();
      }
    }
  }

  _stopActivity() {
    this._activityEpoch += 1;
    if (this._activityUnsub) {
      this._activityUnsub();
      this._activityUnsub = null;
    }
    this._activityPending = false;
  }

  _setView(view) {
    if (view === this._view) return;
    if (this._view === "live") this._stopActivity();
    this._view = view;
    this._activityError = false;
    this._render();
    if (view === "live") this._startActivity();
  }

  _openWheel(key) {
    if (key !== this._open) {
      this._activities = [];
      this._closeEditor();
    }
    this._open = key;
    this._render();
  }

  _backToOverview() {
    this._stopActivity();
    this._view = "channels";
    this._open = null;
    this._activities = [];
    this._closeEditor();
    this._render();
  }

  _showMenuButton() {
    return Boolean(this._narrow) || this._hass?.dockedSidebar === "always_hidden";
  }

  _header() {
    const bar = el("header");
    if (this._showMenuButton()) {
      const menu = el("button", "icon-button");
      menu.type = "button";
      menu.setAttribute("aria-label", this._t("menu"));
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
      (wheel) => wheel.availability === "connected",
    ).length;
    const unknown = s.wheels.filter(
      (wheel) => wheel.availability === "unknown",
    ).length;
    const unavailable = s.wheels.length - connected - unknown;

    wrap.appendChild(
      el("span", null, this._t("summary_connected", { count: connected })),
    );
    if (unavailable > 0) {
      wrap.appendChild(el("span", "sep", "·"));
      wrap.appendChild(
        el(
          "span",
          null,
          this._t("summary_unavailable", { count: unavailable }),
        ),
      );
    }
    if (unknown > 0) {
      wrap.appendChild(el("span", "sep", "·"));
      wrap.appendChild(
        el("span", null, this._t("summary_unknown", { count: unknown })),
      );
    }
    wrap.appendChild(el("span", "sep", "·"));
    wrap.appendChild(
      el(
        "span",
        null,
        this._t(s.matter_connected ? "matter_connected" : "matter_offline"),
      ),
    );
    return wrap;
  }

  _banner(text) {
    const banner = el("div", "banner");
    banner.setAttribute("role", "status");
    banner.appendChild(svg(ICON.alert));
    banner.appendChild(el("span", null, text));
    return banner;
  }

  _status(availability) {
    const status = el("span", "status");
    const dot = el("span", "dot");
    dot.dataset.state = availability;
    status.appendChild(dot);
    status.appendChild(el("span", null, this._t(availability)));
    return status;
  }

  _overviewChannel(channel) {
    const configured = channel.profile !== null && channel.profile !== undefined;
    const row = el("span", "channel");
    row.dataset.state = configured ? "ok" : "empty";
    row.appendChild(el("span", "channel-n", String(channel.channel)));

    const text = el("span", "channel-text");
    text.appendChild(
      el(
        "span",
        "channel-behaviour",
        channel.behaviour ||
          (configured ? channel.profile : this._t("not_configured")),
      ),
    );
    text.appendChild(
      el(
        "span",
        "channel-target",
        channel.target_missing
          ? this._t("target_unavailable", {
              target: channel.target_label || this._t("target_none"),
            })
          : channel.target_label || this._t("add_binding"),
      ),
    );
    row.appendChild(text);
    if (channel.target_missing) row.appendChild(svg(ICON.alert, "channel-warn"));
    return row;
  }

  _wheel(wheel) {
    const card = el("button", "wheel");
    card.type = "button";
    card.setAttribute(
      "aria-label",
      `${wheel.name}${wheel.area ? `, ${wheel.area}` : ""}`,
    );
    card.addEventListener("click", () => this._openWheel(wheel.key));

    const head = el("span", "wheel-head");
    const names = el("span");
    names.appendChild(el("span", "wheel-name", wheel.name));
    const meta = [wheel.area, this._activityLabel(wheel)].filter(Boolean);
    names.appendChild(el("span", "wheel-sub", meta.join(" · ")));
    head.appendChild(names);
    head.appendChild(this._status(wheel.availability));
    head.appendChild(svg(ICON.chevron, "wheel-open"));
    card.appendChild(head);

    const channels = el("span", "channels");
    for (const channel of wheel.channels) {
      channels.appendChild(this._overviewChannel(channel));
    }
    card.appendChild(channels);
    return card;
  }

  _activityLabel(wheel) {
    if (!wheel.last_activity) return this._t("no_activity");
    const when = new Date(wheel.last_activity);
    if (Number.isNaN(when.getTime())) return null;
    const suffix =
      wheel.last_active_channel !== null &&
      wheel.last_active_channel !== undefined
        ? ` · ${this._t("last_on_channel", {
            channel: wheel.last_active_channel,
          })}`
        : "";
    return `${this._formatDate(when)}${suffix}`;
  }

  _formatDate(value) {
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat(this._hass?.language || undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  }

  _formatTime(value) {
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat(this._hass?.language || undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(date);
  }

  _rail() {
    const aside = el("aside", "rail");
    const nav = el("nav");
    nav.setAttribute("aria-label", this._t("wheel_switcher"));
    const back = el("button", "rail-back");
    back.type = "button";
    back.appendChild(svg(ICON.back));
    back.appendChild(el("span", null, this._t("back")));
    back.addEventListener("click", () => this._backToOverview());
    nav.appendChild(back);
    nav.appendChild(el("div", "rail-title", this._t("wheel_switcher")));
    const list = el("ul");
    for (const wheel of this._snapshot.wheels) {
      const item = el("li");
      const button = el("button", "rail-wheel");
      button.type = "button";
      if (wheel.key === this._open) button.setAttribute("aria-current", "page");
      button.setAttribute(
        "aria-label",
        [
          wheel.name,
          wheel.area || this._t("detail_area_none"),
          this._t(wheel.availability),
        ].join(", "),
      );
      button.appendChild(this._statusDot(wheel.availability));
      const copy = el("span", "rail-copy");
      copy.appendChild(el("span", "rail-name", wheel.name));
      copy.appendChild(
        el(
          "span",
          "rail-area",
          [
            wheel.area || this._t("detail_area_none"),
            this._t(wheel.availability),
          ].join(" · "),
        ),
      );
      button.appendChild(copy);
      if (wheel.key === this._open) button.appendChild(svg(ICON.check, "rail-check"));
      button.addEventListener("click", () => this._openWheel(wheel.key));
      item.appendChild(button);
      list.appendChild(item);
    }
    nav.appendChild(list);
    aside.appendChild(nav);
    return aside;
  }

  _statusDot(state) {
    const dot = el("span", "dot");
    dot.dataset.state = state;
    dot.setAttribute("aria-hidden", "true");
    return dot;
  }

  _detailTop(wheel) {
    const top = el("div", "detail-top");
    const back = el("button", "back-button");
    back.id = "back-to-overview";
    back.type = "button";
    back.appendChild(svg(ICON.back));
    back.appendChild(el("span", null, this._t("back")));
    back.addEventListener("click", () => this._backToOverview());
    top.appendChild(back);

    const heading = el("div", "detail-heading");
    heading.appendChild(el("h2", null, wheel.name));
    const meta = [
      wheel.area || this._t("detail_area_none"),
      this._activityLabel(wheel),
    ].filter(Boolean);
    heading.appendChild(el("div", "detail-meta", meta.join(" · ")));
    top.appendChild(heading);
    return top;
  }

  _tabs(wheel) {
    const views = ["channels", "live", "diagnostics"];
    const tabs = el("div", "tabs");
    tabs.setAttribute("role", "tablist");
    tabs.setAttribute("aria-label", this._t("detail_views"));
    views.forEach((view, index) => {
      const tab = el("button", "tab", this._t(`tab_${view}`));
      tab.id = `tab-${wheel.key}-${view}`;
      tab.type = "button";
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-selected", String(this._view === view));
      tab.setAttribute("aria-controls", `panel-${wheel.key}-${view}`);
      tab.tabIndex = this._view === view ? 0 : -1;
      tab.addEventListener("click", () => this._setView(view));
      tab.addEventListener("keydown", (event) => {
        let next = null;
        if (event.key === "ArrowRight") next = (index + 1) % views.length;
        if (event.key === "ArrowLeft") {
          next = (index - 1 + views.length) % views.length;
        }
        if (event.key === "Home") next = 0;
        if (event.key === "End") next = views.length - 1;
        if (next === null) return;
        event.preventDefault();
        const all = tabs.querySelectorAll('[role="tab"]');
        all[next]?.focus();
      });
      tabs.appendChild(tab);
    });
    return tabs;
  }

  _sectionHead(title, body) {
    const head = el("div", "section-head");
    head.appendChild(el("h3", null, title));
    if (body) head.appendChild(el("p", null, body));
    return head;
  }

  _fact(label, value, state) {
    const row = el("div", "fact");
    row.appendChild(el("dt", null, label));
    const description = el("dd", null, value);
    if (state) description.dataset.state = state;
    row.appendChild(description);
    return row;
  }

  _closeEditor() {
    this._editingChannel = null;
    this._editorData = null;
    this._editorBinding = null;
    this._editorErrors = {};
    this._editorBusy = false;
    this._editorMessage = null;
    this._deleteConfirm = false;
  }

  _startEditor(channel) {
    this._editingChannel = channel.channel;
    this._editorBinding = channel.binding || null;
    this._editorData = {
      ...DEFAULT_BINDING,
      ...(channel.binding?.data || {}),
      scenes: [...(channel.binding?.data?.scenes || [])],
    };
    this._editorErrors = {};
    this._editorMessage = null;
    this._deleteConfirm = false;
    this._render();
  }

  _entityRecords(domains) {
    const allowed = new Set(domains);
    return Object.values(this._hass?.states || {})
      .filter((state) => allowed.has(state.entity_id.split(".", 1)[0]))
      .sort((left, right) => {
        const leftName =
          left.attributes?.friendly_name || left.entity_id;
        const rightName =
          right.attributes?.friendly_name || right.entity_id;
        return leftName.localeCompare(rightName);
      });
  }

  _fieldError(name) {
    const code = this._editorErrors[name];
    return code ? this._t(`validation_${code}`) : null;
  }

  _fieldShell(name, label, help, wide = false) {
    const wrap = el("div", "field");
    if (wide) wrap.dataset.wide = "true";
    const labelNode = el("label", null, label);
    labelNode.htmlFor = `binding-${this._open}-${this._editingChannel}-${name}`;
    wrap.appendChild(labelNode);
    if (help) wrap.appendChild(el("span", "field-help", help));
    return wrap;
  }

  _selectField(name, label, options, { optional = false, help, wide = false } = {}) {
    const wrap = this._fieldShell(name, label, help, wide);
    const select = el("select");
    select.id = `binding-${this._open}-${this._editingChannel}-${name}`;
    select.name = name;
    if (optional) {
      const empty = el("option", null, this._t("target_none"));
      empty.value = "";
      select.appendChild(empty);
    } else {
      select.required = true;
    }
    for (const option of options) {
      const item = el("option", null, option.label);
      item.value = option.value;
      select.appendChild(item);
    }
    select.value = this._editorData[name] ?? "";
    select.addEventListener("change", () => {
      this._editorData[name] = select.value || undefined;
      delete this._editorErrors[name];
      this._editorMessage = null;
      this._render();
    });
    wrap.appendChild(select);
    const error = this._fieldError(name);
    if (error) {
      const errorNode = el("span", "field-error", error);
      errorNode.id = `${select.id}-error`;
      select.setAttribute("aria-describedby", errorNode.id);
      wrap.appendChild(errorNode);
    }
    return wrap;
  }

  _entityField(name, label, domains, { optional = false, help, wide = false } = {}) {
    const current = this._editorData[name];
    const records = this._entityRecords(domains);
    const options = records.map((state) => ({
      value: state.entity_id,
      label: `${state.attributes?.friendly_name || state.entity_id} · ${state.entity_id}`,
    }));
    if (current && !options.some((option) => option.value === current)) {
      options.unshift({ value: current, label: current });
    }
    return this._selectField(name, label, options, { optional, help, wide });
  }

  _numberField(name, label, min, max, step, unit) {
    const wrap = this._fieldShell(
      name,
      label,
      unit ? this._t("field_unit", { unit }) : null,
    );
    const input = el("input");
    input.id = `binding-${this._open}-${this._editingChannel}-${name}`;
    input.name = name;
    input.type = "number";
    input.required = true;
    input.min = String(min);
    input.max = String(max);
    input.step = String(step);
    input.value = String(this._editorData[name] ?? "");
    input.addEventListener("input", () => {
      this._editorData[name] = Number(input.value);
      delete this._editorErrors[name];
      this._editorMessage = null;
    });
    wrap.appendChild(input);
    const error = this._fieldError(name);
    if (error) wrap.appendChild(el("span", "field-error", error));
    return wrap;
  }

  _scenesField() {
    const wrap = this._fieldShell(
      "scenes",
      this._t("field_scenes"),
      this._t("field_scenes_help"),
      true,
    );
    const select = el("select");
    select.id = `binding-${this._open}-${this._editingChannel}-scenes`;
    select.multiple = true;
    const selected = new Set(this._editorData.scenes || []);
    for (const state of this._entityRecords(["scene"])) {
      const option = el(
        "option",
        null,
        `${state.attributes?.friendly_name || state.entity_id} · ${state.entity_id}`,
      );
      option.value = state.entity_id;
      option.selected = selected.has(state.entity_id);
      select.appendChild(option);
    }
    select.addEventListener("change", () => {
      this._editorData.scenes = [...select.selectedOptions].map(
        (option) => option.value,
      );
      this._editorMessage = null;
    });
    wrap.appendChild(select);
    return wrap;
  }

  async _refreshSnapshot() {
    this._snapshot = await this._hass.callWS({ type: OVERVIEW });
  }

  async _saveBinding(wheel, channel) {
    if (this._editorBusy) return;
    this._editorBusy = true;
    this._editorErrors = {};
    this._editorMessage = null;
    this._render();
    try {
      const response = await this._hass.callWS({
        type: BINDING_SAVE,
        wheel: wheel.key,
        channel: channel.channel,
        data: this._editorData,
        binding_id: this._editorBinding?.id,
        expected_revision: this._editorBinding?.revision,
      });
      if (!response.ok) {
        if (response.error === "validation") {
          this._editorErrors = response.fields || {};
          this._editorMessage = this._t("binding_validation_failed");
        } else if (response.error === "conflict") {
          this._editorBinding = response.binding;
          this._editorData = {
            ...DEFAULT_BINDING,
            ...(response.binding?.data || {}),
          };
          this._editorMessage = this._t("binding_conflict");
        } else {
          this._editorMessage = this._t(`binding_error_${response.error}`);
        }
        return;
      }
      await this._refreshSnapshot();
      const refreshedWheel = this._snapshot.wheels.find(
        (item) => item.key === wheel.key,
      );
      const refreshedChannel = refreshedWheel?.channels.find(
        (item) => item.channel === channel.channel,
      );
      this._editorBinding = refreshedChannel?.binding || response.binding;
      this._editorData = {
        ...DEFAULT_BINDING,
        ...(this._editorBinding?.data || {}),
      };
      this._editorMessage = this._t("binding_saved");
    } catch (err) {
      this._editorMessage = this._t("binding_save_failed", {
        error: this._message(err),
      });
    } finally {
      this._editorBusy = false;
      this._render();
    }
  }

  async _deleteBinding() {
    if (this._editorBusy || !this._editorBinding) return;
    this._editorBusy = true;
    this._editorMessage = null;
    this._render();
    try {
      const response = await this._hass.callWS({
        type: BINDING_DELETE,
        binding_id: this._editorBinding.id,
        expected_revision: this._editorBinding.revision,
      });
      if (!response.ok) {
        if (response.error === "conflict") {
          this._editorBinding = response.binding;
          this._editorData = {
            ...DEFAULT_BINDING,
            ...(response.binding?.data || {}),
          };
          this._editorMessage = this._t("binding_conflict");
        } else {
          this._editorMessage = this._t(`binding_error_${response.error}`);
        }
        return;
      }
      await this._refreshSnapshot();
      this._closeEditor();
    } catch (err) {
      this._editorMessage = this._t("binding_delete_failed", {
        error: this._message(err),
      });
    } finally {
      this._editorBusy = false;
      this._render();
    }
  }

  _bindingForm(wheel, channel) {
    const form = el("form", "binding-form");
    form.setAttribute("aria-label", this._t("binding_editor_title", {
      channel: channel.channel,
    }));
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      this._saveBinding(wheel, channel);
    });

    if (this._editorMessage) {
      const message = el("p", "form-message", this._editorMessage);
      message.setAttribute("role", "status");
      form.appendChild(message);
    }

    const primary = el("div", "form-grid");
    primary.appendChild(
      this._selectField(
        "mode",
        this._t("field_mode"),
        Object.keys(MODE_DOMAINS).map((mode) => ({
          value: mode,
          label: this._t(`mode_${mode}`),
        })),
      ),
    );
    primary.appendChild(
      this._entityField(
        "target",
        this._t("field_target"),
        MODE_DOMAINS[this._editorData.mode] || [],
        { wide: true },
      ),
    );
    primary.appendChild(
      this._numberField("step", this._t("field_step"), 1, 25, 1, "%"),
    );
    primary.appendChild(
      this._numberField(
        "transition",
        this._t("field_transition"),
        0,
        5,
        0.1,
        "s",
      ),
    );
    primary.appendChild(
      this._selectField(
        "click_action",
        this._t("field_click_action"),
        ["toggle", "on", "off", "none"].map((action) => ({
          value: action,
          label: this._t(`click_${action}`),
        })),
      ),
    );
    primary.appendChild(
      this._entityField(
        "click_target",
        this._t("field_click_target"),
        ["light", "switch"],
        { optional: true },
      ),
    );
    primary.appendChild(
      this._selectField(
        "hold_action",
        this._t("field_hold_action"),
        ["toggle", "ramp", "none"].map((action) => ({
          value: action,
          label: this._t(`hold_${action}`),
        })),
      ),
    );
    if (this._editorData.hold_action === "toggle") {
      primary.appendChild(
        this._entityField(
          "hold_target",
          this._t("field_hold_target"),
          ["light", "switch"],
          { optional: true },
        ),
      );
    }
    primary.appendChild(this._scenesField());
    form.appendChild(primary);

    const advanced = el("details", "advanced");
    const summary = el("summary", null, this._t("advanced_options"));
    advanced.appendChild(summary);
    const advancedGrid = el("div", "form-grid");
    advancedGrid.appendChild(
      this._selectField(
        "button_response",
        this._t("field_button_response"),
        ["multi_press", "fast"].map((response) => ({
          value: response,
          label: this._t(`button_response_${response}`),
        })),
      ),
    );
    advancedGrid.appendChild(
      this._numberField(
        "acceleration",
        this._t("field_acceleration"),
        0,
        100,
        5,
        "%",
      ),
    );
    advancedGrid.appendChild(
      this._numberField(
        "min_brightness",
        this._t("field_min_brightness"),
        0,
        50,
        1,
        "%",
      ),
    );
    advancedGrid.appendChild(
      this._numberField(
        "max_brightness",
        this._t("field_max_brightness"),
        1,
        100,
        1,
        "%",
      ),
    );
    advancedGrid.appendChild(
      this._entityField(
        "double_press_target",
        this._t("field_double_target"),
        ["light", "switch"],
        { optional: true },
      ),
    );
    advancedGrid.appendChild(
      this._entityField(
        "triple_press_target",
        this._t("field_triple_target"),
        ["light", "switch"],
        { optional: true },
      ),
    );
    advanced.appendChild(advancedGrid);
    form.appendChild(advanced);

    const actions = el("div", "form-actions");
    const save = el("button", "action-button", this._t("save_binding"));
    save.type = "submit";
    save.dataset.primary = "true";
    save.disabled = this._editorBusy;
    actions.appendChild(save);
    const cancel = el("button", "action-button", this._t("cancel_edit"));
    cancel.type = "button";
    cancel.disabled = this._editorBusy;
    cancel.addEventListener("click", () => {
      this._closeEditor();
      this._render();
    });
    actions.appendChild(cancel);
    if (this._editorBinding) {
      const remove = el("button", "action-button", this._t("delete_binding"));
      remove.type = "button";
      remove.dataset.danger = "true";
      remove.disabled = this._editorBusy;
      remove.addEventListener("click", () => {
        this._deleteConfirm = true;
        this._render();
      });
      actions.appendChild(remove);
    }
    form.appendChild(actions);

    if (this._deleteConfirm) {
      const confirm = el("div", "delete-confirm");
      confirm.setAttribute("role", "alert");
      confirm.appendChild(el("span", null, this._t("delete_binding_confirm")));
      const deleteButton = el(
        "button",
        "action-button",
        this._t("delete_binding"),
      );
      deleteButton.type = "button";
      deleteButton.dataset.danger = "true";
      deleteButton.addEventListener("click", () => this._deleteBinding());
      confirm.appendChild(deleteButton);
      const keep = el("button", "action-button", this._t("keep_binding"));
      keep.type = "button";
      keep.addEventListener("click", () => {
        this._deleteConfirm = false;
        this._render();
      });
      confirm.appendChild(keep);
      form.appendChild(confirm);
    }
    return form;
  }

  _channelDetail(wheel, channel) {
    const configured = channel.profile !== null && channel.profile !== undefined;
    const missingTarget =
      channel.target_missing ||
      (channel.actions || []).some((action) => action.target_missing);
    const card = el("article", "channel-detail");
    card.dataset.state = missingTarget ? "warning" : configured ? "ready" : "empty";

    const head = el("div", "channel-detail-head");
    head.appendChild(
      el("span", "channel-detail-number", String(channel.channel)),
    );
    const copy = el("div", "channel-detail-copy");
    copy.appendChild(
      el(
        "div",
        "channel-detail-title",
        this._t("channel_title", { channel: channel.channel }),
      ),
    );
    let summary = this._t("not_configured");
    if (configured) {
      const target = channel.target_missing
        ? this._t("target_unavailable", {
            target: channel.target_label || this._t("target_none"),
          })
        : channel.target_label || this._t("target_none");
      summary = [
        channel.behaviour || channel.profile,
        target,
      ].filter(Boolean).join(" · ");
    }
    copy.appendChild(el("div", "channel-detail-summary", summary));
    head.appendChild(copy);

    card.appendChild(head);

    if (configured && (channel.actions || []).length) {
      const actions = el("ul", "channel-action-list");
      for (const action of channel.actions || []) {
        let value = action.action_label;
        if (action.target_label) {
          const target = action.target_missing
            ? this._t("target_unavailable", { target: action.target_label })
            : action.target_label;
          value = `${value} · ${target}`;
        }
        const item = el("li", "channel-action");
        if (action.target_missing) item.dataset.state = "warning";
        item.appendChild(el("span", "channel-action-label", action.gesture_label));
        item.appendChild(el("span", "channel-action-value", value));
        actions.appendChild(item);
      }
      card.appendChild(actions);
    }

    if (this._editingChannel === channel.channel) {
      card.appendChild(this._bindingForm(wheel, channel));
    } else {
      const footer = el("div", "channel-detail-footer");
      const edit = el(
        "button",
        "action-button",
        this._t(configured ? "edit_binding" : "add_binding"),
      );
      edit.type = "button";
      edit.addEventListener("click", () => this._startEditor(channel));
      footer.appendChild(edit);
      card.appendChild(footer);
    }
    return card;
  }

  _channelsView(wheel) {
    const wrap = el("div");
    wrap.appendChild(
      this._sectionHead(
        this._t("detail_channels_heading"),
        this._t("detail_channels_intro"),
      ),
    );
    const grid = el("div", "channel-grid");
    for (const channel of wheel.channels) {
      grid.appendChild(this._channelDetail(wheel, channel));
    }
    wrap.appendChild(grid);
    return wrap;
  }

  _gestureLabel(activity) {
    const channel = activity.channel ?? "?";
    if (activity.gesture === "rotate") {
      const direction = this._t(
        activity.direction === "down" ? "direction_down" : "direction_up",
      );
      return this._t("gesture_rotate", {
        channel,
        direction,
        delta: activity.notches ?? 0,
      });
    }
    if (activity.gesture === "press") {
      const key =
        activity.presses === 2
          ? "gesture_press_double"
          : activity.presses === 3
            ? "gesture_press_triple"
            : "gesture_press_single";
      return this._t(key, { channel });
    }
    if (activity.gesture === "hold") return this._t("gesture_hold", { channel });
    if (activity.gesture === "release") {
      return this._t("gesture_release", { channel });
    }
    return this._t("gesture_unknown", { channel });
  }

  _dispatchLabel(activity) {
    const labels = {
      accepted: ["success", "dispatch_accepted"],
      pending: ["unknown", "dispatch_pending"],
      failed: ["failed", "dispatch_failed"],
      skipped: ["failed", "dispatch_skipped"],
      not_configured: ["failed", "dispatch_not_configured"],
      completed: ["success", "dispatch_completed"],
      received: ["unknown", "dispatch_received"],
    };
    return (
      labels[activity.dispatch_status] ||
      (activity.dispatched === true
        ? ["success", "dispatch_accepted"]
        : activity.dispatched === false
          ? ["failed", "dispatch_failed"]
          : ["unknown", "dispatch_unknown"])
    );
  }

  _formatResult(result) {
    if (!result) return this._t("result_unavailable");
    if (result.before !== undefined && result.after !== undefined) {
      const labels = {
        brightness: "result_kind_brightness",
        color_temp: "result_kind_color_temperature",
        color: "result_kind_color",
        volume: "result_kind_volume",
        cover_position: "result_kind_position",
        temperature: "result_kind_temperature",
        fan_speed: "result_kind_fan_speed",
        number: "result_kind_value",
      };
      const label = this._t(labels[result.kind] || "result_kind_value");
      const unit = result.unit ? ` ${result.unit}` : "";
      return `${label} ${result.before} → ${result.after}${unit}`;
    }
    if (result.kind === "scene") {
      return this._t("result_scene", {
        position: result.position,
        total: result.total,
        target: result.target,
      });
    }
    if (result.kind === "entity_action") {
      return this._t("result_entity_action", {
        action: this._t(`service_${result.action}`),
        target: result.target,
      });
    }
    if (result.kind === "hold") return this._t("result_ramp_stopped");
    if (result.kind === "press" && result.action === "already_dispatched") {
      return this._t("result_fast_press_complete");
    }
    return JSON.stringify(result);
  }

  async _testBinding(wheel, channel, gesture, extra = {}) {
    if (this._testBusy) return;
    this._testBusy = true;
    this._testMessage = null;
    this._render();
    try {
      const response = await this._hass.callWS({
        type: BINDING_TEST,
        wheel: wheel.key,
        channel,
        gesture,
        ...extra,
      });
      if (!response.ok) {
        this._testMessage = this._t(`binding_error_${response.error}`);
      }
    } catch (err) {
      this._testMessage = this._t("binding_test_failed", {
        error: this._message(err),
      });
    } finally {
      this._testBusy = false;
      this._render();
    }
  }

  _testPanel(wheel) {
    const panel = el("details", "detail-card test-panel");
    panel.appendChild(el("summary", null, this._t("test_controls_heading")));
    panel.appendChild(el("p", null, this._t("test_controls_intro")));
    if (this._testMessage) {
      const message = el("p", "form-message", this._testMessage);
      message.setAttribute("role", "status");
      panel.appendChild(message);
    }
    for (const channel of wheel.channels.filter((item) => item.binding)) {
      const actions = el("div", "test-actions");
      actions.setAttribute(
        "aria-label",
        this._t("test_channel", { channel: channel.channel }),
      );
      const tests = [
        ["test_rotate_down", "rotate", { direction: "down", notches: 1 }],
        ["test_rotate_up", "rotate", { direction: "up", notches: 1 }],
        ["test_single", "press", { presses: 1 }],
        ["test_double", "press", { presses: 2 }],
        ["test_triple", "press", { presses: 3 }],
        ["test_hold", "hold", {}],
        ["test_release", "release", {}],
      ];
      actions.appendChild(
        el(
          "strong",
          null,
          this._t("channel_title", { channel: channel.channel }),
        ),
      );
      for (const [label, gesture, extra] of tests) {
        const button = el("button", "action-button", this._t(label));
        button.type = "button";
        button.disabled = this._testBusy;
        button.addEventListener("click", () =>
          this._testBinding(wheel, channel.channel, gesture, extra),
        );
        actions.appendChild(button);
      }
      panel.appendChild(actions);
    }
    if (!wheel.channels.some((item) => item.binding)) {
      panel.appendChild(el("p", null, this._t("test_no_bindings")));
    }
    return panel;
  }

  _liveChannels(wheel) {
    const card = el("section", "detail-card live-channels");
    card.appendChild(el("h4", null, this._t("live_channels_heading")));
    for (const channel of wheel.channels) {
      const row = el("div", "live-channel");
      row.appendChild(
        el("span", "channel-detail-number", String(channel.channel)),
      );
      const copy = el("div", "live-channel-copy");
      copy.appendChild(
        el(
          "div",
          "live-channel-title",
          this._t("channel_title", { channel: channel.channel }),
        ),
      );
      const configured =
        channel.profile !== null && channel.profile !== undefined;
      const target = channel.target_missing
        ? this._t("target_unavailable", {
            target: channel.target_label || this._t("target_none"),
          })
        : channel.target_label;
      copy.appendChild(
        el(
          "div",
          "live-channel-summary",
          configured
            ? [channel.behaviour || channel.profile, target]
                .filter(Boolean)
                .join(" · ")
            : this._t("not_configured"),
        ),
      );
      row.appendChild(copy);
      card.appendChild(row);
    }
    return card;
  }

  _liveView(wheel) {
    const wrap = el("div");
    wrap.appendChild(this._sectionHead(this._t("tab_live")));
    if (this._activityError) wrap.appendChild(this._banner(this._t("live_error")));

    const layout = el("div", "live-layout");
    const output = el("section", "detail-card live-output");
    output.setAttribute("aria-live", "polite");
    output.setAttribute("aria-atomic", "true");
    const listening = el("div", "live-status");
    listening.appendChild(this._statusDot(this._activityError ? "unknown" : "success"));
    listening.appendChild(
      el(
        "span",
        null,
        this._t(this._activityError ? "live_stopped" : "live_listening"),
      ),
    );
    output.appendChild(listening);

    const latest = this._activities[0];
    if (!latest) {
      output.appendChild(el("div", "waiting-title", this._t("live_waiting_title")));
      output.appendChild(
        el("div", "live-explanation", this._t("live_waiting_body")),
      );
    } else {
      const result = this._formatResult(latest.result);
      output.appendChild(el("div", "live-result", result));
      if (latest.result === null || latest.result === undefined) {
        output.appendChild(
          el(
            "div",
            "live-explanation",
            this._t("result_unavailable_detail"),
          ),
        );
      }
      const [dispatchState, dispatchKey] = this._dispatchLabel(latest);
      const dispatch = el("div", "dispatch");
      dispatch.appendChild(this._statusDot(dispatchState));
      dispatch.appendChild(el("span", null, this._t(dispatchKey)));
      output.appendChild(dispatch);
      output.appendChild(el("div", "gesture-caption", this._gestureLabel(latest)));
      if (latest.source === "panel_test") {
        output.appendChild(
          el("div", "gesture-caption", this._t("source_panel_test")),
        );
      }
    }
    layout.appendChild(output);

    const side = el("div", "live-side");
    side.appendChild(this._liveChannels(wheel));
    if (this._activities.length) {
      const recent = el("section", "detail-card recent");
      recent.appendChild(el("h4", null, this._t("live_recent")));
      const list = el("ol");
      for (const activity of this._activities) {
        const item = el("li");
        item.appendChild(el("span", null, this._gestureLabel(activity)));
        const time = el("time", null, this._formatTime(activity.received_at));
        time.dateTime = activity.received_at;
        item.appendChild(time);
        list.appendChild(item);
      }
      recent.appendChild(list);
      side.appendChild(recent);
    }
    layout.appendChild(side);
    layout.appendChild(this._testPanel(wheel));
    wrap.appendChild(layout);
    return wrap;
  }

  _sourceLabel(source) {
    if (source === "core_matter_client") return this._t("source_core");
    if (source === "dedicated_websocket") return this._t("source_fallback");
    if (source === "unloaded") return this._t("source_unloaded");
    return source;
  }

  _recoveryKey(wheel) {
    if (!this._snapshot.matter_connected) return "recovery_matter";
    if (wheel.availability === "unavailable") return "recovery_unavailable";
    if (wheel.availability === "unknown" || !wheel.linked_to_matter) {
      return "recovery_unknown";
    }
    return "recovery_ok";
  }

  _diagnosticsView(wheel) {
    const wrap = el("div");
    wrap.appendChild(
      this._sectionHead(
        this._t("tab_diagnostics"),
        this._t("diagnostics_intro"),
      ),
    );
    const grid = el("div", "diagnostic-grid");
    const recoveryKey = this._recoveryKey(wheel);
    const healthy = recoveryKey === "recovery_ok";

    const health = el("section", "detail-card health-hero");
    health.appendChild(this._statusDot(healthy ? "success" : "unknown"));
    const healthCopy = el("div", "health-copy");
    healthCopy.appendChild(
      el(
        "div",
        "health-title",
        this._t(
          healthy ? "diagnostic_health_ok" : "diagnostic_health_attention",
        ),
      ),
    );
    healthCopy.appendChild(
      el(
        "div",
        "health-body",
        this._t(healthy ? "diagnostic_health_ok_body" : recoveryKey),
      ),
    );
    health.appendChild(healthCopy);
    grid.appendChild(health);

    const status = el("section", "detail-card");
    status.appendChild(
      el("h4", null, this._t("diagnostic_connection_heading")),
    );
    const facts = el("dl", "facts");
    facts.appendChild(
      this._fact(
        this._t("diagnostic_availability"),
        this._t(wheel.availability),
      ),
    );
    facts.appendChild(
      this._fact(
        this._t("diagnostic_matter"),
        this._t(
          this._snapshot.matter_connected ? "matter_connected" : "matter_offline",
        ),
      ),
    );
    facts.appendChild(
      this._fact(
        this._t("diagnostic_source"),
        this._sourceLabel(this._snapshot.event_source),
      ),
    );
    facts.appendChild(
      this._fact(
        this._t("diagnostic_link"),
        this._t(
          wheel.linked_to_matter ? "diagnostic_linked" : "diagnostic_not_linked",
        ),
      ),
    );
    status.appendChild(facts);
    grid.appendChild(status);

    const activity = el("section", "detail-card");
    activity.appendChild(
      el("h4", null, this._t("diagnostic_activity_heading")),
    );
    const activityFacts = el("dl", "facts");
    activityFacts.appendChild(
      this._fact(
        this._t("detail_last_activity"),
        wheel.last_activity
          ? this._formatDate(wheel.last_activity)
          : this._t("no_activity"),
      ),
    );
    activityFacts.appendChild(
      this._fact(
        this._t("detail_last_channel"),
        wheel.last_active_channel ?? this._t("detail_no_last_channel"),
      ),
    );
    activity.appendChild(activityFacts);
    grid.appendChild(activity);

    if (!healthy) {
      const recovery = el("section", "detail-card recovery");
      recovery.appendChild(el("h4", null, this._t("recovery_heading")));
      recovery.appendChild(el("p", null, this._t(recoveryKey)));
      grid.appendChild(recovery);
    }

    const technical = el("details", "detail-card technical-details");
    technical.appendChild(
      el("summary", null, this._t("diagnostic_technical_details")),
    );
    const technicalFacts = el("dl", "facts");
    technicalFacts.appendChild(
      this._fact(
        this._t("diagnostic_contract"),
        String(this._snapshot.contract_version),
      ),
    );
    technical.appendChild(technicalFacts);
    grid.appendChild(technical);

    wrap.appendChild(grid);
    return wrap;
  }

  _detailPanel(wheel) {
    const panel = el("section", "tab-panel");
    panel.id = `panel-${wheel.key}-${this._view}`;
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", `tab-${wheel.key}-${this._view}`);
    if (this._view === "live") panel.appendChild(this._liveView(wheel));
    else if (this._view === "diagnostics") {
      panel.appendChild(this._diagnosticsView(wheel));
    } else panel.appendChild(this._channelsView(wheel));
    return panel;
  }

  _detail(wheel) {
    const outer = el("div");
    if (!this._snapshot.matter_connected) {
      outer.appendChild(this._banner(this._t("banner_matter_offline")));
    } else if (this._error) {
      outer.appendChild(this._banner(this._t("banner_updates_stopped")));
    }

    const shell = el("div", "detail-shell");
    shell.appendChild(this._rail());
    const pane = el("div", "detail-pane");
    pane.appendChild(this._detailTop(wheel));
    pane.appendChild(this._tabs(wheel));
    pane.appendChild(this._detailPanel(wheel));
    shell.appendChild(pane);
    outer.appendChild(shell);
    return outer;
  }

  _missingWheel() {
    const wrap = el("div");
    wrap.appendChild(
      this._placeholder(
        this._t("wheel_missing_title"),
        this._t("wheel_missing_body"),
        false,
      ),
    );
    const row = el("div", "placeholder");
    const back = el("button");
    back.type = "button";
    back.appendChild(svg(ICON.back));
    back.appendChild(el("span", null, this._t("back")));
    back.addEventListener("click", () => this._backToOverview());
    row.appendChild(back);
    wrap.appendChild(row);
    return wrap;
  }

  _placeholder(title, body, retry) {
    const wrap = el("div", "placeholder");
    wrap.appendChild(el("div", "title", title));
    wrap.appendChild(el("div", null, body));
    if (retry) {
      const button = el("button");
      button.type = "button";
      button.appendChild(svg(ICON.refresh));
      button.appendChild(el("span", null, this._t("retry")));
      button.addEventListener("click", () => this._retry());
      wrap.appendChild(button);
    }
    return wrap;
  }

  _body() {
    if (this._error && !this._snapshot) {
      return this._placeholder(this._t("error_title"), this._error, true);
    }
    if (!this._snapshot) {
      const grid = el("div", "grid");
      for (let i = 0; i < 2; i += 1) grid.appendChild(el("div", "skeleton"));
      return grid;
    }
    if (this._open) {
      const wheel = this._snapshot.wheels.find((item) => item.key === this._open);
      if (!wheel) return this._missingWheel();
      return this._detail(wheel);
    }
    if (!this._snapshot.wheels.length) {
      return this._placeholder(
        this._t("empty_title"),
        this._t(
          this._snapshot.matter_connected ? "empty_connected" : "empty_offline",
        ),
        true,
      );
    }

    const wrap = el("div", "overview");
    if (!this._snapshot.matter_connected) {
      wrap.appendChild(this._banner(this._t("banner_matter_offline")));
    } else if (this._error) {
      wrap.appendChild(this._banner(this._t("banner_updates_stopped")));
    }
    const missing = this._snapshot.wheels.filter((wheel) =>
      wheel.channels.some((channel) => channel.target_missing),
    );
    if (missing.length) {
      wrap.appendChild(
        this._banner(
          this._t("banner_target_missing", { count: missing.length }),
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
    const focused = this.shadowRoot.activeElement?.id || null;
    const style = document.createElement("style");
    style.textContent = STYLES;
    const main = el("main");
    main.appendChild(this._body());
    this.shadowRoot.replaceChildren(style, this._header(), main);
    if (focused) this.shadowRoot.getElementById(focused)?.focus({ preventScroll: true });
  }
}

if (!customElements.get("ikea-bilresa-panel")) {
  customElements.define("ikea-bilresa-panel", IkeaBilresaPanel);
}
