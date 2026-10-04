/**
 * BILRESA panel — device overview, live activity and binding editor.
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
const SETTINGS_SAVE = "ikea_bilresa/settings/save";
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
  step_curve: "linear",
  acceleration: 0,
  min_brightness: 1,
  max_brightness: 100,
  transition: 1,
  click_action: "toggle",
  button_response: "multi_press",
  hold_action: "toggle",
  scenes: [],
};

const DEFAULT_BUTTON_BINDING = {
  click_action: "toggle",
  button_response: "multi_press",
  hold_action: "toggle",
  ramp_direction: "alternate",
};

// The server sends these in the panel config (panel_schema.py), from the same
// table it validates against. This copy only serves a backend older than that.
const FALLBACK_SCHEMA = {
  binding_numbers: {
    step: { min: 1, max: 25, step: 1, unit: "%" },
    acceleration: { min: 0, max: 100, step: 5, unit: "%" },
    min_brightness: { min: 0, max: 50, step: 1, unit: "%" },
    max_brightness: { min: 1, max: 100, step: 1, unit: "%" },
    transition: { min: 0, max: 5, step: 0.1, unit: "s" },
  },
  settings_numbers: {
    step: { min: 1, max: 25, step: 1, unit: null },
    acceleration: { min: 0, max: 100, step: 5, unit: "%" },
  },
  mode_domains: MODE_DOMAINS,
  press_target_domains: ["light", "switch"],
  ramp_target_domains: ["light"],
};

// Material Design Icons remain the standard chrome. Product identity and
// gestures use the separately approved BILRESA / Material Rounded geometry.
const ICON = {
  menu: "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z",
  chevron: "M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",
  back: "M20,11H7.83L13.42,5.41L12,4L4,12L12,20L13.42,18.59L7.83,13H20V11Z",
  check: "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
  alert:
    "M13,13H11V7H13M13,17H11V15H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z",
  arrowUp: "M13,20H11V8L5.5,13.5L4.08,12.08L12,4.16L19.92,12.08L18.5,13.5L13,8V20Z",
  arrowDown:
    "M11,4H13V16L18.5,10.5L19.92,11.92L12,19.84L4.08,11.92L5.5,10.5L11,16V4Z",
  remove:
    "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
  refresh:
    "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z",
};

const BILRESA_ICON = Object.freeze({
  viewBox: "0 0 24 24",
  path: `M11.3 1.4
    C15.05 1.4 17.65 4.18 17.65 7.9
    V15.5
    C17.65 19.72 15.02 22.35 11.3 22.35
    C7.58 22.35 4.95 19.72 4.95 15.5
    V7.9
    C4.95 4.18 7.55 1.4 11.3 1.4Z
    M11.3 2.65
    C8.27 2.65 6.2 4.95 6.2 7.98
    V15.38
    C6.2 18.85 8.38 21.1 11.3 21.1
    C14.22 21.1 16.4 18.85 16.4 15.38
    V7.98
    C16.4 4.95 14.33 2.65 11.3 2.65Z
    M11 2.1
    A5.2 5.8 0 1 1 11 13.7
    A5.2 5.8 0 1 1 11 2.1Z
    M11 3.2
    A4.1 4.7 0 1 0 11 12.6
    A4.1 4.7 0 1 0 11 3.2Z
    M10.23 16.08
    A0.58 0.58 0 1 1 9.07 16.08
    A0.58 0.58 0 1 1 10.23 16.08Z
    M11.63 16.08
    A0.58 0.58 0 1 1 10.47 16.08
    A0.58 0.58 0 1 1 11.63 16.08Z
    M13.03 16.08
    A0.58 0.58 0 1 1 11.87 16.08
    A0.58 0.58 0 1 1 13.03 16.08Z`,
  secondaryPath: `M13.05 1.35
    C16.45 1.85 18.65 4.55 18.65 8.15
    V15.48
    C18.65 19.28 16.3 21.9 12.95 22.55
    L12.68 21.22
    C14.95 20.75 16.42 18.62 16.42 15.36
    V8
    C16.42 5.1 15.2 2.75 13.05 1.35Z`,
});

const BILRESA_DUAL_BUTTON_ICON = Object.freeze({
  viewBox: "0 0 24 24",
  path: `M11.3 1.4 C15.05 1.4 17.65 4.18 17.65 7.9 V15.5
    C17.65 19.72 15.02 22.35 11.3 22.35 C7.58 22.35 4.95 19.72
    4.95 15.5 V7.9 C4.95 4.18 7.55 1.4 11.3 1.4Z M11.3 2.65
    C8.27 2.65 6.2 4.95 6.2 7.98 V15.38 C6.2 18.85 8.38 21.1
    11.3 21.1 C14.22 21.1 16.4 18.85 16.4 15.38 V7.98 C16.4
    4.95 14.33 2.65 11.3 2.65Z M11.3 4.35 A1.8 1.9 0 1 1
    11.3 8.15 A1.8 1.9 0 1 1 11.3 4.35Z M11.3 5.05 A1.13 1.2
    0 1 0 11.3 7.45 A1.13 1.2 0 1 0 11.3 5.05Z M11.3 12.23
    A0.42 0.42 0 1 1 11.3 13.07 A0.42 0.42 0 1 1 11.3 12.23Z
    M11.3 17.05 A1.23 1.37 0 1 1 11.3 19.79 A1.23 1.37 0 1 1
    11.3 17.05Z M11.3 17.69 A0.64 0.73 0 1 0 11.3 19.15 A0.64
    0.73 0 1 0 11.3 17.69Z`,
  secondaryPath: `M13.05 1.35 C16.45 1.85 18.65 4.55 18.65 8.15
    V15.48 C18.65 19.28 16.3 21.9 12.95 22.55 L12.68 21.22
    C14.95 20.75 16.42 18.62 16.42 15.36 V8 C16.42 5.1 15.2
    2.75 13.05 1.35Z`,
});

const MATERIAL_VIEWBOX = "0 -960 960 960";

// Official Material Symbols Rounded paths. Counts are part of the glyph, so a
// triple press cannot be mistaken for a normal press when labels are skimmed.
const GESTURE_ICON = {
  rotate_left: {
    viewBox: MATERIAL_VIEWBOX,
    path: "M170-478q-21 0-33.5-15t-7.5-35q6-25 16-48t23-45q10-17 29.5-19t34.5 12q9 9 11 22.5t-5 24.5q-10 17-17.5 35.5T208-508q-3 13-14.5 21.5T170-478Zm268 348q0 22-15 34t-35 7q-24-7-47-16.5T295-128q-17-10-19-29.5t12-34.5q9-9 22.5-11t24.5 5q17 10 35.5 17.5T408-168q13 3 21.5 14.5T438-130ZM232-248q-15 14-34.5 12T168-255q-13-23-22.5-46T129-348q-5-20 7-35t34-15q13 0 24 8.5t14 21.5q5 19 12.5 37.5T238-295q7 11 5 25t-11 22ZM567-90q-20 5-34.5-7T518-130q0-13 8.5-24t21.5-14q92-24 151-98.5T758-438q0-117-81.5-198.5T478-718h-8l36 36q11 11 11 28t-11 28q-11 11-28 11t-28-11L346-730q-6-6-8.5-13t-2.5-15q0-8 2.5-15t8.5-13l103-104q12-11 29-11t28 11q12 12 12 29t-11 28l-35 35h6q150 0 255 105t105 255q0 124-76 220T567-90Z",
  },
  rotate_right: {
    viewBox: MATERIAL_VIEWBOX,
    path: "M790-478q-12 0-23.5-8.5T752-508q-5-19-12.5-37.5T722-581q-7-11-5-24.5t11-22.5q15-14 34.5-12t29.5 19q13 22 23 45t16 48q5 20-7.5 35T790-478ZM522-130q0-12 8.5-23.5T552-168q19-5 37.5-12.5T625-198q11-7 24.5-5t22.5 11q14 15 12 34.5T665-128q-23 13-46 22.5T572-89q-20 5-35-7t-15-34Zm206-118q-9-8-11-22t5-25q10-17 17.5-35.5T752-368q3-13 14-21.5t24-8.5q22 0 34 15t7 35q-7 24-16.5 47T792-255q-10 17-29.5 19T728-248ZM393-90q-119-32-195-128t-76-220q0-150 105-255t255-105h6l-35-35q-11-11-11-28t12-29q11-11 28-11t29 11l103 104q6 6 8.5 13t2.5 15q0 8-2.5 15t-8.5 13L510-626q-11 11-28 11t-28-11q-11-11-11-28t11-28l36-36h-8q-117 0-198.5 81.5T202-438q0 97 59 171.5T412-168q13 3 21.5 14t8.5 24q0 21-14.5 33T393-90Z",
  },
  short_press: {
    viewBox: MATERIAL_VIEWBOX,
    path: "M419-80q-28 0-52.5-12T325-126L124-381q-8-9-7-21.5t9-20.5q20-21 48-25t52 11l74 45v-328q0-17 11.5-28.5T340-760q17 0 29 11.5t12 28.5v400q0 23-20.5 34.5T320-286l-36-22 104 133q6 7 14 11t17 4h221q33 0 56.5-23.5T720-240v-160q0-17-11.5-28.5T680-440H501q-17 0-28.5-11.5T461-480q0-17 11.5-28.5T501-520h179q50 0 85 35t35 85v160q0 66-47 113T640-80H419Zm83-260Zm-23-260q-17 0-28.5-11.5T439-640q0-2 5-20 8-14 12-28.5t4-31.5q0-50-35-85t-85-35q-50 0-85 35t-35 85q0 17 4 31.5t12 28.5q3 5 4 10t1 10q0 17-11 28.5T202-600q-11 0-20.5-6T167-621q-13-22-20-47t-7-52q0-83 58.5-141.5T340-920q83 0 141.5 58.5T540-720q0 27-7 52t-20 47q-5 9-14 15t-20 6Z",
  },
  double_press: {
    viewBox: MATERIAL_VIEWBOX,
    path: "M638-600q-17 0-28-11.5T599-640q0-4 5-20 8-14 12-29t4-31q0-20-5.5-39.5T595-794q-6-7-10-15.5t-4-17.5q0-15 10.5-26t25.5-11q13 0 23.5 6.5T659-841q22 25 31.5 56.5T700-720q0 26-6.5 51.5T673-620q-5 9-14.5 14.5T638-600ZM419-80q-28 0-52.5-12T325-126L124-381q-8-9-7-21.5t9-20.5q20-21 48-25t52 11l74 45v-328q0-17 11.5-28.5T340-760q17 0 29 11.5t12 28.5v400q0 23-20.5 34.5T320-286l-36-22 104 133q6 7 14 11t17 4h221q33 0 56.5-23.5T720-240v-160q0-17-11.5-28.5T680-440H501q-17 0-28.5-11.5T461-480q0-17 11.5-28.5T501-520h179q50 0 85 35t35 85v160q0 66-47 113T640-80H419Zm83-260Zm-23-260q-17 0-28.5-11.5T439-640q0-2 5-20 8-14 12-28.5t4-31.5q0-50-35-85t-85-35q-50 0-85 35t-35 85q0 17 4 31.5t12 28.5q3 5 4 10t1 10q0 17-11 28.5T202-600q-11 0-20.5-6T167-621q-13-22-20-47t-7-52q0-83 58.5-141.5T340-920q83 0 141.5 58.5T540-720q0 27-7 52t-20 47q-5 9-14 15t-20 6Z",
  },
  triple_press: {
    viewBox: MATERIAL_VIEWBOX,
    path: "M798-600q-17 0-28-11.5T759-640q0-4 5-20 8-14 12-29t4-31q0-20-5.5-39.5T755-794q-6-7-10-15.5t-4-17.5q0-15 10.5-26t25.5-11q13 0 23.5 6.5T819-841q22 25 31.5 56.5T860-720q0 26-6.5 51.5T833-620q-5 9-14.5 14.5T798-600Zm-160 0q-17 0-28-11.5T599-640q0-4 5-20 8-14 12-29t4-31q0-20-5.5-39.5T595-794q-6-7-10-15.5t-4-17.5q0-15 10.5-26t25.5-11q13 0 23.5 6.5T659-841q22 25 31.5 56.5T700-720q0 26-6.5 51.5T673-620q-5 9-14.5 14.5T638-600ZM419-80q-28 0-52.5-12T325-126L124-381q-8-9-7-21.5t9-20.5q20-21 48-25t52 11l74 45v-328q0-17 11.5-28.5T340-760q17 0 29 11.5t12 28.5v400q0 23-20.5 34.5T320-286l-36-22 104 133q6 7 14 11t17 4h221q33 0 56.5-23.5T720-240v-160q0-17-11.5-28.5T680-440H501q-17 0-28.5-11.5T461-480q0-17 11.5-28.5T501-520h179q50 0 85 35t35 85v160q0 66-47 113T640-80H419Zm83-260Zm-23-260q-17 0-28.5-11.5T439-640q0-2 5-20 8-14 12-28.5t4-31.5q0-50-35-85t-85-35q-50 0-85 35t-35 85q0 17 4 31.5t12 28.5q3 5 4 10t1 10q0 17-11 28.5T202-600q-11 0-20.5-6T167-621q-13-22-20-47t-7-52q0-83 58.5-141.5T340-920q83 0 141.5 58.5T540-720q0 27-7 52t-20 47q-5 9-14 15t-20 6Z",
  },
  hold: {
    viewBox: MATERIAL_VIEWBOX,
    path: "M419-80q-28 0-52.5-12T325-126L124-381q-8-9-7-21.5t9-20.5q20-21 48-25t52 11l74 45v-328q0-17 11.5-28.5T340-760q17 0 29 11.5t12 28.5v400q0 23-20.5 34.5T320-286l-36-22 104 133q6 7 14 11t17 4h221q33 0 56.5-23.5T720-240v-160q0-17-11.5-28.5T680-440H501q-17 0-28.5-11.5T461-480q0-17 11.5-28.5T501-520h179q50 0 85 35t35 85v160q0 66-47 113T640-80H419Zm83-260ZM340-820q-42 0-71 29t-29 71v136q0 12-11 17.5t-20-2.5q-32-28-50.5-67T140-720q0-83 58.5-141.5T340-920q83 0 141.5 58.5T540-720q0 45-18 83.5T472-570q-9 8-20 3t-11-18v-135q0-42-30-71t-71-29Z",
  },
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
    --_space-10: var(--ha-space-10, 40px);
    --_font: var(--ha-font-family-body, Roboto, Noto, sans-serif);
    --_fast: var(--ha-animation-duration-fast, 120ms);
    --_ease-out: cubic-bezier(0.16, 1, 0.3, 1);
    --_rail-width: 256px;
    --_overview-max: 1120px;
    /* The detail needs the same ceiling as the overview. Without it a 1650px
       window drags a fact's label and value ~600px apart. */
    --_detail-max: 1100px;
    /* The icon colour clears the 3:1 non-text bar where a word would not. */
    --_accent: var(--state-icon-color, #44739e);

    /* A theme may inset the whole panel (padding on the element that hosts
       it). Measured in _fitFrame, so the header sticks where it already sits
       instead of travelling across the inset first. */
    --_frame-start: 0px;
    --_frame-end: 0px;
    --_frame-bg: var(--_bg);
    --_top: calc(56px + env(safe-area-inset-top, 0px) + var(--_frame-start));
    min-block-size: calc(100vh - var(--_frame-start) - var(--_frame-end));
    min-block-size: calc(100dvh - var(--_frame-start) - var(--_frame-end));
    background: var(--_bg);
    color: var(--_ink);
    font-family: var(--_font);
  }

  *, *::before, *::after { box-sizing: border-box; }

  /* The safe-area inset is added to the 56px bar. A border-box header would
     consume the inset and put the exit control under an iPhone notch. */
  header {
    position: sticky;
    inset-block-start: var(--_frame-start);
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
  /* Covers the theme's inset above the bar, or the page would scroll through
     that strip. Zero height when the panel is not inset. */
  header::before {
    content: "";
    position: absolute;
    inset-inline: 0;
    inset-block-end: 100%;
    block-size: var(--_frame-start);
    background: var(--_frame-bg);
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
    padding-block: var(--_space-6) max(var(--_space-6), env(safe-area-inset-bottom, 0px));
    padding-inline:
      max(var(--_space-6), env(safe-area-inset-left, 0px))
      max(var(--_space-6), env(safe-area-inset-right, 0px));
  }
  /* The detail's rail is a wall flush with the viewport edge, so the page frame
     moves inside it, onto .detail-pane. */
  main[data-view="detail"] { padding: 0; }
  @media (max-width: 600px) {
    main {
      padding-inline:
        max(var(--_space-4), env(safe-area-inset-left, 0px))
        max(var(--_space-4), env(safe-area-inset-right, 0px));
    }
  }

  .overview-head { margin-block-end: var(--_space-6); }
  .overview-head h1 {
    margin: 0;
    font-size: var(--ha-font-size-3xl, 30px);
    font-weight: var(--ha-font-weight-normal, 400);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  .summary {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--_space-3) var(--_space-5);
    margin-block-start: var(--_space-4);
    font-size: var(--ha-font-size-m, 14px);
  }
  .summary-item {
    display: inline-flex;
    align-items: center;
    gap: var(--_space-2);
    color: var(--_ink);
    white-space: nowrap;
  }

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
    transition: border-color var(--_fast) var(--_ease-out);
  }
  /* One signal per element. The old rule swung the hairline to full ink and
     shifted the surface at the same time, which reads as a flash. */
  @media (hover: hover) {
    .wheel:hover { border-color: var(--_accent); }
  }

  .wheel-head {
    display: flex;
    align-items: center;
    gap: var(--_space-3);
    min-block-size: 88px;
    padding: var(--_space-5) var(--_space-6);
  }
  .wheel-names { min-inline-size: 0; }
  /* The device glyph. --state-icon-color is HA's own entity-icon colour and
     clears the 3:1 non-text bar; an icon may carry it where a word may not. */
  /* The BILRESA glyph draws with currentColor (outline + dots), so it is
     coloured via the color property, not fill. */
  .device-glyph {
    flex: 0 0 auto;
    inline-size: 32px;
    block-size: 32px;
    color: var(--_accent);
    fill: currentColor;
  }
  /* Home Assistant's own sidebar marks its active entry with an accent icon and
     heavier text, not with a tint alone: the selected tint measures only
     1.22:1 against the rail in both default themes, so on its own it is a
     colour-only signal too faint to carry the state. The glyph may take the
     accent where a word may not — it is non-text, and clears the 3:1 bar. */
  .rail-glyph {
    flex: 0 0 auto;
    inline-size: 26px;
    block-size: 26px;
    color: var(--_ink-dim);
    fill: currentColor;
    transition: color var(--_fast) var(--_ease-out);
  }
  .rail-wheel[aria-current="page"] .rail-glyph { color: var(--_accent); }
  .device-glyph .secondary-path,
  .rail-glyph .secondary-path { opacity: 0.32; }
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
  /* Dimmed, not italic: HA never italicises a state, and an italic label is a
     reliable generated-UI tell. --_ink-dim clears AA; --disabled-text-color
     does not (2.8:1) and must not be used to say "empty". */
  .channel[data-state="empty"] .channel-behaviour { color: var(--_ink-dim); }
  .channel-warn,
  .wheel-open {
    flex: 0 0 auto;
    inline-size: 20px;
    block-size: 20px;
    fill: var(--_ink);
  }
  .channel-warn { fill: var(--error-color, var(--_ink)); }

  .detail-shell {
    display: grid;
    grid-template-columns: var(--_rail-width) minmax(0, 1fr);
    align-items: start;
  }
  /* The rail is a wall of the page, not a card floating on it: one hairline
     against the content, no radius, flush with the header. */
  .rail {
    position: sticky;
    inset-block-start: var(--_top);
    block-size: calc(100dvh - var(--_top) - var(--_frame-end));
    overflow: auto;
    padding: var(--_space-4) var(--_space-3)
      max(var(--_space-4), env(safe-area-inset-bottom, 0px));
    border-inline-end: 1px solid var(--_divider);
    background: var(--_card);
  }
  .rail-back {
    inline-size: fit-content;
    min-block-size: 44px;
    display: inline-flex;
    align-items: center;
    gap: var(--_space-2);
    padding-inline: var(--_space-2);
    border: 0;
    border-radius: var(--ha-border-radius-md, 8px);
    background: transparent;
    color: var(--_ink);
    text-align: start;
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    cursor: pointer;
  }
  .rail-back svg {
    inline-size: 20px;
    block-size: 20px;
    fill: currentColor;
  }
  .rail ul {
    margin: var(--_space-6) 0 0;
    padding: 0;
    list-style: none;
  }
  .rail li + li { margin-block-start: var(--_space-1); }
  /* Exactly three columns for exactly three children. The old rule declared
     three and rendered four, so the dot took the 1fr track, the name was pushed
     flush right, and the tick wrapped onto a second row. */
  .rail-wheel {
    inline-size: 100%;
    min-block-size: 56px;
    display: grid;
    grid-template-columns: 26px minmax(0, 1fr) 8px;
    align-items: center;
    gap: var(--_space-3);
    padding: var(--_space-2) var(--_space-3);
    border: 0;
    border-radius: var(--ha-border-radius-md, 8px);
    background: transparent;
    color: var(--_ink);
    text-align: start;
    cursor: pointer;
    transition: background-color var(--_fast) var(--_ease-out);
  }
  .rail-wheel[aria-current="page"] {
    background: var(--_selected);
  }
  .rail-copy { min-inline-size: 0; }
  .rail-name,
  .rail-area {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .rail-name {
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-normal, 400);
  }
  .rail-wheel[aria-current="page"] .rail-name {
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .rail-area {
    margin-block-start: 1px;
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-s, 12px);
    font-weight: var(--ha-font-weight-normal, 400);
  }
  .rail-wheel[aria-current="page"] .rail-area { color: var(--_ink); }

  .detail-pane {
    min-inline-size: 0;
    container-type: inline-size;
    padding: var(--_space-6) var(--_space-8)
      max(var(--_space-10), env(safe-area-inset-bottom, 0px)) var(--_space-6);
  }
  .detail-inner { inline-size: min(100%, var(--_detail-max)); }
  .detail-top {
    display: flex;
    align-items: flex-start;
    gap: var(--_space-4);
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
  .detail-glyph {
    flex: 0 0 auto;
    inline-size: 48px;
    block-size: 48px;
    color: var(--_accent);
    fill: currentColor;
  }
  .detail-heading { min-inline-size: 0; flex: 1; }
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
  .detail-meta-part + .detail-meta-part::before { content: " · "; }
  .detail-top .status { align-self: center; }

  /* overflow-x: auto keeps a long translation from pushing the page sideways,
     but it costs more than it looks: the moment one axis is not visible, the
     other's visible computes to auto too, so this box scrolls in BOTH axes
     whether or not we asked for it. Anything that overhangs it vertically then
     becomes a scrollbar or gets clipped. Hence the rule below is painted inside
     as a shadow rather than hung off the border edge, the underline sits at 0
     rather than -1px, and the tabs' focus ring is inset. */
  .tabs {
    display: flex;
    gap: var(--_space-6);
    overflow-x: auto;
    margin-block: var(--_space-5) var(--_space-6);
    box-shadow: inset 0 -1px 0 var(--_divider);
  }
  .tab {
    position: relative;
    min-block-size: 48px;
    flex: 0 0 auto;
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    white-space: nowrap;
    cursor: pointer;
    transition: color var(--_fast) var(--_ease-out);
  }
  /* A tab fills the scroll container's height exactly, so an outset ring would
     be clipped top and bottom. Inset, it is whole. */
  .tab:focus-visible { outline-offset: -2px; }
  .tab[aria-selected="true"] { color: var(--_ink); }
  .tab[aria-selected="true"]::after {
    content: "";
    position: absolute;
    inset-inline: 0;
    inset-block-end: 0;
    block-size: 3px;
    background: var(--_accent);
  }
  .tab-panel { min-inline-size: 0; }

  /* The tab IS the heading. A second heading repeating it is a wasted storey,
     so only the explanatory line survives here. */
  .section-head { margin-block-end: var(--_space-5); }
  .section-head p {
    max-inline-size: 56ch;
    margin: 0;
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
  /* Physical controls navigate the workbench: three positions for a wheel or
     two buttons for a dual button, one open at a time. The overview compares
     devices; the detail keeps the established spine-and-surface composition. */
  .channel-workbench {
    min-inline-size: 0;
    display: grid;
    grid-template-columns: 86px minmax(0, 1fr);
    overflow: hidden;
    border: var(--ha-card-border-width, 1px) solid var(--_border);
    border-radius: var(--_radius);
    background: var(--_card);
    box-shadow: var(--ha-card-box-shadow, none);
  }
  .channel-spine {
    position: relative;
    display: grid;
    align-content: start;
    gap: var(--_space-8);
    padding: var(--_space-8) var(--_space-3);
    border-inline-end: 1px solid var(--_divider);
    background: var(--_surface-subtle);
  }
  .channel-spine::before {
    content: "";
    position: absolute;
    inset-block: 58px;
    inset-inline-start: 50%;
    inline-size: 1px;
    background: var(--_divider);
    transform: translateX(-50%);
  }
  .channel-position {
    position: relative;
    z-index: 1;
    inline-size: 54px;
    block-size: 54px;
    display: grid;
    place-items: center;
    justify-self: center;
    border: 1px solid var(--_border);
    border-radius: 50%;
    background: var(--_card);
    color: var(--_ink-dim);
    font: inherit;
    font-size: var(--ha-font-size-l, 16px);
    font-weight: var(--ha-font-weight-medium, 500);
    font-variant-numeric: tabular-nums;
    cursor: pointer;
    transition:
      background-color var(--_fast) var(--_ease-out),
      border-color var(--_fast) var(--_ease-out),
      color var(--_fast) var(--_ease-out);
  }
  .channel-position[aria-selected="true"] {
    border-color: var(--_accent);
    background: var(--_accent);
    color: var(--text-primary-color, #fff);
  }
  .channel-position:active { transform: translateY(1px); }
  /* Struck through rather than merely dimmed: dimming reads as "unconfigured",
     which this is not — it is a position that has been switched off. */
  .channel-position-off {
    opacity: 0.55;
    text-decoration: line-through;
  }

  /* A sibling card to the workbench, not a form floating on the page
     background. Same tokens as .channel-workbench so the two read as one
     surface; PANEL_DESIGN.md forbids nesting one inside the other. */
  .settings-section {
    margin-block-start: var(--_space-4);
    padding: var(--_space-6);
    border: var(--ha-card-border-width, 1px) solid var(--_border);
    border-radius: var(--_radius);
    background: var(--_card);
    box-shadow: var(--ha-card-box-shadow, none);
  }
  .settings-title {
    margin: 0;
    font-size: var(--ha-font-size-l, 16px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  .settings-intro {
    max-inline-size: 70ch;
    margin: var(--_space-2) 0 var(--_space-4);
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.6);
  }
  .settings-toggles {
    display: flex;
    flex-wrap: wrap;
    gap: 0 var(--_space-8);
  }
  .settings-toggles ha-selector { min-inline-size: 200px; }
  .settings-toggle {
    display: flex;
    align-items: center;
    gap: var(--_space-2);
    min-block-size: 44px;
    color: var(--_ink);
    font-size: var(--ha-font-size-m, 14px);
    cursor: pointer;
  }
  .settings-toggle input {
    inline-size: 18px;
    block-size: 18px;
    margin: 0;
    accent-color: var(--_accent);
    cursor: pointer;
  }
  .settings-toggle input:focus-visible {
    outline: 2px solid var(--_accent);
    outline-offset: 2px;
  }
  .settings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: var(--_space-6);
  }
  .settings-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--_space-4);
    margin-block-start: var(--_space-6);
  }
  .settings-message {
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
  }
  .channel-surface {
    min-inline-size: 0;
    padding: var(--_space-8);
  }
  .channel-detail-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--_space-6);
    margin-block-end: var(--_space-6);
  }
  .channel-detail-copy { min-inline-size: 0; }
  .channel-detail-title {
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  .channel-detail-summary {
    margin-block-start: var(--_space-2);
    overflow-wrap: anywhere;
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
  }
  .channel-detail[data-state="warning"] .channel-detail-summary {
    color: var(--_ink);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .channel-empty {
    min-block-size: 300px;
    display: grid;
    align-content: center;
    justify-items: start;
    gap: var(--_space-3);
  }
  .channel-empty-title {
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .channel-empty-body {
    max-inline-size: 50ch;
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.6);
  }
  .channel-empty .action-button { margin-block-start: var(--_space-3); }
  /* A ledger, not a stack of cards: hairlines carry the rhythm. */
  .channel-action-list {
    margin: 0;
    padding: 0;
    border-block-start: 1px solid var(--_divider);
    list-style: none;
  }
  .channel-action {
    display: grid;
    grid-template-columns: minmax(180px, 0.65fr) minmax(0, 1.35fr);
    gap: var(--_space-6);
    align-items: center;
    min-inline-size: 0;
    padding-block: var(--_space-4);
    border-block-end: 1px solid var(--_divider);
  }
  .channel-action-label {
    min-inline-size: 0;
    display: flex;
    align-items: center;
    gap: var(--_space-3);
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.4);
  }
  .gesture-glyph {
    flex: 0 0 auto;
    inline-size: 24px;
    block-size: 24px;
    color: var(--_accent);
    fill: currentColor;
  }
  .gesture-glyph-pair {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    gap: var(--_space-1);
  }
  /* The mark for a release: where a hold ends. */
  .gesture-sequence-end {
    flex: 0 0 auto;
    inline-size: 8px;
    block-size: 8px;
    border: 2px solid var(--_accent);
    border-radius: 50%;
    background: var(--_card);
  }
  .channel-action-value {
    min-inline-size: 0;
    overflow-wrap: anywhere;
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-normal, 1.45);
  }
  .channel-action[data-state="empty"] .channel-action-value {
    color: var(--_ink-dim);
    font-weight: var(--ha-font-weight-normal, 400);
  }
  .channel-action-add {
    grid-column: 1 / -1;
    justify-self: start;
    min-block-size: 44px;
    padding: 0;
    border: 0;
    background: none;
    /* Ink, not the theme's primary colour: the default light blue is 2.6:1 on
       a white card. The underline is what says "this is the way in". */
    color: var(--_ink);
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    text-align: start;
    text-decoration: underline;
    text-underline-offset: 3px;
    cursor: pointer;
  }
  .channel-action[data-state="warning"] .channel-action-value {
    color: var(--error-color, var(--_ink));
  }
  .channel-detail .binding-form {
    padding: var(--_space-4) 0 0;
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
  /* A group of facts is a section, not a card: heading on the page, hairlines
     between rows. The bordered-box-per-group was the card-in-card tell. */
  .diagnostic-section {
    min-inline-size: 0;
    margin-block-start: var(--_space-6);
  }
  .diagnostic-section h4 {
    margin: 0 0 var(--_space-2);
    font-size: var(--ha-font-size-l, 16px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .facts {
    margin: 0;
    padding: 0;
    border-block-start: 1px solid var(--_divider);
  }
  .fact {
    display: grid;
    grid-template-columns: minmax(180px, 0.6fr) minmax(0, 1.4fr);
    gap: var(--_space-6);
    padding-block: var(--_space-3);
    border-block-end: 1px solid var(--_divider);
  }
  .fact dt { color: var(--_ink-dim); font-size: var(--ha-font-size-m, 14px); }
  .fact dd {
    min-inline-size: 0;
    margin: 0;
    justify-self: end;
    overflow-wrap: anywhere;
    text-align: end;
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    font-variant-numeric: tabular-nums;
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
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--_space-2);
    padding-inline: var(--_space-4);
    border: 1px solid var(--_border);
    border-radius: var(--ha-border-radius-md, 8px);
    background: transparent;
    color: var(--_ink);
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    white-space: nowrap;
    cursor: pointer;
    transition:
      background-color var(--_fast) var(--_ease-out),
      border-color var(--_fast) var(--_ease-out);
  }
  @media (hover: hover) {
    .action-button:hover { border-color: var(--_ink-dim); background: var(--_selected); }
  }
  /* The press is the one animation the panel owes a user: without it a click
     has no acknowledgement until the network answers. */
  .action-button:active { transform: translateY(1px); }
  .action-button svg { inline-size: 18px; block-size: 18px; fill: currentColor; }
  .action-button[data-primary="true"] {
    border-color: var(--_accent);
    background: var(--_accent);
    color: var(--text-primary-color, #fff);
  }
  .action-button[data-danger="true"] {
    border-color: var(--error-color, var(--_ink));
    color: var(--error-color, var(--_ink));
  }
  .action-button[data-apart="true"] {
    margin-inline-start: auto;
    border-color: transparent;
  }
  .action-button:disabled { cursor: wait; opacity: 0.65; }
  .action-button:disabled:active { transform: none; }

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
  .form-sections {
    display: grid;
    gap: var(--_space-4);
  }
  /* A hairline between groups, never a box around each one: the editor already
     sits on a card, and nesting cards is what made this panel read as a form
     builder rather than a control surface. */
  .form-section + .form-section {
    border-block-start: 1px solid var(--_divider);
    padding-block-start: var(--_space-4);
  }
  .form-section-title {
    margin: 0 0 var(--_space-3);
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    color: var(--_ink);
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
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .field ha-selector { display: block; }
  .number-input {
    display: flex;
    align-items: center;
    gap: var(--_space-2);
  }
  .number-unit {
    flex: 0 0 auto;
    min-inline-size: 2ch;
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
  }
  .scene-list {
    margin: var(--_space-1) 0 var(--_space-2);
    padding: 0;
    border-block-start: 1px solid var(--_divider);
    list-style: none;
  }
  .scene-item {
    display: flex;
    align-items: center;
    gap: var(--_space-3);
    min-block-size: 48px;
    border-block-end: 1px solid var(--_divider);
  }
  .scene-order {
    flex: 0 0 auto;
    min-inline-size: 2ch;
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
    font-variant-numeric: tabular-nums;
    text-align: end;
  }
  .scene-name {
    flex: 1 1 auto;
    min-inline-size: 0;
    overflow-wrap: anywhere;
    font-size: var(--ha-font-size-m, 14px);
  }
  .scene-controls { display: inline-flex; flex: 0 0 auto; }
  .scene-button {
    inline-size: 44px;
    block-size: 44px;
    color: var(--_ink-dim);
  }
  @media (hover: hover) {
    .scene-button:not(:disabled):hover { background: var(--_selected); }
  }
  .scene-button svg { inline-size: 20px; block-size: 20px; fill: currentColor; }
  .scene-button:disabled { opacity: 0.35; cursor: default; }
  .scene-add { display: grid; gap: var(--_space-1); }
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
  .field-error {
    color: var(--error-color, var(--_ink));
    font-weight: var(--ha-font-weight-medium, 500);
  }
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
    grid-template-columns: minmax(0, 1fr) minmax(280px, 340px);
    gap: var(--_space-8);
    align-items: start;
  }
  .live-output {
    min-block-size: 420px;
    display: flex;
    flex-direction: column;
    padding: var(--_space-8);
  }
  .live-status {
    display: inline-flex;
    align-items: center;
    gap: var(--_space-2);
    color: var(--_ink);
    font-size: var(--ha-font-size-s, 12px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .live-body { margin-block: auto; padding-block: var(--_space-8); }
  .live-result-label {
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-s, 12px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .live-result {
    margin-block-start: var(--_space-3);
    overflow-wrap: anywhere;
    font-size: clamp(32px, 5cqi, 56px);
    font-weight: var(--ha-font-weight-medium, 500);
    letter-spacing: -0.02em;
    line-height: 1.05;
    font-variant-numeric: tabular-nums;
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
    gap: var(--_space-3);
    margin-block-start: var(--_space-5);
    font-size: var(--ha-font-size-l, 16px);
  }
  .live-setup-action { margin-block-start: var(--_space-5); }
  .gesture-caption {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--_space-2);
    margin-block-start: var(--_space-5);
    padding-block-start: var(--_space-5);
    border-block-start: 1px solid var(--_divider);
    color: var(--_ink-dim);
    font-size: var(--ha-font-size-m, 14px);
  }
  .gesture-caption + .gesture-caption {
    margin-block-start: var(--_space-2);
    padding-block-start: 0;
    border-block-start: 0;
  }
  /* Eighteen detents because eighteen is the highest rotary count
     DEVICE_REFERENCE.md has ever observed. The strip is a measured scale, not
     decoration; do not change the count without a new observation. */
  .detent-strip {
    display: flex;
    align-items: flex-end;
    gap: var(--_space-2);
    block-size: 32px;
    margin-block-start: var(--_space-5);
  }
  .detent {
    inline-size: 2px;
    block-size: 14px;
    background: var(--_divider);
  }
  .detent[data-active="true"] {
    block-size: 28px;
    background: var(--_accent);
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
  .recent ol {
    max-block-size: 320px;
    margin: 0;
    padding: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
    list-style: none;
  }
  .recent ol:focus-visible {
    outline: 2px solid var(--_ink);
    outline-offset: -2px;
  }
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

  /* These measure the detail pane, not the window: with the rail present the
     pane is ~256px narrower, and a window-width breakpoint keeps two columns in
     a pane far too narrow for them. */
  @container (max-width: 700px) {
    .diagnostic-grid,
    .live-layout,
    .form-grid { grid-template-columns: minmax(0, 1fr); }
    .field[data-wide="true"] { grid-column: auto; }
    .channel-workbench { grid-template-columns: minmax(0, 1fr); }
    .channel-spine {
      grid-auto-flow: column;
      grid-auto-columns: minmax(0, 1fr);
      gap: var(--_space-3);
      padding: var(--_space-4);
      border-inline-end: 0;
      border-block-end: 1px solid var(--_divider);
    }
    .channel-spine::before {
      inset-block: auto;
      inset-block-start: 50%;
      inset-inline: 44px;
      inline-size: auto;
      block-size: 1px;
      transform: translateY(-50%);
    }
    .channel-surface { padding: var(--_space-6) var(--_space-4); }
    .channel-detail-head { display: grid; }
    .channel-action {
      grid-template-columns: minmax(0, 1fr);
      gap: var(--_space-2);
    }
    .channel-action-value { padding-inline-start: 37px; }
    .fact {
      grid-template-columns: minmax(0, 1fr);
      gap: var(--_space-1);
    }
    .fact dd { justify-self: start; text-align: start; }
  }

  @media (max-width: 619px) {
    .detail-shell { grid-template-columns: minmax(0, 1fr); }
    .rail { display: none; }
    .detail-pane {
      padding: var(--_space-5) var(--_space-4)
        max(var(--_space-8), env(safe-area-inset-bottom, 0px));
    }
    .back-button { display: inline-flex; margin-block-end: var(--_space-4); }
    .detail-top { flex-wrap: wrap; gap: var(--_space-2) var(--_space-3); }
    .detail-glyph { inline-size: 40px; block-size: 40px; }
    .detail-meta-part { display: block; }
    .detail-meta-part + .detail-meta-part::before { content: none; }
    .detail-top .status {
      flex: 0 0 100%;
      padding-inline-start: calc(40px + var(--_space-3));
    }
    .detail-heading h2 { font-size: var(--ha-font-size-2xl, 24px); }
    .wheel-head { padding-inline: var(--_space-4); }
    .channel { padding-inline: var(--_space-4); }
    .live-output {
      min-block-size: 340px;
      padding: var(--_space-6) var(--_space-4);
    }
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

const SVG_NS = "http://www.w3.org/2000/svg";

const svg = (icon, cls) => {
  const data =
    typeof icon === "string"
      ? { path: icon, viewBox: "0 0 24 24" }
      : icon;
  const node = document.createElementNS(SVG_NS, "svg");
  node.setAttribute("viewBox", data.viewBox || "0 0 24 24");
  node.setAttribute("aria-hidden", "true");
  node.setAttribute("focusable", "false");
  if (cls) node.setAttribute("class", cls);
  const primary = document.createElementNS(SVG_NS, "path");
  primary.setAttribute("d", data.path);
  primary.setAttribute("class", "primary-path");
  node.appendChild(primary);
  if (data.secondaryPath) {
    const secondary = document.createElementNS(SVG_NS, "path");
    secondary.setAttribute("d", data.secondaryPath);
    secondary.setAttribute("class", "secondary-path");
    node.appendChild(secondary);
  }
  return node;
};

// ha-icon does not reliably render inside a custom panel's shadow root (the
// element is not always upgraded there), so icons are inline SVG with real paths,
// which always render.

// The panel uses the exact same V2 geometry as bilresa:scroll-wheel in the
// global provider. Inline SVG remains intentional: it renders reliably inside
// this dependency-free custom panel's shadow root.
const bilresaIcon = (cls) => svg(BILRESA_ICON, cls);
const deviceIcon = (device, cls) =>
  svg(
    device?.variant === "dual_button"
      ? BILRESA_DUAL_BUTTON_ICON
      : BILRESA_ICON,
    cls,
  );

const gestureGlyph = (gesture) => {
  if (gesture === "rotation") {
    const pair = el("span", "gesture-glyph-pair");
    pair.setAttribute("aria-hidden", "true");
    pair.appendChild(svg(GESTURE_ICON.rotate_left, "gesture-glyph"));
    pair.appendChild(svg(GESTURE_ICON.rotate_right, "gesture-glyph"));
    return pair;
  }
  if (gesture === "release") {
    const endpoint = el("span", "gesture-sequence-end");
    endpoint.setAttribute("aria-hidden", "true");
    return endpoint;
  }
  return svg(GESTURE_ICON[gesture] || GESTURE_ICON.short_press, "gesture-glyph");
};

// "unavailable" is a bulb switched off at the wall; "missing" is an entity
// Home Assistant no longer has. Only the second is a fault to repair. A
// backend from before contract 6 sends target_missing alone, and meant both.
const targetState = (item) =>
  item?.target_state || (item?.target_missing ? "missing" : "ok");

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
    this._openChannel = 1;
    this._openButton = 1;
    this._view = "channels";
    this._activities = [];
    this._activityUnsub = null;
    this._activityPending = false;
    this._activityError = false;
    this._activityEpoch = 0;
    this._editingChannel = null;
    this._editingKind = null;
    this._editorData = null;
    this._editorBinding = null;
    this._editorErrors = {};
    this._editorBusy = false;
    // Per-wheel settings draft, keyed by wheel so switching wheels in the rail
    // cannot carry one wheel's unsaved edits onto another.
    this._settingsDraft = null;
    this._settingsDraftKey = null;
    this._settingsBusy = false;
    this._settingsMessage = null;
    this._editorMessage = null;
    this._deleteConfirm = false;
    // A re-render builds a new <details>; without this it would close itself
    // every time a field inside it changed.
    this._advancedOpen = false;
    // A snapshot that arrived while a form control held focus.
    this._renderDeferred = false;
    this._settingsMessageScope = null;
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

  // The target's name, with its state appended when it is not simply there.
  _targetText(item) {
    const state = targetState(item);
    if (state === "ok" || !item.target_label) return item.target_label || null;
    return this._t(
      state === "missing" ? "target_missing" : "target_unavailable",
      { target: item.target_label },
    );
  }

  // A channel or button carries the worst state of all its targets, while its
  // label names one of them (or "2 targets"). Appending the state to that label
  // would blame the wrong entity, so name the target the state belongs to.
  _controlTargetText(control) {
    const state = targetState(control);
    if (state === "ok") return control.target_label || null;
    const culprit = (control.actions || []).find(
      (action) => action.target_label && targetState(action) === state,
    );
    return this._targetText(culprit || control);
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
          if (this._editingChannel !== null && this._formHasFocus()) {
            this._renderDeferred = true;
            return;
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

  connectedCallback() {
    this._fitFrame();
  }

  // Read the inset a theme put around the panel. Home Assistant itself adds
  // none; without a browser (tests) or a parent there is nothing to measure.
  _fitFrame() {
    const frame = this.parentElement;
    if (!frame || typeof getComputedStyle !== "function") return;
    const style = getComputedStyle(frame);
    const start = Number.parseFloat(style.paddingTop) || 0;
    const end = Number.parseFloat(style.paddingBottom) || 0;
    this.style.setProperty("--_frame-start", `${start}px`);
    this.style.setProperty("--_frame-end", `${end}px`);
    const background = style.backgroundColor;
    if (start && background && background !== "rgba(0, 0, 0, 0)") {
      this.style.setProperty("--_frame-bg", background);
    }
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
      this._openChannel = 1;
      this._openButton = 1;
      this._closeEditor();
    }
    const device = this._snapshot?.wheels.find((item) => item.key === key);
    const views = this._viewsFor(device);
    if (!views.includes(this._view)) {
      if (this._view === "live") this._stopActivity();
      this._view = views[0];
    }
    this._open = key;
    this._render();
  }

  _openChannelAt(channel) {
    if (channel === this._openChannel) return;
    this._openChannel = channel;
    this._closeEditor();
    this._render();
    this.shadowRoot
      ?.getElementById(`spine-${this._open}-${channel}`)
      ?.focus({ preventScroll: true });
  }

  _openButtonAt(button) {
    if (button === this._openButton) return;
    this._openButton = button;
    this._closeEditor();
    this._render();
    this.shadowRoot
      ?.getElementById(`button-${this._open}-${button}`)
      ?.focus({ preventScroll: true });
  }

  _backToOverview() {
    this._stopActivity();
    this._view = "channels";
    this._open = null;
    this._openChannel = 1;
    this._openButton = 1;
    this._activities = [];
    this._closeEditor();
    this._render();
  }

  _viewsFor(device) {
    return device?.variant === "dual_button"
      ? ["buttons", "live", "diagnostics"]
      : ["channels", "live", "diagnostics"];
  }

  _controlsFor(device) {
    return device?.variant === "dual_button"
      ? device.buttons || []
      : device.channels || [];
  }

  _controlNumber(device, control) {
    return device?.variant === "dual_button" ? control.button : control.channel;
  }

  _isConfigured(control) {
    return control.configured ??
      (control.profile !== null && control.profile !== undefined);
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

  _summaryItem(text, state) {
    const item = el("span", "summary-item");
    item.appendChild(this._statusDot(state));
    item.appendChild(el("span", null, text));
    return item;
  }

  _overviewHead() {
    const s = this._snapshot;
    const head = el("div", "overview-head");
    head.appendChild(el("h1", null, this._t("overview_title")));

    const wrap = el("div", "summary");
    const connected = s.wheels.filter(
      (wheel) => wheel.availability === "connected",
    ).length;
    const unknown = s.wheels.filter(
      (wheel) => wheel.availability === "unknown",
    ).length;
    const unavailable = s.wheels.length - connected - unknown;

    wrap.appendChild(
      this._summaryItem(
        this._t("summary_connected", { count: connected }),
        "connected",
      ),
    );
    if (unavailable > 0) {
      wrap.appendChild(
        this._summaryItem(
          this._t("summary_unavailable", { count: unavailable }),
          "unavailable",
        ),
      );
    }
    if (unknown > 0) {
      wrap.appendChild(
        this._summaryItem(
          this._t("summary_unknown", { count: unknown }),
          "unknown",
        ),
      );
    }
    wrap.appendChild(
      this._summaryItem(
        this._t(s.matter_connected ? "matter_connected" : "matter_offline"),
        s.matter_connected ? "connected" : "unavailable",
      ),
    );
    head.appendChild(wrap);
    return head;
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

  _overviewControl(device, control) {
    const configured = this._isConfigured(control);
    const number = this._controlNumber(device, control);
    const row = el("span", "channel");
    row.dataset.state = configured ? "ok" : "empty";
    row.appendChild(el("span", "channel-n", String(number)));

    const text = el("span", "channel-text");
    text.appendChild(
      el(
        "span",
        "channel-behaviour",
        control.behaviour ||
          (configured ? control.profile : this._t("not_configured")),
      ),
    );
    text.appendChild(
      el(
        "span",
        "channel-target",
        this._controlTargetText(control) || this._t("add_binding"),
      ),
    );
    row.appendChild(text);
    if (targetState(control) === "missing") {
      row.appendChild(svg(ICON.alert, "channel-warn"));
    }
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
    head.appendChild(deviceIcon(wheel, "device-glyph"));
    const names = el("span", "wheel-names");
    names.appendChild(el("span", "wheel-name", wheel.name));
    const meta = [wheel.area, this._activityLabel(wheel)].filter(Boolean);
    const sub = el("span", "wheel-sub", meta.join(" · "));
    // The relative time is for reading; the exact stamp stays one hover away.
    if (wheel.last_activity) sub.title = this._formatDate(wheel.last_activity);
    names.appendChild(sub);
    head.appendChild(names);
    head.appendChild(this._status(wheel.availability));
    head.appendChild(svg(ICON.chevron, "wheel-open"));
    card.appendChild(head);

    const channels = el("span", "channels");
    for (const control of this._controlsFor(wheel)) {
      channels.appendChild(this._overviewControl(wheel, control));
    }
    card.appendChild(channels);
    return card;
  }

  _activityLabel(wheel) {
    if (!wheel.last_activity) return this._t("no_activity");
    const when = new Date(wheel.last_activity);
    if (Number.isNaN(when.getTime())) return null;
    let suffix = "";
    if (
      wheel.variant === "dual_button" &&
      wheel.last_active_button !== null &&
      wheel.last_active_button !== undefined
    ) {
      suffix = ` · ${this._t("last_on_button", {
        button: wheel.last_active_button,
      })}`;
    } else if (
      wheel.last_active_channel !== null &&
      wheel.last_active_channel !== undefined
    ) {
      suffix = ` · ${this._t("last_on_channel", {
        channel: wheel.last_active_channel,
      })}`;
    }
    return `${this._formatRelative(when)}${suffix}`;
  }

  _formatDate(value) {
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat(this._hass?.language || undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  }

  // "2 hours ago" is read at a glance; "16. 7. 2026 9:54" has to be subtracted
  // from now. Home Assistant tells time this way everywhere, and the exact
  // stamp stays one hover away in the title.
  _formatRelative(value) {
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    const seconds = (date.getTime() - Date.now()) / 1000;
    const units = [
      ["year", 31536000],
      ["month", 2592000],
      ["day", 86400],
      ["hour", 3600],
      ["minute", 60],
    ];
    const format = new Intl.RelativeTimeFormat(this._hass?.language || undefined, {
      numeric: "auto",
    });
    for (const [unit, size] of units) {
      if (Math.abs(seconds) >= size) {
        return format.format(Math.round(seconds / size), unit);
      }
    }
    return format.format(Math.round(seconds), "second");
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
      // Exactly three children for the rail's three columns. The tick that used
      // to trail the open wheel was a fourth, so it wrapped to its own row — and
      // it was redundant anyway: the tinted surface already says "open".
      button.appendChild(deviceIcon(wheel, "rail-glyph"));
      const copy = el("span", "rail-copy");
      copy.appendChild(el("span", "rail-name", wheel.name));
      copy.appendChild(
        el("span", "rail-area", wheel.area || this._t("detail_area_none")),
      );
      button.appendChild(copy);
      button.appendChild(this._statusDot(wheel.availability));
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
    top.appendChild(deviceIcon(wheel, "detail-glyph"));

    const heading = el("div", "detail-heading");
    heading.appendChild(el("h2", null, wheel.name));
    const meta = [
      wheel.area || this._t("detail_area_none"),
      this._activityLabel(wheel),
    ].filter(Boolean);
    // Separate parts, so a phone puts the room and the activity on a line each
    // by design instead of breaking one long line wherever it happens to fit.
    const metaNode = el("div", "detail-meta");
    for (const part of meta) metaNode.appendChild(el("span", "detail-meta-part", part));
    if (wheel.last_activity) metaNode.title = this._formatDate(wheel.last_activity);
    heading.appendChild(metaNode);
    top.appendChild(heading);
    top.appendChild(this._status(wheel.availability));
    return top;
  }

  _mobileBack() {
    const back = el("button", "back-button");
    back.id = "back-to-overview";
    back.type = "button";
    back.appendChild(svg(ICON.back));
    back.appendChild(el("span", null, this._t("back")));
    back.addEventListener("click", () => this._backToOverview());
    return back;
  }

  _tabs(wheel) {
    const views = this._viewsFor(wheel);
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

  // The selected tab already names the view; a heading repeating it is a second
  // storey of hierarchy carrying no information. Only the explanation remains.
  _sectionHead(body) {
    const head = el("div", "section-head");
    head.appendChild(el("p", null, body));
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

  // Turning the wheel pushes a snapshot. Rebuilding the form at that moment
  // would close an open entity picker and drop the caret from a number field.
  _formHasFocus() {
    const active = this.shadowRoot?.activeElement;
    return Boolean(active?.closest?.(".binding-form"));
  }

  _closeEditor() {
    this._advancedOpen = false;
    this._renderDeferred = false;
    this._editingChannel = null;
    this._editingKind = null;
    this._editorData = null;
    this._editorBinding = null;
    this._editorErrors = {};
    this._editorBusy = false;
    this._editorMessage = null;
    this._deleteConfirm = false;
  }

  _defaultBindingFor(device) {
    return device.variant === "dual_button"
      ? DEFAULT_BUTTON_BINDING
      : DEFAULT_BINDING;
  }

  _startEditor(device, control) {
    this._editingChannel = this._controlNumber(device, control);
    this._editingKind =
      device.variant === "dual_button" ? "button" : "channel";
    this._editorBinding = control.binding || null;
    this._editorData = {
      ...this._defaultBindingFor(device),
      ...(control.binding?.data || {}),
      ...(device.variant === "dual_button"
        ? {}
        : { scenes: [...(control.binding?.data?.scenes || [])] }),
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

  _schema() {
    return this._panel?.config?.schema || FALLBACK_SCHEMA;
  }

  _numberRange(group, name) {
    return this._schema()[group]?.[name] || FALLBACK_SCHEMA[group][name];
  }

  _fieldId(name) {
    return `binding-${this._open}-${this._editingChannel}-${name}`;
  }

  _editorChanged(name) {
    delete this._editorErrors[name];
    this._editorMessage = null;
  }

  // Home Assistant's own control for a selector: the same entity picker,
  // slider and dropdown its settings pages use. The frontend offers no loader
  // a custom panel may rely on, so this returns null when the element is not
  // registered and every caller falls back to the panel's own control.
  _haSelector({ id, selector, value, label, helper, required, onChange }) {
    if (!customElements.get("ha-selector")) return null;
    const node = document.createElement("ha-selector");
    node.id = id;
    node.hass = this._hass;
    node.selector = selector;
    node.value = value;
    node.label = label;
    if (helper) node.helper = helper;
    node.required = Boolean(required);
    node.addEventListener("value-changed", (event) => {
      event.stopPropagation();
      onChange(event.detail?.value);
    });
    return node;
  }

  _selectSelector(options) {
    return { select: { options, mode: "dropdown" } };
  }

  _entitySelector(domains, exclude) {
    const entity = { domain: [...domains] };
    if (exclude?.length) entity.exclude_entities = [...exclude];
    return { entity };
  }

  _numberSelector(range) {
    const number = {
      min: range.min,
      max: range.max,
      step: range.step,
      mode: "slider",
    };
    if (range.unit) number.unit_of_measurement = range.unit;
    return { number };
  }

  _field(wide) {
    const wrap = el("div", "field");
    if (wide) wrap.dataset.wide = "true";
    return wrap;
  }

  _fieldErrorNode(wrap, name, control) {
    const error = this._fieldError(name);
    if (!error) return;
    const node = el("span", "field-error", error);
    node.id = `${this._fieldId(name)}-error`;
    if (control?.setAttribute) control.setAttribute("aria-describedby", node.id);
    wrap.appendChild(node);
  }

  // The panel's own dropdown, used when Home Assistant's is not available.
  _nativeSelect(wrap, id, label, help, options, { emptyLabel, value, onChange }) {
    const labelNode = el("label", null, label);
    labelNode.htmlFor = id;
    wrap.appendChild(labelNode);
    if (help) wrap.appendChild(el("span", "field-help", help));
    const select = el("select");
    select.id = id;
    if (emptyLabel !== undefined) {
      // An empty optional target does not always mean "nothing happens", so the
      // placeholder must say what leaving it empty actually does.
      const empty = el("option", null, emptyLabel);
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
    select.value = value ?? "";
    select.addEventListener("change", () => onChange(select.value));
    wrap.appendChild(select);
    return select;
  }

  _selectField(name, label, options, { help, wide = false } = {}) {
    const wrap = this._field(wide);
    const id = this._fieldId(name);
    const value = this._editorData[name] ?? "";
    const onChange = (next) => {
      this._editorData[name] = next || undefined;
      this._editorChanged(name);
      this._render();
    };
    let control = this._haSelector({
      id,
      selector: this._selectSelector(options),
      value,
      label,
      helper: help,
      required: true,
      onChange,
    });
    if (control) wrap.appendChild(control);
    else control = this._nativeSelect(wrap, id, label, help, options, { value, onChange });
    this._fieldErrorNode(wrap, name, control);
    return wrap;
  }

  // emptyLabel names what an empty optional target does. The native dropdown
  // shows it as its empty option; Home Assistant's picker has no such option,
  // so there the same fact goes under the field as emptyHelp.
  _entityField(
    name,
    label,
    domains,
    { optional = false, help, wide = false, emptyLabel, emptyHelp } = {},
  ) {
    const wrap = this._field(wide);
    const id = this._fieldId(name);
    const current = this._editorData[name];
    const onChange = (next) => {
      this._editorData[name] = next || undefined;
      this._editorChanged(name);
      this._render();
    };
    let control = this._haSelector({
      id,
      selector: this._entitySelector(domains),
      value: current,
      label,
      helper: help || (optional ? emptyHelp : undefined),
      required: !optional,
      onChange,
    });
    if (control) {
      wrap.appendChild(control);
    } else {
      const options = this._entityRecords(domains).map((state) => ({
        value: state.entity_id,
        label: `${state.attributes?.friendly_name || state.entity_id} · ${state.entity_id}`,
      }));
      if (current && !options.some((option) => option.value === current)) {
        options.unshift({ value: current, label: current });
      }
      control = this._nativeSelect(wrap, id, label, help, options, {
        emptyLabel: optional ? emptyLabel || this._t("target_none") : undefined,
        value: current,
        onChange,
      });
    }
    this._fieldErrorNode(wrap, name, control);
    return wrap;
  }

  // One number control for both forms. The caller owns what a change does:
  // a binding field updates the draft quietly, so typing keeps the caret.
  _numberControl({ id, label, help, range, value, onChange }) {
    const wrap = this._field(false);
    let control = this._haSelector({
      id,
      selector: this._numberSelector(range),
      value,
      label,
      helper: help,
      required: true,
      onChange: (next) => onChange(Number(next)),
    });
    if (control) {
      wrap.appendChild(control);
      return { wrap, control };
    }
    const labelNode = el("label", null, label);
    labelNode.htmlFor = id;
    wrap.appendChild(labelNode);
    if (help) wrap.appendChild(el("span", "field-help", help));
    const row = el("div", "number-input");
    control = el("input");
    control.id = id;
    control.type = "number";
    control.required = true;
    control.min = String(range.min);
    control.max = String(range.max);
    control.step = String(range.step);
    control.value = String(value ?? "");
    control.addEventListener("input", () => onChange(Number(control.value)));
    row.appendChild(control);
    // The unit sits beside the value it qualifies, not in a line of help text.
    if (range.unit) row.appendChild(el("span", "number-unit", range.unit));
    wrap.appendChild(row);
    return { wrap, control };
  }

  _numberField(name, label, { help } = {}) {
    const { wrap, control } = this._numberControl({
      id: this._fieldId(name),
      label,
      help,
      range: this._numberRange("binding_numbers", name),
      value: this._editorData[name],
      onChange: (next) => {
        this._editorData[name] = next;
        this._editorChanged(name);
      },
    });
    this._fieldErrorNode(wrap, name, control);
    return wrap;
  }

  _formSection(parent, title) {
    // A title exists to tell two groups apart. A button binding has only one
    // group, so titling it would repeat the editor's own heading.
    const section = el("section", "form-section");
    if (title) section.appendChild(el("h4", "form-section-title", title));
    const grid = el("div", "form-grid");
    section.appendChild(grid);
    parent.appendChild(section);
    return grid;
  }

  _sceneName(entityId) {
    return this._hass?.states?.[entityId]?.attributes?.friendly_name || entityId;
  }

  _sceneAdd(entityId) {
    const scenes = this._editorData.scenes || [];
    if (!entityId || scenes.includes(entityId)) return;
    this._editorData.scenes = [...scenes, entityId];
    this._editorChanged("scenes");
  }

  _sceneRemove(index) {
    this._editorData.scenes = (this._editorData.scenes || []).filter(
      (_scene, position) => position !== index,
    );
    this._editorChanged("scenes");
  }

  _sceneMove(index, delta) {
    const scenes = [...(this._editorData.scenes || [])];
    const to = index + delta;
    if (to < 0 || to >= scenes.length) return;
    [scenes[index], scenes[to]] = [scenes[to], scenes[index]];
    this._editorData.scenes = scenes;
    this._editorChanged("scenes");
  }

  _sceneButton(kind, path, labelKey, entityId, disabled, handler) {
    const button = el("button", "icon-button scene-button");
    button.type = "button";
    // Keyed by the scene, not its position, so focus follows the scene when
    // it moves and repeated presses keep moving the same one.
    button.id = `${this._fieldId("scenes")}-${kind}-${entityId}`;
    const label = this._t(labelKey, { scene: this._sceneName(entityId) });
    button.setAttribute("aria-label", label);
    button.title = label;
    button.disabled = disabled;
    button.appendChild(svg(path));
    button.addEventListener("click", () => {
      handler();
      this._render();
    });
    return button;
  }

  // Scene cycling follows the order of this list, so the list has to show an
  // order and let it be changed. A multi-select can do neither.
  _scenesField() {
    const wrap = this._field(true);
    wrap.appendChild(el("span", "field-label", this._t("field_scenes")));
    wrap.appendChild(el("span", "field-help", this._t("field_scenes_help")));
    const scenes = this._editorData.scenes || [];
    if (scenes.length) {
      const list = el("ol", "scene-list");
      scenes.forEach((entityId, index) => {
        const item = el("li", "scene-item");
        item.appendChild(el("span", "scene-order", String(index + 1)));
        item.appendChild(el("span", "scene-name", this._sceneName(entityId)));
        const controls = el("span", "scene-controls");
        controls.appendChild(
          this._sceneButton("up", ICON.arrowUp, "scene_move_up", entityId, index === 0, () =>
            this._sceneMove(index, -1),
          ),
        );
        controls.appendChild(
          this._sceneButton(
            "down",
            ICON.arrowDown,
            "scene_move_down",
            entityId,
            index === scenes.length - 1,
            () => this._sceneMove(index, 1),
          ),
        );
        controls.appendChild(
          this._sceneButton("remove", ICON.remove, "scene_remove", entityId, false, () =>
            this._sceneRemove(index),
          ),
        );
        item.appendChild(controls);
        list.appendChild(item);
      });
      wrap.appendChild(list);
    }
    const id = `${this._fieldId("scenes")}-add`;
    const onChange = (next) => {
      this._sceneAdd(next);
      this._render();
    };
    const add = this._haSelector({
      id,
      selector: this._entitySelector(["scene"], scenes),
      value: undefined,
      label: this._t("scene_add"),
      required: false,
      onChange,
    });
    if (add) {
      wrap.appendChild(add);
    } else {
      const options = this._entityRecords(["scene"])
        .filter((state) => !scenes.includes(state.entity_id))
        .map((state) => ({
          value: state.entity_id,
          label: `${state.attributes?.friendly_name || state.entity_id} · ${state.entity_id}`,
        }));
      const shell = el("div", "scene-add");
      this._nativeSelect(shell, id, this._t("scene_add"), null, options, {
        emptyLabel: this._t("scene_add_placeholder"),
        value: "",
        onChange,
      });
      wrap.appendChild(shell);
    }
    this._fieldErrorNode(wrap, "scenes", null);
    return wrap;
  }

  async _refreshSnapshot() {
    this._snapshot = await this._hass.callWS({ type: OVERVIEW });
  }

  async _saveBinding(wheel, control) {
    if (this._editorBusy) return;
    this._editorBusy = true;
    this._editorErrors = {};
    this._editorMessage = null;
    this._render();
    try {
      const number = this._controlNumber(wheel, control);
      const response = await this._hass.callWS({
        type: BINDING_SAVE,
        wheel: wheel.key,
        [wheel.variant === "dual_button" ? "button" : "channel"]: number,
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
            ...this._defaultBindingFor(wheel),
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
      const refreshedControl = this._controlsFor(refreshedWheel).find(
        (item) => this._controlNumber(refreshedWheel, item) === number,
      );
      this._editorBinding = refreshedControl?.binding || response.binding;
      this._editorData = {
        ...this._defaultBindingFor(wheel),
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
            ...(this._editingKind === "button"
              ? DEFAULT_BUTTON_BINDING
              : DEFAULT_BINDING),
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

  _bindingForm(wheel, control) {
    const isButton = wheel.variant === "dual_button";
    const number = this._controlNumber(wheel, control);
    const form = el("form", "binding-form");
    form.setAttribute(
      "aria-label",
      this._t(
        isButton ? "binding_editor_button_title" : "binding_editor_title",
        isButton ? { button: number } : { channel: number },
      ),
    );
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      this._saveBinding(wheel, control);
    });
    form.addEventListener("focusout", () => {
      if (!this._renderDeferred) return;
      setTimeout(() => {
        if (!this._renderDeferred || this._formHasFocus()) return;
        this._renderDeferred = false;
        this._render();
      }, 0);
    });

    if (this._editorMessage) {
      const message = el("p", "form-message", this._editorMessage);
      message.setAttribute("role", "status");
      form.appendChild(message);
    }

    // The gesture ledger above lists rotation, short, double, triple and hold
    // as one sequence. The editor follows that same order, and one grid row
    // carries one gesture: its action beside its target. Fields are grouped by
    // what they belong to, never by how advanced they are — a double press is
    // no more advanced than a short press.
    const sections = el("div", "form-sections");
    const pressDomains = this._schema().press_target_domains;

    if (!isButton) {
      const rotation = this._formSection(sections, this._t("section_rotation"));
      rotation.appendChild(
        this._selectField(
          "mode",
          this._t("field_mode"),
          Object.keys(this._schema().mode_domains).map((mode) => ({
            value: mode,
            label: this._t(`mode_${mode}`),
          })),
        ),
      );
      rotation.appendChild(
        this._entityField(
          "target",
          this._t("field_target"),
          this._schema().mode_domains[this._editorData.mode] || [],
        ),
      );
      rotation.appendChild(
        this._numberField("step", this._t("field_step"), {
          help: this._t("field_step_help"),
        }),
      );
      rotation.appendChild(
        this._numberField("transition", this._t("field_transition"), {
          help: this._t("field_transition_help"),
        }),
      );
    }

    const button = this._formSection(
      sections,
      isButton ? null : this._t("section_button"),
    );
    button.appendChild(
      this._selectField(
        "click_action",
        this._t("field_click_action"),
        ["toggle", "on", "off", "none"].map((action) => ({
          value: action,
          label: this._t(`click_${action}`),
        })),
      ),
    );
    if (!isButton || this._editorData.click_action !== "none") {
      button.appendChild(
        this._entityField(
          "click_target",
          this._t("field_click_target"),
          pressDomains,
          {
            optional: !isButton,
            // A wheel with no explicit short-press target falls back to the
            // rotation target, which the gesture ledger already reports. Saying
            // "no target" here contradicted that on the same screen.
            emptyLabel: isButton ? undefined : this._t("target_same_as_rotation"),
            emptyHelp: isButton ? undefined : this._t("target_empty_is_rotation"),
          },
        ),
      );
    }
    if (!isButton) button.appendChild(this._scenesField());
    // Double and triple press take a target but never an action, so each owns
    // a full row instead of leaving a hole where an action select would be.
    button.appendChild(
      this._entityField(
        "double_press_target",
        this._t("field_double_target"),
        pressDomains,
        { optional: true, wide: true },
      ),
    );
    if (!isButton) {
      button.appendChild(
        this._entityField(
          "triple_press_target",
          this._t("field_triple_target"),
          pressDomains,
          { optional: true, wide: true },
        ),
      );
    }
    button.appendChild(
      this._selectField(
        "hold_action",
        this._t("field_hold_action"),
        ["toggle", "ramp", "none"].map((action) => ({
          value: action,
          label: this._t(`hold_${action}`),
        })),
      ),
    );
    if (this._editorData.hold_action !== "none") {
      button.appendChild(
        this._entityField(
          "hold_target",
          this._t("field_hold_target"),
          this._editorData.hold_action === "ramp"
            ? this._schema().ramp_target_domains
            : pressDomains,
          { optional: !isButton },
        ),
      );
    }
    if (isButton && this._editorData.hold_action === "ramp") {
      button.appendChild(
        this._selectField(
          "ramp_direction",
          this._t("field_ramp_direction"),
          ["alternate", "up", "down"].map((direction) => ({
            value: direction,
            label: this._t(`ramp_direction_${direction}`),
          })),
          { wide: true },
        ),
      );
    }
    form.appendChild(sections);

    // What is left is genuinely set-once: a recognition policy and the limits
    // of the rotation range. Minimum and maximum stay adjacent because they
    // are one pair, which the old flat ordering split across two rows.
    const advanced = el("details", "advanced");
    advanced.open = this._advancedOpen;
    advanced.addEventListener("toggle", () => {
      this._advancedOpen = advanced.open;
    });
    const summary = el("summary", null, this._t("advanced_options"));
    advanced.appendChild(summary);
    const advancedGrid = el("div", "form-grid");
    advancedGrid.appendChild(
      this._selectField(
        "button_response",
        this._t("field_button_response"),
        ["multi_press", "fast", "instant"].map((response) => ({
          value: response,
          label: this._t(
            `${isButton ? "dual_button_response" : "button_response"}_${response}`,
          ),
        })),
        { wide: true },
      ),
    );
    if (!isButton) {
      // Set-once, so it belongs under the disclosure rather than beside the
      // rotation fields - PANEL_DESIGN.md. Full width because its help text
      // carries the one thing a reader has to know: do not correct twice.
      advancedGrid.appendChild(
        this._selectField(
          "step_curve",
          this._t("field_step_curve"),
          ["linear", "perceptual"].map((curve) => ({
            value: curve,
            label: this._t(`step_curve_${curve}`),
          })),
          { wide: true, help: this._t("field_step_curve_help") },
        ),
      );
      advancedGrid.appendChild(
        this._numberField("min_brightness", this._t("field_min_brightness")),
      );
      advancedGrid.appendChild(
        this._numberField("max_brightness", this._t("field_max_brightness")),
      );
      advancedGrid.appendChild(
        this._numberField("acceleration", this._t("field_acceleration"), {
          help: this._t("field_acceleration_help"),
        }),
      );
    }
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
      // Pushed to the far end of the row: a slip next to Save must not land on
      // the one action that throws the binding away.
      remove.dataset.apart = "true";
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
      confirm.appendChild(
        el(
          "span",
          null,
          this._t(
            isButton
              ? "delete_button_binding_confirm"
              : "delete_binding_confirm",
          ),
        ),
      );
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
    const isButton = wheel.variant === "dual_button";
    const number = this._controlNumber(wheel, channel);
    const configured = this._isConfigured(channel);
    const missingTarget =
      targetState(channel) === "missing" ||
      (channel.actions || []).some(
        (action) => targetState(action) === "missing",
      );
    const card = el("div", "channel-detail");
    card.dataset.state = missingTarget ? "warning" : configured ? "ready" : "empty";

    if (!configured && this._editingChannel !== number) {
      const empty = el("div", "channel-empty");
      empty.appendChild(
        el(
          "div",
          "channel-empty-title",
          this._t(
            isButton ? "button_empty_title" : "channel_empty_title",
            isButton ? { button: number } : { channel: number },
          ),
        ),
      );
      empty.appendChild(
        el(
          "div",
          "channel-empty-body",
          this._t(isButton ? "button_empty_body" : "channel_empty_body"),
        ),
      );
      const add = el("button", "action-button", this._t("add_binding"));
      add.type = "button";
      add.dataset.primary = "true";
      add.addEventListener("click", () => this._startEditor(wheel, channel));
      empty.appendChild(add);
      card.appendChild(empty);
      return card;
    }

    const head = el("div", "channel-detail-head");
    const copy = el("div", "channel-detail-copy");
    copy.appendChild(
      el(
        "div",
        "channel-detail-title",
        this._t(
          isButton ? "button_title" : "channel_title",
          isButton ? { button: number } : { channel: number },
        ),
      ),
    );
    let summary = this._t("not_configured");
    if (configured) {
      const target =
        this._controlTargetText(channel) || this._t("target_none");
      summary = [
        channel.behaviour || channel.profile,
        target,
      ].filter(Boolean).join(" · ");
    }
    copy.appendChild(el("div", "channel-detail-summary", summary));
    head.appendChild(copy);
    if (this._editingChannel !== number) {
      const edit = el(
        "button",
        "action-button",
        this._t(configured ? "edit_binding" : "add_binding"),
      );
      edit.type = "button";
      edit.addEventListener("click", () => this._startEditor(wheel, channel));
      head.appendChild(edit);
    }
    card.appendChild(head);

    // Editing replaces the ledger: the form states the same facts, and keeping
    // both made a phone scroll past the summary to reach the fields.
    if (
      configured &&
      this._editingChannel !== number &&
      (channel.actions || []).length
    ) {
      const actions = el("ul", "channel-action-list");
      const actionValue = (action) => {
        let value = action.action_label;
        if (action.target_label) {
          value = `${value} · ${this._targetText(action)}`;
        }
        return value;
      };
      const { rows, unset } = this._ledgerRows(channel.actions || [], actionValue);
      for (const row of rows) {
        const item = el("li", "channel-action");
        if (row.warning) item.dataset.state = "warning";
        const label = el("span", "channel-action-label");
        label.appendChild(gestureGlyph(row.gesture));
        label.appendChild(el("span", null, row.label));
        item.appendChild(label);
        item.appendChild(el("span", "channel-action-value", row.value));
        actions.appendChild(item);
      }
      if (unset.length) {
        // One row for everything that does nothing yet, and it is the way in:
        // three "No action" rows said the same thing three times.
        const item = el("li", "channel-action");
        item.dataset.state = "empty";
        const add = el(
          "button",
          "channel-action-add",
          this._t("ledger_unset", {
            gestures: unset
              .map((name) =>
                name.toLocaleLowerCase(this._hass?.language || undefined),
              )
              .join(", "),
          }),
        );
        add.type = "button";
        add.addEventListener("click", () => this._startEditor(wheel, channel));
        item.appendChild(add);
        actions.appendChild(item);
      }
      card.appendChild(actions);
    }

    if (this._editingChannel === number) {
      card.appendChild(this._bindingForm(wheel, channel));
    }
    return card;
  }

  _isNoAction(action) {
    return !action.target_label && action.action_label === this._t("action_none");
  }

  // Turn the read model's gesture list into ledger rows. Hold and release are
  // one gesture: the row states the hold, and mentions the release only when
  // the release does something. Gestures with no action are returned by name.
  _ledgerRows(summaries, actionValue) {
    const rows = [];
    const unset = [];
    for (let index = 0; index < summaries.length; index += 1) {
      const action = summaries[index];
      const next = summaries[index + 1];
      const release =
        action.gesture === "hold" && next?.gesture === "release" ? next : null;
      if (release) index += 1;
      if (this._isNoAction(action) && (!release || this._isNoAction(release))) {
        unset.push(action.gesture_label);
        continue;
      }
      let value = actionValue(action);
      if (release && !this._isNoAction(release)) {
        value = this._t("ledger_then_release", {
          hold: value,
          release: actionValue(release),
        });
      }
      rows.push({
        gesture: action.gesture,
        label: action.gesture_label,
        value,
        warning:
          targetState(action) === "missing" ||
          (release !== null && targetState(release) === "missing"),
      });
    }
    return { rows, unset };
  }


  _settingsStateFor(wheel) {
    if (this._settingsDraftKey === wheel.key && this._settingsDraft) {
      return this._settingsDraft;
    }
    return this._storedSettings(wheel);
  }

  _storedSettings(wheel) {
    const stored = wheel.settings || {};
    const enabled = {};
    (wheel.channels || []).forEach((channel) => {
      enabled[String(channel.channel)] = channel.enabled !== false;
    });
    return {
      channel_enabled: enabled,
      step: stored.step ?? 2,
      acceleration: stored.acceleration ?? 0,
    };
  }

  // Quiet on purpose: a re-render here would take a slider out of the hand
  // that is dragging it.
  _updateSettingsDraft(wheel, patch) {
    this._settingsDraft = { ...this._settingsStateFor(wheel), ...patch };
    this._settingsDraftKey = wheel.key;
    this._settingsMessage = null;
  }

  // The two cards save separately. "channels" sends the switches with the
  // stored dial values, "dial" the reverse, so one card's Save never carries
  // the other card's unsaved edits. No scope sends the whole draft.
  async _saveSettings(wheel, scope) {
    if (this._settingsBusy) return;
    this._settingsBusy = true;
    this._settingsMessage = null;
    this._settingsMessageScope = scope || null;
    this._render();
    try {
      const draft = this._settingsStateFor(wheel);
      const stored = this._storedSettings(wheel);
      const channels = scope === "dial" ? stored : draft;
      const dial = scope === "channels" ? stored : draft;
      const payload = {
        type: SETTINGS_SAVE,
        wheel: wheel.key,
        channel_enabled: channels.channel_enabled,
        step: Number(dial.step),
        acceleration: Number(dial.acceleration),
      };
      // Omitted, never null: a wheel saving for the first time has no stored
      // revision, and the command's schema takes a string or nothing. The
      // server still treats a missing token as "I expect no stored settings",
      // so a subentry created meanwhile is reported as a conflict.
      const revision = wheel.settings?.revision;
      if (revision) payload.expected_revision = revision;
      const response = await this._hass.callWS(payload);
      if (!response.ok) {
        this._settingsMessage = this._t(
          response.error === "conflict"
            ? "settings_error_conflict"
            : "settings_error_generic",
        );
        // A conflict means the stored value is the truth now: drop the draft
        // so the refreshed snapshot is what the owner sees and re-edits.
        if (response.error === "conflict") {
          this._settingsDraft = null;
          this._settingsDraftKey = null;
          await this._refreshSnapshot();
        }
        return;
      }
      // The part that was not saved stays a draft.
      const kept =
        scope === "channels"
          ? { step: draft.step, acceleration: draft.acceleration }
          : scope === "dial"
            ? { channel_enabled: draft.channel_enabled }
            : null;
      this._settingsDraft = null;
      this._settingsDraftKey = null;
      await this._refreshSnapshot();
      const refreshed = this._snapshot?.wheels?.find(
        (item) => item.key === wheel.key,
      );
      if (kept && refreshed) {
        this._settingsDraft = { ...this._storedSettings(refreshed), ...kept };
        this._settingsDraftKey = refreshed.key;
      }
      this._settingsMessage = this._t(
        scope === "channels" ? "settings_channels_saved" : "settings_saved",
      );
    } catch (err) {
      this._settingsMessage = this._t("settings_error_generic");
    } finally {
      this._settingsBusy = false;
      this._render();
    }
  }

  _settingsCard(title, intro) {
    const section = el("section", "settings-section");
    section.appendChild(el("h4", "settings-title", title));
    section.appendChild(el("p", "settings-intro", intro));
    return section;
  }

  _settingsStatus(scope) {
    if (!this._settingsMessage || this._settingsMessageScope !== scope) return null;
    const message = el("span", "settings-message", this._settingsMessage);
    message.setAttribute("role", "status");
    return message;
  }

  // Which selector positions exist at all. A switch applies at once, like
  // every other switch in Home Assistant, so this card needs no Save.
  _activeChannelsSection(wheel) {
    const draft = this._settingsStateFor(wheel);
    const section = this._settingsCard(
      this._t("settings_channels_title"),
      this._t("settings_intro"),
    );
    const toggles = el("div", "settings-toggles");
    (wheel.channels || []).forEach((channel) => {
      const key = String(channel.channel);
      const label = this._t("settings_channel_enabled", {
        channel: channel.channel,
      });
      const apply = (checked) => {
        this._updateSettingsDraft(wheel, {
          channel_enabled: {
            ...this._settingsStateFor(wheel).channel_enabled,
            [key]: Boolean(checked),
          },
        });
        this._saveSettings(wheel, "channels");
      };
      const id = `settings-${wheel.key}-channel-${key}`;
      const control = this._haSelector({
        id,
        selector: { boolean: {} },
        value: draft.channel_enabled[key] !== false,
        label,
        required: false,
        onChange: apply,
      });
      if (control) {
        control.disabled = this._settingsBusy;
        toggles.appendChild(control);
        return;
      }
      const row = el("label", "settings-toggle");
      const box = el("input");
      box.id = id;
      box.type = "checkbox";
      box.checked = draft.channel_enabled[key] !== false;
      box.disabled = this._settingsBusy;
      box.addEventListener("change", () => apply(box.checked));
      row.appendChild(box);
      row.appendChild(el("span", null, label));
      toggles.appendChild(row);
    });
    section.appendChild(toggles);
    const status = this._settingsStatus("channels");
    if (status) section.appendChild(status);
    return section;
  }

  // The dial is the number entity each channel carries. It is not the binding,
  // and its step and acceleration are not the binding's: the card says so.
  _dialSection(wheel) {
    const draft = this._settingsStateFor(wheel);
    const section = this._settingsCard(
      this._t("settings_dial_title"),
      this._t("settings_dial_intro"),
    );
    const grid = el("div", "settings-grid");
    for (const [name, label, help] of [
      ["step", this._t("settings_step"), this._t("settings_step_help")],
      [
        "acceleration",
        this._t("settings_acceleration"),
        this._t("settings_acceleration_help"),
      ],
    ]) {
      grid.appendChild(
        this._numberControl({
          id: `settings-${wheel.key}-${name}`,
          label,
          help,
          range: this._numberRange("settings_numbers", name),
          value: draft[name],
          onChange: (next) => this._updateSettingsDraft(wheel, { [name]: next }),
        }).wrap,
      );
    }
    section.appendChild(grid);

    const actions = el("div", "settings-actions");
    const save = el("button", "action-button", this._t("settings_save"));
    save.type = "button";
    save.dataset.primary = "true";
    save.disabled = this._settingsBusy;
    save.addEventListener("click", () => this._saveSettings(wheel, "dial"));
    actions.appendChild(save);
    const status = this._settingsStatus("dial");
    if (status) actions.appendChild(status);
    section.appendChild(actions);
    return section;
  }

  _channelsView(wheel) {
    const wrap = el("div");
    wrap.appendChild(this._sectionHead(this._t("detail_channels_intro")));

    const open =
      wheel.channels.find((item) => item.channel === this._openChannel) ||
      wheel.channels[0];
    if (!open) return wrap;

    const workbench = el("div", "channel-workbench");
    // The wheel's three selector positions ARE the navigation: the spine mirrors
    // the hardware, so picking a position on screen is the same act as clicking
    // one in the hand. Every channel of every wheel is compared on the overview;
    // the detail is a workbench for one.
    const spine = el("div", "channel-spine");
    spine.setAttribute("role", "tablist");
    spine.setAttribute("aria-orientation", "vertical");
    spine.setAttribute("aria-label", this._t("channel_spine"));
    wheel.channels.forEach((channel, index) => {
      const dot = el(
        "button",
        "channel-position",
        String(channel.channel),
      );
      dot.type = "button";
      dot.id = `spine-${wheel.key}-${channel.channel}`;
      dot.setAttribute("role", "tab");
      dot.setAttribute("aria-selected", String(channel.channel === open.channel));
      dot.setAttribute("aria-controls", `channel-${wheel.key}-${channel.channel}`);
      dot.tabIndex = channel.channel === open.channel ? 0 : -1;
      const configured =
        channel.profile !== null && channel.profile !== undefined;
      // A disabled channel reads as disabled before anything else: whatever
      // binding it still holds is not going to run.
      if (channel.enabled === false) dot.classList.add("channel-position-off");
      dot.setAttribute(
        "aria-label",
        `${this._t("channel_title", { channel: channel.channel })}: ${
          channel.enabled === false
            ? this._t("settings_disabled_badge")
            : configured
              ? channel.behaviour || channel.profile
              : this._t("not_configured")
        }`,
      );
      dot.addEventListener("click", () => this._openChannelAt(channel.channel));
      dot.addEventListener("keydown", (event) => {
        const keys = {
          ArrowDown: (index + 1) % wheel.channels.length,
          ArrowRight: (index + 1) % wheel.channels.length,
          ArrowUp: (index - 1 + wheel.channels.length) % wheel.channels.length,
          ArrowLeft: (index - 1 + wheel.channels.length) % wheel.channels.length,
          Home: 0,
          End: wheel.channels.length - 1,
        };
        const next = keys[event.key];
        if (next === undefined) return;
        event.preventDefault();
        spine.querySelectorAll('[role="tab"]')[next]?.focus();
      });
      spine.appendChild(dot);
    });
    workbench.appendChild(spine);

    const surface = el("div", "channel-surface");
    surface.id = `channel-${wheel.key}-${open.channel}`;
    surface.setAttribute("role", "tabpanel");
    surface.setAttribute("aria-labelledby", `spine-${wheel.key}-${open.channel}`);
    surface.appendChild(this._channelDetail(wheel, open));
    workbench.appendChild(surface);

    wrap.appendChild(workbench);
    wrap.appendChild(this._activeChannelsSection(wheel));
    wrap.appendChild(this._dialSection(wheel));
    return wrap;
  }

  _buttonsView(wheel) {
    const wrap = el("div");
    wrap.appendChild(this._sectionHead(this._t("detail_buttons_intro")));

    const buttons = wheel.buttons || [];
    const open =
      buttons.find((item) => item.button === this._openButton) || buttons[0];
    if (!open) return wrap;

    const workbench = el("div", "channel-workbench");
    const spine = el("div", "channel-spine");
    spine.setAttribute("role", "tablist");
    spine.setAttribute("aria-orientation", "vertical");
    spine.setAttribute("aria-label", this._t("button_spine"));
    buttons.forEach((button, index) => {
      const position = el("button", "channel-position", String(button.button));
      position.type = "button";
      position.id = `button-${wheel.key}-${button.button}`;
      position.setAttribute("role", "tab");
      position.setAttribute(
        "aria-selected",
        String(button.button === open.button),
      );
      position.setAttribute(
        "aria-controls",
        `button-panel-${wheel.key}-${button.button}`,
      );
      position.tabIndex = button.button === open.button ? 0 : -1;
      position.setAttribute(
        "aria-label",
        `${this._t("button_title", { button: button.button })}: ${
          this._isConfigured(button)
            ? button.behaviour || this._t("configured")
            : this._t("not_configured")
        }`,
      );
      position.addEventListener("click", () =>
        this._openButtonAt(button.button),
      );
      position.addEventListener("keydown", (event) => {
        const keys = {
          ArrowDown: (index + 1) % buttons.length,
          ArrowRight: (index + 1) % buttons.length,
          ArrowUp: (index - 1 + buttons.length) % buttons.length,
          ArrowLeft: (index - 1 + buttons.length) % buttons.length,
          Home: 0,
          End: buttons.length - 1,
        };
        const next = keys[event.key];
        if (next === undefined) return;
        event.preventDefault();
        spine.querySelectorAll('[role="tab"]')[next]?.focus();
      });
      spine.appendChild(position);
    });
    workbench.appendChild(spine);

    const surface = el("div", "channel-surface");
    surface.id = `button-panel-${wheel.key}-${open.button}`;
    surface.setAttribute("role", "tabpanel");
    surface.setAttribute(
      "aria-labelledby",
      `button-${wheel.key}-${open.button}`,
    );
    surface.appendChild(this._channelDetail(wheel, open));
    workbench.appendChild(surface);
    wrap.appendChild(workbench);
    return wrap;
  }

  _gestureLabel(activity) {
    const button = activity.button;
    if (button !== null && button !== undefined) {
      const keys = {
        press:
          activity.presses === 2
            ? "gesture_button_press_double"
            : "gesture_button_press_single",
        hold: "gesture_button_hold",
        release: "gesture_button_release",
      };
      return this._withObservedDuration(
        this._t(keys[activity.gesture] || "gesture_button_unknown", {
          button,
        }),
        activity,
      );
    }
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
    if (activity.gesture === "hold") {
      return this._withObservedDuration(
        this._t("gesture_hold", { channel }),
        activity,
      );
    }
    if (activity.gesture === "release") {
      return this._withObservedDuration(
        this._t("gesture_release", { channel }),
        activity,
      );
    }
    return this._t("gesture_unknown", { channel });
  }

  _withObservedDuration(label, activity) {
    const milliseconds = Number(activity.observed_duration_ms);
    if (
      !Number.isFinite(milliseconds) ||
      milliseconds < 0 ||
      !["hold", "release"].includes(activity.gesture)
    ) {
      return label;
    }
    const seconds = new Intl.NumberFormat(this._language || "en", {
      maximumFractionDigits: 2,
    }).format(milliseconds / 1000);
    return `${label} · ${this._t("gesture_observed_duration", {
      duration: seconds,
    })}`;
  }

  _dispatchLabel(activity) {
    const labels = {
      accepted: ["success", "dispatch_accepted"],
      pending: ["unknown", "dispatch_pending"],
      failed: ["failed", "dispatch_failed"],
      skipped: ["failed", "dispatch_skipped"],
      not_configured: [
        "unknown",
        activity.button !== null && activity.button !== undefined
          ? "dispatch_not_configured_button"
          : "dispatch_not_configured",
      ],
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

  _recognizedResult(activity) {
    if (activity.gesture === "press") {
      const press =
        activity.presses === 2
          ? "result_gesture_double_press"
          : activity.presses === 3
            ? "result_gesture_triple_press"
            : "result_gesture_press";
      return this._t(press);
    }
    const labels = {
      rotate: "result_gesture_rotate",
      hold: "result_gesture_hold",
      release: "result_gesture_release",
    };
    return this._t(labels[activity.gesture] || "result_gesture_received");
  }

  _liveResult(activity) {
    return activity.result === null || activity.result === undefined
      ? this._recognizedResult(activity)
      : this._formatResult(activity.result);
  }

  _liveResultLabel(activity) {
    return this._t(
      activity.result === null || activity.result === undefined
        ? "live_event_label"
        : "live_result_label",
    );
  }

  _liveExplanation(activity) {
    if (activity.result !== null && activity.result !== undefined) return null;
    if (activity.dispatch_status === "not_configured") {
      return this._t(
        activity.button !== null && activity.button !== undefined
          ? "result_not_configured_button_detail"
          : "result_not_configured_channel_detail",
      );
    }
    if (
      activity.dispatch_status === "received" ||
      activity.dispatch_status === "pending"
    ) {
      return this._t("result_pending_detail");
    }
    return this._t("result_unavailable_detail");
  }

  _configureFromLive(wheel, activity) {
    const number =
      wheel.variant === "dual_button" ? activity.button : activity.channel;
    const control = this._controlsFor(wheel).find(
      (item) => this._controlNumber(wheel, item) === number,
    );
    if (!control) return;
    this._stopActivity();
    this._activityError = false;
    this._view = wheel.variant === "dual_button" ? "buttons" : "channels";
    if (wheel.variant === "dual_button") this._openButton = number;
    else this._openChannel = number;
    this._startEditor(wheel, control);
  }

  async _testBinding(wheel, control, gesture, extra = {}) {
    if (this._testBusy) return;
    this._testBusy = true;
    this._testMessage = null;
    this._render();
    try {
      const response = await this._hass.callWS({
        type: BINDING_TEST,
        wheel: wheel.key,
        [wheel.variant === "dual_button" ? "button" : "channel"]: control,
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
    const isButton = wheel.variant === "dual_button";
    panel.appendChild(
      el(
        "p",
        null,
        this._t(
          isButton ? "test_controls_button_intro" : "test_controls_intro",
        ),
      ),
    );
    if (this._testMessage) {
      const message = el("p", "form-message", this._testMessage);
      message.setAttribute("role", "status");
      panel.appendChild(message);
    }
    const controls = this._controlsFor(wheel);
    for (const control of controls.filter((item) => item.binding)) {
      const number = this._controlNumber(wheel, control);
      const actions = el("div", "test-actions");
      actions.setAttribute(
        "aria-label",
        this._t(isButton ? "test_button" : "test_channel", {
          [isButton ? "button" : "channel"]: number,
        }),
      );
      const tests = isButton
        ? [
            ["test_single", "press", { presses: 1 }],
            ["test_double", "press", { presses: 2 }],
            ["test_hold", "hold", {}],
            ["test_release", "release", {}],
          ]
        : [
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
          this._t(isButton ? "button_title" : "channel_title", {
            [isButton ? "button" : "channel"]: number,
          }),
        ),
      );
      for (const [label, gesture, extra] of tests) {
        const button = el("button", "action-button", this._t(label));
        button.type = "button";
        button.disabled = this._testBusy;
        button.addEventListener("click", () =>
          this._testBinding(wheel, number, gesture, extra),
        );
        actions.appendChild(button);
      }
      panel.appendChild(actions);
    }
    if (!controls.some((item) => item.binding)) {
      panel.appendChild(
        el(
          "p",
          null,
          this._t(
            isButton ? "test_no_button_bindings" : "test_no_bindings",
          ),
        ),
      );
    }
    return panel;
  }

  _liveControls(wheel) {
    const isButton = wheel.variant === "dual_button";
    const card = el("section", "detail-card live-channels");
    card.appendChild(
      el(
        "h4",
        null,
        this._t(isButton ? "live_buttons_heading" : "live_channels_heading"),
      ),
    );
    for (const control of this._controlsFor(wheel)) {
      const number = this._controlNumber(wheel, control);
      const row = el("div", "live-channel");
      row.appendChild(el("span", "channel-n", String(number)));
      const copy = el("div", "live-channel-copy");
      copy.appendChild(
        el(
          "div",
          "live-channel-title",
          this._t(isButton ? "button_title" : "channel_title", {
            [isButton ? "button" : "channel"]: number,
          }),
        ),
      );
      const configured = this._isConfigured(control);
      const target = this._controlTargetText(control);
      copy.appendChild(
        el(
          "div",
          "live-channel-summary",
          configured
            ? [control.behaviour || control.profile, target]
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

  // Eighteen is the highest rotary count DEVICE_REFERENCE.md has ever observed,
  // so the strip is a measured scale of what this hardware can emit in one
  // batch, not a decorative bar. Do not change the count without a new
  // observation to justify it.
  _detentStrip(notches) {
    const total = 18;
    const active = Math.min(Math.abs(Number(notches) || 0), total);
    const strip = el("div", "detent-strip");
    strip.setAttribute(
      "aria-label",
      this._t("gesture_rotate", {
        channel: "",
        direction: "",
        delta: active,
      }).trim(),
    );
    for (let index = 0; index < total; index += 1) {
      const detent = el("span", "detent");
      if (index >= total - active) detent.dataset.active = "true";
      strip.appendChild(detent);
    }
    return strip;
  }

  _liveView(wheel) {
    const isButton = wheel.variant === "dual_button";
    const wrap = el("div");
    wrap.appendChild(
      this._sectionHead(
        this._t(isButton ? "live_button_intro" : "live_intro"),
      ),
    );
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
    const body = el("div", "live-body");
    if (!latest) {
      body.appendChild(
        el(
          "div",
          "waiting-title",
          this._t(
            isButton ? "live_button_waiting_title" : "live_waiting_title",
          ),
        ),
      );
      body.appendChild(
        el(
          "div",
          "live-explanation",
          this._t(
            isButton ? "live_button_waiting_body" : "live_waiting_body",
          ),
        ),
      );
      output.appendChild(body);
    } else {
      body.appendChild(
        el("div", "live-result-label", this._liveResultLabel(latest)),
      );
      body.appendChild(el("div", "live-result", this._liveResult(latest)));
      const explanation = this._liveExplanation(latest);
      if (explanation) {
        body.appendChild(
          el("div", "live-explanation", explanation),
        );
      }
      const [dispatchState, dispatchKey] = this._dispatchLabel(latest);
      const dispatch = el("div", "dispatch");
      dispatch.appendChild(this._statusDot(dispatchState));
      dispatch.appendChild(el("span", null, this._t(dispatchKey)));
      body.appendChild(dispatch);
      if (latest.dispatch_status === "not_configured") {
        const number = isButton ? latest.button : latest.channel;
        const control = this._controlsFor(wheel).find(
          (item) => this._controlNumber(wheel, item) === number,
        );
        if (control) {
          const configure = el(
            "button",
            "action-button live-setup-action",
            this._t(isButton ? "live_setup_button" : "live_setup_channel", {
              [isButton ? "button" : "channel"]: number,
            }),
          );
          configure.type = "button";
          configure.dataset.primary = "true";
          configure.addEventListener("click", () =>
            this._configureFromLive(wheel, latest),
          );
          body.appendChild(configure);
        }
      }
      output.appendChild(body);

      output.appendChild(el("div", "gesture-caption", this._gestureLabel(latest)));
      if (latest.source === "panel_test") {
        output.appendChild(
          el("div", "gesture-caption", this._t("source_panel_test")),
        );
      }
      if (latest.gesture === "rotate") {
        output.appendChild(this._detentStrip(latest.notches));
      }
    }
    layout.appendChild(output);

    const side = el("div", "live-side");
    side.appendChild(this._liveControls(wheel));
    if (this._activities.length) {
      const recent = el("section", "detail-card recent");
      const recentHeading = el("h4", null, this._t("live_recent"));
      recentHeading.id = `live-recent-${wheel.key}`;
      recent.appendChild(recentHeading);
      const list = el("ol");
      list.id = `live-recent-list-${wheel.key}`;
      list.tabIndex = 0;
      list.setAttribute("aria-labelledby", recentHeading.id);
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
    wrap.appendChild(this._sectionHead(this._t("diagnostics_intro")));
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

    const status = el("section", "diagnostic-section");
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

    const activity = el("section", "diagnostic-section");
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
        this._t(
          wheel.variant === "dual_button"
            ? "detail_last_button"
            : "detail_last_channel",
        ),
        wheel.variant === "dual_button"
          ? wheel.last_active_button ?? this._t("detail_no_last_button")
          : wheel.last_active_channel ?? this._t("detail_no_last_channel"),
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
    } else if (this._view === "buttons") {
      panel.appendChild(this._buttonsView(wheel));
    } else panel.appendChild(this._channelsView(wheel));
    return panel;
  }

  _detail(wheel) {
    const shell = el("div", "detail-shell");
    shell.appendChild(this._rail());

    const pane = el("div", "detail-pane");
    const inner = el("div", "detail-inner");
    if (!this._snapshot.matter_connected) {
      inner.appendChild(this._banner(this._t("banner_matter_offline")));
    } else if (this._error) {
      inner.appendChild(this._banner(this._t("banner_updates_stopped")));
    }
    inner.appendChild(this._mobileBack());
    inner.appendChild(this._detailTop(wheel));
    inner.appendChild(this._tabs(wheel));
    inner.appendChild(this._detailPanel(wheel));
    pane.appendChild(inner);
    shell.appendChild(pane);
    return shell;
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
      this._controlsFor(wheel).some(
        (control) => targetState(control) === "missing",
      ),
    );
    if (missing.length === 1) {
      // The backend knows the exact device and control, so the banner says so.
      const wheel = missing[0];
      const control = this._controlsFor(wheel).find(
        (item) => targetState(item) === "missing",
      );
      const isButton = wheel.variant === "dual_button";
      wrap.appendChild(
        this._banner(
          this._t(
            isButton
              ? "banner_target_missing_button_named"
              : "banner_target_missing_named",
            isButton
              ? { wheel: wheel.name, button: control.button }
              : { wheel: wheel.name, channel: control.channel },
          ),
        ),
      );
    } else if (missing.length > 1) {
      wrap.appendChild(
        this._banner(
          this._t("banner_target_missing", { count: missing.length }),
        ),
      );
    }
    wrap.appendChild(this._overviewHead());
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
    // The detail's rail runs to the viewport edge, so the page frame lives on
    // .detail-pane instead of here.
    if (this._open && this._snapshot) main.dataset.view = "detail";
    main.appendChild(this._body());
    this.shadowRoot.replaceChildren(style, this._header(), main);
    if (focused) this.shadowRoot.getElementById(focused)?.focus({ preventScroll: true });
  }
}

if (!customElements.get("ikea-bilresa-panel")) {
  customElements.define("ikea-bilresa-panel", IkeaBilresaPanel);
}
