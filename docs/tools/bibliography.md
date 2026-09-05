# CAL bibliography search

CAL-MCP exposes four bounded operations over CAL's current public bibliography interfaces. Each public call performs exactly **one** user-initiated CAL request. Author-prefix discovery and exact-author retrieval are intentionally separate calls; CAL-MCP does not choose an author, follow bibliography tags, traverse the archive, or build a local index.

## Which tool to use

| Goal | Tool |
| --- | --- |
| Discover CAL's exact author choices from a 1–6 character prefix | `cal_bibliography_authors(prefix)` |
| Retrieve bibliography records for one exact CAL author value | `cal_bibliography_author(author)` |
| Retrieve records for one exact CAL text/subject bibliography tag | `cal_bibliography_keyword(keyword)` |
| Retrieve records for one exact CAL lemma key | `cal_bibliography_lemma(lemma_key)` |

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

## Bibliography records and links

Each final bibliography result preserves CAL's ordered record cards. A record contains:

- `citation` — CAL's rendered bibliographic text, including Unicode text and diacritics;
- `links` — ordered record-local CAL links/tags.

A link contains its rendered `label` and absolute `url`. When the target is one of CAL's recognized bibliography result families, CAL-MCP also exposes:

- `query_kind` — `author`, `keyword`, or `lemma`;
- `query_value` — CAL's exact upstream value.

Those fields are navigation metadata only. Returning a tag never causes an automatic follow-up request.

Record-local links are required to remain on the same CAL origin. Cross-origin record links or malformed bibliography navigation query semantics fail as parser drift rather than being silently trusted.

## Empty results and parser drift

The current author, keyword, and lemma result endpoints use the explicit marker:

```text
NO data FOR <query> ARE CURRENTLY STORED
```

A page with that marker and no record cards is a valid successful empty result. CAL-MCP keeps the following states separate:

- a valid CAL empty result;
- local input validation failure before transport;
- network, timeout, redirect, HTTP, maintenance/content, or response-size failure from the shared request layer;
- parser drift when a successful-looking page lacks required result semantics;
- contradictory markup, such as an explicit no-data marker together with bibliography records.

Parser drift is not converted into an empty result.

## Pagination, continuation, and request bounds

During the bounded live audit on **2026-09-05**, representative current author, text/subject, and lemma bibliography result pages exposed no next/previous result link, page number, continuation token, or stable result-limit parameter.

CAL-MCP therefore exposes no `page`, `offset`, or `limit` parameter for these tools. Each call requests one complete current CAL result page subject to the shared decoded-response limit. If CAL later adds a real continuation mechanism, that is a new upstream contract to research and test; CAL-MCP will not infer hidden iteration from it.

Every bibliography operation has an exact one-request upper bound:

- one author-prefix selector request;
- one exact-author result request;
- one exact text/subject-tag result request;
- one exact lemma result request.

There is no archive crawl, tag expansion, prefetch, background indexing, or local bibliography mirror. The separate CAL recent-five-years bibliography view is outside issue #9's search contract and remains for the broader public-surface audit.

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
- representative author, text/subject-tag, and lemma result pages;
- multiple and empty results;
- Unicode citation/title text and diacritics;
- ordered CAL tags/links and recognized navigation metadata;
- malformed/missing citation/link semantics and cross-origin links;
- contradictory no-data-plus-record markup;
- local input bounds and lemma-key validation;
- exact one-request service mappings and provenance;
- MCP introspection with no private CAL form parameters and no invented bibliography pagination.

Normal CI performs zero CAL requests.
