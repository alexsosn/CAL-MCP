# Issue #112 research — bounded CAL lexicon prefix browsing

**Research date:** 2026-09-12  
**Baseline:** `main` at `2f291988c5557ecd6eaedd90ab2be3403d931b05`  
**Issue:** #112

## Question

How should CAL-MCP expose CAL's current lexicon browsing workflow without changing exact `cal_lexicon_lookup` semantics, silently truncating paginated results, automatically walking pages, or exposing arbitrary CAL URLs/private navigation controls?

## Current CAL entry point

A bounded live recheck on 2026-09-12 confirms that `searching/fullbrowser.html` still documents two browse modes:

1. enter the first **two or three consonants** and select from all corresponding entries;
2. use a one-letter **JUMP TO** link.

CAL states that typed input may be CAL code, Unicode transliteration, Unicode Hebrew, or Unicode Syriac. It also documents underscore for bound one-letter forms (for example `w_`) and space for CAL `@` combinations.

The one-letter `b` jump currently resolves to:

```text
GET browseSKEYheaders.php?first3="b"
```

The existing adapter already uses this route privately while resolving exact lexical lookup:

```python
CalRequest(
    method="GET",
    path="browseSKEYheaders.php",
    params=(("first3", f'"{prefix}"'),),
)
```

A reduced repository fixture captured from CAL for two-letter `br` uses the same initial request family:

```text
browseSKEYheaders.php?first3="br"
```

So one-letter jump navigation and typed 2–3-character browsing can share one bounded adapter operation, provided their different user intent is documented.

## Pagination is part of the browse contract

The current one-letter `b` result still renders an explicit `NEXT PAGE` link. Its continuation changes request shape to:

```text
GET browseSKEYheaders.php?direction=1&sortkey=baoinjo+b
```

The reduced current-shape `br` fixture likewise contains a `NEXT PAGE` link with:

```text
browseSKEYheaders.php?direction=1&sortkey=br
```

Therefore even a documented two-character prefix cannot truthfully be described as returning *all* matching entries in one request. `parse_browse_page()` currently returns only the ordered lemma rows on one response and ignores navigation.

A correct public operation must expose one CAL page at a time plus explicit continuation. It must never auto-follow `NEXT PAGE`.

## Existing parser/model reuse

`parse_browse_page()` already preserves the useful one-page lexical semantics:

- rendered CAL order;
- lemma key;
- headwords;
- aliases rendered before `→`;
- pronunciation where present;
- part of speech;
- associated gloss;
- explicit no-match recognition;
- fail-closed behavior when neither entries nor a known no-match marker is present.

`LemmaRef` is already the correct result item model. The missing browse-specific semantics are safe pagination state and public provenance.

`cal_lexicon_lookup` should remain unchanged. Lookup deliberately exact-filters browse candidates and may fetch a selected entry. Prefix browsing is a different task and should return the CAL browse rows themselves without filtering or entry expansion.

## Input normalization and ambiguity

The browse operation should reuse the existing `normalize_query()` / `convert_to_cal_code()` subsystem and accept the same optional `InputRepresentation` used by `cal_convert_to_code`.

Exact lookup can fan out finite conversion ambiguity because it later exact-matches candidates. Prefix browsing cannot safely flatten multiple distinct converted prefixes: concatenating independently ordered CAL pages would invent an ordering CAL never supplied.

Chosen rule for browsing:

- normalize/convert locally before transport;
- derive the complete requested 1–3 browse-character prefix rather than truncating a longer lexical query;
- if conversion yields more than one distinct CAL-code prefix, fail locally with `ConversionExpansionError` and direct the caller to `cal_convert_to_code` / an explicit CAL-code choice;
- one accepted browse call submits exactly one CAL request.

No flat merge of ambiguity branches is allowed.

## Prefix length / jump mode

The public browse operation should cover both current CAL modes without adding a second tool:

- **1 browse character:** CAL's explicit JUMP TO semantics;
- **2–3 browse characters:** CAL's documented typed prefix semantics.

Empty input, more than three browse characters, whitespace-separated multiword input, and unsupported characters fail before transport. Bound forms such as `w_` remain valid when normalization/conversion accepts them.

This does not imply alphabet enumeration: one call handles one explicit initial/prefix only.

## Continuation boundary

CAL continuation links expose private fields such as:

```text
direction=1
sortkey=baoinjo+b
```

`sortkey` is adapter-owned continuation state, not a scholarly identifier. Raw URLs must not become public inputs.

The smallest faithful contract is:

