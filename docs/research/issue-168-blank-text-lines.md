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


## 2026-09-26 live amendment — empty anchors are lexical slots, not only blank lines

The first installed-stdio live verification of PR #191 reached current CAL successfully (HTTP 200)
but still failed with `CAL lexical token link has no rendered token`. Two bounded follow-up GETs
then inspected only the structure of empty lexical anchors and affected rows; no full scholarly text
was retained.

Current `60424` evidence:

- the structural probe counted 314 `<tr>` elements under the current text-display region; a later installed-stdio verification returned 313 parsed two-cell lines. The row count is not an invariant for this issue;
- 10 rows contain empty `getlex.php` anchors;
- 29 empty anchors total;
- empty anchors occur at CAL word indexes 0 through 11;
- only coordinate `60424100508` is an all-empty row (one empty slot, word 0);
- the other 9 affected rows mix empty slots with rendered lexical links;
- every affected row has one machine coordinate across all of its lexical links;
- for example, coordinate `60424100509` has empty slots
  `0,1,2,3,8,9,10,11` plus four rendered lexical links;
- coordinate `60424100523` has an empty slot at word 1 and rendered links including word 0.

This supersedes the earlier hypothesis that every empty anchor is the sole `word=0` link of a
blank line. It also supersedes the original issue acceptance statement that an empty link at
`word>0` or mixed with rendered tokens must fail closed.

### Revised representation

An empty lexical anchor is an explicit CAL **word slot with no rendered token text**. Silently
dropping it would erase information that CAL exposes: its word index. Returning it as a
`TextToken(text="")` would make the existing `tokens` field mix rendered tokens with
non-rendered placeholders.

Therefore each `TextLine` gains additive `empty_word_indexes`:

- `tokens` continues to contain only rendered lexical links;
- `empty_word_indexes` preserves the ordered indexes of exact current empty `getlex.php` slots;
- `text` is still composed only from rendered token text;
- an all-empty row has `text=""`, `tokens=[]`, and e.g. `empty_word_indexes=[0]`;
- a mixed row keeps its rendered tokens and records the empty slots separately.

For every empty slot, the accepted current shape is narrowly bounded to the relative
`getlex.php` route with exactly `coord`, `word`, and `hasvariant`; `coord` must be a
positive decimal, `word` a non-negative decimal, and `hasvariant=0`. All rendered and empty
lexical links in one row must name the same coordinate. Duplicate empty indexes or an empty index
that collides with a rendered token index fail closed.

This is an additive output-schema change. It does not add requests or expose a new operation.

### Final live verification

On 2026-09-26, an installed `cal-mcp` candidate was launched over stdio and
`cal_text_page("60424")` was called once against current CAL. The call succeeded and returned
29 `empty_word_indexes` slots across 9 mixed rows plus the known all-empty row. The serialized
page contained 313 parsed lines. The earlier structural probe's 314 count referred to raw
`<tr>` elements and is deliberately not treated as a public line-count contract.
