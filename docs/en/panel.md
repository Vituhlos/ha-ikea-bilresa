# The BILRESA panel

[README](../../README.md) · [All guides](../README.md) · **English** · [Čeština](../cs/panel.md)

Home Assistant adds an **IKEA BILRESA** entry to the sidebar (administrators
only; you can hide it like any other panel). It is where you see and set up
everything without YAML.

- **Overview.** Every wheel and dual button the integration found, with its
  name, area and the time of its last activity. A banner says when Matter is
  disconnected, when live updates have stopped, or when a binding points to an
  entity that no longer exists.
- **A device's page** has three tabs. *Channels* (a dual button has *Buttons*)
  lists each channel with what every gesture does and on what, and an **Edit
  binding** button; a switch on the channel turns it off, and a channel that is
  off does nothing until you turn it back on. *Live test* shows each gesture as
  it is recognised and the action it sent to its target, but only while the tab
  is open. *Diagnostics* is a read-only view of availability, the Matter
  connection, the event source in use and the device link; private Matter
  identifiers are not shown.
- **The editor** has one section for each gesture: rotation (a wheel only),
  short press, double press, triple press (a wheel only) and hold. Each shows its
  action and its target. The short press also holds the **response**: wait for
  single/double/triple press, run after the first short release, or run on the
  initial press (see [Control bindings](bindings.md#gui-control-bindings-turnkey-control)).
  A response that rules a gesture out says so in that gesture's section instead
  of failing on save. **Save binding** checks the fields and marks any it
  refuses; **Discard** closes an untouched editor at once and asks for a second
  press when there are unsaved changes; **Delete binding** asks to confirm. If
  the binding was changed elsewhere in the meantime, the panel says so instead of
  overwriting it.
- **Dial.** Each wheel channel has a number entity (1 to 100) that scrolling
  moves. The *Dial* section sets how far one notch moves it and how much
  turning faster adds; it does not affect the binding.
- **Language and theme.** The panel follows the language chosen in each user's
  own profile (English or Czech). A theme that makes the primary buttons
  unreadable can set two variables; see [Troubleshooting](troubleshooting.md).

The panel can be used instead of, or together with, the native flow described in
[control bindings](bindings.md#gui-control-bindings-turnkey-control); both write
the same bindings.
