# CAL Targum Studies

CAL-MCP exposes six bounded task-level operations over CAL's current Targum Studies interfaces. Each valid explicit operation submits at most one new logical CAL request to the shared client. Moving from a returned source, concordance row, or Hebrew lemma selector to a second CAL view always requires another explicit caller action; CAL-MCP does not walk biblical verses, enumerate sources, automatically fetch examples, or build a local Targum corpus.

Public tools: `cal_targum_parallel`, `cal_targum_concordance`, `cal_targum_concordance_examples`, `cal_targum_hebrew_lemmas`, `cal_targum_hebrew_reflexes`, and `cal_targum_reflex_examples`.

## Which tool to use

| Goal | Tool |
| --- | --- |
| Compare one biblical verse across MT and CAL's available Targum readings | `cal_targum_parallel(book, chapter, verse, include_peshitta=False, include_samaritan=False)` |
| Count one CAL lemma across CAL's Targum source groups | `cal_targum_concordance(lemma_key)` |
| Read one returned Targum concordance group's KWIC examples | `cal_targum_concordance_examples(lemma_key, text_ids)` |
| Discover CAL's MT Hebrew lemma choices for Onqelos or Neofiti reflex study | `cal_targum_hebrew_lemmas(initial, targum)` |
| Retrieve the CAL Aramaic lemma reflexes for one selected MT Hebrew lemma | `cal_targum_hebrew_reflexes(targum, mt_lemma_id)` |
| Read one explicit MT/Aramaic reflex example page | `cal_targum_reflex_examples(targum, mt_lemma_id, lemma_key)` |

Single-source chapter reading is intentionally **not** duplicated as a Targum-specific MCP tool. Where CAL exposes a source chapter link, it points into CAL's ordinary text browser and can be followed through the existing text tools in a separate caller-controlled step.

For source discovery, CAL's current Text Browse root gives the Onkelos/Jonathan family a dedicated upstream page rather than an ordinary category link. `cal_text_catalogue()` now preserves that branch as category `51`; a separate `cal_text_catalogue(category_id="51")` call lists one level of the Onkelos/Jonathan collection. Subdivided sources remain catalogue categories and direct sources remain text references. No source or chapter is fetched automatically.

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

CAL heads the returned MT/Targum verse with its own book abbreviation (for example `Ps 23:1`, `Sam1 1:1`, `Chron1 1:1`). CAL-MCP accepts the page only when that heading names the requested chapter and verse with CAL's recorded label for the requested book (or the exact selector label), so a page for another book or verse fails closed. The result's `book` is always the selector label you passed.

CAL repeats the verse coordinate at the end of every displayed MT line, inside the Hebrew text (for example `… הַשָּׁמַיִם Gen 1:1` / `וְאֵת הָאָרֶץ Gen 1:1`). CAL-MCP removes only that exact, validated heading coordinate from each line and joins the lines with one space, so `mt_text` contains only CAL's MT text. CAL's `<br>` line breaks are the only line boundaries. A line that lacks the label while others carry it, a line that is only a label, a different coordinate, or any chapter:verse-shaped text left in the MT after that removal (glued to a word, bracketed, a verse range, a bare `1:1`, or joined by markup other than `<br>`) fails closed as `parser_drift` rather than being guessed at.

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
- CAL's section structure separately from individual source labels. On CAL's earlier layout, explicit section headers (`<th colspan>`) group the rows after them, and those rows carry `section`. On CAL's current layout (2026-09-24) the page renders a single label row (`Torah`) followed by every Targum, including Former and Writing Prophets, Psalms and Chronicles, so it is not a grouping. Rows then carry `section: null`, and the result's additive `section_labels` lists each label row as `{label, row_index}`, where `row_index` is the index in `rows` of the first row after it (it equals the number of rows when no row follows, and consecutive labels share an index). CAL-MCP does not attribute rows to a label;
- exact source labels;
- occurrence counts;
- each row's additive ordered `text_ids`, identifying one exact source-group followup;
- absolute same-origin CAL example URLs;
- CAL's reported total;
- provenance.

A complete CAL table in which every row is zero and `total examples: 0` is a valid successful empty concordance. It is not treated as parser drift. Conversely, missing table/heading/total semantics, nonnumeric counts, malformed links, or a total that disagrees with the sum of parsed source counts fail closed.

Returned example URLs are navigation metadata only. CAL-MCP does not automatically follow them.

