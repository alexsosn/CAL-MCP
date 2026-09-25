# Issue #167 plan — pagination marker on current paginated text pages

Date: 2026-09-25. Research: `docs/research/issue-167-talmud-pagination.md`, committed before behavior tests.

1. Reduced current fixtures with provenance comments: `text_page_bt_ber_p2_current.html` (middle page, both markers, previous and next navigation) and `text_page_bt_ber_last_current.html` (last page, previous only).
2. RED tests (`tests/test_text_page_pagination_current.py`) through `TextService.page` with a fixture transport:
   - page 2 gives `page` 2, `page_count` 50, `total_lines` 2251, previous 1, next 3;
   - the last page gives 50/50/2251, previous 49, next none;
   - fail closed on markers disagreeing in page, count or total; on a marker line with stray non-link text; and on navigation with no recognizable marker.
3. A valid RED has the positive tests and the tests that pin new fail-closed messages failing (6 of 8 on `b9ba0ce`), with lint, format and mypy green.
4. GREEN: marker recognition on link-stripped non-token lines, with optional total and merged agreement.
5. The existing `text_page_bt_az.html` and other text-page fixtures stay green.
6. Docs: `docs/tools/texts.md` if wording needs it, `research.md` R-034, fixture README.
7. Verification: the full offline suite; live over MCP for 71001 pages 1, 2 and 50 and 71026 page 1.
8. Independent adversarial review of the exact candidate SHA.
9. Out-of-range pages, added after the live check: RED tests (`tests/test_text_page_out_of_range.py`) for a page beyond the last (paginated and single-page), a mismatch on a non-last page staying drift, and the MCP error envelope. GREEN: `CalOutOfRangeError`, classified as `invalid_input` with `upstream_reached=true`. Live verification includes `71001` page 51.
