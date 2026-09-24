# Issue #150 plan — bibliography result-page drift

Date: 2026-09-24. Research: `docs/research/issue-150-bibliography-drift.md`, committed before behavior tests.

1. Reduced current fixtures, each with a provenance comment:
   - `bibliography_lemma_br_n_current.html`: three `<p>` records inside the single card, with the legacy `<TITLE>`;
   - `bibliography_author_sokoloff_current.html`: two records, one with the trailing empty-placeholder link;
   - `bibliography_empty_current.html`: the no-data marker inside the card.
2. RED tests (`tests/test_bibliography_current_shape.py`):
   - lemma: 3 records in order, no heading or title text in any citation, per-record links preserved;
   - author: 2 records, the placeholder omitted, the real links kept;
   - empty page: a valid empty result;
   - fail-closed cases: text outside `<p>` inside a record card, a nested `<p>`, an unclosed `<p>`, an unlabelled link with a non-empty target, a labelled link with an empty target, a mixed marker plus records;
   - `live_smoke` bibliography probe: a merged-title citation is reported as drift.
3. A valid RED has only the new behavior tests failing, with lint, format and mypy green.
4. GREEN: the smallest parser change in `src/cal_mcp/bibliography.py` (`<p>`-record mode per card, title skipping, placeholder omission, marker card); a strengthened `live_smoke` assertion.
5. Keep every existing fixture and regression green (the one-card-per-record fallback).
6. Docs: `docs/tools/bibliography.md` (placeholder omission), `research.md` R-029, fixture README.
7. Verification: the full offline suite; live over MCP for author, keyword and lemma plus one empty query (about 4 requests); `live_smoke`.
8. Independent adversarial review of the exact candidate SHA before merge.