### Explicit concordance example follow-up

```text
cal_targum_concordance_examples(
    lemma_key: string,
    text_ids: array[string],
)
```

Choose one parent row's exact ordered `text_ids`, keeping the same canonical
`lemma_key`. This stateless follow-up validates selector shape and CAL response
identity, but does **not** prove that caller-supplied IDs previously appeared
in a parent row; verifying that by refetching would add an unwanted CAL request.
The adapter constructs one fixed GET to CAL
`show1dialectKWIC.php` with `charset=H`. No arbitrary URL parameter, other
group merging, prefetch or traversal is supported. Up to 32 distinct ASCII
decimal text identifiers are allowed, with an additional bounded query length.

The result preserves CAL's ordered `hits`, including file/subtext,
coordinate, rendered context, highlighted target and source-validated
`full_context_url`. Reuse `cal_kwic_full_context` for a *separate*
explicit action on one returned hit's coordinate. Heading/total/source
mismatches are parser drift, not invented empty results.

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

The two-step boundary is deliberate. One discovery call plus one reflex call remains two caller-controlled scholarly operations; CAL-MCP never selects a Hebrew lemma or follows all candidates automatically.

CAL has a notable invalid-ID fallback: a nonexistent opaque MT selector may return a broad frequency list with a heading ending at `correspondences to` and no selected Hebrew lemma. CAL-MCP rejects that response as parser drift instead of presenting an unrelated broad list as the requested result.

### Step 3: explicitly read one returned reflex example

```text
cal_targum_reflex_examples(
    targum: string,
    mt_lemma_id: string,
    lemma_key: string,
)
```

Choose one `reflexes[].lemma_key` in the Step 2 response. Preserve the
same `targum` and opaque `mt_lemma_id` returned by the parent; do **not**
pass `example_url` as an argument. CAL-MCP constructs exactly one allowed
GET (`getOMT.php` or `getNMT.php`) from these exact typed selectors.

The response keeps CAL's selected Hebrew lemma and its rendered
Onqelos/Neofiti source label, then ordered `examples` containing
`mt_text` and `targum_text`. Original CAL line breaks and repeated
example blocks are preserved; no verse IDs, distinct-verse count,
cross-source alignment, or preferred reading is invented. Each response
includes the actual CAL source URL and retrieval timestamp in provenance.
Invalid selectors are rejected before any CAL request. The upstream
lexicon link is validated but never followed automatically.

## CAL labels and Unicode fidelity

CAL-MCP preserves CAL's source/version labels and returned order. It does not harmonize names such as `Onqelos:`, `Pseudo Jonathan:`, `Neofiti:`, or fragment labels into a local ontology, and it does not infer equivalence between versions.

Hebrew, Aramaic, and Syriac rendered text is preserved through ordinary HTML text extraction. CAL-MCP does not add vocalization, transliteration, morphological analysis, or reconstructed readings to these Targum results.

## Request and traversal bounds

Each valid explicit operation submits at most one new logical CAL request to the shared client:

- one verse-comparison request;
- one Targum concordance request;
- one explicit Targum KWIC text-group example GET;
- one source/initial MT-lemma chooser request;
- one selected MT-lemma reflex request;
- one explicitly selected Onqelos/Neofiti reflex-example request.

There is no hidden biblical verse walking, all-book traversal, all-version expansion, chooser-alphabet crawl, automatic example fetching, chapter prefetch, background indexing, or local mirror. The shared CAL HTTP client still enforces origin, redirect, timeout, concurrency, retry, cache/single-flight, and response-size policy.

Private CAL form fields such as `bookname`, `Peshitta`, `Sam`, `R1`, `lemma`, `pos`, `texts`, and `charset` are adapter implementation details and are not public MCP parameters.

### Shared cache, single-flight, and retry semantics

Each valid explicit operation in this family submits at most one new logical CAL request to the shared client. A completed cache hit performs zero new upstream I/O, and an identical simultaneous call can be a single-flight follower without duplicating the active request. Retryable failures may consume bounded retry transport attempts under the shared policy. These mechanisms do not create hidden traversal, prefetch, or background work.

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

Issue #101 adds a separate reduced text-catalogue contract for discovering the Onkelos/Jonathan collection as category `51`; it does not add a fifth Targum-specific operation.

These fixtures are reduced parser contracts, not archived CAL pages. Live research was bounded to explicit scholarly examples and did not crawl or prefetch other returned CAL pages.
