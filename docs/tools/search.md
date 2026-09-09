# English search

CAL-MCP exposes three bounded CAL-backed English search tools:

```text
cal_gloss_search(query, all_glosses=False)
cal_gloss_field(field)
cal_citation_text_search(query)
```

They adapt distinct current CAL search workflows. They do not perform local indexing, fuzzy expansion, semantic reranking, or automatic follow-up lookups.

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

## `cal_gloss_field`

Search one of CAL's current indexed **Search by Specialized Field** categories. This is a separate CAL workflow from searching the visible word `alchemy`, `medicine`, and so on as an ordinary English gloss.

The public `field` argument is a readable enum. Current values, in CAL's displayed order, are:

| Field value | CAL label |
| --- | --- |
| `alchemy` | alchemy |
| `anatomy` | anatomy |
| `architecture` | architecture |
| `astronomy` | astronomy |
| `botany` | botany, flora |
| `cantillation` | cantillation |
| `chemistry` | chemistry |
| `geography` | geography |
| `geology` | geology, gemology |
| `geometry` | geometry |
| `grammar` | grammar |
| `liturgy` | liturgy |
| `logic` | logic |
| `magic` | magic |
| `mathematics` | mathematics |
| `medicine` | medicine |
| `music` | music |
| `philosophy` | philosophy |
| `topography` | topography |
| `zoology` | zoology, fauna |

CAL-MCP maps the readable enum to CAL's private current indexing token internally. Callers cannot supply that private token through this operation, and an unknown field is not reinterpreted as an ordinary English query.

The result contains:

- `field` — the readable enum value;
- `label` — CAL's current human-facing field label;
- `matches` — the same ordered CAL lemma-reference shape used by ordinary gloss results;
- provenance for the actual CAL request.

each valid explicit operation submits at most one new logical CAL request to the shared client. It does not search every field, follow matching lemmas, or expand the selected field into additional queries.

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

The ordinary CAL form contract was rechecked on 2026-09-04 and the specialized-field navigation on 2026-09-08:

| Tool | CAL form behavior |
| --- | --- |
| gloss search | one `POST` to the current gloss-search handler with the English query and CAL's primary/all-glosses radio value |
| specialized gloss field | one `GET` to the current gloss-search handler using CAL's private indexed field selector and subsidiary-gloss mode |
| citation-text search | one `POST` to the current citation-search handler with the English query |

The PHP handler names, form-field names, and specialized-field tokens are adapter internals and are not public MCP parameters.

each valid explicit operation submits at most one new logical CAL request to the shared client. It does not fetch each matched lexicon entry, follow search results, or make a second request to obtain context.

### Pagination and result bounds

The current representative CAL gloss, specialized-field, and citation-result pages inspected during the focused audits exposed no page number, next-page link, continuation token, or other bounded continuation control. CAL-MCP therefore does **not** invent `page`, `offset`, or `continuation` parameters and does not split or auto-traverse the result set as though CAL provided such semantics.

a search is bounded operationally by at most one new logical CAL request and by the shared CAL HTTP response-size limit. If CAL later exposes a stable pagination contract, it must be researched, tested, and added explicitly rather than inferred from layout.


### Shared cache, single-flight, and retry semantics

Each valid explicit operation in this family submits at most one new logical CAL request to the shared client. A completed cache hit performs zero new upstream I/O, and an identical simultaneous call can be a single-flight follower without duplicating the active request. Retryable failures may consume bounded retry transport attempts under the shared policy. These mechanisms do not create hidden traversal, prefetch, or background work.

## Provenance

Search results return adapter provenance with:

- `source: "CAL"`;
- exact upstream result URL;
- timezone-aware `retrieved_at` timestamp;
- `original_query`;
- `submitted_query`;
- `search_kind`.

For ordinary gloss and citation searches, `original_query` preserves the caller's input and `submitted_query` records deterministic ASCII-space cleanup. For `cal_gloss_field`, `original_query` is the readable field slug, `submitted_query` records CAL's private current indexed field token for reproducibility, and `search_kind` is `gloss_field`. The private token is provenance, not an accepted public selector.

Cache hits retain the timestamp of the actual CAL retrieval.

## Empty results and failures

These states remain distinct:

- **ordinary empty result** — an empty `matches` or `hits` list after CAL explicitly reports no matches;
- **invalid local query/selector** — rejected before transport, including unsupported specialized-field values;
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

Specialized indexed field:

```text
cal_gloss_field(field="medicine")
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
- automatic traversal across all specialized fields;
- automatic lexicon-entry fetches for returned references;
- client-invented pagination over CAL results;
- the separate CAL Citation Finder for texts not fully present in the online database;
- concordance/KWIC search.

Use `cal_lexicon_lookup` when the task begins from an Aramaic lexical form rather than an English search term.
