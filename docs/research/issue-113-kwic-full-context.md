# Issue #113 research — typed KWIC full-context follow-up

**Research date:** 2026-09-10  
**Current implementation baseline:** `main` at `8281d436498f40bfa01aba4000d65100b3a37d04`  
**Issue:** #113

## Question

How should CAL-MCP make the `full_context_url` already returned by `KwicHit` followable without accepting arbitrary URLs, weakening ordinary text-page parsing, or automatically fetching context for every hit?

## Existing typed input

Current `KwicHit` already preserves every selector needed by CAL's full-context route:

- `file_id`;
- optional `subtext_id`;
- `target_coordinate`;
- `charset` (`R`, `H`, or `S`);
- the validated same-origin `full_context_url`.

`_parse_kwic_hits()` already validates that the upstream link targets `get_a_kwicchapter.php`, has one `file`, one `target`, one `cset`, optional decimal `sub`, and stays on the CAL origin. The missing capability is therefore a typed explicit follow-up, not a URL-fetching primitive.

## Bounded current-CAL probes

Research used two branch-only workflows and five fixed requests total. Every request had a 15-second timeout, 512 KiB response cap, redirects disabled, and no traversal of returned links. The temporary workflows are not part of the planned implementation diff.

### Probe 1 — result/missing/charset contract

Run `34415985962`, job `102680858819` made exactly three GETs.

Representative current hit selector:

```text
file=13250&sub=&cset=R&target=1325003
```

CAL returned HTTP 200, `text/html; charset=UTF-8`, 9,199 bytes. The semantic page identifies `13250: TDanStel (Tel Dan Stele)`, renders lines 01–13, and exposes ordinary `getlex.php?coord=...&word=...` token links plus `comment.php?coord=...` line links. Target `1325003` is rendered as display coordinate `03`.

The identical file/target with `cset=H` returned HTTP 200 and 14,687 bytes with Hebrew-script rendering. The visible line content therefore depends materially on `cset`; charset cannot be discarded or silently normalized.

An intentionally invalid target:

```text
file=13250&sub=&cset=R&target=999999999999
```

returned HTTP 200 and the explicit semantic marker:

```text
Target coordinate 999999999999 not found.
```

No text lines were rendered. This is a typed not-found state, not transport failure.

The full-context page also exposes presentation controls such as manuscript-variant toggling and script-switch links. Those controls are not required to follow a `KwicHit` and should stay private/unexposed.

### Probe 2 — row structure and script-specific empty anchors

Run `34464205324`, job `102828822994` made exactly two GETs for the same fixed Tel Dan target with `cset=H` and `cset=S`.

Current full-context text rows are table rows with two semantic cells:

1. a coordinate cell, normally containing `comment.php?coord=<machine coordinate>` and the rendered display coordinate;
2. a text cell containing ordered `getlex.php` token anchors and rendered text.

This is materially different from the ordinary `get_a_chapter.php` parser assumption: the shared semantic HTML parser flushes at `td`, so passing these rows through the ordinary text-line parser would separate the coordinate/comment cell from the token cell and lose their relationship.

For `cset=S`, the probe found 80 lexical anchors and zero empty lexical anchors. The target row contained eight rendered Syriac lexical anchors for coordinate `1325003`.

For `cset=H`, the probe found 141 lexical anchors, including exactly 13 empty lexical anchors — one terminal empty `getlex.php` anchor on each of Tel Dan's 13 rendered rows. The target row ends with:

```text
getlex.php?coord=1325003&word=13&hasvariant=0
```

with an empty rendered label. Raw HTML confirms this is literally a trailing empty `<a ...></a>` after the visible tokens, not hidden token text. The other target-row anchors contain the visible Hebrew tokens and `*` separators.

This empty-anchor behavior is specific to the current Hebrew full-context rendering. Ordinary text-page parsing should remain strict and unchanged.

## Result shape

The full-context page is target-centered context, not an ordinary paginated `get_a_chapter.php` page and not another KWIC hit list. The existing `TextLine` and `TextToken` data models nevertheless represent its scholarly line/token relationships faithfully:

