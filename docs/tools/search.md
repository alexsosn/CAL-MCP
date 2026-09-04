# English search

CAL-MCP exposes two bounded CAL-backed English search tools:

```text
cal_gloss_search(query, all_glosses=False)
cal_citation_text_search(query)
```

They adapt two distinct current CAL search forms. They do not perform local indexing, fuzzy expansion, semantic reranking, or automatic follow-up lookups.

## `cal_gloss_search`

Search CAL's English lexical glosses.

### Arguments

- `query` — the English search string submitted to CAL. CAL's current interface requires at least three letters. CAL's documented trailing `#` convention for a complete-word search is preserved and passed upstream rather than reinterpreted locally.
- `all_glosses` — when `false` (default), search CAL's primary glosses; when `true`, include subsidiary glosses as CAL's current form does.

CAL-MCP trims surrounding ASCII spaces and collapses repeated internal ASCII spaces. It otherwise preserves the submitted search text and records both the original and submitted forms in provenance.

### Result

`matches` is an ordered list of CAL lemma references. Each match preserves:

- CAL lemma key;
- rendered headword variants;
- pronunciation when present;
- part-of-speech text;
- the gloss returned on the CAL result page.

An ordinary no-match search returns `matches: []`. It is not represented as a parser or network failure.

## `cal_citation_text_search`

Search for English words inside the citations attached to CAL lexicon entries.

CAL's current form accepts one to three English words separated by spaces. CAL-MCP enforces the one-to-three-word bound before any network request. CAL documents additional upstream behavior for very common short words; CAL-MCP does not maintain or guess a local stop-word/exception list and therefore leaves those scholarly search rules to CAL.

Each ordered hit preserves:

- the CAL lemma reference associated with the citation;
- `lexical_context` — the rendered lexical/sense context shown by CAL for that hit;
- `reference` — CAL's rendered citation reference;
- `source_text` — the Aramaic/source-language citation text;
- `translation` — CAL's English rendering when present.

Repeated hits for the same lemma remain separate and in CAL order. CAL-MCP does not deduplicate or rerank them.

## Request behavior

The current CAL form contract was rechecked on 2026-09-04:

| Tool | CAL form behavior |
| --- | --- |
| gloss search | one `POST` to the current gloss-search handler with the English query and CAL's primary/all-glosses radio value |
| citation-text search | one `POST` to the current citation-search handler with the English query |

The PHP handler names and form-field names are adapter internals and are not part of the MCP contract.

One MCP call performs exactly one CAL search request. It does not fetch each matched lexicon entry, follow search results, or make a second request to obtain context.

### Pagination and result bounds

The current representative CAL gloss and citation-result pages inspected on 2026-09-04 exposed no page number, next-page link, continuation token, or other bounded continuation control. CAL-MCP therefore does **not** invent `page`, `offset`, or `continuation` parameters and does not split or auto-traverse the result set as though CAL provided such semantics.

A search is bounded operationally by one upstream request and by the shared CAL HTTP response-size limit. If CAL later exposes a stable pagination contract, it must be researched, tested, and added explicitly rather than inferred from layout.

## Provenance

Both tools return adapter provenance with:

- `source: "CAL"`;
- exact upstream result URL;
- timezone-aware `retrieved_at` timestamp;
- `original_query` exactly as supplied by the caller;
- `submitted_query` after the documented deterministic ASCII-space cleanup;
- `search_kind` (`gloss` or `citation_text`).

Cache hits retain the timestamp of the actual CAL retrieval.

## Empty results and failures

These states remain distinct:

- **ordinary empty result** — an empty `matches` or `hits` list after CAL explicitly reports no matches;
- **invalid local query** — rejected before transport (for example, fewer than three letters for gloss search or more than three words for citation-text search);
- **network/HTTP/content failure** — typed failure from the shared conservative CAL request layer;
- **parser drift** — CAL returned successful HTML but the required search-result semantics can no longer be recognized safely.

Search parsers do not reinterpret a nonempty unrecognized page as an empty result.

## Examples

Primary-gloss search:

```text
cal_gloss_search(query="camel#")
```

Include subsidiary glosses:

```text
cal_gloss_search(query="camel#", all_glosses=true)
```

Citation-text search:

```text
cal_citation_text_search(query="camel")
```

The offline test fixtures use deliberately reduced excerpts from these current CAL result shapes. They are parser contracts, not archived CAL pages.

## Non-capabilities

These tools do not provide:

- fuzzy or semantic English search;
- local full-text indexing;
- automatic expansion to synonyms or related lemmas;
- automatic lexicon-entry fetches for returned references;
- client-invented pagination over CAL results;
- the separate CAL Citation Finder for texts not fully present in the online database;
- concordance/KWIC search.

Use `cal_lexicon_lookup` when the task begins from an Aramaic lexical form rather than an English search term.
