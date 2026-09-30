# Issue #203 research — `bablex.php` token links on KWIC full-context pages

Date: 2026-09-29 (capture from #181). Base: `3c47db7`.

## Trigger

#181's research found that `cal_kwic_full_context("71002", "7100201051217", "H", subtext_id="01051")` (Babylonian Talmud, Shabbat) fails with `parser_drift` "CAL full-context context row has no recognized lexical links". The row parser accepts only `getlex.php` token links. Text pages (`cal_text_page`) already accept both CAL endpoint families, `getlex.php` and `bablex.php`.

## Evidence

A capture of `get_a_kwicchapter.php?file=71002&sub=01051&cset=H&target=7100201051217` from 2026-09-29, a bounded GET through the production client (see `docs/research/issue-181-full-context-subtext.md`). No new request was needed.

- 34 rows, 204 token links, all `bablex.php?coord=…&word=…`. The selector set is exactly `{coord, word}`, with no `hasvariant`.
- There are 7 `comment.php?coord=…` links. The target row and some others wrap CAL's display locator (`ms01 pg051 sd2 ln17`) in the comment anchor; other rows show the locator as plain text.
- 31 rows end with one empty `bablex.php` anchor whose word index is the successor of the last visible token. In one of them (row `7100201050244`, `ms01 pg050 sd2 ln44`) that anchor wraps an empty `<cal-variant></cal-variant>`. That is the same Hebrew-rendering artifact the full-context parser already accepts for `getlex.php` under `cset=H` (research of 2026-09-10).
- The file-info coordinate is the bare `71002`, which #181 accepts.
- CAL's manuscript-variant layer is present (`.hide-variants cal-variant{display:none;}` and a "Hide manuscript variants" `variants=0` toggle). In row ln44, token 1 renders as `ברגזתא<cal-variant>/גזרתא</cal-variant>`, and tokens 2–4 consist entirely of `<cal-variant>` content.

## Consequences

- Full-context rows accept `bablex.php` token links with exactly the selectors `{coord, word}`, and `getlex.php` links with exactly `{coord, word, hasvariant}` as before. Mixing the two endpoint families in one row fails closed.
- All other row checks apply unchanged: one coordinate per row, decimal word indexes, the terminal empty anchor only under `H`, and the comment coordinate matching its row.
- Production requests are unchanged.
- Manuscript-variant readings are kept inline in the token text, exactly as `cal_text_page` does (`<cal-variant>` is an allowed text-row tag there). A token whose whole text is a variant reading is an ordinary token. The variant-wrapped terminal empty anchor is the same Hebrew rendering artifact and is omitted.
- The endpoint family is checked per row. A page mixing `getlex.php` rows and `bablex.php` rows would be accepted; none was observed.

## Review follow-up (2026-09-29)

The review found that the full-context row parser (before this change, and for both families) accepts loose text between token links, and silently drops unknown tags inside a token. `cal_text_page` rejects both. It also found that `_is_path` compares only the final path segment. These are pre-existing and not specific to `bablex.php`, so they are tracked as a follow-up issue rather than widened into this change.
