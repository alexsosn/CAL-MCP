# Issue #108 research — CAL line comments and citation translations

**Research date:** 2026-09-10  
**Implementation baseline:** `main` at `b745efad184302925c69e7fbbc796c00c7e2d6c2`  
**Issue:** #108

## Question

How should CAL-MCP make the `comment.php?coord=...` navigation already returned by `TextLine.comment_url` followable without exposing arbitrary URLs or pretending CAL distinguishes a missing line from a line with no citation/comment records?

## Existing parent contract

`cal_text_page` returns `TextLine.coordinate` and, when CAL renders a red coordinate link, an absolute `comment_url`. The page parser deliberately does not follow that link. A public follow-up should therefore be explicit and coordinate-based, leaving parent page retrieval one request and non-recursive.

The existing file/subtext validators are not automatically suitable for this route. They enforce decimal identifiers, while current CAL line coordinates are not uniformly decimal.

## Current CAL evidence

### Bounded raw probe

Branch-only workflow run `34484072607`, job `102893806459` made exactly three fixed GET requests on 2026-09-10. Each request had a 15-second timeout, a 512 KiB response cap, redirects disabled, and no returned links were followed.

1. `https://cal.huc.edu/comment.php?coord=8100110821`
   - HTTP 200, `text/html; charset=UTF-8`, 2,608 bytes.
   - title: `CAL: citations and comments for 8100110821`.
   - two ordered records are rendered inside `div.summary-card` as separate `<p>` blocks.
   - both records identify `PJ Gen8:21` and contain a source-language `<span class="heb">`.
   - the first has an empty `<span class="rom">`; the second has `I shall not again curse the earth any more`.
   - each record ends with `See the entire entry for` followed by a `oneentry.php?lemma=...&cits=all` link, rendered headword, POS text, and bold gloss.

2. `https://cal.huc.edu/comment.php?coord=5400111937`
   - HTTP 200, 2,323 bytes.
   - title identifies the same requested coordinate.
   - one record: `TN Gen19:37`, source text `עד זמן יומא הדין`, translation `until this very day`, and a linked lexical entry for `ˁd@zmn` (`prep.`, gloss `until`).

3. `https://cal.huc.edu/comment.php?coord=999999999999`
   - HTTP 200, 2,131 bytes.
   - title still identifies the requested coordinate.
   - the summary card contains exactly the semantic empty marker `NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED` and no record blocks.

The third response is important: CAL does not expose a separate route-level signal proving whether the coordinate itself exists. The public adapter must therefore call this state `no_citations` (or equivalent), not `not_found`.

### Current indexed pages broaden the coordinate and record shapes

Current CAL search-index snapshots rechecked on 2026-09-10 show live `comment.php` pages including:

- `comment.php?coord=444015370A04` for `4Q537 A:4`, with three records;
- decimal examples such as `8101120405`, `5400000413826`, and `620350010710`;
- records whose source-language citation text or English translation is empty while the lexical-entry relationship remains present.

Thus the route selector is an opaque CAL line coordinate, not a decimal database ID. The current observed selector alphabet is ASCII alphanumeric. The adapter should preserve it verbatim, accept only a small bounded ASCII-alphanumeric token, and keep the endpoint fixed to `comment.php`; it must not generalize this into arbitrary URL/query execution.

## Semantic record shape

The current page is best represented as an ordered collection of CAL citation/comment records. A record can faithfully expose:

- rendered reference (for example `PJ Gen8:21`);
- source-language citation text, nullable when CAL renders none;
- Roman/English translation/comment text, nullable when CAL renders an empty `rom` span;
- CAL lemma key selected by the `oneentry.php?lemma=...` link;
- rendered headword;
- rendered part-of-speech text;
- rendered gloss;
- validated absolute CAL lexical-entry URL.

This should not be collapsed to one free-form `comment` string: a line can have multiple ordered records for different lexical entries and different citation translations.

The existing `LemmaRef` is not a perfect replacement for this relationship because the comment page provides one rendered headword plus record-local citation text/translation and does not necessarily expose the full browse-entry shape. A small text-local record model avoids fabricating aliases/pronunciation fields.

## Proposed public selector and status

Use an explicit typed operation over the selector already represented by the parent text row:

```text
cal_text_line_comments(coordinate: string)
```

The coordinate is validated locally as a non-empty bounded ASCII-alphanumeric CAL coordinate. This deliberately differs from decimal `file_id` / `subtext_id` validation.

Public status should be:

- `found` — one or more recognizable ordered records;
- `no_citations` — CAL returned the exact explicit empty marker and no records.

Do not expose `not_found`, because current CAL returns the same empty marker for an intentionally invalid coordinate and does not establish line existence on this endpoint.

## Request and response identity

One cache-miss call submits exactly:

```text
GET comment.php?coord=<coordinate>
```

Before accepting semantic content, require the actual response URL to remain canonical CAL HTTPS, path `/comment.php`, with exactly one `coord` selector equal to the request, no fragment, and no extra query controls.

Require the page title to identify the same coordinate exactly. A missing/mismatched title is drift.

## Parser boundary

Parse only the summary-card content. Navigation/footer links (`javascript:history.back()`, search page, text browser) are presentation controls and must never become records or be followed.

For a found page:

- preserve `<p>` record order;
- require exactly one validated same-origin `/oneentry.php` link per record;
- require its query to contain exactly one non-empty `lemma` and `cits=all`, with no unexpected selectors;
- preserve the rendered reference/headword/POS/gloss and source/translation fields;
- allow an empty source or translation field where CAL renders one empty, but do not accept a structurally empty record;
- reject duplicate/conflicting lexical links, foreign origins, malformed query shapes, detached record fields, or an empty marker mixed with records.

For `no_citations`, require exactly the current empty marker and zero recognizable record blocks. Unknown successful HTML remains `TextParseError`, not an empty result.

## Provenance and load

Reuse `TextProvenance` with:

- `source = "CAL"`;
- actual `source_url` and timezone-aware `retrieved_at`;
- `operation = "line_comments"`;
- `upstream_id = coordinate`.

One explicit call performs at most one new logical CAL request. Shared cache/single-flight behavior may reduce duplicate upstream I/O. `cal_text_page` must remain non-prefetching and no lexical-entry link returned by the comment page is followed automatically.

## Release consequence

After #113, the pre-release manifest has 31 public tools. Adding this missing typed follow-up changes it to 32. Release/runtime/docs contracts that freeze the tool count must be updated only after the implementation GREEN gate; live-smoke request budget should not increase merely because this explicit follow-up exists.

## Decision

Implement `cal_text_line_comments(coordinate)` in the text family with a dedicated current-shape parser and typed `found` / `no_citations` result. Keep CAL line coordinates opaque but narrowly validated, preserve ordered record semantics, validate lexical-entry navigation without following it, and leave ordinary text-page parsing unchanged.