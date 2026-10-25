# Security policy

## Supported versions

Fixes are released on top of the latest stable version. Older releases and
pre-releases (`*-rc.*`) are not patched — please upgrade before reporting
problems that may already be fixed.

| Version          | Supported |
| ---------------- | --------- |
| Latest release   | Yes       |
| Older releases   | No        |

## Reporting a vulnerability

GitHub private vulnerability reporting is **not** enabled for this repository
yet, so there is currently no confidential reporting channel.

- If the issue is **not sensitive**, open a normal
  [bug report](https://github.com/Vituhlos/ha-ikea-bilresa/issues/new/choose).
- If the report **is sensitive** (e.g. it could affect other users' systems),
  open an issue with minimal detail — for example a short "possible security
  issue, requesting a private contact" — and a maintainer will get in touch
  through that issue to arrange a private channel.

The integration is passive by design: it only subscribes to Matter Switch
cluster events and never sends commands to devices. Reports about command
injection, credential handling or data exposure are still taken seriously.
