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

const DEFAULT_BUTTON_BINDING = {
  click_action: "toggle",
  button_response: "multi_press",
  hold_action: "toggle",
  ramp_direction: "alternate",
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

  .detail-shell {
    display: grid;
    grid-template-columns: var(--_rail-width) minmax(0, 1fr);
    align-items: start;
  }
  /* The rail is a wall of the page, not a card floating on it: one hairline
     against the content, no radius, flush with the header. */
  .rail {
    position: sticky;
    inset-block-start: calc(56px + env(safe-area-inset-top, 0px));
    block-size: calc(100dvh - 56px - env(safe-area-inset-top, 0px));
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
  /* Hold and release are one gesture with a beginning and an end, so they read
     as one horizontal sequence rather than two unrelated rows. */
  .gesture-sequence-rail {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
  }
  .gesture-sequence-line {
    inline-size: 16px;
    block-size: 1px;
    background: var(--_accent);
  }
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
  .channel-detail .binding-form {
    margin-block-start: var(--_space-8);
    padding: var(--_space-6) 0 0;
    border-block-start: 1px solid var(--_ink);
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
    .detail-top { gap: var(--_space-3); }
    .detail-glyph { inline-size: 40px; block-size: 40px; }
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
        control.target_missing
          ? this._t("target_unavailable", {
              target: control.target_label || this._t("target_none"),
            })
          : control.target_label || this._t("add_binding"),
      ),
    );
    row.appendChild(text);
    if (control.target_missing) row.appendChild(svg(ICON.alert, "channel-warn"));
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
    const metaNode = el("div", "detail-meta", meta.join(" · "));
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

  _closeEditor() {
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

    if (this._editorMessage) {
      const message = el("p", "form-message", this._editorMessage);
      message.setAttribute("role", "status");
      form.appendChild(message);
    }

    const primary = el("div", "form-grid");
    if (!isButton) {
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
    }
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
    if (!isButton || this._editorData.click_action !== "none") {
      primary.appendChild(
        this._entityField(
          "click_target",
          this._t("field_click_target"),
          ["light", "switch"],
          { optional: !isButton },
        ),
      );
    }
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
    if (this._editorData.hold_action !== "none") {
      primary.appendChild(
        this._entityField(
          "hold_target",
          this._t("field_hold_target"),
          this._editorData.hold_action === "ramp"
            ? ["light"]
            : ["light", "switch"],
          { optional: !isButton },
        ),
      );
    }
    if (isButton && this._editorData.hold_action === "ramp") {
      primary.appendChild(
        this._selectField(
          "ramp_direction",
          this._t("field_ramp_direction"),
          ["alternate", "up", "down"].map((direction) => ({
            value: direction,
            label: this._t(`ramp_direction_${direction}`),
          })),
        ),
      );
    }
    if (!isButton) primary.appendChild(this._scenesField());
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
          label: this._t(
            `${isButton ? "dual_button_response" : "button_response"}_${response}`,
          ),
        })),
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
    if (!isButton) {
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
          "triple_press_target",
          this._t("field_triple_target"),
          ["light", "switch"],
          { optional: true },
        ),
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
      channel.target_missing ||
      (channel.actions || []).some((action) => action.target_missing);
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

    if (configured && (channel.actions || []).length) {
      const actions = el("ul", "channel-action-list");
      const actionValue = (action) => {
        let value = action.action_label;
        if (action.target_label) {
          const target = action.target_missing
            ? this._t("target_unavailable", { target: action.target_label })
            : action.target_label;
          value = `${value} · ${target}`;
        }
        return value;
      };
      const summaries = channel.actions || [];
      for (let index = 0; index < summaries.length; index += 1) {
        const action = summaries[index];
        const release = summaries[index + 1];

        // Hold and release are one gesture with a start and an end, so they
        // share one row and one glyph sequence rather than reading as two
        // unrelated actions.
        if (action.gesture === "hold" && release?.gesture === "release") {
          const item = el("li", "channel-action");
          if (action.target_missing || release.target_missing) {
            item.dataset.state = "warning";
          } else if (this._isNoAction(action) && this._isNoAction(release)) {
            item.dataset.state = "empty";
          }

          const label = el("span", "channel-action-label");
          const rail = el("span", "gesture-sequence-rail");
          rail.setAttribute("aria-hidden", "true");
          rail.appendChild(svg(GESTURE_ICON.hold, "gesture-glyph"));
          rail.appendChild(el("span", "gesture-sequence-line"));
          rail.appendChild(el("span", "gesture-sequence-end"));
          label.appendChild(rail);
          label.appendChild(
            el(
              "span",
              null,
              `${action.gesture_label} → ${release.gesture_label.toLocaleLowerCase(
                this._hass?.language || undefined,
              )}`,
            ),
          );
          item.appendChild(label);
          item.appendChild(
            el(
              "span",
              "channel-action-value",
              this._isNoAction(action) && this._isNoAction(release)
                ? actionValue(action)
                : [action, release].map(actionValue).join(" → "),
            ),
          );
          actions.appendChild(item);
          index += 1;
          continue;
        }

        const item = el("li", "channel-action");
        if (action.target_missing) item.dataset.state = "warning";
        else if (this._isNoAction(action)) item.dataset.state = "empty";
        const label = el("span", "channel-action-label");
        label.appendChild(gestureGlyph(action.gesture));
        label.appendChild(el("span", null, action.gesture_label));
        item.appendChild(label);
        item.appendChild(
          el("span", "channel-action-value", actionValue(action)),
        );
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
      dot.setAttribute(
        "aria-label",
        `${this._t("channel_title", { channel: channel.channel })}: ${
          configured
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
      return this._t(keys[activity.gesture] || "gesture_button_unknown", {
        button,
      });
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
      not_configured: [
        "failed",
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
      const target = control.target_missing
        ? this._t("target_unavailable", {
            target: control.target_label || this._t("target_none"),
          })
        : control.target_label;
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
        el("div", "live-result-label", this._t("live_result_label")),
      );
      body.appendChild(el("div", "live-result", this._formatResult(latest.result)));
      if (latest.result === null || latest.result === undefined) {
        body.appendChild(
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
      body.appendChild(dispatch);
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
      this._controlsFor(wheel).some((control) => control.target_missing),
    );
    if (missing.length === 1) {
      // The backend knows the exact device and control, so the banner says so.
      const wheel = missing[0];
      const control = this._controlsFor(wheel).find(
        (item) => item.target_missing,
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
