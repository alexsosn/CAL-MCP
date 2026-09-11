# Issue #127 plan — typed lexicon citation context follow-up

**Plan date:** 2026-09-11  
**Research:** `docs/research/issue-127-lexicon-citation-context.md`  
**Baseline:** `main` at `5263f8562d1aa1e5fc6be3e55ddc59b2a7c81634`

Sequence: research → plan → deterministic RED → minimal implementation → docs/release surface → dual-matrix GREEN → exact-head logically independent adversarial review → guarded merge.

## Frozen public contract

### Parent citation enrichment

Extend the existing lexicon `Citation` output additively:

```text
reference: string | null
url: string | null
text: string
full_coordinate: string | null
```

`full_coordinate` is populated only for canonical current CAL `showachapter.php?fullcoord=<ASCII-decimal>` links. Existing raw citation URL/text/reference fields remain unchanged.

### New explicit tool

```text
cal_lexicon_citation_context(full_coordinate: string)
```

The tool accepts only an ASCII-decimal CAL coordinate. It does not accept URLs or decomposed file/chapter/verse selectors.

One cache-miss operation constructs exactly:

```text
GET showachapter.php?fullcoord=<full_coordinate>
```

No child link is followed.

### Result

```text
status: "found" | "not_found"
full_coordinate: string
source_label: string | null
source_info_url: string | null
lines: [TextLine]
provenance: {
  source: "CAL"
  source_url: string
  retrieved_at: datetime
  operation: "lexicon_citation_context"
  full_coordinate: string
}
```

Reuse existing `TextLine` / `TextToken` result models and serializers. Do not expose inferred `file_id`, chapter, verse, corpus, or subtext fields.

## Production structure

### `src/cal_mcp/lexicon.py`

- add `full_coordinate: str | None = None` to `Citation` so current constructors remain source-compatible;
- add a private helper that derives a follow-up selector only from a canonical resolved citation URL;
- keep `Citation.url` exactly as today;
- include `full_coordinate` in citation serialization;
- raw citations and noncanonical links return `full_coordinate=None` rather than becoming parser errors.

Canonical selector extraction requires:

- resolved scheme `https`;
- host `cal.huc.edu`;
- path exactly `/showachapter.php`;
- no fragment;
- exactly one query key `fullcoord`;
- exactly one nonempty ASCII-decimal value.

Do not accept suffix-path matches, other origins, repeated values, blank values, nondecimal values, or extra query controls as executable selectors.

### `src/cal_mcp/lexicon_citation_context.py` (new)

Keep the route-specific parser/service separate from the large lexicon parser and from KWIC internals.

Add:

- `LexiconCitationContextParseError(CalContentError)`;
- `LexiconCitationContextStatus(StrEnum)` with `FOUND` / `NOT_FOUND`;
- private semantic table/cell parser for the researched `showachapter.php` shape;
- `LexiconCitationContextPage` internal parse result;
- `LexiconCitationContextProvenance`;
- `LexiconCitationContextResult` with `to_dict()`;
- `parse_lexicon_citation_context_page(response, requested_full_coordinate=...)`;
- `LexiconCitationContextService.context(full_coordinate)`.

Import and reuse `TextLine` / `TextToken` from `cal_mcp.texts` for public line/token objects. Avoid importing private KWIC parser helpers.

## Parser contract

### Input validation

`full_coordinate` must be a `str`, contain only ASCII digits `0-9`, be nonempty, and represent a positive integer. Preserve it as a string; do not cast in the public result.

### Response identity

Before parsing semantics, require:

```text
scheme == https
host == cal.huc.edu
path == /showachapter.php
query keys == {fullcoord}
query fullcoord == requested_full_coordinate
fragment == empty
```

Any contradiction raises `LexiconCitationContextParseError`.

### Source info

Across the page, recognize at most one `get_file_info.php?coord=<ASCII-decimal>` link.

Require canonical CAL origin/path and exactly one positive-decimal `coord`; nonempty rendered label. Preserve:

- `source_label = rendered label`
- `source_info_url = absolute canonical URL`

