# Issue #120 research — cache-aware request-volume wording outside core text tools

**Research date:** 2026-09-09  
**Baseline:** `main` at `c8dc0be2b73cd575775e26a6ad34b96f53f635c8`  
**Predecessor:** #117 / PR #121 corrected the four core `TextService` operations.

## Question

Which remaining public CAL-MCP tools have request-volume wording that contradicts the shared lifespan-managed cache, single-flight, retry, and provenance contract, and which tools are intentional exceptions to the single-logical-request pattern?

## Shared request architecture

`src/cal_mcp/server.py` creates one `CalHttpClient` for the MCP lifespan and reuses it across CAL-backed tool calls. `docs/configuration.md` and request-layer tests establish three distinct layers:

1. **Explicit MCP operation** — the caller's scholarly action.
2. **Logical CAL request identity/workflow** — one normalized request passed to the shared client for most operations, or an explicitly bounded multi-request workflow for lexicon lookup.
3. **Raw upstream transport attempts/new I/O** — zero on a completed cache hit; no duplicate active I/O for an identical single-flight follower; normally one on an ordinary successful cache miss; potentially more within the finite retry budget after whitelisted transient failures.

Completed cache hits preserve the original CAL `source_url` and `retrieved_at`. Single-flight coordination creates no background crawl or refresh. Invalid public input can fail before any transport.

Therefore unconditional statements such as “every call performs exactly one CAL request” conflate caller action, logical request identity, and actual upstream I/O.

## Runtime service audit

The current services were inspected on the baseline above. Except for lexicon lookup, every CAL-backed operation outside the core text family constructs at most one logical `CalRequest` and calls `CalHttpClient.fetch()` once after local validation, with a stable cache namespace.

| Family | Public tools | Runtime logical workflow | Current wording state |
| --- | --- | --- | --- |
| Local conversion | `cal_convert_to_code` | zero CAL requests | Correct zero-network exception; preserve. |
| Lexicon | `cal_lexicon_lookup` | bounded multi-request: up to 8 unique browse requests + at most 1 selected entry request | Correct explicit exception; preserve. |
| English search | `cal_gloss_search`, `cal_gloss_field`, `cal_citation_text_search` | one shared-client `fetch()` each | Server/docs contain unconditional one-request wording. |
| Token analysis | `cal_token_analysis` | one `fetch()` | Server/docs contain unconditional one-request wording. |
| Concordance/KWIC | `cal_text_concordance`, `cal_kwic_texts`, `cal_kwic_dialects`, `cal_kwic_dialect` | one `fetch()` each | Family docs claim every call/exact upper bound; several server descriptions repeat it. |
| Bibliography | `cal_bibliography_authors`, `cal_bibliography_author`, `cal_bibliography_keyword`, `cal_bibliography_lemma` | one `fetch()` each | Server/docs claim exact one-request execution. |
| Dictionary collation | `cal_dictionary_collation` | one `fetch()` | Server/docs claim exactly one request/POST. |
| Targum Studies | `cal_targum_parallel`, `cal_targum_concordance`, `cal_targum_hebrew_lemmas`, `cal_targum_hebrew_reflexes` | one `fetch()` each | Family docs claim every public tool performs one request; parallel server description repeats it. |
| Syriac Studies | `cal_syriac_texts`, `cal_syriac_missing_words`, `cal_syriac_peshitta_parallel` | one `fetch()` each | Family docs claim every operation performs one request; two server descriptions repeat it. |
| External citations | `cal_external_citation_dialects`, `cal_external_citation_sources`, `cal_external_citations` | one `fetch()` each | Workflow docs and all three server descriptions claim exactly one request. |
| Core text | `cal_text_catalogue`, `cal_text_search`, `cal_text_page`, `cal_text_information` | one `fetch()` each | Already corrected by #117; out of scope except as wording model. |

No hidden route-discovery, prefetch, fallback source discovery, or automatic result traversal was found in the audited one-fetch services.

## Detailed runtime evidence

### English search

`EnglishSearchService.search_gloss`, `.search_gloss_field`, and `.search_citations` each validate/normalize locally and then call the shared client once, using `english-gloss-search-v1`, `english-gloss-field-v1`, and `english-citation-search-v1` respectively.

### Token analysis

`TokenAnalysisService.analyze` validates coordinate/token index locally and then makes one `fetch()` under `token-analysis-v1`.

### Concordance/KWIC

`ConcordanceService.text_concordance`, `.kwic_texts`, `.kwic_dialects`, and `.kwic_dialect` each make exactly one shared-client `fetch()` after validation, under distinct namespaces. Returned full-context URLs are not followed.

### Bibliography

`BibliographyService.authors` uses one `fetch()`. Exact-author, keyword, and lemma operations funnel through `_result()`, which performs one `fetch()` with the operation-specific path/namespace. Record-local navigation links remain metadata only.

### Targum Studies

