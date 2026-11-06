# CAL bibliography search

The current development source exposes five bounded bibliography operations (four in published v0.1.0). Each valid explicit operation submits at most one new logical CAL request to the shared client. Author-prefix discovery and exact-author retrieval are intentionally separate calls; CAL-MCP does not choose an author, follow bibliography tags, traverse the archive, or build a local index.

## Which tool to use

| Goal | Tool |
| --- | --- |
| Discover CAL's exact author choices from a 1–6 character prefix | `cal_bibliography_authors(prefix)` |
| Retrieve bibliography records for one exact CAL author value | `cal_bibliography_author(author)` |
| Retrieve records for one exact CAL text/subject bibliography tag | `cal_bibliography_keyword(keyword)` |
| Retrieve records for one exact CAL lemma key | `cal_bibliography_lemma(lemma_key)` |
| Browse the ordered CAL recent-years bibliography snapshot | `cal_bibliography_recent()` |

The word `keyword` follows CAL's bibliography/archive terminology. The current upstream surface is an exact text/subject tag lookup, not arbitrary full-text, fuzzy, ranked, stemmed, or substring search.

## `cal_bibliography_authors`

```text
cal_bibliography_authors(prefix: string)
```

CAL's author search begins with the first one to six characters of a romanized author name. This tool returns CAL's ordered exact author choices as `value` / `label` pairs.

`prefix` is trimmed at its outer ASCII spaces and must contain 1–6 single-line characters. Invalid or oversized values fail locally before transport.

A prefix that matches several authors remains ambiguous. A caller must choose one returned `value` and make a separate `cal_bibliography_author` call. CAL-MCP never selects the first candidate automatically.

A CAL page carrying the explicit `No authors found matching ...` marker is returned as a valid empty candidate list. A successful-looking response with neither the expected author selector nor that explicit marker is parser drift and fails closed.

## `cal_bibliography_author`

```text
cal_bibliography_author(author: string)
```

Retrieve the bibliography for one exact CAL author value, normally copied from a candidate returned by `cal_bibliography_authors`.

The result contains:

- `query_kind: "author"`;
- the exact submitted `query`;
- CAL's result `heading`;
- ordered `records`;
- per-record rendered `citation` text;
- ordered record-local CAL `links` / tags;
- provenance for the actual request.

CAL-MCP preserves CAL's rendered citation as a citation string. It does not infer or split locally guessed author/title/journal/year fields.

## `cal_bibliography_keyword`

```text
cal_bibliography_keyword(keyword: string)
```

Retrieve bibliography records for one exact CAL text/subject tag, for example a CAL text siglum or subject label discovered from CAL's bibliography UI or from links returned on another bibliography record.

`keyword` must be nonempty and single-line. CAL-MCP submits it unchanged apart from outer-space trimming. There is no query expansion, case folding, stemming, ranking, fallback search, or local subject ontology.

The result uses the same record model as author search with `query_kind: "keyword"`.

## `cal_bibliography_lemma`

```text
cal_bibliography_lemma(lemma_key: string)
```

Retrieve bibliography records for one exact canonical CAL lemma key, such as:

```text
cly V
mlk N
)ryk#2 A
```

Lemma-key validation is shared with the concordance/KWIC surface. A terminal positive-decimal homograph marker such as `#2` is part of CAL's lemma identity and is preserved. Callers should reuse canonical keys returned by CAL-MCP lexicon, search, concordance, or token-analysis results instead of reconstructing them heuristically.

The result uses the common bibliography record model with `query_kind: "lemma"`.

CAL echoes a lemma key containing `$` (shin) or `(` (ʿayin) with those characters backslash-escaped. For example, `(bd V` comes back as `CAL Bibliography for \(bd V`. CAL-MCP accepts exactly that escaped echo, or the unescaped key, as naming the submitted key. `query` and provenance always carry the canonical unescaped key, while `heading` preserves CAL's literal text. Any other difference between the echo and the key is `parser_drift`.

## `cal_bibliography_recent`

```text
cal_bibliography_recent()
```

Retrieve CAL's current **five most recent years of bibliographic records** view. This is an aggregate snapshot, not a filtered author/tag/lemma lookup. The operation accepts **no arguments**: no year, date range, search text, page, limit or continuation token. CAL chooses the years and entries. On 2026-11-04, its current page presents **2021–2025** despite the calendar year being 2026; no locally calculated rolling year range is promised.

The result contains the exact `heading: "CAL Recent Bibliography"`, `records` in CAL order, and standard `provenance`. Each record retains its citation text and links; duplicate-looking works are preserved without deduplication. CAL exposes no stable typed publication-year/group field on this page, so CAL-MCP does not invent `year`, parse incidental year tokens, or sort/group records by year. Unlike the targeted bibliography tools, this result has no `query_kind` or `query` value. In provenance, the no-input operation is `bibliography_recent` and `original_query` / `submitted_query` are empty strings.

The operation issues one fixed logical GET to CAL's current snapshot. No additional bibliography, record, or archive links are followed. The shared client enforces its decoded-response cap (2 MiB by default), timeouts and conservative request policy. No explicit empty-result marker has been established for this surface: if the current page has no recognized records or gains a pagination selector, CAL-MCP returns parser drift rather than an empty or partial bibliography.

This operation is added on unreleased development source for 0.2.0; it is **not available in the immutable `cal-mcp==0.1.0` release**.

## Bibliography records and links

