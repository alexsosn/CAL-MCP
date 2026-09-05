# CAL Dictionary Spelling Collation

`cal_dictionary_collation` exposes CAL's current Dictionary Spelling Collation as one bounded page lookup. It asks CAL which CAL lemmas are currently associated with one page reference in one selected dictionary. It does not crawl a dictionary, compare every source automatically, or follow returned lemma links.

## Tool

```text
cal_dictionary_collation(source, page)
```

Each call performs exactly one user-initiated CAL request.

## Dictionary sources

The public `source` parameter uses readable CAL-MCP identifiers. CAL's current one-letter HTML form controls remain internal to the adapter.

| `source` | CAL dictionary label |
| --- | --- |
| `jastrow` | Jastrow |
| `lexicon_syriacum` | Lexicon Syriacum |
| `syriac_lexicon` | A Syriac Lexicon |
| `compendious_syriac_dictionary` | A Compendious Syriac Dictionary |
| `djba` | A Dictionary of Jewish Babylonian Aramaic |
| `djpa` | A Dictionary of Jewish Palestinian Aramaic |
| `levy_targumim` | Levy, Chaldäisches Wörterbuch ü.die Targumim |
| `mandaic_dictionary` | A Mandaic Dictionary |
| `dnsi` | Dictionary of the Northwest Semitic Inscriptions |
| `thesaurus_syriacus` | Thesaurus Syriacus |
| `samaritan_aramaic` | Dictionary of Samaritan Aramaic |
| `schulthess` | Schulthess Lexicon Syropalaestinum |
| `dcpa` | A Dictionary of Christian Palestinian Aramaic |
| `judean_aramaic` | A Dictionary of Judean Aramaic |
| `qumran_aramaic` | Dictionary of Qumran Aramaic Page |

These labels and their current CAL selector mapping were rechecked on **2026-09-05**. CAL-MCP validates the dictionary label echoed by the result page. If CAL changes or reassigns a selector value, the adapter fails as parser/upstream drift rather than silently returning a result for another dictionary.

## Page references

`page` is a string because CAL documents both ordinary decimal pages and volume-qualified references. Supported forms are:

```text
705
1:134
1:134, 2:212
```

CAL-MCP accepts decimal `page` and `volume:page` components separated by commas. Outer spaces and spaces around commas are normalized, so:

```text
1:134,2:212
```

is submitted as:

```text
1:134, 2:212
```

The adapter does not guess undocumented page syntax. Empty values, line breaks, ranges such as `100-105`, alphabetic page names, malformed colon/comma forms, values longer than 96 characters, and lists longer than 16 page references fail locally before any CAL request.

## Result fields

A successful result contains:

- `source` — the public CAL-MCP dictionary identifier;
- `source_label` — CAL's exact current rendered dictionary label;
- `page` — the canonical page reference submitted and echoed by CAL;
- ordered `entries`;
- request provenance.

Each entry contains:

- `display_lemma` — the lemma text CAL rendered on the dictionary-collation page;
- `target_lemma_key` — the exact CAL lemma key encoded in that row's entry link;
- `gloss` — CAL's rendered row text after the structural leading colon;
- `entry_url` — the absolute same-origin CAL entry link.

`display_lemma` and `target_lemma_key` are deliberately separate. CAL can display a spelling that links to a different canonical entry. For example, the bounded 2026-09-05 Jastrow page-705 fixture contains:

```text
display_lemma:    lxt V
target_lemma_key: lht V
gloss:            to pant → lht V
```

CAL-MCP preserves that distinction and does not reinterpret it as an adapter-generated equivalence rule.

CAL lemma punctuation is also preserved after normal URL decoding, including CAL characters such as `+`, `#`, `$`, and parentheses.

## Empty results

The current CAL result page explicitly reports an empty dictionary page with:

```text
No data available for that page.
```

CAL-MCP returns that as a successful result with an empty `entries` sequence. A successful HTTP response with neither recognized entries nor that explicit marker is parser drift and fails closed.

Contradictory markup, such as the no-data marker together with result rows, also fails instead of returning a partial or ambiguous answer.

## Parser and link boundaries

Current result rows are read only from CAL's result summary card. A recognized entry row must contain exactly one same-origin `oneentry.php` link with one `lemma` value. The only additional entry-link query control currently accepted is CAL's observed `cits=no` value.

Cross-origin links, unexpected entry endpoints, duplicate/missing lemma values, extra query controls, missing glosses, duplicated result cards, or missing page identity are treated as parser drift.

Navigation links outside the result rows are ignored and never mistaken for lexical entries.

## Request bounds

One `cal_dictionary_collation` call performs exactly one bounded POST to CAL through the shared request layer. There is no runtime form discovery, fallback source-code retry, hidden page traversal, lemma expansion, prefetch, or background indexing.

The shared CAL client supplies:

- same-origin request and redirect boundaries;
- bounded concurrency and timeout behavior;
- transient-only bounded retries;
- duplicate in-flight request suppression;
- process-local cache behavior;
- the configured decoded-response size limit.

If a CAL result exceeds the shared response-size bound, the request fails instead of being truncated.

## Provenance

Results include:

- `source: "CAL"`;
- the actual CAL `source_url`;
- timezone-aware `retrieved_at`;
- `operation: "dictionary_collation"`;
- the public `dictionary_source`;
- `original_page` supplied by the caller;
- canonical `submitted_page`.

Cache hits preserve the original upstream retrieval time and source URL under the shared request-layer provenance policy.

## Coverage and interpretation

CAL describes its dictionary collation data as part of an evolving scholarly database. A returned row means CAL currently stores that correspondence for the selected dictionary/page. Absence from a page result should not be interpreted as proof that no lexical relationship exists outside CAL's stored collation data.

CAL-MCP does not infer dictionary headwords, spelling rules, POS conversions, etymology, or cross-dictionary equivalence beyond CAL's returned rows.

## Fixture-backed contract

Normal CI uses reduced semantic fixtures based on the CAL shape rechecked on **2026-09-05**. Coverage includes:

- Jastrow page 705 with ordered direct and redirect-style entries;
- punctuation-bearing CAL lemma keys;
- explicit empty page behavior;
- all current public source mappings, including the case-sensitive CAL `J` / `j` distinction behind the adapter boundary;
- decimal and volume-qualified page normalization;
- local input bounds;
- source/page identity mismatch;
- malformed, contradictory, cross-origin, and changed markup;
- exact one-request POST mapping and provenance;
- MCP schema exposure without raw CAL form controls.

Normal CI performs zero live CAL requests.
