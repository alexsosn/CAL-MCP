# Issue #153 plan — repeated abbreviations on the external-citation source list

Date: 2026-09-24. Research: `docs/research/issue-153-external-sources-repeated-abbreviations.md`, committed before behavior tests.

1. Add a reduced current fixture `external_citation_sources_syriac_current.html`: the heading, the counter, the `1CorH` row and the `EbPar` and `JS` pairs, in CAL order.
2. RED: all five rows are returned in order with distinct descriptions. A repeated abbreviation with a different citations link fails closed.
3. GREEN: replace the uniqueness check with a same-link consistency check.
4. Docs: `docs/tools/external-citations.md`, `research.md` R-032, fixture README.
5. Verification: full offline suite; the full 702-row capture offline; live over MCP (about 2 requests); independent review.
