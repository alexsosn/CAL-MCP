# Issue #203 research — `bablex.php` token links on KWIC full-context pages

Date: 2026-09-29 (capture from #181). Base: `3c47db7`.

## Trigger

#181's research found that `cal_kwic_full_context("71002", "7100201051217", "H", subtext_id="01051")` (Babylonian Talmud, Shabbat) fails with `parser_drift` "CAL full-context context row has no recognized lexical links". The row parser accepts only `getlex.php` token links. Text pages (`cal_text_page`) already accept both CAL endpoint families, `getlex.php` and `bablex.php`.

## Evidence

A capture of `get_a_kwicchapter.php?file=71002&sub=01051&cset=H&target=7100201051217` from 2026-09-29, a bounded GET through the production client (see `docs/research/issue-181-full-context-subtext.md`). No new request was needed.

- 34 rows, 204 token links, all `bablex.php?coord=…&word=…`. The selector set is exactly `{coord, word}`, with no `hasvariant`.
- There are 7 `comment.php?coord=…` links. The target row and some others wrap CAL's display locator (`ms01 pg051 sd2 ln17`) in the comment anchor; other rows show the locator as plain text.
- 30 rows end with one empty `bablex.php` anchor whose word index is the successor of the last visible token. That is the same Hebrew-rendering artifact the full-context parser already accepts for `getlex.php` under `cset=H` (research of 2026-09-10).
- The file-info coordinate is the bare `71002`, which #181 accepts.

## Consequences

- Full-context rows accept `bablex.php` token links with exactly the selectors `{coord, word}`, and `getlex.php` links with exactly `{coord, word, hasvariant}` as before. Mixing the two endpoint families in one row fails closed.
- All other row checks apply unchanged: one coordinate per row, decimal word indexes, the terminal empty anchor only under `H`, and the comment coordinate matching its row.
- Production requests are unchanged.
