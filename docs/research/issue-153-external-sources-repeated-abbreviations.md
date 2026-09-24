# Issue #153 research — repeated abbreviations on the external-citation source list

Date: 2026-09-24. Base: `2a9a2c5e00c18e441b2fb79ec666dad2aba72bd7`.

## Trigger

In the 2026-09-24 user-level MCP end-to-end run (#15), `cal_external_citation_sources(dialect_id="6")` failed with `parser_drift` "CAL external-source page repeats an abbreviation", which blocks the dialect → source → citations workflow.

## Live-current evidence

One bounded GET, `display.notext.abbrevs.php?dial1=6&dial=6`, returned HTTP 200 with 316,643 bytes. The page (heading `Texts With Citations, No Full Text Yet`, CAL's counter `702 texts`) holds 702 `div.cit-row` rows, each an abbreviation link to `displaycits.abbrev.php?abbrev=<abbrev>` plus a `cit-defined` description.

Five abbreviations appear in **two adjacent rows each, with different descriptions and the identical citations link**:

| Abbreviation | Descriptions |
| --- | --- |
| `EbPar` | E. Gismondi, *Ebed-Jesu Sobensis carmina selecta…* Beirut 1888 / P. Cardahi, *Ebedjesu Liber Paridis*, Beirut 1889 |
| `JS` | Jacob of Sarug / Jacob of Sarug in Cureton, *Ancient Syriac Documents* |
| `Lag,` | P. de Lagarde, *Bibliothecae Syriacae* 1892 / P. de Lagarde, *Symmicta* 1877 |
| `PO` | *Patrologia Orientalis* / F. Nau, *Les Légendes Syriaques d'Aaron de Saroug…* |
| `Th` | S.J. Carr, *Thomae Edesseni Tractatus…* / Ed. Sachau, *Theodori Mopsuesteni Fragmenta Syriaca* |

This is CAL's own bibliographic data: several source works share one citation abbreviation, and CAL lists each work while pointing all of them to the same citation list. The parser's assumption that abbreviations are unique is therefore wrong. Nothing in the markup is mis-split.

## Consequences

- Source rows are returned exactly as CAL lists them, in order, including repeated abbreviations with their distinct descriptions. No merging or deduplication.
- The existing per-row check that a link's `abbrev` value equals its displayed abbreviation already guarantees that rows sharing an abbreviation share one citation list, so no extra guard is needed. A repeated abbreviation whose link names another value still fails closed through that check.
- The public schema and request count are unchanged. The docs state that abbreviations are not unique keys, and that `cal_external_citations(source_abbrev)` returns CAL's combined citation list for every work sharing that abbreviation.

## Verification (2026-09-24)

- Offline, the full 702-row capture parses into 702 sources in CAL order.
- Live over MCP (a wheel built from this branch, stdio, 2 sequential requests): `cal_external_citation_sources("6")` → 702 sources, including both `EbPar` rows; `cal_external_citations("EbPar")` → total 26, 26 citations.
