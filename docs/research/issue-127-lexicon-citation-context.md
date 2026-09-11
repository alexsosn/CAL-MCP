# Issue #127 research — typed lexicon citation full context

**Research date:** 2026-09-11  
**Baseline:** `main` at `5263f8562d1aa1e5fc6be3e55ddc59b2a7c81634`  
**Issue:** #127

## Question

How should CAL-MCP make linked lexicon citations such as `showachapter.php?fullcoord=31000424` followable without accepting arbitrary URLs, inventing a decomposition of CAL's opaque coordinate, weakening ordinary text/KWIC parsers, or automatically expanding every lexicon citation?

## Existing parent contract

`Citation` currently contains only:

```text
reference: string | null
url: string | null
text: string
```

Linked citations therefore preserve CAL navigation but expose no typed selector for a follow-up operation. A caller would have to parse `fullcoord` from `url`, which is not an MCP-native composition contract.

The current citation parser also preserves non-followable/raw citation links as data. Reduced fixtures intentionally include a nondecimal synthetic `fullcoord=ishdan-example`, while current real followable links use decimal `fullcoord` values. Consequently, the implementation must not redefine every citation URL as executable navigation or reject all previously tolerated noncanonical fixture/raw links.

## Recovered bounded current-CAL research

No new CAL requests were needed for this research pass. Two already-completed issue-127 probe runs were recovered from the project branches.

### Probe A — route/result/missing semantics

Run `34625759146`, job `103350325544` used exactly three fixed GETs with redirects disabled, 15-second timeout, and a 512 KiB response cap.

#### Biblical Aramaic example

```text
GET https://cal.huc.edu/showachapter.php?fullcoord=31000424
```

Current result:

- HTTP 200, HTML, about 29 KiB;
- source heading/file-info link `/get_file_info.php?coord=310004` rendered as `31000: BA Ezra chapter 4`;
- chapter-like context containing rendered lines 4:08 through 4:24;
- each text row uses a coordinate/comment cell and a token/text cell;
- lexical anchors are `getlex.php?coord=<line-coordinate>&word=<index>`;
- the requested full coordinate `31000424` occurs as the target line coordinate;
- chapter-navigation links are present but are not required to consume the citation context.

#### Targum example

```text
GET https://cal.huc.edu/showachapter.php?fullcoord=5101431061
```

Current result:

- HTTP 200, HTML, about 33 KiB;
- file-info link `/get_file_info.php?coord=5101431` rendered as `51014: TgJ Ez`;
- chapter-like context around Ezekiel 31, including the requested target coordinate;
- lexical anchors again use `getlex.php?coord=<line-coordinate>&word=<index>`;
- ordinary chapter-navigation links use a different route (`get_a_chapter.php`) and remain navigation metadata only.

The two examples prove that `fullcoord` cannot safely be decomposed locally into a universal public `file_id`/chapter/verse tuple: CAL's file-info coordinates have different lengths and semantics across these route families. Preserve the requested `fullcoord` as one opaque decimal CAL selector.

#### Missing example

```text
GET https://cal.huc.edu/showachapter.php?fullcoord=999999999999
```

Current result:

- HTTP 200;
- no text rows;
- explicit marker `NO CITATIONS FOR 99999 9999999 ARE CURRENTLY STORED`;
- a minimal file-info link is still rendered.

This is a typed not-found/empty state, not a transport failure. The two decimal groups in the marker concatenate back to the requested `fullcoord`; that relationship is useful for fail-closed validation without assigning scholarly meaning to either group.

### Probe B — lexical-anchor edge shape

Run `34625996174`, job `103351120645` rechecked the two real examples above.

- `31000424`: 277 `getlex.php` anchors, **0 empty lexical labels**;
- `5101431061`: 330 `getlex.php` anchors, **0 empty lexical labels**;
- representative text rows have two semantic cells and all retained lexical anchors have visible labels.

Therefore the special Hebrew terminal-empty-anchor tolerance researched for `cal_kwic_full_context` must **not** be generalized to this route. Empty lexical anchors here remain drift.

## Comparison with the existing KWIC full-context operation

Issue #113 / PR #129 added `cal_kwic_full_context(file_id, target_coordinate, charset, subtext_id=None)` over `get_a_kwicchapter.php`.

The citation route is distinct:

- endpoint: `showachapter.php`, not `get_a_kwicchapter.php`;
- selector: one opaque `fullcoord`, not file/target/charset/sub selectors;
- no caller-selected charset in the researched route;
- missing marker is different;
- no current Hebrew empty-anchor artifact was observed;
- source/file identity cannot be derived by reusing KWIC selector fields.

The existing `TextLine` and `TextToken` result models still fit the scholarly row/token data, but the parser and public operation must remain route-specific.

## Chosen parent-selector contract

Add an optional field to `Citation`:

```text
full_coordinate: string | null
```

Populate it only when the citation URL is a canonical followable CAL citation-context link:

