# Issue #178 plan — citation search rows and headerless citations

Date: 2026-09-29. Research: `docs/research/issue-178-headerless-citation.md`, committed before behavior tests.

1. A reduced current fixture from the `king` capture, with a provenance comment: the `brt ym` row with its headerless pair, a `kl … n.(pr.)` row, a `krk … n.m.(f.)` row and one ordinary row.
2. RED tests (`tests/test_citation_search_rows_current.py`):
   - hits are in CAL's order, and the headerless pair has `lemma: null` with its own context, reference, source text and translation;
   - headers with unusual POS forms keep CAL's `<pos>` text, headwords and pronunciation;
   - on the current camel capture, the output is identical to the earlier parser's output (regression);
   - fail-closed shapes: a row without a header, two headers, no `<pos>`, a context without a citation, a citation without a context.
3. GREEN: a row-container parser for the current layout; `CitationSearchHit.lemma` becomes nullable.
4. Docs: `docs/tools/search.md`, the tool docstring, `research.md` R-048, the fixture README, CHANGELOG.
5. Verification: the full suite; offline on both captures; live over MCP for `king` and `camel`.
6. Independent adversarial review of the exact candidate SHA.