`TargumService.parallel`, `.concordance`, `.hebrew_lemmas`, and `.hebrew_reflexes` each make one `fetch()` after validation. The Hebrew-lemma chooser → reflex sequence is correctly a two-step caller-controlled scholarly workflow; the inaccurate part is claiming that each explicit step necessarily causes fresh upstream I/O.

### Syriac Studies

`SyriacService.texts`, `.missing_words`, and `.peshitta_parallel` each make one `fetch()`. Returned catalogue/text/entry/chapter links are not followed automatically.

### External citations

`ExternalCitationService.dialects`, `.sources`, and `.citations` each make one `fetch()`. The three-stage dialect → source → citations workflow remains caller-controlled and should stay explicit.

### Dictionary collation

`DictionaryCollationService.collate` validates source/page locally and performs one shared-client `fetch()` under `dictionary-collation-v1`; returned lemma links remain metadata.

## Protected exceptions

### `cal_convert_to_code`

This is local-only. Its current “no CAL network request” contract is exact and should not be weakened into generic cache-aware language.

### `cal_lexicon_lookup`

Lexicon lookup is intentionally multi-request because CAL's public lexicon interface separates bounded browser discovery and selected-entry retrieval. Current documented bounds are semantically meaningful:

- deterministic not-found/ambiguous lookup: one browser request;
- deterministic successful lookup: normally browser + one entry request;
- finite orthographic ambiguity: at most eight unique browser-prefix requests plus one selected entry request.

Cache/single-flight still apply to each underlying logical request identity, but the operation itself must not be rewritten as a one-request workflow. Tests for #120 should protect this exception explicitly.

## User-documentation audit

### `docs/tools/search.md`

Stale claims include “One call performs exactly one field-result request”, “One MCP call performs exactly one CAL search request”, and “bounded operationally by one upstream request”. The endpoint/form mapping table itself remains useful as the cache-miss request shape and should be retained.

### `docs/tools/token-analysis.md`

The Request bound section says every invocation performs exactly one user-initiated CAL request. It simultaneously documents local validation and shared retry/cache policy, making the contradiction visible.

### `docs/tools/concordance.md`

The opening says every public call performs exactly one user-initiated request and the Request/result bounds section calls this an exact one-request upper bound. The document already states duplicate-request cache hits preserve original provenance.

### `docs/tools/bibliography.md`

The opening and request-bounds section claim exact one-request execution, while invalid inputs may fail locally and cache-hit provenance is explicitly documented. Fixture wording such as “exact one-request service mappings” can remain only if clearly scoped to fresh-client/service request construction rather than every public invocation.

### `docs/tools/dictionary-collation.md`

The tool and Request bounds sections claim exactly one user-initiated request / bounded POST, while the same section lists retries, in-flight suppression, and cache behavior. The useful invariant is one POST-shaped logical request identity on a cache miss, not one raw transport attempt per invocation.

### `docs/tools/targum.md`

The opening and Request/traversal bounds claim each operation performs exactly one request. The two-step Hebrew chooser/reflex workflow correctly requires two explicit caller actions and must remain explicit; cache hits may make either step require zero new upstream I/O.

### `docs/tools/syriac.md`

The opening and Request/traversal bounds claim one request per public operation. The Peshitta text-category composition correctly requires separate explicit caller actions and should retain that workflow boundary without promising fresh I/O for each step.

### `docs/tools/external-citations.md`

The explicit three-stage workflow correctly requires caller choices between stages, but its “each tool call performs exactly one bounded CAL request” sentence is stale under cache/single-flight/retry semantics.

### `docs/tools/lexicon.md`

Current bounded multi-request counts are intentional and should remain. Cache-hit provenance is already documented. This file is a protected exception, not a target for generic replacement.

### `docs/tools/texts.md`

Already corrected by #117 and is the wording reference for #120. Do not churn it again.

## Correct contract for one-fetch operations

For the audited one-fetch tools, the technically accurate public contract is:

- a valid explicit operation constructs/submits at most one new logical CAL request identity to the shared client;
- a completed cache hit performs zero new upstream I/O;
- an identical simultaneous follower does not duplicate the active upstream operation;
- a retryable cache miss may consume bounded transport attempts under the shared retry policy;
- invalid input may fail before transport;
- returned links/results are not recursively followed or prefetched unless a separate explicit caller operation is documented.

This wording describes request pressure without pretending that cache/single-flight are hidden work or that retry attempts are additional user operations.

## Scope decision

#120 should be a documentation/description-contract change only:

- correct stale request-count phrases in `src/cal_mcp/server.py` for affected non-text one-fetch operations;
- correct request-volume sections in the eight affected tool documents: search, token analysis, concordance, bibliography, dictionary collation, Targum, Syriac, external citations;
- add centralized offline contract tests that catch stale unconditional wording and protect the converter/lexicon exceptions;
- do not change service/client/parser/schema/provenance/request construction.

No separate runtime defect issue is necessary because the audit found no implementation mismatch.

## CAL load impact

Zero. The audit is based on current repository implementation, existing offline tests, and the already documented shared request layer. No live CAL probe is required.