- same CAL origin after resolution against the entry source URL;
- path exactly `/showachapter.php`;
- exactly one query key, `fullcoord`;
- exactly one nonempty ASCII-decimal value;
- no fragment.

For current raw/unlinked/noncanonical citations, preserve existing `reference`, `url`, and `text` behavior and set `full_coordinate = null`. This is additive and avoids making existing citation parsing more brittle while making genuine current CAL context links directly composable.

A canonical-looking `showachapter.php` link whose `fullcoord` field is repeated/empty/nondecimal or whose query adds request-control fields should not be advertised as followable. The implementation may preserve the raw URL with `full_coordinate=null`; parser drift should be reserved for contradictions in the new explicit follow-up response, not legacy citation display data.

## Chosen public follow-up

Add one explicit operation in the lexicon family:

```text
cal_lexicon_citation_context(full_coordinate: string)
```

Input is an ASCII-decimal CAL coordinate already returned as `Citation.full_coordinate`. Do not accept a URL, path, query mapping, file/chapter/verse decomposition, script selector, or traversal flag.

One cache-miss call constructs exactly:

```text
GET showachapter.php?fullcoord=<full_coordinate>
```

No chapter-navigation, token, comment, file-info, previous/next, or other links are followed automatically.

## Result shape

Use a typed result analogous to other explicit context operations:

```text
status: "found" | "not_found"
full_coordinate: string
source_label: string | null
source_info_url: string | null
lines: [TextLine]
provenance: {
  source: "CAL"
  source_url: <actual response URL>
  retrieved_at: <timestamp>
  operation: "lexicon_citation_context"
  ...
}
```

`source_label` / `source_info_url` preserve CAL's rendered file-information identity without inventing a universal file-id decomposition. For `not_found`, `lines` is empty; source metadata may be preserved if CAL renders it.

Reuse `TextLine` / `TextToken`; do not modify their public meaning.

## Parser boundary

### Response identity

Require the successful response URL to be canonical CAL:

- `https://cal.huc.edu/showachapter.php`;
- exactly one `fullcoord` query value;
- no unexpected query fields or fragment;
- returned `fullcoord` exactly equals the requested selector.

Foreign origin, wrong path, repeated/missing selector, extra request-control field, or selector mismatch is parser drift.

### Source information

Accept at most one semantic `get_file_info.php?coord=<decimal>` link. If present:

- it must remain on canonical CAL origin/path;
- query must contain exactly one decimal `coord`;
- rendered label must be nonempty;
- preserve the absolute URL and rendered label as source metadata.

Do not infer `file_id`, chapter, verse, corpus, or subtext from the relationship between this coordinate and `full_coordinate`.

### Found rows

Current text rows are table rows with two semantic cells, analogous structurally to the KWIC full-context rows but with route-specific surrounding content.

For each recognized row:

- first cell may contain one `comment.php?coord=<row coordinate>` link and rendered display coordinate;
- second cell contains ordered `getlex.php?coord=<row coordinate>&word=<index>` lexical anchors;
- lexical/comment URLs must remain on canonical CAL routes;
- token coordinates in a row must agree;
- lexical word indexes must be ASCII decimal;
- lexical labels must be nonempty;
- preserve rendered row text and CAL order;
- do not follow any link.

For `found`, require the requested `full_coordinate` to occur in exactly one returned `TextLine`. Zero or multiple target rows are drift.

### Not found

Recognize the current marker only when it has the exact semantic form:

```text
NO CITATIONS FOR <decimal group A> <decimal group B> ARE CURRENTLY STORED
```

Accept `not_found` only when:

- exactly one such marker is present;
- `group A + group B == requested full_coordinate`;
- no recognized text rows are present.

Marker mismatch, duplicate/conflicting marker, marker mixed with rows, or successful-looking HTML with neither rows nor a matching marker is parser drift.

## Request/load boundary

- Parent `cal_lexicon_lookup` remains unchanged in request count and never prefetches citation context.
- One explicit `cal_lexicon_citation_context` call submits at most one new logical CAL request; shared cache/single-flight may reduce duplicate I/O.
- No recursive chapter navigation or lexical/comment expansion.
- Normal CI remains offline.

## Public/release consequence

Current `V01_PUBLIC_TOOLS` contains 32 tools on this baseline. Adding this operation changes the pre-release surface to 33 tools. Release manifest/runtime registry/docs with explicit counts must remain synchronized.

This work should not be merged against a stale public-error boundary if PR #134 lands first; synchronize with `main`, rerun CI, and review the exact rebased/synchronized candidate.

## Decision

Implement additive typed `Citation.full_coordinate` metadata plus one URL-free `cal_lexicon_citation_context(full_coordinate)` operation. Keep `fullcoord` opaque, reuse line/token output models, implement a citation-route-specific table parser, preserve current raw citation behavior, model CAL's explicit no-citations page as `not_found`, and keep all traversal caller-controlled.

## CAL load impact

No new research requests in this pass: the decision reuses two bounded successful probe runs already made for #127. Production remains one request per explicit context call and zero hidden citation expansion from lexicon lookup.
