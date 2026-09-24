# Issue #151 research — lexicon citation context for Babylonian Talmud texts

Date: 2026-09-24. Base: `2a9a2c5e00c18e441b2fb79ec666dad2aba72bd7`.

## Trigger

In the 2026-09-24 user-level MCP end-to-end run (#15), `cal_lexicon_lookup(query="br", lemma_key="br N")` returned a citation `BT Git 48a(50)` with `full_coordinate: "7101801048150"`. Following it with `cal_lexicon_citation_context("7101801048150")` failed with `LexiconCitationContextParseError: CAL citation context has neither text rows nor an explicit no-citations marker`. Over MCP this surfaced misleadingly as `kind: content`, "rejected as unsafe"; that classification is #156.

## Live-current evidence

One GET made during the E2E triage, `https://cal.huc.edu/showachapter.php?fullcoord=7101801048150`, returned HTTP 200 with 14,578 bytes of `text/html; charset=UTF-8`:

- the file-info link `/get_file_info.php?coord=7101801048` with label `71018: BT Git`;
- 21 `<tr>` rows. Text rows have two cells: a coordinate cell whose visible label is manuscript-style (`ms01 pg048 sd1 ln05`) and a Hebrew text cell. Separator rows are `<td colspan="2"><hr></td>`;
- the **target row** `7101801048150` (`ms01 pg048 sd1 ln50`) is present, bold, and its coordinate is a red `comment.php?coord=7101801048150` link;
- every lexical token link uses **`bablex.php?coord=…&word=…`**, not `getlex.php`.

The page is complete and consistent. The parser recognises text rows only by `getlex.php` token links, so it found no text rows.

This is the second lexical-token link family already recorded for text pages in R-024 (Babylonian Talmud texts such as `BT AZ` use `bablex.php`), and `texts.py` already accepts both families. The citation-context parser (fixtures `Ezra 4:24` and `TgJ Ez 31:6`) was built only against `getlex.php` texts. So this is a long-standing gap for Babylonian Talmud citations, not new upstream drift.

## Consequences

- Citation-context text rows accept both current CAL lexical-token families, `getlex.php` and `bablex.php`, with the same query-shape validation (`coord` and `word` only), coordinate/word-index checks, same-origin rule and exact returned URL.
- One row must not mix the two families. Mixing fails closed.
- The public schema, request count and target/not-found semantics are unchanged.

## Verification (2026-09-24)

- Offline, the full 14,578-byte live page parses as `found`: 19 text lines (21 rows minus 2 separators), target `ms01 pg048 sd1 ln50` reading `אלא חד בר חד עד יהושע בן נון,`, which contains the lexicon citation's `חד בר חד`.
- Live over MCP (a wheel built from this branch, stdio, 2 sequential requests):
  - `cal_lexicon_citation_context("7101801048150")` → `found`, `71018: BT Git`, 19 lines, `bablex.php` token URLs;
  - `cal_lexicon_citation_context("31000424")` (a `getlex.php` text) → `found`, `31000: BA Ezra chapter 4`, 17 lines, unchanged behaviour.
