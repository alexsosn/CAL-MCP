# Issue #130 research — KWIC full-context row identity drift

**Research date:** 2026-09-10  
**Baseline:** `main` at `b745efad184302925c69e7fbbc796c00c7e2d6c2`  
**Issue:** #130

## Question

Can the newly merged KWIC full-context parser silently return incomplete scholarly context when one CAL text row loses its recognized lexical-link route?

## Current behavior

`parse_kwic_full_context_page()` parses every table row through `_parse_full_context_row()`. That helper first collects links whose path is `getlex.php` and immediately returns `None` when the collection is empty.

This means “row has no recognized lexical links” is currently indistinguishable from “row is a presentation/control row and should be ignored”.

The reduced Roman fixture merged with #129 contains three current-shaped context rows. Each has two cells:

1. a coordinate cell with one `comment.php?coord=<machine coordinate>` link;
2. a rendered text cell whose token anchors point to `getlex.php?coord=...&word=...&hasvariant=0`.

If both `getlex.php` routes in non-target row `1325002` are changed to an unrecognized path while the row's comment link and rendered text remain intact, current code returns `None` for that row. Rows `1325003` and `1325004` still parse, the requested target still occurs exactly once, and the overall result remains `found`. The caller therefore receives plausible but incomplete context.

No live CAL probe is needed: this is a deterministic consequence of the merged parser and retained current-shaped fixture.

## Why this is material

Repository policy requires fail-closed handling of material upstream drift. Full-context output is explicitly target-centered context, and #113's plan requires recognized rows to preserve CAL row order and line/token relationships. Silently omitting one line changes the scholarly data returned while preserving a superficially successful result.

The existing target-exactly-once invariant cannot catch loss of a different context row.

## Safe row-identity signal

The parser must not reject every arbitrary two-cell table row without lexical links: current full-context pages also contain presentation controls, so generic table shape is not sufficient evidence that a row is scholarly context.

A `comment.php` link is a stronger current contract signal. #113 research identifies the first cell of a full-context text row as the coordinate/comment cell, and the retained Roman fixture uses exactly that form. Existing parser logic already treats `comment.php` as the only permitted coordinate-cell link for recognized text rows and validates its `coord` selector against the lexical row coordinate.

Therefore the narrow fail-closed distinction is:

- no recognized `getlex.php` links **and no `comment.php` line-identity link** → continue treating the row as non-context/presentation and ignore it;
- no recognized `getlex.php` links **but at least one `comment.php` link** → this is context-shaped row drift and must raise `ConcordanceParseError` rather than disappear;
- rows with recognized lexical links continue through all existing strict validation unchanged.

This does not claim that every future context row must have a comment link. It closes the demonstrated silent-loss path for a row that still exposes the currently recognized line identity while avoiding a new assumption about unrelated control tables.

## Test strategy

Use the existing reduced Roman fixture only. Mutate both `getlex.php?coord=1325002...` paths in the non-target row to `brokenlex.php?...`, leaving `comment.php?coord=1325002` and rendered labels/text unchanged.

Expected behavior after the fix: `parse_kwic_full_context_page()` raises `ConcordanceParseError`.

The test is effective because current production drops that row and returns `found`; it should therefore be a clean behavior-first RED with no fixture/network changes.

Existing full-context tests must stay GREEN, especially:

- valid Roman and Hebrew rows;
- scoped Hebrew terminal empty-anchor handling;
- typed not-found state;
- target exactly-once validation;
- strict lexical selector validation;
- one-request service behavior.

## Scope and non-goals

Change only full-context row classification/error handling plus its regression coverage. Do not change:

- public MCP schema or 31-tool release manifest;
- request construction, cache namespace, request count, retry/backoff, or transport policy;
- ordinary text-page parsing;
- existing KWIC hit parsing;
- child-link traversal/prefetch behavior;
- live smoke request budget.

## Conclusion

Issue #130 is a real fail-closed defect. A current-shaped context row that retains its `comment.php` line identity but loses all recognized lexical links can currently vanish from an otherwise successful result. The minimal robust correction is to treat such a comment-bearing row as malformed context and raise rather than ignore it.