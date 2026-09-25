# Issue #182 plan — display coordinate and comment link on table-layout text pages

Date: 2026-09-25. Research: `docs/research/issue-182-text-row-coordinates.md`, committed before behavior tests.

1. Reduced current fixture with a provenance comment: `text_page_philemon_62057_current.html`, with 2 rows carrying the "[ai]" link. Reuse the current Samaritan (comment-link rows) and Ginza (plain rows) fixtures from #166.
2. RED tests (`tests/test_text_page_row_coordinates_current.py`) through `TextService.page`:
   - Samaritan: `display_coordinate` `Gen12:01)0(` and `comment_url` set;
   - Ginza: `001:01` with no comment URL;
   - Philemon: `01`, without the "[ai]" text;
   - line text and tokens unchanged;
   - fail closed on a comment link for another coordinate, an unknown link in the coordinate cell, a third cell, lexical links in the coordinate cell, loose text in the token cell, and a lexical link outside a text row.
3. A valid RED has the positive tests failing, with lint, format and mypy green.
4. GREEN: a `text-display` row reader in `texts.py`, keeping the line-mode fallback.
5. All existing text-page fixtures stay green.
6. Docs: `docs/tools/texts.md` (row fields), `research.md` R-035, fixture README, CHANGELOG.
7. Verification: the full offline suite; offline over the 17 captures; live over MCP for five collections.
8. Independent adversarial review of the exact candidate SHA.