Each final bibliography result preserves CAL's ordered records. CAL currently renders every record of a result page as one `<p>` element inside a single result card, which wraps CAL's legacy result document. The earlier layout used one card per record and is still accepted. A record contains:

- `citation` — CAL's rendered bibliographic text, including Unicode text and diacritics;
- `links` — ordered record-local CAL links/tags.

A link contains its rendered `label` and absolute `url`. When the target is one of CAL's recognized bibliography result families, CAL-MCP also exposes:

- `query_kind` — `author`, `keyword`, or `lemma`;
- `query_value` — CAL's exact upstream value.

Those fields are navigation metadata only. Returning a tag never causes an automatic follow-up request.

Record-local links must remain on CAL's origin. A **typed** bibliography follow-up is recognized only for a canonical root-level bibliography handler with one nonempty, well-formed UTF-8 `myauthor` field: no additional query fields, path aliases, dot-segment normalization, raw whitespace/control characters, fragments, or malformed percent escapes. CAL's exact decoded values (including Unicode and encoded punctuation) and absolute link URLs are preserved. Cross-origin links and noncanonical links impersonating recognized bibliography handlers fail as parser drift; links to **other** same-origin CAL endpoints remain generic (`query_kind: null`) rather than being misrepresented as typed bibliography queries.

CAL renders an empty tag-list entry as a link whose label and query value are both empty or whitespace-only (for example `getbiblemma.php?myauthor=` or `getbibsigla.php?myauthor=%0A`). Such a placeholder carries no data and is omitted from `links`. Any other link without a label, or a labelled link with an empty value, is still parser drift. Text inside a result card but outside its records, nested or unclosed records, title metadata inside a record, and CAL's embedded legacy result document without `<p>` record boundaries all fail closed rather than being merged into a record. Page-title metadata outside records (the page `<title>` and CAL's embedded legacy `<TITLE>`) is ignored.

Known limit: if CAL ever dropped a single `</p><p>` boundary between two works while keeping the others, the two would render as one `<p>`, and nothing in the markup distinguishes that from one long record. The `live_smoke` check bounds record length to catch gross merging.

## Empty results and parser drift

The current author, keyword, and lemma result endpoints use the explicit marker:

```text
NO data FOR <query> ARE CURRENTLY STORED
```

A page with that marker and no records is a valid successful empty result. On current pages the marker sits alone inside the result card. CAL-MCP keeps the following states separate:

- a valid CAL empty result;
- local input validation failure before transport;
- network, timeout, redirect, HTTP, maintenance/content, or response-size failure from the shared request layer;
- parser drift when a successful-looking page lacks required result semantics;
- contradictory markup, such as an explicit no-data marker together with bibliography records.

Parser drift is not converted into an empty result.

## Pagination, continuation, and request bounds

During the bounded live audit on **2026-09-05**, representative current author, text/subject, and lemma bibliography result pages exposed no next/previous result link, page number, continuation token, or stable result-limit parameter.

CAL-MCP therefore exposes no `page`, `offset`, or `limit` parameter for these tools. Each call requests one complete current CAL result page subject to the shared decoded-response limit. If CAL later adds a real continuation mechanism, that is a new upstream contract to research and test; CAL-MCP will not infer hidden iteration from it.

Each valid explicit operation submits at most one new logical CAL request to the shared client:

- one author-prefix selector request;
- one exact-author result request;
- one exact text/subject-tag result request;
- one exact lemma result request;
- one recent-bibliography snapshot request, without any caller-controlled selectors.

There is no archive crawl, tag expansion, prefetch, background indexing, or local bibliography mirror. The recent-years snapshot remains excluded from the frozen v0.1.0 contract and is implemented only in the newer development source.

### Shared cache, single-flight, and retry semantics

Each valid explicit operation in this family submits at most one new logical CAL request to the shared client. A completed cache hit performs zero new upstream I/O, and an identical simultaneous call can be a single-flight follower without duplicating the active request. Retryable failures may consume bounded retry transport attempts under the shared policy. These mechanisms do not create hidden traversal, prefetch, or background work.

## Provenance

Results include adapter provenance with:

- `source: "CAL"`;
- the actual CAL `source_url`;
- timezone-aware `retrieved_at`;
- the bibliography operation name;
- `original_query` supplied by the caller;
- `submitted_query` sent after local validation/canonicalization.

Duplicate-request cache hits preserve the original CAL retrieval timestamp and source URL, following the shared request-layer provenance contract.

## Fixture-backed contract

Normal tests use reduced semantic excerpts rather than archived full CAL pages. The fixture/test set covers:

- multiple ordered author candidates;
- explicit no-author matches;
- representative author, text/subject-tag, and lemma result pages, including CAL's current one-card `<p>`-record layout (2026-09-24) and the earlier one-card-per-record layout;
- CAL's empty placeholder links and the in-card no-data marker;
- multiple and empty results;
- Unicode citation/title text and diacritics;
- ordered CAL tags/links and recognized navigation metadata;
- malformed/missing citation/link semantics and cross-origin links;
- contradictory no-data-plus-record markup;
- local input bounds and lemma-key validation;
- single-fetch request construction and provenance;
- MCP introspection with no private CAL form parameters and no invented bibliography pagination;
- current recent-bibliography heading, ordered duplicate records, Unicode, one fixed GET, provenance, absent empty marker and unexpected pagination/drift.

Normal CI performs zero CAL requests.
