# Issue #207 plan — CAL's "is not a valid search string" citation-search rejection

Date: 2026-09-29. Research: `docs/research/issue-207-invalid-search-string.md`, committed before behavior tests.

1. A reduced fixture `search_citations_invalid_god_current.html` (CAL's page without its style block), with a provenance comment.
2. RED tests (`tests/test_citation_search_invalid_string_current.py`):
   - the parser raises `CalRejectedInputError` with CAL's message for `god`;
   - the MCP tool returns `invalid_input` with `upstream_reached: true`;
   - a marker quoting another string fails closed as `SearchParseError`;
   - `CalOutOfRangeError` is still classified as before.
3. GREEN: `CalRejectedInputError` in `errors.py`, and the marker check in `parse_citation_search_page` (which needs the submitted query).
4. Docs: `docs/tools/search.md`, the error documentation, `research.md` R-052, the fixture README, CHANGELOG.
5. Verification: the full suite; live over MCP for `god`, `the`, `king god` and `king`.
6. Independent adversarial review of the exact candidate SHA.
