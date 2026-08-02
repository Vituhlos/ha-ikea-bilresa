/**
 * Global Home Assistant icon provider for IKEA BILRESA.
 *
 * This module is loaded through frontend.add_extra_js_url(), before the custom
 * panel is opened, so bilresa:scroll-wheel is available to the HA sidebar.
 */

const BILRESA_SCROLL_WHEEL = Object.freeze({
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

const BILRESA_DUAL_BUTTON = Object.freeze({
  viewBox: "0 0 24 24",
  path: `M11.3 1.4 C15.05 1.4 17.65 4.18 17.65 7.9 V15.5 C17.65 19.72 15.02 22.35 11.3 22.35 C7.58 22.35 4.95 19.72 4.95 15.5 V7.9 C4.95 4.18 7.55 1.4 11.3 1.4Z M11.3 2.65 C8.27 2.65 6.2 4.95 6.2 7.98 V15.38 C6.2 18.85 8.38 21.1 11.3 21.1 C14.22 21.1 16.4 18.85 16.4 15.38 V7.98 C16.4 4.95 14.33 2.65 11.3 2.65Z M11.3 4.35 A1.8 1.9 0 1 1 11.3 8.15 A1.8 1.9 0 1 1 11.3 4.35Z M11.3 5.05 A1.13 1.2 0 1 0 11.3 7.45 A1.13 1.2 0 1 0 11.3 5.05Z M11.3 12.23 A0.42 0.42 0 1 1 11.3 13.07 A0.42 0.42 0 1 1 11.3 12.23Z M11.3 17.05 A1.23 1.37 0 1 1 11.3 19.79 A1.23 1.37 0 1 1 11.3 17.05Z M11.3 17.69 A0.64 0.73 0 1 0 11.3 19.15 A0.64 0.73 0 1 0 11.3 17.69Z`,
  secondaryPath: `M13.05 1.35 C16.45 1.85 18.65 4.55 18.65 8.15 V15.48 C18.65 19.28 16.3 21.9 12.95 22.55 L12.68 21.22 C14.95 20.75 16.42 18.62 16.42 15.36 V8 C16.42 5.1 15.2 2.75 13.05 1.35Z`,
});

const getIcon = async (name) => {
  if (name === "scroll-wheel") return BILRESA_SCROLL_WHEEL;
  if (name === "dual-button") return BILRESA_DUAL_BUTTON;
  return undefined;
};

const getIconList = async () => [
  { name: "scroll-wheel" },
  { name: "dual-button" },
];

// Current HA API. Register synchronously at module evaluation so the sidebar
// never needs the custom panel to be opened first.
window.customIcons = window.customIcons || {};
window.customIcons.bilresa = { getIcon, getIconList };

// Backward-compatible API used by older supported frontends.
window.customIconsets = window.customIconsets || {};
window.customIconsets.bilresa = getIcon;
