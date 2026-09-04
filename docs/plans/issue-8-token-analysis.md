# Issue #8 plan — token-at-coordinate lexical analysis

**Plan date:** 2026-09-04

This plan follows the repository agentic loop: research → plan → test-only RED → implementation → GREEN → docs → independent skeptical review → review-fix RED/GREEN if needed → independent re-review → merge.

## Public contract

Add one bounded MCP tool:

```text
cal_token_analysis(coordinate: string, word_index: integer)
```

The public names describe CAL semantics rather than private endpoint parameters. Internally the service maps them to CAL's current `coord` and zero-based `word` query parameters.

Each call performs exactly one CAL request. It never fetches a full lexicon entry automatically.

## Typed result

Introduce a token-analysis module with:

- `TokenAnalysisStatus`: `found` / `not_found`;
- `TokenAnalysisCandidate`:
  - exact CAL `analysis_label`;
  - existing `LemmaRef` from the lexicon model;
- `TokenAnalysisResult`:
  - status;
  - requested decimal `coordinate` preserved as a string;
  - zero-based `word_index`;
  - ordered candidate tuple;
  - provenance containing CAL source URL and timezone-aware retrieval timestamp.

Multiple candidates remain multiple and ordered. The adapter does not choose a preferred analysis or parse CAL's compact analysis label into an invented morphology schema in this ticket.

## Parser contract

Use the shared semantic HTML parser and shared lexicon lemma-header parsing where semantics match.

A recognized found page must contain CAL's current analysis-page marker and one or more candidate pairs. Each candidate is represented by an exact compact analysis-label line immediately followed by a linked CAL lemma header. The lemma link must contain exactly one non-empty CAL lemma key and must parse into the existing `LemmaRef` structure.

Fail closed when:

- the analysis marker is present but candidate pairing is incomplete;
- a candidate link lacks a lemma key or recognizable lemma header;
- duplicate/conflicting markup prevents deterministic pairing;
- a successful page has neither candidates nor CAL's explicit no-data marker.

CAL's current explicit no-data phrase maps to `not_found` with an empty candidate tuple.

## Local validation

Before transport:

- `coordinate` must be a decimal string and is preserved verbatim;
- `word_index` must be an integer ≥ 0;
- boolean values are rejected as word indices.

No normalization, guessed coordinate resolution, or fallback query is attempted.

## Test-first sequence

### RED 1 — parser/service contract

Add reduced fixtures and tests before production code for:

1. one analysis preserving exact `analysis_label` and `LemmaRef` fields;
2. multiple analyses preserving CAL order and ambiguity;
3. Unicode Hebrew/Syriac headword display preservation;
4. explicit no-data → `not_found`;
5. marker-without-analysis → parser drift;
6. malformed/missing lemma link → parser drift;
7. invalid caller coordinate and invalid word indices fail before transport;
8. service sends exactly one ordered GET request to `getlex.php` and preserves coordinate/index provenance.

The valid RED is a CI run where install, Ruff, format, and strict mypy pass and pytest fails because the token-analysis production module/API does not yet exist.

### GREEN 1 — adapter/service

Implement the smallest code needed to satisfy parser/service tests. Reuse `LemmaRef`; do not duplicate lexicon entry models or add hidden follow-up requests.

### RED 2 — MCP registration

Add/extend server introspection tests so `cal_token_analysis` appears with only `coordinate` and `word_index` public parameters and neither private CAL names nor hidden expansion options.

If practical, include this assertion in the initial test-only commit; otherwise keep the registration failure isolated after core adapter GREEN.

### GREEN 2 — MCP registration

Register the tool in `server.py`, using the server-lifespan `CalHttpClient`.

## Documentation gate

Before independent review:

- add `docs/tools/token-analysis.md`;
- link it from README/docs index where current conventions require;
- document zero-based `word_index`, opaque coordinate semantics, ambiguity preservation, no-data vs parser drift, provenance, and one-request bound;
- record reduced fixture provenance;
- fold stable research conclusions into `research.md` if appropriate.

## Review gate

Run an independent skeptical review on the exact final SHA. Review specifically for:

- accidental ranking/collapse of ambiguous analyses;
- loss or reinterpretation of CAL compact analysis labels;
- divergence from the shared `LemmaRef` model;
- malformed-success pages being treated as empty/not-found;
- invalid parameters reaching CAL;
- hidden second requests / lexicon expansion;
- parser accepting unrelated lemma links from sense content;
- provenance coordinate/index contradictions;
- public exposure of private `coord`/`word` endpoint naming.

Any blocker gets a new test-only review-regression RED before its fix, followed by a fresh independent re-review. Merge only after a clean final verdict and fully green CI.

## CAL load bound

Production: exactly one user-initiated CAL GET per tool call.

Tests: offline fixtures only.

No batch token analysis, text traversal, prefetch, background indexing, or automatic lexicon-entry retrieval.
