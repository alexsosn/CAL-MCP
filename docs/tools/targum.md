# CAL Targum Studies

CAL-MCP exposes four bounded task-level operations over CAL's current Targum Studies interfaces. Each public tool call performs exactly **one** user-initiated CAL request. Moving from a returned source, concordance row, or Hebrew lemma selector to a second CAL view always requires another explicit caller action; CAL-MCP does not walk biblical verses, enumerate sources, fetch examples, or build a local Targum corpus.

Public tools: `cal_targum_parallel`, `cal_targum_concordance`, `cal_targum_hebrew_lemmas`, and `cal_targum_hebrew_reflexes`.

## Which tool to use

| Goal | Tool |
| --- | --- |
| Compare one biblical verse across MT and CAL's available Targum readings | `cal_targum_parallel(book, chapter, verse, include_peshitta=False, include_samaritan=False)` |
| Count one CAL lemma across CAL's Targum source groups | `cal_targum_concordance(lemma_key)` |
| Discover CAL's MT Hebrew lemma choices for Onqelos or Neofiti reflex study | `cal_targum_hebrew_lemmas(initial, targum)` |
| Retrieve the CAL Aramaic lemma reflexes for one selected MT Hebrew lemma | `cal_targum_hebrew_reflexes(targum, mt_lemma_id)` |

Single-source chapter reading is intentionally **not** duplicated as a Targum-specific MCP tool. Where CAL exposes a source chapter link, it points into CAL's ordinary text browser and can be followed through the existing text tools in a separate caller-controlled step.

## `cal_targum_parallel`

```text
cal_targum_parallel(
    book: string,
    chapter: integer,
    verse: integer,
    include_peshitta: boolean = false,
    include_samaritan: boolean = false,
)
```

This operation returns CAL's rendered comparison for one explicit biblical verse. The result preserves:

- the exact requested CAL book label and CAL's current internal book identifier as provenance/result metadata;
- chapter and verse;
- MT text;
- ordered source readings with CAL's exact rendered source labels;
- optional same-origin CAL chapter URLs where CAL supplies them;
- CAL provenance and retrieval time.

The accepted book labels are CAL's current selector labels:

```text
Gen, Exod, Levit, Numb, Deut, Joshua, Judges,
1 Sam, 2 Sam, 1 Kings, 2 Kings, Isaiah, Jeremiah, Ezekiel,
Hosea, Joel, Amos, Obadiah, Jonah, Micah, Nahum, Hab., Zeph.,
Haggai, Zechariah, Malachi, Psalms, Job, Song of Songs, Ruth,
Qoheleth, Lamentations, Proverbs, 1 Chronicles, 2 Chronicles, Esther
```

`chapter` and `verse` are positive integers bounded at 999. Invalid public values fail before transport.

`include_peshitta` and `include_samaritan` request CAL's optional comparison sources. They do **not** promise that a reading exists for the requested verse. In particular, CAL's Samaritan coverage is conditional; absence remains absence and CAL-MCP never manufactures an empty source row to make the result look uniform.

CAL currently reports an invalid/missing biblical coordinate through an HTTP-200 page containing its explicit `error in coordinate` semantic marker. CAL-MCP represents that as `status: "not_found"` only when no valid comparison blocks are also present. A page that contradicts the marker or lacks the required comparison semantics fails closed as parser drift.

## `cal_targum_concordance`

```text
cal_targum_concordance(lemma_key: string)
```

This operation asks CAL for its Targum-specific source/count table for one canonical CAL lemma key. Callers should normally reuse a `lemma_key` returned by CAL-MCP lexicon, token-analysis, concordance, or search results rather than constructing one heuristically.

The result preserves:

- the canonical CAL `lemma_key`;
- ordered rows;
- CAL's section headings separately from individual source labels;
- exact source labels;
- occurrence counts;
- absolute same-origin CAL example URLs;
- CAL's reported total;
- provenance.

A complete CAL table in which every row is zero and `total examples: 0` is a valid successful empty concordance. It is not treated as parser drift. Conversely, missing table/heading/total semantics, nonnumeric counts, malformed links, or a total that disagrees with the sum of parsed source counts fail closed.

Returned example URLs are navigation metadata only. CAL-MCP does not automatically follow them or fetch detailed KWIC examples.

## Hebrew lemma discovery and reflexes

CAL's current MT-Hebrew-to-Targumic-lemma workflow is intentionally exposed as two explicit operations because the upstream selector ID is CAL-owned and opaque.

### Step 1: discover an MT Hebrew lemma

```text
cal_targum_hebrew_lemmas(
    initial: string,
    targum: string,
)
```

`targum` currently accepts:

- `onqelos`;
- `neofiti`.

CAL currently marks the corresponding Pseudo-Jonathan workflow as under development, so CAL-MCP does not advertise it as supported.

