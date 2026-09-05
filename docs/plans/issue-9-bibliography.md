# Issue #9 plan — bounded CAL bibliography search

**Plan date:** 2026-09-05

This plan follows the repository loop: research → plan → test-only RED → minimal implementation → GREEN → documentation → independent skeptical review → review-fix RED/GREEN if needed → fresh independent re-review → merge.

## Public contract

Expose the current CAL bibliography workflow as four caller-controlled operations:

```text
cal_bibliography_authors(prefix)
cal_bibliography_author(author)
cal_bibliography_keyword(keyword)
cal_bibliography_lemma(lemma_key)
```

- `cal_bibliography_authors` performs the one-to-six-character author-prefix lookup and returns CAL's ordered exact author choices.
- `cal_bibliography_author` retrieves records for one exact author value chosen by the caller.
- `cal_bibliography_keyword` retrieves records for one exact CAL text/subject bibliography tag. “Keyword” follows the issue/CAL archive terminology; it is not substring/full-text search.
- `cal_bibliography_lemma` retrieves records for one exact CAL lemma key.

Each operation performs exactly one CAL request. Prefix → author-result navigation is explicitly two calls. Record tags are returned as navigable metadata but are never followed automatically.

## Bounds and continuation

- Author prefix: 1–6 characters after trimming surrounding ASCII spaces.
- Exact author: nonempty, single-line, at most 160 characters.
- Keyword/tag: nonempty, single-line, at most 128 characters.
- Lemma key: reuse the current CAL lemma-key structural/CAL-code validation used by concordance operations; at most 128 characters.
- No current bibliography result surface exposes pagination or a continuation token. No public page/offset/limit parameter is invented.
- The shared 2 MiB decoded-response limit remains the hard per-request result bound; over-limit pages fail rather than truncate.
- If CAL later adds a continuation control to these pages, that is parser/contract drift to review, not permission for hidden iteration.

## Typed models

Add `bibliography.py` with:

- `BibliographyQueryKind` — `author`, `keyword`, `lemma`;
- `BibliographyAuthorCandidate` — exact CAL author value/label;
- `BibliographyLink` — rendered label, absolute CAL URL, recognized query kind when applicable, and exact `myauthor` query value when present;
- `BibliographyRecord` — rendered citation text plus ordered CAL links/tags;
- `BibliographyAuthorOptionsResult` — submitted prefix, ordered candidates, provenance;
- `BibliographyResult` — query kind, submitted query, CAL display heading, ordered records, provenance;
- `BibliographyProvenance` — CAL source URL, retrieval time, operation, original/submitted query.

Do not split CAL's rendered citation into locally inferred author/title/journal/year fields. CAL does not expose a stable machine schema for those components and the issue requires fidelity rather than bibliographic re-parsing.

## Parser contracts

### Author-prefix selector

Parse only the current selector that targets `getbibauthor.php` and uses `myauthor`. Preserve option order and exact values. Empty prefix results require CAL's explicit `No authors found matching ...` marker.

A response with neither a valid selector nor that explicit no-match marker fails as `BibliographyParseError`.

### Final bibliography results

Recognize one heading beginning `CAL Bibliography for `. Parse only bibliography record cards, preserving record order, Unicode citation text, and every record-local link.

For recognized CAL bibliography navigation links:

- resolve relative URLs against the response URL;
- require the same CAL origin;
- recognize only `getbibauthor.php`, `getbibsigla.php`, and `getbiblemma.php` as bibliography query links;
- require one nonempty `myauthor` value;
- map those targets to `author`, `keyword`, or `lemma` without altering the query value.

Other record-local CAL links may be preserved with `query_kind=null`/`query_value=null`; cross-origin links fail closed rather than being silently trusted as CAL navigation metadata.

A page containing the explicit `NO data FOR ... ARE CURRENTLY STORED` marker is a valid empty result only if it contains no record cards. A nonempty response with no records and no marker is parser drift. Empty-marker-plus-record contradictions also fail closed.

## Test-first sequence

### RED — fixtures/parser/service/MCP contract

Before production code, add reduced semantic fixtures/tests covering:

1. author prefix with multiple ordered candidates including punctuation;
2. explicit empty author-prefix result;
3. representative author bibliography with multiple ordered records;
4. representative keyword/text-subject bibliography;
5. representative lemma bibliography;
6. explicit final-result empty state shared by all result modes;
7. Unicode citation/title text preserved exactly;
8. linked CAL tags preserve label, absolute URL, endpoint-derived query kind, and exact query value;
9. malformed/missing record citation, malformed bibliography link query, or cross-origin record link → parser drift;
10. nonempty unrecognized page → parser drift rather than empty success;
11. invalid prefix, multiline/empty/oversize author/keyword values, and invalid lemma key fail before transport;
12. exact one-request mappings for all four service methods;
13. provenance preserves original/submitted query, operation, source URL, and retrieval time;
14. MCP introspection exposes the four public operations and no private CAL endpoint/form names or page/offset parameters.

A valid primary RED requires installation, Ruff lint/format, and strict mypy to pass, with pytest failing because `cal_mcp.bibliography`/server tools do not yet exist.

### GREEN — minimal implementation

Implement only the models, dedicated small HTML parsers, validation, service methods, and MCP registration required by the RED tests. Reuse `CalHttpClient`, current lemma-key validation, and shared provenance/request-size behavior. Do not add another HTTP stack, bibliographic metadata inference, hidden follow-up calls, or result traversal.

## Documentation gate

Before review:

- add `docs/tools/bibliography.md`;
- update README's implemented tool surface;
- record reduced fixture provenance;
- document the two-step author workflow, exact-tag semantics of `keyword`, lemma-key input, Unicode fidelity, no current pagination, response-size failure, and one-request-per-call behavior;
- note that CAL's separate recent-five-years bibliography view remains for issue #12's capability audit rather than silently expanding #9.

## Independent review gate

Run a separate skeptical review on the exact final SHA. Review specifically for:

- collapsing ambiguous author prefixes into one author;
- treating arbitrary words as fuzzy/full-text keyword search;
- silently dropping record links/tags or Unicode text;
- inferring structured bibliographic fields CAL did not provide;
- accepting changed/error HTML as an empty result;
- trusting cross-origin or malformed navigation links;
- hidden pagination/tag traversal or more than one CAL request per public call;
- request values that bypass local length/single-line validation;
- provenance/query-kind contradictions;
- public schema leakage of CAL's private form/endpoint names.

Any blocker gets a new test-only review-regression RED before its fix, then a fresh independent re-review. Merge only after a clean final verdict and fully green CI.

## CAL load bound

Production: exactly one CAL request per public operation, with author discovery and exact-author retrieval remaining separate caller actions. No archive traversal, recent-bibliography prefetch, tag expansion, result pagination loop, local index, or mirror.

Tests: offline reduced fixtures only.
