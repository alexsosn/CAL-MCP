# Issue #168 research — empty word links on blank Syriac text lines

Date: 2026-09-26. Base: `9926a040`.

## Trigger

The 2026-09-25 user-level stdio MCP end-to-end run found that `cal_text_page("60424")`
(Ephrem sermons) fails closed with `CAL lexical token link has no rendered token`.

The captured current CAL row was:

```html
<tr><td valign="top">1.005:08 </td><td><a href="getlex.php?coord=60424100508&word=0&hasvariant=0"></a> </td></tr>
```

The same capture contained 29 such rows. They have a normal display coordinate, exactly one
`getlex.php` anchor in the token cell, `word=0`, `hasvariant=0`, and no rendered token text.

## Recheck and evidence boundary

A fresh CAL GET was attempted from the current development environment on 2026-09-26, but this
runtime cannot resolve `cal.huc.edu`; web retrieval also cannot open that route. I therefore do
not invent or broaden live evidence. The implementation is bounded to the exact shape already
captured by the 2026-09-25 E2E run and recorded in issue #168.

The current table-row parser merged in #187 already preserves the coordinate cell and deliberately
fails on rows with no usable token. This issue changes only the one researched sentinel shape.

## Contract

Treat a row as a CAL blank line only when all of these are true:

1. it is in the current two-cell `text-display` row shape;
2. the token cell has no loose text;
3. the token cell contains exactly one link;
4. that link is `getlex.php`;
5. its selectors are exactly `coord`, `word`, and `hasvariant`;
6. `coord` is a positive-decimal CAL coordinate;
7. `word=0` and `hasvariant=0`;
8. the anchor text is empty.

Represent it as a normal `TextLine` with the machine `coordinate` from the link,
CAL's `display_coordinate`, `text=""`, and `tokens=[]`. Coordinate-cell validation
(comment/Ask-AI links) remains identical to ordinary rows.

Fail closed on an empty anchor mixed with real tokens, an empty anchor at `word>0`, a different
route/query shape, loose text, or a row with no lexical link at all.

## TDD evidence source

The RED fixture will preserve the exact captured blank row above. A separately captured current
Peshitta Philemon fixture from #182 is reused as the normal-row control rather than fabricating a
normal Ephrem row that is not present in the retained evidence.

## Upstream/request impact

Parsing only. No additional CAL requests, retries, traversal, caching, or hidden pagination.
