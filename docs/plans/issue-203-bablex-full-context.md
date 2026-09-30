# Issue #203 plan — `bablex.php` token links on KWIC full-context pages

Date: 2026-09-29. Research: `docs/research/issue-203-bablex-full-context.md`, committed before behavior tests.

1. A reduced fixture `kwic_full_context_bt_71002_01051_current.html` (the target row and its neighbours) with a provenance comment.
2. RED tests (`tests/test_kwic_full_context_bablex_current.py`):
   - the page is found, with `bablex.php` lexical URLs, the target row, its display locator and comment URL, and the terminal empty anchor omitted;
   - fail-closed cases: a `bablex.php` link with `hasvariant` or another extra selector, a missing `word`, a row mixing `bablex.php` and `getlex.php`, and a `bablex.php` link naming another coordinate.
3. GREEN: the full-context row parser accepts the `bablex.php` family with its own selector set.
4. Docs: `docs/tools/concordance.md` (the #203 note becomes a supported statement), `research.md` R-049, the fixture README, CHANGELOG.
5. Verification: the full suite; offline on the full capture; live over MCP (BT KWIC hit → full context).
6. Independent adversarial review of the exact candidate SHA.