Do not require a fixed-length relation between source `coord` and requested `fullcoord`.

### Text rows

Parse only semantic table rows that expose lexical-token anchors. Current found pages have two cells per text row.

For each text row:

- token anchors must target canonical CAL `/getlex.php`;
- query keys exactly `coord` and `word`;
- `coord` and `word` ASCII decimal;
- `word` index nonnegative;
- labels nonempty;
- all token coordinates in one row identical;
- word indices in rendered token order strictly increase without duplicates (do not require starting at zero if CAL changes omissions/punctuation handling unless tests show that is stable);
- optional coordinate/comment anchor targets canonical `/comment.php?coord=<same row coord>` with no extra fields;
- at most one semantic comment/coordinate link per row;
- rendered display coordinate must be nonempty when a comment link exists;
- rendered row text after the display coordinate must be nonempty.

Ignore ordinary page-navigation links outside recognized text-row semantics; never follow them.

For `FOUND`:

- require one or more parsed lines;
- requested `full_coordinate` appears as a line `coordinate` exactly once;
- no valid no-citations marker is present.

### Not found

Extract semantic visible text and recognize only:

```regex
^NO CITATIONS FOR ([0-9]+) ([0-9]+) ARE CURRENTLY STORED$
```

(case-insensitive surrounding CAL presentation may be normalized, but do not substring-match arbitrary prose).

Return `NOT_FOUND` only if:

- exactly one marker is present;
- concatenating its two captured decimal groups equals requested `full_coordinate`;
- no text rows were recognized.

Marker mismatch, duplicate/conflicting markers, marker+rows, or neither rows nor matching marker is drift.

### Current empty-anchor difference from KWIC

Do not copy `cal_kwic_full_context`'s route-specific tolerance for a terminal empty `getlex.php` anchor. Issue-127 probes found 607 lexical anchors across the two representative pages and zero empty labels. Empty lexical anchors on this route remain parser drift.

## Service/request contract

`LexiconCitationContextService.context()`:

1. validates `full_coordinate` locally;
2. submits one `CalRequest(method="GET", path="showachapter.php", params=(("fullcoord", selector),))`;
3. parses with the requested selector bound into the parser closure;
4. uses a route-specific cache namespace, e.g. `lexicon-citation-context-v1`;
5. returns typed result/provenance.

No implicit call from `LexiconLookupService.lookup()`.

## Server and release surface

In `src/cal_mcp/server.py`:

- construct one `LexiconCitationContextService` from the shared client;
- register `cal_lexicon_citation_context` with a concise tool description that tells agents to use `Citation.full_coordinate` from `cal_lexicon_lookup`;
- return `result.to_dict()`;
- do not add URL/path inputs or hidden lookup composition.

In `src/cal_mcp/release_surface.py` add the tool. Baseline public tool count is 32; candidate count becomes 33.

Update any explicit server-instruction/release-contract count tests and tool inventory docs.

If PR #134 merges before final synchronization, adapt the new wrapper to the structured-error helper/current server conventions instead of preserving stale exception translation code.

## Gate 1 — deterministic RED

Commit tests after research and plan.

### Parent-selector tests

Using existing/reduced lexicon fixtures, prove:

1. a canonical `/showachapter.php?fullcoord=7101301076140` citation serializes `full_coordinate="7101301076140"` while preserving its current absolute URL/reference/text;
2. raw citation has `full_coordinate=None`;
3. nondecimal synthetic `fullcoord=ishdan-example` remains preserved as a citation but has no typed selector;
4. foreign origin, nested/suffix lookalike path, repeated/blank `fullcoord`, fragment, and extra query controls never become typed selectors;
5. no extra CAL request occurs during lexicon lookup.

### Context-parser tests

Add deliberately reduced semantic fixtures based on the recovered 2026-09-11 probes, not full upstream pages:

- Biblical Aramaic context around `31000424`, including source info, one preceding line, target line, comment links, and token anchors;
- Targum context around `5101431061`, including the target row and a navigation link that must remain unfollowed/ignored;
- not-found page for `999999999999` with the exact no-citations marker and file-info link.

