# BILRESA panel design QA

## Comparison target

- Source visual truth:
  - `docs/images/panel/01-native-overview.png` for overview scale and hierarchy;
  - `docs/images/panel/04-selected-combined-direction.png` for desktop detail
    proportions and live-result hierarchy;
  - owner-provided real Home Assistant screenshots from 2026-07-16 for the RC.1
    implementation defects.
- Implementation screenshot: unavailable for the post-RC.1 working tree.
- Intended viewport: desktop 1320-1665 px matching the supplied HA screenshots,
  followed by 380 px and 320 px mobile checks.
- State: overview, channels, idle/active live test, healthy diagnostics.

## Full-view comparison evidence

The RC.1 screenshots and source references were inspected together before the
correction. They established five P1/P2 mismatches: a false third navigation
column, undersized overview composition, equally weighted channel cards,
secondary live-result hierarchy, and default exposure of internal diagnostics.

The working tree addresses those findings in code, but no browser-rendered
post-fix screenshot is available in this Codex task. A source-to-implementation
visual comparison therefore cannot be completed honestly.

## Focused region comparison evidence

Blocked for the same reason. Required focused regions after deployment:

- desktop rail, back action and wheel heading alignment;
- one configured and one empty channel row;
- live result, dispatch status, gesture caption and collapsed synthetic tests;
- diagnostics health statement and collapsed technical details;
- overview card width and two-column centering.

## Comparison history

### Iteration 1 - RC.1 owner screenshots

- P1: desktop back action formed a third column between rail and content.
- P1: live test did not visually lead with the calculated result.
- P2: overview was narrow and left-heavy on a wide viewport.
- P2: channel cards had equal weight regardless of configuration.
- P2: diagnostics repeated headings and exposed `Panel contract` by default.

### Working-tree fixes

- Desktop back action moved into the 256 px rail; mobile back remains in-pane.
- Overview constrained to a centered 1120 px frame with responsive `auto-fit`
  columns.
- Channels consolidated into one continuous surface with responsive gesture
  summaries.
- Live result promoted to hero scale; configured channels/recent activity moved
  to a secondary column; synthetic tests collapsed.
- Diagnostics now leads with health and hides contract data under technical
  details.

### Post-fix evidence

Not yet captured. The custom panel must be packaged, installed, opened in a new
Home Assistant tab and screenshotted at matching states and viewports.

## Required fidelity surfaces

- Fonts and typography: HA font tokens retained; post-fix optical hierarchy
  needs browser review.
- Spacing and layout rhythm: token-based spacing retained; rail/content and
  overview measurements need screenshot confirmation.
- Colors and visual tokens: HA semantic theme variables retained; light, dark
  and one non-default theme remain to be visually checked.
- Image quality and assets: no raster imagery is required; existing standard MDI
  paths remain the only icons.
- Copy and content: English/Czech keys remain paired; real wrapping needs desktop
  and mobile screenshots.

## Remaining blocker

The current task surface cannot control the authenticated Home Assistant browser
or capture the post-fix implementation. Static and unit checks cannot replace
visual comparison.

final result: blocked
