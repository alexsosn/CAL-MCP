# Issue #6 plan — bounded CAL concordance and KWIC

**Plan date:** 2026-09-05

This plan follows the repository loop: research → plan → test-only RED → minimal implementation → GREEN → documentation → independent skeptical review → review-fix RED/GREEN if needed → fresh independent re-review → merge.

## Public contract

Expose four small caller-controlled operations rather than one implicit traversal:

```text
cal_text_concordance(text_id, script="semitic")
cal_kwic_texts(lemma_key, text_ids, script="roman")
cal_kwic_dialects(lemma_key)
cal_kwic_dialect(lemma_key, dialect_id)
```

Rationale:

- `cal_text_concordance` is CAL's one-text lemma-frequency index (`newconcord.php`), not a hidden KWIC expansion.
- `cal_kwic_texts` performs one advanced KWIC request over an explicit caller-supplied text set.
- `cal_kwic_dialects` exposes CAL's current per-lemma dialect ID/label selector without hard-coding those IDs as adapter-owned constants.
- `cal_kwic_dialect` performs one KWIC request for one explicit CAL dialect ID.

Every operation performs exactly one CAL request. Moving from a frequency row or dialect selector to a KWIC result requires a second explicit MCP call by the caller.

## Bounds

- `cal_kwic_texts` accepts 1–8 text IDs per call.
- Text IDs and dialect IDs are decimal strings and remain opaque.
- Duplicate text IDs are rejected locally.
- No result pagination/continuation exists in the current observed surface, so CAL-MCP does not invent one.
- No `lth`/context-window parameter is exposed because current CAL ignores it in bounded A/B testing.
- The shared HTTP decoded-response limit remains the hard per-request body bound; over-limit responses fail rather than truncate.

## Rendering choices

Basic one-text concordance currently exposes CAL's two rendering choices:

- `transliteration` → upstream `R`;
- `semitic` → upstream `S`.

Advanced text-scoped KWIC exposes:

- `roman` → `R`;
- `hebrew` → `H`;
- `syriac` → `S`.

Dialect KWIC uses CAL's dialect result rendering and therefore has no adapter rendering parameter.

## Typed models

Add a `concordance.py` module with models along these lines:

- `ConcordanceLemma` — `frequency`, `lemma_key`, `gloss`, `kwic_url`;
- `TextConcordanceResult` — requested text ID, rendering choice, ordered lemma rows, provenance;
- `KwicDialectRef` — opaque `dialect_id`, CAL display `label`;
- `KwicDialectOptionsResult` — requested lemma key, ordered dialect refs, provenance;
- `KwicHit` — CAL file ID, optional subtext ID, target coordinate, rendered context string, full-context URL, returned charset code;
- `KwicResult` — requested lemma key, scope kind (`texts` or `dialect`), ordered scope IDs, upstream total count, ordered hits, explicitly empty scope IDs, provenance;
- `ConcordanceProvenance` — CAL source URL, retrieval timestamp, operation, original/submitted lemma key where relevant, requested text/dialect IDs, rendering choice.

Hits remain ordered and duplicate target coordinates remain duplicate hits.

## Parser contracts

### One-text frequency index

Recognize the current `Frequencies of lemmas in text <id>` marker. For every `showKWIC.php` row, preserve:

- integer frequency;
- linked CAL lemma key;
- rendered gloss;
- absolute KWIC URL.

Validate that the link's `texts` parameter matches the requested text ID and that its character-set parameter matches the requested rendering. Missing frequency/gloss/key, repeated/conflicting required parameters, or a page without the expected marker is parser drift.

### Dialect selector

Parse only the form targeting `show1dialectKWIC.php`. Validate the hidden lemma/POS values against the requested lemma key and preserve every ordered `texts` option as an opaque ID/label pair. Missing/duplicate selector semantics fail closed.

### KWIC results

Recognize the exact requested heading and the rendered `total examples: N` count. Preserve every `get_a_kwicchapter.php` target link in order. For each hit validate and return:

- decimal file ID;
- optional decimal subtext ID;
- decimal target coordinate equal to the rendered link coordinate;
- current charset code from the link;
- rendered target-row context;
- absolute full-context URL.

A `total examples: 0` page with CAL's explicit `no examples found in ...` marker is a valid empty result. A positive total must equal the number of parsed target links. Any mismatch is parser drift rather than partial success.

## Lemma-key validation

Concordance operations take a CAL lemma key rather than a free natural-language query. Split the final ASCII-space token as CAL's POS/internal key suffix, validate the lemma portion using the existing CAL-code validator semantics, and preserve the CAL-code spelling sent upstream. Do not convert `x`, `)`, `$`, etc. to Unicode for this endpoint family.

The suffix is validated structurally as a short ASCII CAL key token, not against a locally frozen POS ontology, because current CAL keys include internal variants such as `V01` and other suffixes beyond the advanced form's human-facing POS menu.

## Test-first sequence

### RED — fixtures/parser/service/MCP contract

Before production code, add reduced semantic fixtures/tests covering:

1. Tel Dan single-text frequency rows with frequency, lemma key, gloss and KWIC URL;
2. multi-text KWIC where one text is empty and another has multiple ordered hits;
3. duplicate target coordinate preserved as two hits;
4. explicit all-empty KWIC (`total examples: 0`);
5. one dialect KWIC result;
6. dialect selector option IDs/labels;
7. positive total differing from parsed target links → parser drift;
8. missing target context or malformed file/sub/target query parameter → parser drift;
9. malformed lemma key/text ID/dialect ID/rendering value and duplicate/too-many text IDs fail before transport;
10. exact one-request mappings for each service method;
11. provenance preserves submitted lemma key/scope/rendering/source URL/retrieval time;
12. MCP introspection exposes the four tools and no private CAL endpoint/form names or `lth` parameter.

A valid primary RED requires install, Ruff lint/format and strict mypy to pass, with pytest failing because the new production module/tools do not yet exist.

### GREEN — minimal implementation

Implement only the models, row/selector parsers, validation, services and MCP registration required by those tests. Reuse the shared `CalHttpClient` and semantic HTML/link utilities where their contract fits; do not add a second HTTP stack or hidden follow-up calls.

## Documentation gate

Before review:

- add `docs/tools/concordance.md`;
- update README's MCP surface/current-state sections;
- record reduced fixture provenance;
- fold stable conclusions into `research.md` if appropriate;
- document 1–8 text scope, rendering choices, no `lth`, no pagination, response-size failure, duplicate-hit preservation, and explicit two-step frequency/dialect traversal.

## Independent review gate

Run a separate skeptical review on the exact final SHA. Review specifically for:

- accidental result truncation when CAL's total exceeds parsed hit links;
- deduplication of repeated target coordinates;
- treating a missing/changed result page as empty;
- incorrect text-vs-dialect semantics caused by CAL's confusing `texts`/`dialect` labels;
- stale/hard-coded dialect IDs;
- sending malformed or unbounded text lists upstream;
- exposing or honoring the stale `lth` parameter;
- hidden second requests or automatic traversal from frequency/dialect selectors;
- unsafe Unicode conversion of CAL lemma keys;
- provenance contradictions or wrong charset mapping.

Any blocker gets a new test-only review-regression RED before its fix, then a fresh independent re-review. Merge only after clean final verdict and fully green CI.

## CAL load bound

Production:

- one CAL request per public operation;
- at most 8 explicitly selected text IDs in one advanced KWIC call;
- no result-page iteration, no dialect expansion, no full-text follow-up, no prefetch/crawl/mirror.

Tests are offline fixtures only.
