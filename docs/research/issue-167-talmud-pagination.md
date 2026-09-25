# Issue #167 research — pagination marker on current paginated text pages

Date: 2026-09-25. Base: `0338642`.

## Trigger

The 2026-09-25 user-level MCP end-to-end run (#15) found that `cal_text_page("71001")` (BT Berakhot) fails with `parser_drift` "CAL text page has navigation without pagination metadata", although the page renders `Page 1 of 50`.

## Live-current evidence

Four bounded GETs through the production `CalHttpClient` (project User-Agent, sequential): `71001` pages 1, 2 and 50 (`page=0`, `1`, `49`), and `71026` page 1 (BT Avodah Zarah, the text of the existing `text_page_bt_az.html` fixture).

Each page renders the marker twice. The top copy sits in a `<center>` directly after the "Hide manuscript variants" toggle, and the bottom copy after the text table:

```html
…Hide manuscript variants</a></center><center>Page 1 of 50 &nbsp; (2251 lines total) &nbsp; <a href="get_a_chapter.php?file=71001&sub=&cset=R&clen=5&page=1">next page &raquo;</a> &nbsp; <a href="get_a_chapter.php?file=71001&amp;sub=&amp;cset=R&amp;page=all">show all</a></center>
…
<center>Page 1 of 50 &nbsp; <a href="…&clen=5&page=1">next page &raquo;</a> &nbsp; <a href="…&page=all">show all</a></center>
```

The text-page line splitter does not break at `</center><center>`. The marker therefore reaches the parser inside lines such as:

| Page | Top line text | Bottom line text |
| --- | --- | --- |
| 71001 p1 | `Hide manuscript variantsPage 1 of 50 (2251 lines total) next page » show all` | `Page 1 of 50 next page » show all` |
| 71001 p2 | `Hide manuscript variants« previous page Page 2 of 50 (2251 lines total) next page » show all` | `« previous page Page 2 of 50 next page » show all` |
| 71001 p50 | `Hide manuscript variants« previous page Page 50 of 50 (2251 lines total) show all` | `« previous page Page 50 of 50 show all` |
| 71026 p1 | `Hide manuscript variantsPage 1 of 50 (2413 lines total) next page » show all` | `Page 1 of 50 next page » show all` |

The parser only recognized a line whose whole text is `Page N of M (T lines total)`, which was the shape of the reduced `text_page_bt_az.html` fixture. The current page has no such line, so `page_count` stays unknown and the rendered navigation is rejected.

The navigation links themselves are unchanged in meaning. `previous page` / `next page` links address the same file with a zero-based `page`, and carry an extra `clen=5` context-length parameter and an empty `sub=`. The `show all` (`page=all`) and `variants=0` toggle links are not page navigation, and the navigation parser already ignores them by label.

## Consequences

- A pagination marker is the text that remains on a non-token line after removing that line's link texts. It must be exactly `Page N of M`, optionally followed by `(T lines total)`. Any other leftover text means the line is not a marker.
- All markers on a page must agree on page and count. The total is taken from the marker that shows it; two different totals fail closed.
- If navigation is present and no marker is recognized, the page still fails closed.
- Navigation handling, `clen`, `show all` and the variants toggle are unchanged. Public schema and request counts are unchanged.

## Offline verification

With the rule applied, `71001` pages 1, 2 and 50 give `page`/`page_count`/`total_lines` of 1/50/2251, 2/50/2251 and 50/50/2251, with previous and next navigation 2, 1–3 and 49–none. `71026` page 1 gives 1/50/2413.