`initial` is one of CAL's current Hebrew-letter selector slugs:

```text
alef, bet, gimel, dalet, heh, waw, zayin, xet, tet, yod, kaf,
lamed, mem, nun, samekh, ayin, peh, cade, qof, resh, shin, sin, taw
```

The result preserves the chooser's order and, for each candidate:

- opaque `mt_lemma_id`;
- vocalized/rendered Hebrew label;
- displayed part-of-speech label.

The opaque ID is not decoded or assigned linguistic meaning by CAL-MCP.

### Step 2: retrieve Targumic reflexes

```text
cal_targum_hebrew_reflexes(
    targum: string,
    mt_lemma_id: string,
)
```

Use an ID returned by the discovery operation. Public IDs must be positive decimal strings of at most eight digits.

The result preserves:

- selected Targum source;
- opaque MT lemma ID;
- CAL's source label;
- selected rendered MT Hebrew lemma;
- ordered CAL Aramaic lemma correspondences;
- each canonical CAL `lemma_key` and CAL-rendered label separately;
- frequency;
- absolute same-origin CAL example URL;
- provenance.

The two-step boundary is deliberate. One discovery call plus one reflex call means two caller-controlled CAL requests; CAL-MCP never selects a Hebrew lemma or follows all candidates automatically.

CAL has a notable invalid-ID fallback: a nonexistent opaque MT selector may return a broad frequency list with a heading ending at `correspondences to` and no selected Hebrew lemma. CAL-MCP rejects that response as parser drift instead of presenting an unrelated broad list as the requested result.

## CAL labels and Unicode fidelity

CAL-MCP preserves CAL's source/version labels and returned order. It does not harmonize names such as `Onqelos:`, `Pseudo Jonathan:`, `Neofiti:`, or fragment labels into a local ontology, and it does not infer equivalence between versions.

Hebrew, Aramaic, and Syriac rendered text is preserved through ordinary HTML text extraction. CAL-MCP does not add vocalization, transliteration, morphological analysis, or reconstructed readings to these Targum results.

## Request and traversal bounds

Every public Targum operation performs exactly one CAL request:

- one verse-comparison request;
- one Targum concordance request;
- one source/initial MT-lemma chooser request;
- one selected MT-lemma reflex request.

There is no hidden biblical verse walking, all-book traversal, all-version expansion, chooser-alphabet crawl, concordance example fetching, chapter prefetch, background indexing, or local mirror. The shared CAL HTTP client still enforces origin, redirect, timeout, concurrency, retry, cache/single-flight, and response-size policy.

Private CAL form fields such as `bookname`, `Peshitta`, `Sam`, `R1`, `lemma`, `pos`, `texts`, and `charset` are adapter implementation details and are not public MCP parameters.

## Empty results, upstream failures, and parser drift

The adapter keeps these states distinct:

- an explicit CAL `error in coordinate` with no result blocks → typed parallel `not_found`;
- a complete Targum concordance table with total zero → valid successful zero result;
- invalid public values → local caller error before transport;
- network, timeout, HTTP, maintenance/content, redirect, and oversized-response failures → shared request-layer failures;
- wrong-query headings, missing semantic tables/forms, contradictory totals, malformed or cross-origin links, invalid opaque IDs returned by CAL, or CAL's broad invalid-ID reflex fallback → `TargumParseError`.

CAL-MCP does not convert a successful-looking but structurally unrecognized page into an empty result.

## Provenance

Results include adapter provenance with:

- `source: "CAL"`;
- actual `source_url`;
- timezone-aware `retrieved_at`;
- operation name;
- relevant submitted public values such as book/chapter/verse, canonical lemma key, Targum source, selector initial, or opaque MT lemma ID;
- CAL's current book identifier for parallel comparison where applicable.

Duplicate-request cache hits retain the original upstream retrieval timestamp and source URL under the shared request-layer provenance contract.

## Fixture-backed contracts

The normal test suite is offline. Reduced semantic fixtures were captured/rechecked during the bounded **2026-09-05** Targum audit and cover:

- Gen 1:1 with MT, multiple ordered Targum readings, Unicode Hebrew/Aramaic/Syriac, optional Peshitta, and absent Samaritan output;
- explicit coordinate-not-found output;
- a positive `klb N` Targum concordance and a complete zero-count concordance;
- Onqelos and Neofiti MT Hebrew lemma chooser pages;
- valid Onqelos and Neofiti reflex results for opaque MT lemma ID `1751`;
- CAL's invalid-ID broad-reflex fallback;
- wrong headings, contradictory totals, duplicate IDs, query contradictions, and cross-origin links.

These fixtures are reduced parser contracts, not archived CAL pages. The live research used 15 bounded CAL requests total and did not traverse books, verses, sources, lemma alphabets, KWIC examples, chapters, or corpora automatically.