- machine coordinate;
- rendered display coordinate;
- rendered line text;
- ordered token coordinates/word indices/text/lexical URLs;
- optional comment URL.

The models can therefore be reused while parsing the different table-row structure locally in the concordance adapter.

## Narrow public selector

Use the fields already returned by `KwicHit`; do not accept `full_context_url` as an input:

```text
cal_kwic_full_context(
    file_id: string,
    target_coordinate: string,
    charset: string,
    subtext_id: string | null = null,
)
```

`charset` deliberately uses CAL's already-returned values `R`, `H`, and `S`, so a caller can pass a hit's typed field directly without a second mapping step.

The adapter privately constructs exactly one GET to `get_a_kwicchapter.php` with `file`, `sub`, `cset`, and `target`. No arbitrary path/origin/query parameter is public.

## Parser contract

A successful response must remain on canonical CAL `https://cal.huc.edu/get_a_kwicchapter.php` and its returned selectors must agree with the request. Repeated/missing selector values, foreign origin, wrong path, unknown charset, or selector mismatch are parser drift.

The page must identify the requested file through its file-information link/label. Found context must contain ordered recognized text rows, and the requested target coordinate must occur exactly once among them. Missing target, duplicate target coordinate, mismatched line/token coordinates, detached comments, or contradictory explicit not-found marker are parser drift.

The explicit `Target coordinate <requested target> not found.` marker maps to `not_found` only when no context rows are present. A marker for another target, or a marker mixed with valid rows, is contradictory drift.

### Hebrew trailing empty lexical anchor

For current `cset=H` full-context rows only, the parser may discard one terminal empty lexical anchor after validating that:

- it is a `getlex.php` link for the same row coordinate;
- it is the final lexical link in that row;
- its word index follows the last preceding lexical word index;
- its rendered label is empty.

Do not globally teach the ordinary text-page parser to ignore empty lexical anchors. For `R` and `S`, an empty lexical anchor remains drift. Multiple/nonterminal/mismatched empty anchors remain drift for `H` as well.

## Missing, empty, and drift semantics

Public result status should be `found` or `not_found`. A found result returns the typed request selectors and ordered `TextLine` values. A recognized not-found result returns the same selectors with an empty line collection. Unknown successful HTML is parser drift; it is not converted to `not_found` or an empty result.

## Provenance

Reuse the existing concordance provenance contract rather than creating a competing provenance shape:

- `source = "CAL"`;
- actual `source_url`;
- timezone-aware `retrieved_at`;
- `operation = "kwic_full_context"`;
- `text_id = file_id`.

The precise target/charset/subtext selectors are already first-class fields of the result and do not need new nullable provenance fields added to every existing concordance result.

## Request/load boundary

One explicit call submits at most one new logical CAL request; a completed cache hit can perform zero new I/O under the shared client. Parent `cal_kwic_texts` / `cal_kwic_dialect` calls must remain non-prefetching. No pagination, variant traversal, script-switch traversal, lexical-entry expansion, line comments, or other child links are fetched automatically.

The shared response-byte ceiling remains the production size bound. Tel Dan's 13-line result is representative evidence, not a claim that all full-context pages are that small or that CAL guarantees a fixed line window.

## Release-surface consequence

The current v0.1 manifest `V01_PUBLIC_TOOLS` contains 30 tools and runtime equality is tested. Adding this explicit follow-up makes the pre-release public surface 31 tools. The implementation must update the shared release manifest plus the changelog/docs contracts that currently freeze `30 public tools` / `30-tool schema`; it must not bypass the manifest test or leave the new operation undocumented.

## Decision

Implement one explicit `cal_kwic_full_context` operation in the concordance family. Reuse existing line/token result models, but implement a full-context-specific table-row parser and keep ordinary text-page parsing unchanged. Preserve CAL's charset distinction, explicit target-not-found state, strict selector consistency, one-request bound, and caller-controlled traversal.