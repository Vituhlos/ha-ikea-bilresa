# Troubleshooting

[README](../../README.md) · [All guides](../README.md) · **English** · [Čeština](../cs/troubleshooting.md)

**Enable debug logging** (Settings → System → Logs, or):

```yaml
logger:
  logs:
    custom_components.ikea_bilresa: debug
```

- **No wheels discovered** — confirm the wheel works in the core Matter
  integration and that the Matter Server URL is correct. The log prints
  `Discovered BILRESA wheel: node …` on startup.
- **Connected, but no events when you turn or press** — go in this order:
  1. In **Settings → Devices & Services → Matter**, open the BILRESA device. Do
     its `event.*` entities update when you turn the wheel or press? If not, the
     cause is below this integration (battery, Thread network or border router,
     pairing); fix that first.
  2. Open the BILRESA panel, choose the device and open **Live test**. Turn one
     notch and press once. If rows appear, events reach the integration. If the
     core entities update but the Live test stays empty, go on to step 3.
  3. Open **Diagnostics** in the panel: it shows whether Matter is connected,
     which event source is in use (the core Matter client or the dedicated
     WebSocket) and when the last event arrived. Enable debug logging as above.
  4. Check the channel: the wheel has a 3-position selector and only the
     selected channel sends. A channel switched off in the panel emits nothing
     (its switch is on its card).
  5. Still silent? Open a [bug report](https://github.com/Vituhlos/ha-ikea-bilresa/issues/new/choose) with the Home Assistant Core
     version, the Matter Server version, the device model and firmware, whether
     it is also paired to another controller, what Live test and Diagnostics
     show, and the integration's downloaded diagnostics (**Settings → Devices &
     Services → IKEA BILRESA → ⋮ → Download diagnostics**; it redacts known
     identifiers, but look through it before attaching it).
- **Wrong channel** — the physical wheel has a 3-position channel selector; the
  active channel is what fires.
- **A button in the panel has no readable label in my theme** — the panel fills
  its primary buttons with the accent colour, which is the theme's
  `state-icon-color`, and writes on them in the theme's `text-primary-color`.
  A theme that sets both to one colour (some light-on-dark themes do) makes the
  label as bright as its fill. Set the panel's own variables in the theme, which
  change nothing else in Home Assistant:

  ```yaml
  # in your theme
  bilresa-accent: "#44739e"                # optional: the fill
  bilresa-on-accent: "rgba(0, 0, 0, 0.85)" # the label on the fill
  ```

  Both are optional and fall back to `state-icon-color` and
  `text-primary-color`, so a theme that does not set them looks as before.
