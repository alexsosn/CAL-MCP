# Issue #52 plan — ambiguity-aware lexicon provenance

Date: 2026-09-07

## Problem

`docs/research/issue-52-ambiguity-expansion.md` requires lexicon results to preserve how conversion-driven search was reached: original query/script, generated CAL-code candidates, browse prefixes actually requested, and the candidate/lemma relationship after a single lemma is selected. The current `Provenance` records only the original/normalized query and upstream entry ID, so an ambiguity-aware lookup can deduplicate several encoding paths into one lemma while erasing those paths from the returned result.

This is a public provenance-contract gap and must be fixed before PR #53 final review.

## Public schema

Extend `Provenance` additively with stable fields present on every lexicon result:

- `cal_code_word_candidates: tuple[tuple[str, ...], ...]` — ordered candidate set for each converter word when the lookup actually uses CAL-code conversion; empty for the legacy pass-through lookup path;
- `cal_code_query_candidates: tuple[str, ...]` — ordered complete CAL-code candidates used for matching; empty for the legacy pass-through lookup path;
- `browse_prefixes: tuple[str, ...]` — exact ordered unique browse prefixes actually requested, for both conversion and legacy paths;
- `selected_cal_code_candidates: tuple[str, ...]` — conversion candidates that matched the selected lemma when exactly one entry is fetched; empty for `not_found`, ambiguous results, and legacy pass-through searches.

The serialized dictionary must always include these keys so the v0.1 schema is stable rather than conditional on result status.

## Test-first gate

Before production changes add regression tests proving:

1. bare Hebrew shin ambiguity exposes both CAL query candidates and both requested prefixes in provenance;
2. if the same lemma is reached through multiple encoding candidates, the returned lemma is deduplicated but provenance retains every matching candidate in stable order;
3. explicit `lemma_key` selection preserves only the candidate encodings that actually match that selected lemma;
4. deterministic dedicated-script lookup records its one converted candidate and actual CAL browse prefix;
5. legacy deterministic Hebrew/Syriac lookup keeps conversion-candidate fields empty while recording the raw Unicode browse prefix;
6. `not_found` retains generated candidates/prefixes but has no selected candidate relationship;
7. serialized provenance always contains the four additive fields.

A valid RED keeps Ruff lint/format and mypy GREEN and fails only because the current provenance schema lacks these fields.

## Minimal implementation

In `src/cal_mcp/lexicon.py`:

- add the four tuple fields to `Provenance` with stable serialization;
- pass converter word/query candidates and actual `browse_prefixes` into `_make_provenance()` when the conversion search path is used;
- pass only `browse_prefixes` for the legacy path;
- after selecting one lemma, compute the ordered conversion candidates whose comparison surfaces match that selected lemma and place them in `selected_cal_code_candidates`;
- retain candidate order and deduplicate without reordering;
- do not add requests or alter lookup selection/fan-out semantics.

## GREEN gate

Require deterministic and latest-compatible CI to pass Ruff, format, mypy, and full pytest. Then repeat the issue-wide acceptance audit and proceed to exact-head adversarial review only if no blocker remains.