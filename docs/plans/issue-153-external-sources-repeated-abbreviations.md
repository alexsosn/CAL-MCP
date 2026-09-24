# Issue #153 plan — repeated abbreviations on the external-citation source list

Date: 2026-09-24. Research: `docs/research/issue-153-external-sources-repeated-abbreviations.md`, committed before behavior tests.

1. Add a reduced current fixture `external_citation_sources_syriac_current.html`: the heading, the `1CorH` row and the `EbPar` and `JS` pairs, in CAL order (CAL's JavaScript result counter is omitted).
2. RED: all five rows are returned in order with distinct descriptions. A repeated abbreviation with a different citations link fails closed.
3. GREEN: remove the uniqueness check. The existing per-row check that each link's `abbrev` value equals its displayed abbreviation already guarantees that shared abbreviations share one citation list; a separate same-link check would be unreachable.
4. Docs: `docs/tools/external-citations.md`, `research.md` R-032, fixture README.
5. Verification: full offline suite; the full 702-row capture offline; live over MCP (about 2 requests); independent review.
