# Issue #80 research — current Ginza text-search result links

Date: 2026-09-08
Baseline: `main` at `88892f4054d470f2d7fa7e72b647ada13befbd11`

## Reported failure

`cal_text_search(query="Ginza")` can surface only a generic tool execution error even though CAL currently exposes Ginza Rabba entries.

The existing public search operation is deliberately bounded to one POST to `newsearchtxts.php`. Its parser recognizes CAL's explicit no-files marker and ordinary text-result links whose path ends in `get_a_chapter.php`.

## Current CAL evidence

Two fixed, branch-only research probes were made on 2026-09-08. Each probe performed exactly one POST to:

```text
https://cal.huc.edu/newsearchtxts.php
search=Ginza
```

Both returned HTTP 200, `text/html; charset=UTF-8`, a 3,845-byte body, the normal `CAL search for texts like:` result marker, and no explicit no-files marker.

The first probe established that the result page contains exactly two relevant specialized links:

```text
/showsubtexts.php?subtext=74410&cset=M
/showsubtexts.php?subtext=74411&cset=M
```

Their rendered anchor texts are `74410` and `74411`.

The second probe reproduced the repository's semantic block/line boundaries and established the corresponding result rows:

```text
74410 : Ginza Rabba (Great Treasury) Right Side: MsPage 3 Line 2 ...
74411 : Ginza Rabba (Great Treasury) Left Side: Ginza Smala ...
```

Therefore the existing `_search_label_and_description()` logic already has the right row semantics: the text immediately after the file-number link begins with `:`, the next colon separates the label from CAL's longer descriptive note, and the resulting public labels are:

- `Ginza Rabba (Great Treasury) Right Side`
- `Ginza Rabba (Great Treasury) Left Side`

## Root cause

`parse_text_search_page()` currently iterates result links but immediately discards every link whose path is not `get_a_chapter.php`.

Current Ginza results are Mandaic collection links to `showsubtexts.php`, so both valid result rows are ignored. The page still contains the normal search-result marker and does not contain the explicit no-files marker. With zero recognized matches, the parser then correctly fails closed with:

```text
CAL text search page has neither results nor the explicit no-files marker
```

The generic MCP execution error reported in issue #80 is therefore downstream of a precise parser-shape mismatch, not evidence that CAL returned no Ginza results.

## Specialized-link semantics

For the current Mandaic search-result shape:

- link path: `showsubtexts.php`;
- `subtext=74410` / `74411` identifies the CAL **file** selected by the result despite the upstream query-key name;
- `cset=M` identifies CAL's specialized Mandaic route family;
- the public `TextRef.subtext_id` must remain `None` because the upstream `subtext` query key here is not a public text sub-selection;
- label and optional description come from the same rendered result-row convention already used by ordinary search results.

This matches the collection-74 route research already implemented for Ginza page retrieval in issue #85. No route-discovery request is needed.

## Smallest compatible repair

Keep `cal_text_search` as one POST and preserve the current public result schema.

Extend only search-result link interpretation so that a result row may be represented by either:

1. the existing ordinary `get_a_chapter.php?file=<id>[&sub=<id>]` link; or
2. the current Mandaic `showsubtexts.php?subtext=<decimal file id>&cset=M` link.

For the Mandaic shape:

- require exactly one non-empty `subtext` query value and validate it as a decimal CAL identifier;
- require exactly one non-empty `cset` value equal to `M`;
- map `subtext` to `TextRef.file_id`;
- set public `TextRef.subtext_id=None`;
- reuse `_search_label_and_description()` for rendered label/description;
- do not fetch `showsubtexts.php` automatically.

Ordinary `get_a_chapter.php` result parsing, explicit empty-result handling, request normalization, result order, provenance, and the one-request bound remain unchanged.

## Safety boundary

The parser must not treat arbitrary `showsubtexts.php` links as ordinary text references outside the text-search result path. A malformed current-Mandaic result link should fail closed rather than silently disappear into an empty result.

This ticket does not implement Mandaic catalogue discovery (#78/#83), typed public error envelopes (#84), or any recursive expansion of the returned Ginza entries.

## Test target

Use a deliberately reduced offline fixture with:

- the normal text-search marker;
- the two current Ginza result rows in CAL order;
- `showsubtexts.php?subtext=74410&cset=M` and `...74411...` links;
- enough description text to prove the existing row splitter is reused faithfully.

Before production changes, pin:

- `TextService.search("Ginza")` returns both `TextRef` values in CAL order after exactly one existing POST;
- `file_id` is `74410` / `74411` and public `subtext_id` is `None`;
- labels/descriptions are parsed from the row rather than invented from route metadata;
- malformed/repeated/non-decimal `subtext` and malformed/repeated/foreign `cset` on a Mandaic result fail closed;
- the existing ordinary Tel Dan search regression remains unchanged.

A valid RED requires dependency setup, Ruff lint, Ruff format, and strict mypy to pass in both CI matrices, with pytest failures confined to the new Ginza expectations.

## Probe load and cleanup

Research generated exactly two CAL requests total: two fixed `Ginza` POSTs to the same text-search endpoint. No returned link was followed, no catalogue/page was fetched, and no result enumeration beyond the two rows in the returned page occurred.

The temporary branch-only research workflow is removed before the TDD phase. Normal CI remains offline.

## Evidence

- research workflow runs `34241354468` and `34241600037`;
- issue #80 reproduction;
- current `src/cal_mcp/texts.py` parser behavior on the baseline above;
- issue #85 Mandaic route research for collection-74 semantics.
