# Issue #52 plan — provenance documentation synchronization

Date: 2026-09-07

## Problem

The implementation now exposes four additive ambiguity/conversion-path fields on every lexicon `provenance` object, as required by `docs/research/issue-52-ambiguity-expansion.md` and planned in `docs/plans/issue-52-lexicon-provenance.md`. `docs/tools/lexicon.md` still documents only the pre-#52 provenance schema, so the public documentation is stale.

## Test-first gate

Add a documentation contract test that requires the lexicon provenance table to name all four stable fields:

- `cal_code_word_candidates`;
- `cal_code_query_candidates`;
- `browse_prefixes`;
- `selected_cal_code_candidates`.

The valid RED must keep Ruff, format, mypy, and all unrelated tests GREEN and fail only because the current tool documentation omits those fields.

## Minimal documentation change

Update only the provenance section of `docs/tools/lexicon.md` to explain the four fields, including that conversion-candidate fields are empty for legacy pass-through lookup and that selected candidates are populated only when one lemma entry is fetched.

## GREEN gate

Require deterministic and latest-compatible full CI GREEN. No production code or CAL requests are part of this slice.
