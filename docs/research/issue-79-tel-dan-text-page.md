# Issue #79 research — Tel Dan `cal_text_page` retrieval regression

Date: 2026-09-08
Baseline: `main` at `d704ee5c2b542e22c22a3929771fa466dea0a0f6`.

## Reported regression

Issue #79 reports that `cal_text_search("Tel Dan")` returns file `13250` (`TDanStel (Tel Dan Stele)`) with no subtext, while `cal_text_page(file_id="13250", page=1)` currently surfaces only a generic execution error. Existing offline coverage predates the report and models Tel Dan as a valid unpaginated text page.

## Current CAL evidence

A branch-only bounded live probe rechecked the current `get_a_chapter.php` response on 2026-09-08.

Two fixed requests were first compared:

- `https://cal.huc.edu/get_a_chapter.php?file=13250`
- `https://cal.huc.edu/get_a_chapter.php?file=13250&page=0`

Both returned HTTP 200, `text/html; charset=UTF-8`, the same 9002-byte body, the same file-information link (`/get_file_info.php?coord=13250`), the same unpaginated Tel Dan line content, and the same lexical-navigation structure. Therefore the adapter's public-page-1 to upstream-`page=0` mapping is not the cause.

The material upstream drift is the token-link endpoint. Current Tel Dan rows expose token links such as:

```text
getlex.php?coord=1325001&word=0&hasvariant=0
getlex.php?coord=1325002&word=1&hasvariant=0
```

and comment links such as:

```text
comment.php?coord=1325002
```

The current page still explicitly says “Click on a word for lexical analysis.” The `coord` and `word` fields remain decimal machine coordinates and zero-based word positions. The additional `hasvariant=0` query field is upstream navigation metadata and is not needed as a public MCP argument.

By contrast, the existing parser recognizes a token only when its link path ends in `bablex.php`. Because every current Tel Dan token is therefore ignored, `_parse_text_line()` yields no rows and `parse_text_page()` raises `TextParseError("CAL text page contains no recognizable coordinate/token rows")`. This explains the generic MCP execution error without requiring a request-routing or pagination change.

This is not evidence that `bablex.php` disappeared globally. A separately current CAL page for file `71026` (`BT AZ`) still renders token links to `bablex.php?coord=...&word=...`. CAL-MCP's token-analysis service itself already uses `getlex.php` as the generic coordinate/word analysis endpoint. The text-page adapter must therefore recognize both current CAL token-link families rather than replacing one with the other.

Current Tel Dan machine coordinates are also shorter than the 2026-09-04 reduced fixture (for example `1325001` instead of the fixture's synthetic `1325000000001`). The parser already treats coordinates as opaque decimal strings, so no length rule should be added.

## Safety and compatibility implications

The smallest faithful correction is parser-only:

- accept lexical token links whose path ends in either `bablex.php` or `getlex.php`;
- keep requiring exactly one non-empty `coord` and `word` value and validate both with the existing decimal/index rules;
- preserve the exact returned link as `lexical_url`, including CAL's extra `hasvariant` field when present;
- keep comment-coordinate consistency, file-info validation, pagination validation, request count, and public tool schema unchanged;
- do not infer tokens from unlinked text and do not weaken the requirement that a successful text page contain recognizable token rows.

A link to any other endpoint must remain non-token markup. Malformed/repeated/missing `coord` or `word` fields on either recognized token endpoint remain parser drift.

## Test strategy

Add a deliberately reduced current-shape Tel Dan fixture containing only the file-info row and a small number of lines with `getlex.php` token links (including `hasvariant=0` and one comment link). The primary service-level regression should reproduce the public call `TextService.page("13250", page=1)`, assert one CAL request, `status="found"`, current coordinate/token metadata, and exact `getlex.php` lexical URLs.

Also pin parser safety for malformed `getlex.php` token coordinates/word indexes and retain the existing `bablex.php` BT AZ fixture/tests unchanged so compatibility with both endpoint families is explicit.

Normal CI remains offline.

## Probe load and cleanup

The research probe made four fixed Tel Dan GETs total across three runs: the first successful comparison made two requests; a second one-request inspection fetched the page but failed locally because the probe accidentally reused an `HTMLParser` internal attribute name; the corrected final inspection made one request. No categories, pages, files, tokens, or lexical analyses were traversed or followed. Only bounded semantic text/link metadata was printed; no CAL page was committed.

The temporary workflow is deleted before planning/implementation.

## Sources

- CAL current Tel Dan browser: `https://cal.huc.edu/get_a_chapter.php?file=13250`
- CAL current BT AZ browser: `https://cal.huc.edu/get_a_chapter.php?file=71026`
- issue #79 reproduction
- bounded probe runs `34234831987`, `34235002531`, and `34235088010`

## Implementation implication

Issue #79 is a current upstream token-link-family drift regression. Restore `cal_text_page` by recognizing both current CAL lexical token endpoints while leaving the public schema, one-request bound, line/token model, and fail-closed validation intact.