RED expectations:

6. found parse preserves source label/info URL and ordered `TextLine`/`TextToken` data;
7. target coordinate occurs exactly once;
8. Targum variable-length source info does not trigger invented file-id assumptions;
9. not-found marker returns typed `NOT_FOUND` with empty lines;
10. mismatched marker concatenation fails;
11. marker mixed with rows fails;
12. successful-looking page with no marker/no rows fails;
13. target absent/duplicated fails;
14. response origin/path/query/selector/fragment drift fails;
15. foreign/malformed token/comment/info routes fail;
16. empty lexical anchor fails;
17. mixed row token coordinates / duplicate or decreasing word indexes fail;
18. one service call emits exactly one expected request.

### MCP/release tests

19. tool is registered once with input `full_coordinate: string` only;
20. tool output is JSON-serializable typed result;
21. release surface includes it and tool-count expectations are synchronized;
22. normal test suite remains offline.

Accepted RED: dependency installation, Ruff lint, Ruff format, and strict mypy all green; pytest failures limited to absent #127 production behavior/release registration.

## Gate 2 — minimal implementation

Expected production files:

- `src/cal_mcp/lexicon.py`
- `src/cal_mcp/lexicon_citation_context.py` (new)
- `src/cal_mcp/server.py`
- `src/cal_mcp/release_surface.py`

Avoid changes to generic HTTP behavior, text-page routing, KWIC routing, citation search, or unrelated parsers.

## Gate 3 — docs

Update at minimum:

- `docs/tools/lexicon.md`: `Citation.full_coordinate`, explicit follow-up example, null semantics, no hidden prefetch;
- `docs/index.md`: lexicon citation context reachability no longer a known gap;
- release/tool inventory docs with any explicit count/surface assertions;
- `tests/fixtures/cal/README.md`: provenance of new reduced context fixtures.

Do not imply that all displayed citation URLs are executable or that `fullcoord` has a locally decoded file/chapter/verse grammar.

## Gate 4 — GREEN

On the exact candidate head require both deterministic and latest-compatible CI matrices to pass:

- dependency/environment validation;
- Ruff lint;
- Ruff format;
- strict mypy;
- full pytest.

Freeze changed-file scope after GREEN.

## Gate 5 — logically independent adversarial review

Review the exact GREEN diff from issue/research/live evidence rather than implementation narrative. Challenge at least:

1. whether parent citation enrichment accidentally turns arbitrary URLs into executable selectors;
2. same-origin/path/query/fragment validation;
3. opaque selector preservation and absence of invented coordinate decomposition;
4. target-line uniqueness;
5. not-found marker binding to the requested selector;
6. source-info variable-length semantics;
7. token/comment route/query validation;
8. accidental reuse of KWIC-only empty-anchor tolerance;
9. one-request/no-prefetch bound;
10. compatibility of existing citation fixtures/serialization;
11. tool registration/release-surface count;
12. docs accurately describe nullable selector vs raw URL;
13. exact candidate includes no probe/helper workflow residue;
14. compatibility with the current structured-error boundary if #134 merged.

Any blocking finding gets a focused regression test first, minimal correction, fresh dual GREEN, and a fresh exact-head review.

## Merge / synchronization gate

Before merge:

- refetch `main`;
- if it advanced, synchronize/rebase the branch and resolve public server/release/error-boundary changes;
- require dual GREEN on the synchronized exact head;
- require clean exact-head independent review;
- mark ready and squash-merge guarded by expected head SHA.

After merge:

- confirm #127 closes;
- remove/reset obsolete `issue-127-live-probe`, `issue-127-probe-work`, and `issue-127-lexicon-citation-context-probe` branches if tooling permits;
- reevaluate release #15 vs the remaining independent reachability tickets.

## CAL load impact

Research adds zero CAL requests beyond already completed bounded probes. Production adds one CAL request only when the caller explicitly follows a typed citation coordinate; lexicon lookup remains unchanged in request volume.
