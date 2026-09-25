# Issue #151 plan — citation context for `bablex.php` texts

Date: 2026-09-24. Research: `docs/research/issue-151-citation-context-bablex.md`, committed before behavior tests.

1. Add a reduced fixture `lexicon_citation_context_bt_git_48a50.html` from the 2026-09-24 page: the file-info link, the line before, a separator, the bold target row with its red comment link, a separator and one row after, with a few tokens each.
2. RED tests: the page parses as `found` with the target row's coordinate, manuscript-style display coordinate, `bablex.php` token URLs and a comment URL; a row mixing `getlex.php` and `bablex.php` fails closed; an unexpected `bablex.php` query key fails closed.
3. GREEN: accept both families in `_parse_text_row` (candidate detection and URL validation), and reject a mixed row.
4. Docs: `docs/tools/lexicon.md` (citation context covers both token families), `research.md` R-030, fixture README, CHANGELOG.
5. Verification: full offline suite; live over MCP (about 2 requests); independent review of the exact SHA.
