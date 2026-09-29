# Issue #176 plan — dialect KWIC pages that omit the requested form

Date: 2026-09-25. Research: `docs/research/issue-176-kwic-omitted-form.md`, committed before behavior tests.

1. A reduced current fixture with a provenance comment: `kwic_dialect_nqh_71_current.html`, with the single hit and both summaries.
2. RED tests (`tests/test_kwic_dialect_omitted_form_current.py`) through `ConcordanceService.kwic_dialect`:
   - the dialect-71 page returns `forms` [`n)qt) N` 1, `nqh N` 0], `total` 1, one hit with `form_lemma_key` `n)qt) N`, `requested_form_listed` false;
   - the existing dialect-6 fixture gives `requested_form_listed` true;
   - text scope gives null;
   - fail closed when a summary's count contradicts its hits, or when no summaries remain.
3. A valid RED has the new tests failing, with lint, format and mypy green.
4. GREEN: relax the "requested form exactly once" rule to "at most once"; add `requested_form_listed` to the result, the page model and `to_dict`.
5. Docs: `docs/tools/concordance.md` (Lemma forms), server tool description, `wiki/decisions.md` D-014 amendment, `research.md` R-043, fixture README, CHANGELOG.
6. Verification: the full offline suite; live over MCP for `n)qh N` in 71 and 6.
7. Independent adversarial review of the exact candidate SHA.
