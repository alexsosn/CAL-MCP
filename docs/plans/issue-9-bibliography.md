# Issue #9 plan — bounded CAL bibliography lookup

**Plan date:** 2026-09-05

This plan follows the repository development loop: research → plan → test-only RED → minimal implementation → GREEN → documentation → independent skeptical review → test-first review fixes → fresh independent re-review → squash merge.

## Scope correction from research

Issue #9 originally said “author, keyword, and lemma.” Current CAL does not expose a generic free-text bibliography keyword form. Its bibliography index exposes:

- author lookup;
- a live **text/subject taxonomy**;
- lexical-item lookup.

The public capability will represent those current CAL semantics directly. It will not invent a generic keyword search.

## Public tools

Expose five explicit caller-controlled operations:

```text
cal_bibliography_authors(prefix)
cal_bibliography_author(author)
cal_bibliography_topics(general_class=None)
cal_bibliography_topic(general_class, subclass)
cal_bibliography_lemma(lemma_key)
```

Every tool performs exactly one CAL request.

### `cal_bibliography_authors(prefix)`

One `POST /browsenames.php` request with CAL's `first3` field.

Returns CAL's ordered author choices. It does not automatically fetch any author's bibliography.

Local input contract:

- 1–6 characters;
- ASCII letters plus the punctuation useful in romanized names (`-`, `'`, and CAL's backtick for ayin);
- no whitespace/control characters.

### `cal_bibliography_author(author)`

One `POST /getbibauthor.php` request with the selected author name.

The author string is treated as a CAL-owned selector value, not a fuzzy-search query. Reject blank/control-containing/overlong input locally; do not normalize names linguistically.

Returns `found` with ordered bibliography records or `not_found` only for CAL's explicit no-data marker.

### `cal_bibliography_topics(general_class=None)`

A bounded one-level taxonomy discovery operation:

- `general_class=None` → one `GET /allsigs.html` request;
- explicit `general_class` → one `GET /browsegclass.php?generalclass=...` request.

Returns ordered `BibliographyTopicRef` values. Each ref has:

- CAL display label;
- `general_class`;
- optional `subclass`;
- `kind`: `group` or `selection`.

`group` means the caller may explicitly call `cal_bibliography_topics(general_class=...)`. `selection` means the caller may explicitly call `cal_bibliography_topic(...)`.

No recursive traversal is performed.

### `cal_bibliography_topic(general_class, subclass)`

One `GET /browsesigla.php` request with the explicit CAL taxonomy pair.

Returns ordered bibliography records or the explicit `not_found` state for CAL's `NO CURRENT ENTRIES FOR: ...` marker.

### `cal_bibliography_lemma(lemma_key)`

One `POST /getbiblemma.php` request with the explicit canonical CAL lemma key.

Canonical homograph keys such as `sbk#2 N` must be supported. Rather than importing another feature module's private validator, extract the already-tested CAL lemma-key structure validation into a small shared internal helper and keep concordance behavior unchanged.

No lexicon lookup is performed implicitly.

## Typed result model

Add `bibliography.py` with a model family along these lines:

- `BibliographyStatus`: `found`, `not_found`;
- `BibliographyTagKind`: `subject`, `lemma`;
- `BibliographyTag`: kind, rendered label, CAL selector value, absolute CAL URL;
- `BibliographyEntry`: rendered citation text plus ordered tags;
- `BibliographyTopicKind`: `group`, `selection`;
- `BibliographyTopicRef`: label, general class, optional subclass, kind;
- `BibliographyProvenance`: source, source URL, retrieval timestamp, operation/mode and submitted selector fields;
- operation-specific result dataclasses with `to_dict()`.

Do **not** invent a stable record ID, DOI, publication type, author/title/year decomposition, or record-detail URL when CAL does not expose one.

## Bibliography record parser

Current positive result pages render each bibliography record as one `<p>` block. Parse each nonempty bibliography record block as an ordered unit.

Within one record:

- collect rendered citation text while preserving text from ordinary inline elements such as CAL title markup and italics;
- recognize `/getbibsigla.php?myauthor=...` links as subject/text tags;
- recognize `/getbiblemma.php?myauthor=...` links as lemma tags;
- preserve tag order and duplicates;
- remove recognized tag-anchor text from the citation string so tags are structured separately;
- preserve unusual CAL tag artifacts rather than silently deleting them. Current live output includes at least one blank subject-tag anchor; an empty rendered label may therefore be retained when the upstream selector itself is blank/whitespace-like.

Citation whitespace may be normalized for HTML presentation, but wording, punctuation, Unicode, ordering, and content must not be editorially rewritten.

## Result-page identity and empty states

### Author/lemma result

Require the response to identify the requested selector in the current `CAL Bibliography for ...` heading family.

Valid empty marker:

```text
NO data FOR <selector> ARE CURRENTLY STORED
```

A page containing both records and the no-data marker is parser drift.

### Topic result

Require the current heading family to agree with the requested `general_class` and `subclass`.

Valid empty marker:

```text
NO CURRENT ENTRIES FOR: <subclass>
```

Again, records plus empty marker is parser drift.

### Unknown successful markup

HTTP 200 with neither recognizable records nor the mode-specific explicit empty marker is `BibliographyParseError`, not an empty result.

## Author-selector parser

Parse exactly one relevant form targeting `getbibauthor.php` and its `myauthor` select values.

The form action must resolve to the same CAL origin and have the exact expected final path segment. Preserve server order and duplicates unless CAL's own markup structurally contradicts itself.

Do not depend on custom JavaScript/CSS used to render the modern author-selector UI.

## Topic taxonomy parser

Parse CAL-owned links only:

- exact `browsegclass.php` → `group`;
- exact `browsesigla.php` → `selection`.

For every accepted link:

- require same CAL origin;
- require exactly the expected final endpoint path segment;
- require required query fields exactly once;
- when expanding a requested general class, require returned child links to name the same `generalclass`;
- preserve rendered labels and CAL selector strings exactly except HTML whitespace normalization.

Do not recursively follow child links.

## Tag/link validation

For record tags, use the same fail-closed navigation boundary:

- same CAL origin;
- exact final endpoint filename;
- exactly one `myauthor` query value.

For lemma tags with a nonblank rendered/value identity, validate the canonical CAL lemma-key structure. Subject/text tag values are CAL-owned opaque strings and are not interpreted linguistically.

## Order and deduplication

No deduplication or reranking.

Preserve:

- author choice order;
- taxonomy link order;
- bibliography record order;
- tag order within each record;
- duplicate records/tags if CAL renders them.

## Pagination contract

No paginator/continuation was observed on sampled current author, topic, or lemma result pages.

Therefore:

- each result tool fetches one page only;
- no synthetic `page` parameter is exposed;
- no automatic continuation is performed;
- the shared decoded-response-size limit is the hard per-request bound.

Parsers should fail closed on an obvious newly introduced pagination control (for example a result-page link carrying a page selector / explicit next-page semantic) rather than silently present a partial result as complete. If CAL later adds pagination, that becomes a new researched contract.

## Provenance

Successful and explicit-empty results preserve:

- `source = "CAL"`;
- final source URL;
- retrieval timestamp;
- operation;
- requested author prefix/author/general class/subclass/lemma key as applicable.

## Test-first sequence

Before production implementation, add reduced semantic fixtures and tests for:

1. author prefix selector preserving ordered choices;
2. selector target form must be same-origin and exact `getbibauthor.php` endpoint;
3. positive author result with multiple ordered `<p>` records;
4. multilingual citation text;
5. subject and lemma tags preserved in order, including homograph lemma keys;
6. a current blank/whitespace subject-tag artifact is not silently discarded;
7. explicit author no-data marker;
8. root topic taxonomy with group and selection refs;
9. one-level general-class expansion and request/returned-class consistency;
10. positive topic result;
11. explicit topic-empty marker;
12. positive lemma bibliography and canonical homograph key support;
13. explicit lemma-empty marker;
14. unknown successful markup → `BibliographyParseError`;
15. records plus an empty marker → parser drift;
16. off-origin and same-origin endpoint-lookalike forms/links → parser drift;
17. malformed/repeated required tag/taxonomy query fields → parser drift;
18. obvious newly introduced pagination → parser drift;
19. invalid caller prefix/author/topic/lemma inputs fail before transport;
20. exact one-request mappings for all five service methods;
21. no implicit author-result, topic-recursion, or lexicon follow-up;
22. provenance fields;
23. MCP introspection exposes the five scholarly tools without CAL PHP/form names such as `myauthor`, `first3`, or endpoint filenames.

A valid primary RED requires install, Ruff lint/format, and strict mypy to pass while pytest fails because the bibliography production capability does not yet exist.

## GREEN implementation gate

Implement only the models, semantic HTML parsers, local validators, service methods, shared lemma-key helper extraction, and MCP registration required by the frozen tests.

Reuse the lifespan-managed shared `CalHttpClient`; do not add another HTTP stack.

## Documentation gate

Before independent review:

- add `docs/tools/bibliography.md`;
- update README tool/current-state surfaces;
- document that the former “keyword” wording maps to CAL's current text/subject taxonomy;
- document result completeness caveat from CAL;
- document no record IDs, no dedup/rerank, no current pagination, one-request bounds, and explicit follow-up workflow;
- record fixture provenance.

## Independent review gate

Run a fresh skeptical review on the exact final SHA. Review specifically for:

- accidentally treating tag links as record-detail identities;
- record-boundary loss or merging adjacent `<p>` citations;
- silent dropping of multilingual text or empty CAL tag artifacts;
- invented citation fields not supported by CAL;
- deduplication/reordering;
- treating malformed output as empty;
- stale hard-coded topic taxonomy;
- hidden recursive topic traversal or implicit author/lemma follow-up;
- unsafe/off-origin/endpoint-lookalike links;
- accepting an unrepresented paginator and silently returning partial results;
- weakening canonical lemma-key validation;
- provenance contradictions.

Any blocker gets a new test-only review-regression RED before its production fix, followed by full GREEN CI and a fresh whole-PR re-review.

## CAL load bound

Production network bound:

- exactly one CAL request for each public tool call;
- no recursion, prefetch, crawl, mirror, background indexing, or result-page continuation;
- response body remains bounded by the shared HTTP client policy.
