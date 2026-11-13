# Recorded contribution examples / Zaznamenané příklady

Captured with read-only GitHub REST requests on **2026-11-13**, from
`Vituhlos/ha-ikea-bilresa`. These are deterministic input fixtures, not AI output.

| Reference | Revision |
|---|---|
| main | `b2118a32c12afad465d68f1fc699694c0e8f1dfd` |
| agent/panel-0.6.1 | `28c1035f30411fc105575fdd64a9ede19c623c44` |
| stable v0.6.1 | `514811a9b1cc1536591c513a1d1d4ef369cc951f` |
| PR #71 head | `f44ddfd229189667849c9583b99b4e639e63e40b` |

- [#70](https://github.com/Vituhlos/ha-ikea-bilresa/issues/70): first-notch fade request; existing later-batch smoothing is a different behavior.
- [#9](https://github.com/Vituhlos/ha-ikea-bilresa/issues/9): merged #14, development source observations and two existing owner follow-ups; exact reporter hardware remains pending.
- [#71](https://github.com/Vituhlos/ha-ikea-bilresa/pull/71): contributor's zero-bound fix, seven changed paths, exact-head check runs including the skipped optional job. Reproducing the old bug is not testing the patched build.

Reduction is explicit: API fields not used by the collector were removed;
third-party bot prose was omitted; related PR bodies retain only local `#N`
references. `sources.json` retains selected **original source lines**, replacing
other lines with blanks to preserve line numbers. `retainedLines` identifies
these excerpts; `originalContentSha256` is SHA-256 of the full captured UTF-8
content. Fixture-generated file/method digests describe these excerpts, **not
the full upstream files**. Live collection hashes complete bounded source files.
No fixture code is imported or executed. Test symbols are source evidence,
not a claim that those runtime tests ran in this task.

Refresh deliberately: resolve all revisions again, read the issues, full paginated
PR file/check lists and source files at those immutable SHAs, review/redact the
data, preserve excerpt line numbers, and review expected assertions. Do not
blindly regenerate expectations from the implementation under test.

Česky: vstupy pocházejí ze skutečných veřejných #70, #9 a #71 a z revizí v tabulce.
Nepoužívaná metadata a botí texty byly odstraněny; těla souvisejících PR obsahují
jen odkazy `#N`. Zdrojové výřezy zachovávají původní čísla řádků pomocí prázdných
řádků. Jejich hashe nejsou hashe celých původních souborů; původní SHA-256 je
uloženo zvlášť. Kód fixture se nespouští. Aktualizace vyžaduje kontrolu zdrojů,
redakci a nezávislou kontrolu očekávaných výsledků. Testy ani CI nedokládají
fyzickou validaci opravy.
