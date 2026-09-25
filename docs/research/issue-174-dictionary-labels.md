# Issue #174 research — dictionary-collation result labels

Date: 2026-09-25. Base: `f53e523`.

## Trigger

The 2026-09-25 user-level MCP end-to-end run (#15) found that `cal_dictionary_collation` fails with `parser_drift` "CAL dictionary collation result source does not match the submitted source" for `djba` and `schulthess` (`page="100"`).

## Live-current evidence

Sixteen bounded requests through the production `CalHttpClient` (project User-Agent, sequential): the form `searchdicts.html` (GET), then `searchdicts.php` (POST `dict=<code>`, `page=100`) for each of the 15 sources.

| `source` | Form label (`searchdicts.html`) | Result heading (`… page 100 of <i>…</i>`) |
| --- | --- | --- |
| `jastrow` | Jastrow | Jastrow |
| `lexicon_syriacum` | Lexicon Syriacum | Lexicon Syriacum |
| `syriac_lexicon` | A Syriac Lexicon | A Syriac Lexicon |
| `compendious_syriac_dictionary` | A Compendious Syriac Dictionary | A Compendious Syriac Dictionary |
| `djba` | A Dictionary of Jewish Babylonian Aramaic | **Dictionary of Jewish Babylonian Aramaic** |
| `djpa` | A Dictionary of Jewish Palestinian Aramaic | **Dictionary of Jewish Palestinian Aramaic** |
| `levy_targumim` | Levy, Chaldäisches Wörterbuch ü.die Targumim | **Levy Chaldäisches Wörterbuch** |
| `mandaic_dictionary` | A Mandaic Dictionary | A Mandaic Dictionary |
| `dnsi` | Dictionary of the Northwest Semitic Inscriptions | Dictionary of the Northwest Semitic Inscriptions |
| `thesaurus_syriacus` | Thesaurus Syriacus | Thesaurus Syriacus |
| `samaritan_aramaic` | Dictionary of Samaritan Aramaic | Dictionary of Samaritan Aramaic |
| `schulthess` | Schulthess Lexicon Syropalaestinum | **Schulthess** |
| `dcpa` | A Dictionary of Christian Palestinian Aramaic | A Dictionary of Christian Palestinian Aramaic |
| `judean_aramaic` | A Dictionary of Judean Aramaic | A Dictionary of Judean Aramaic |
| `qumran_aramaic` | Dictionary of Qumran Aramaic | Dictionary of Qumran Aramaic |

The form still uses the full titles, and the form codes are unchanged. The result heading of four sources now uses a shorter title. The result-page parser reads all 15 pages: 5, 24, 11, 22, 2, 4, 0, 11, 1, 0, 5, 9, 4, 0 and 1 entries. Three pages (Levy, Thesaurus Syriacus, Judean Aramaic) render CAL's "No data available for that page", which parses as a valid empty result. Levy's new label is therefore evidenced by the `<title>` and heading of an empty page.

## Consequences

- The service accepts, for each source, CAL's form label or its current result-heading label. It returns the heading label as `source_label`, which is the documented contract: CAL's exact rendered label. A heading naming any other dictionary still fails closed.
- The docs table gains the current heading labels.
- The public schema and request counts are unchanged.