```text
cal_lexicon_browse(prefix, representation=null, continuation=null)
```

where:

- initial call (`continuation=null`) sends only `first3="<normalized CAL prefix>"`;
- result returns `next_continuation` as the exact validated `sortkey` from a canonical same-origin `NEXT PAGE` link, or `null`;
- continuation call revalidates the supplied prefix and continuation locally, then sends only `direction=1&sortkey=<continuation>` to the fixed `browseSKEYheaders.php` endpoint;
- callers are documented to pass only a continuation returned by the same operation;
- the adapter never accepts a URL, path, direction value, or arbitrary query map.

Because continuation is still user-controlled text at the MCP boundary, it must be syntax-bounded before transport. It should be printable, nonempty, length-bounded, contain no control characters, URL delimiters, or query separators, and remain within a conservative adapter limit. The parser additionally checks the canonical CAL endpoint/origin/query shape before returning it.

The continuation value need not be cryptographically opaque: the safety boundary is the fixed endpoint, fixed `direction=1`, strict local validation, and bounded request count. Adding signatures/secrets would be unnecessary machinery for a read-only browse cursor.

## Browse parser navigation rules

Extend `BrowsePage` additively with `next_continuation: str | None = None` so existing lookup/tests remain source-compatible.

For a canonical `NEXT PAGE` link:

- resolved origin must be `https://cal.huc.edu`;
- path must be exactly `/browseSKEYheaders.php`;
- fragment must be empty;
- query keys must be exactly `direction` and `sortkey`;
- `direction` must be exactly `1`;
- one nonempty `sortkey` value is required;
- more than one distinct `NEXT PAGE` continuation fails closed.

A `NEXT PAGE` label on any other route/query shape fails closed. Unrelated links remain ignored.

No continuation is represented as `None`; end-of-results is never inferred from row count.

## Public result / provenance

Add a browse-specific result rather than overloading `LexiconLookupResult`:

```text
LexiconBrowseResult
  prefix                 original caller prefix
  normalized_prefix      normalized CAL-code prefix submitted for initial selection
  entries                ordered LemmaRef[] from this CAL page
  next_continuation      validated continuation sortkey or null
  provenance
```

Browse provenance should record:

- CAL source URL and retrieval timestamp;
- operation = `lexicon_browse`;
- original prefix;
- normalized prefix / representation / normalization strategy;
- whether this request was initial or continuation;
- submitted continuation when present.

The browse operation never fetches returned lemma entries automatically.

## Empty and drift semantics

Reuse existing explicit no-match detection:

- a recognized CAL no-match page returns `entries=[]`, `next_continuation=null`;
- a successful-looking page with neither entries nor explicit no-match remains `LexiconParseError`;
- contradictory/malformed continuation navigation remains parser drift and fails closed.

A no-match response must not be inferred from an empty parser result alone.

## Request bound

Each public browse call performs at most one new logical CAL request:

- initial page: one fixed `browseSKEYheaders.php?first3=...` request;
- continuation page: one fixed `browseSKEYheaders.php?direction=1&sortkey=...` request;
- completed cache hit: zero new upstream I/O.

There is no recursive pagination, alphabet traversal, entry expansion, or background prefetch.

## Release surface

This is a new user-facing task and requires one new MCP tool, `cal_lexicon_browse`. It should be added to the public inventory/release-surface tests and docs. `cal_lexicon_lookup` remains unchanged.

## TDD implications

The deterministic RED should pin:

1. current-shaped `br` page returns ordered `LemmaRef` rows without exact filtering;
2. current-shaped `b`/`br` `NEXT PAGE` yields one safe continuation;
3. one-letter and 2–3-character initial requests use only `first3`;
4. continuation uses only fixed `direction=1` plus returned `sortkey`;
5. no automatic second request occurs when a page has `NEXT PAGE`;
6. duplicate/conflicting, foreign-origin, wrong-path, wrong-direction, extra-query, fragment-bearing, or empty continuation links fail closed;
7. explicit no-match is a structured empty browse result while unrecognized empty markup is drift;
8. multi-prefix conversion ambiguity fails before transport rather than being merged;
9. invalid prefix length/content fails before transport;
10. existing `cal_lexicon_lookup` request/filter behavior is unchanged;
11. normal CI remains offline.

## CAL load

The 2026-09-12 recheck opened only the current Lexicon Browser, one `b` jump page, and its single `NEXT PAGE` continuation. Existing reduced fixtures cover the two-character `br` shape. Production remains one request per explicit browse page.