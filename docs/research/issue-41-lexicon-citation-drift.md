# Issue #41 research — current CAL lexicon citation-count drift

**Rechecked:** 2026-09-06

## Trigger

The bounded v0.1 release probe (`33995822616`) exercised `cal_lexicon_lookup(query="br", lemma_key="br N")` with retries disabled, cache disabled, and concurrency 1. CAL returned HTTP 200 for both the browser request and the selected full entry, but `parse_lexicon_entry()` failed with:

```text
LexiconParseError: CAL lexicon citation count does not match the rendered citation marker
```

This is a release blocker because `br N` is a common, ordinary successful lookup path and the release smoke must reject MCP tool-error results.

## Current parser contract

`_SenseBuilder.freeze()` requires the number of parsed `Citation` records to equal CAL's rendered `▶ N citations` marker. This is an important fail-closed integrity check and should remain.

`_parse_citations()` currently treats semicolons as citation-record separators in two places:

1. unlinked text before the first citation link; and
2. the rendered text belonging to each linked citation.

The second rule is the drift source.

Existing reduced fixture `entry_br_nested.html` proves that semicolon splitting is still needed for unlinked citation records before the first link: it contains two raw records followed by two linked records under a `▶ 4 citations` marker.

## Bounded live evidence

Two temporary branch-only probes were run against exactly one entry, `cal_entry_web.php?lemma=br+N`. Each made one CAL request, with no retries, cache, enumeration, or neighboring-entry traversal. Both workflows deleted themselves immediately after the run.

### Probe 1 — marker/count shape

Run `33995948350` inspected only semantic citation marker blocks and parser counts. Every observed `br N` citation block matched its marker except one:

```text
marker: ▶ 3 citations
linked references: 3
current parser output: 6 Citation records
```

Representative other blocks were exact: 2→2, 7→7, 1→1, 4→4, 5→5, 10→10.

### Probe 2 — link boundaries in the failing block

Run `33996085475` inspected only the failing three-link block.

The block has:

- empty unlinked prefix;
- exactly three citation links: `AGnEx 4.9`, `JSBhom 71day1 293`, and `BT Yev 76a(40)`;
- one rendered text chunk after each link;
- the first two chunks end with ` ; ` immediately before the next citation link;
- the third citation contains a semicolon *inside its own transliteration/translation material*.

Thus CAL's semantic record boundaries in this linked block are the citation links themselves. The semicolon before the next link is presentation punctuation, and a semicolon inside the final linked citation is citation content. Re-splitting linked chunks on semicolons creates false extra citations.

## Interpretation

For a line containing citation links:

- unlinked prefix material before the first link can still contain one or more raw citation records and remains semicolon-splittable;
- each citation link starts exactly one linked citation record;
- the linked record's text extends until the next citation link (or end of line);
- a separator semicolon immediately before the next link should be trimmed from the preceding linked record's text, not converted into another citation;
- semicolons inside a linked record's own text must be preserved.

This matches both the current live `br N` shape and the existing mixed raw+linked reduced fixture.

## Minimal implementation consequence

Change only linked-region parsing in `_parse_citations()`:

1. keep semicolon splitting for an unlinked prefix and for wholly unlinked citation lines;
2. for each link, create exactly one `Citation` from the entire rendered region until the next link/end of line;
3. remove only the inter-record separator punctuation/whitespace at the linked-region edge;
4. preserve internal semicolons verbatim;
5. retain `_SenseBuilder.freeze()`'s rendered-count equality check unchanged.

No public model, MCP schema, request flow, cache behavior, or request volume changes.

## Regression fixture requirements

Add a deliberately reduced full-entry fragment containing:

- recognizable `br N` header and one complete sense;
- `▶ 3 citations`;
- exactly three links;
- a semicolon between linked citations;
- a semicolon inside the final linked citation's text.

The fixture must contain only enough text to reproduce the semantic boundary issue, not the current full CAL entry.

Tests should prove:

- the reduced current shape yields exactly three citations;
- linked references/URLs remain attached to the correct text;
- internal semicolons remain inside citation text;
- the existing mixed raw-prefix + linked fixture still yields four citations;
- a genuinely contradictory rendered count still raises `LexiconParseError`.

## Sources / evidence

- Current CAL entry: https://cal.huc.edu/cal_entry_web.php?lemma=br+N
- Release probe run `33995822616`
- Citation-marker shape run `33995948350`
- Link-boundary shape run `33996085475`
- Existing parser and reduced fixtures in `src/cal_mcp/lexicon.py` and `tests/fixtures/cal/`

## CAL load impact

Research used two additional fixed requests for the single `br N` entry after the release probe. No crawl, pagination loop, neighboring-entry enumeration, or lexical follow-up occurred. Normal implementation tests remain offline.