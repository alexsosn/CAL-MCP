# Issue #112 research — bounded CAL lexicon prefix browsing

**Research date:** 2026-09-09
**Scope:** research only while #106 is blocked on hosted CI; no #112 production/TDD work starts from this artifact.

## Research question

How can CAL-MCP expose CAL's current Lexicon Browser discovery task faithfully and boundedly without changing `cal_lexicon_lookup`, leaking arbitrary upstream navigation controls, or silently truncating paginated browse results?

## Current CAL entry point

CAL's current Lexicon Browser (`searching/fullbrowser.html`) explicitly documents two discovery modes:

1. enter the first **two or three consonants** and select from all corresponding entries;
2. use a one-letter **JUMP TO** alphabet link.

The page says the typed form may be CAL code, Unicode transliteration, Unicode Hebrew, or Unicode Syriac. It also documents underscore for bound one-letter forms (for example `w_`) and space for CAL `@` combinations.

Current indexed navigation confirms a one-letter `b` jump resolves to:

```text
GET browseSKEYheaders.php?first3="b"
```

The existing adapter already uses the same private route for exact lexical lookup prefiltering:

```python
CalRequest(
    method="GET",
    path="browseSKEYheaders.php",
    params=(("first3", f'"{prefix}"'),),
)
```

A reduced repository fixture captured from CAL on 2026-09-06 confirms a two-letter `br` request uses:

```text
browseSKEYheaders.php?first3="br"
```

Thus one-letter jumps and documented 2–3-consonant prefix entry share the initial route family.

## Pagination is part of the browse contract

The current live/indexed one-letter `b` result contains an explicit `NEXT PAGE` link. Its continuation request changes shape:

```text
GET browseSKEYheaders.php?direction=1&sortkey=baoinjo+b
```

The repository's reduced `br` fixture also contains:

```text
NEXT PAGE -> browseSKEYheaders.php?direction=1&sortkey=br
```

Therefore pagination is not confined to one-letter jumps. Even a documented two-consonant prefix may require more than one CAL response.

This invalidates a tempting implementation that would expose the existing `parse_browse_page()` result as "all matching entries": the parser currently returns only the ordered `LemmaRef` entries on the current response and ignores `NEXT PAGE` / previous-page navigation entirely.

A public prefix-browse contract must either:

- model one-page results plus a safe continuation token/selector; or
- establish and enforce a narrower prefix class that is proven never to paginate.

Current evidence supports the first direction; no safe non-paginating prefix class has been established.

## Existing parser/model reuse

`parse_browse_page()` already preserves useful CAL browse semantics for one page:

- rendered lemma order;
- lemma key;
- headwords;
- aliases rendered before `→`;
- pronunciation where present;
- part of speech;
- the immediately associated gloss;
- explicit no-match recognition through CAL no-match phrases;
- fail-closed behavior when a page has neither recognizable entries nor an explicit no-match marker.

It does **not** currently expose browse navigation. Adding pagination for #112 should extend the page/result contract rather than replacing the lemma parser or reranking/deduplicating results.

## Relationship to `cal_lexicon_lookup`

`LexiconLookupService.lookup()` currently:

1. normalizes/converts the requested lexical form;
2. derives up to three base characters through `_browse_prefix()`;
3. makes one or more bounded `browseSKEYheaders.php?first3="..."` requests (finite ambiguity fan-out);
4. exact-filters the returned candidates with `_query_matches()`;
5. optionally fetches one selected lexicon entry.

That behavior is correct for lookup but not for browsing: a browse operation must return CAL's ordered candidates instead of exact-filtering them.

`cal_lexicon_lookup` must remain unchanged. #112 should expose a separate discovery task.

## Input normalization and ambiguity

CAL documents multiple input scripts. The existing normalization/conversion subsystem should be reused rather than duplicating transliteration tables.

However, exact lookup can safely fan out ambiguous conversions and then exact-match/deduplicate by lemma key. Prefix browsing has a different ordering problem: if one public Unicode prefix expands to multiple distinct CAL-code browse prefixes, issuing multiple browse requests and concatenating them does not define a single authentic CAL ordering.

The public contract should therefore avoid silently merging multiple independently ordered CAL pages. The plan should choose one of these explicit behaviors:

- reject/return a structured ambiguity before transport when normalization yields multiple distinct browse prefixes, allowing the caller to select one CAL-code candidate; or
- expose separate candidate browse groups with provenance per upstream request.

A flat merged list would be semantically invented and should not be used.

For an unambiguous normalized prefix, one initial browse page should require exactly one CAL request.

## Prefix length and one-letter mode

CAL explicitly documents 2–3 consonants for typed prefix browsing, while one-letter browsing is exposed as a separate JUMP TO navigation mode.

Because both one-letter and two-letter results can paginate, pagination alone does not force two public tools. Still, the one-letter mode has a much larger result space and different user intent (alphabet navigation rather than concentrating on a partial root).

The narrowest first public contract should prioritize the documented **2–3-consonant prefix** task. One-letter JUMP TO should be included only if the plan can model the same continuation mechanism cleanly without implying automatic alphabet enumeration.

Do not allow an empty prefix or automatic "all lexicon" traversal.

## Continuation boundary

Current CAL continuation links expose private controls such as:

```text
direction=1
sortkey=baoinjo+b
```

The `sortkey` is not reliably identical to the public prefix or last rendered headword; it must be treated as adapter-owned continuation state.

A plan should not expose arbitrary URL execution. Candidate designs to evaluate before TDD:

1. an opaque adapter continuation token returned from the first page and accepted only by the same browse operation;
2. an explicit structured continuation model whose components are strictly parsed from CAL navigation and validated locally before the fixed endpoint is called.

A stateless opaque encoding is ergonomic but is not a security boundary by itself; validation must still restrict the decoded route to the fixed browse endpoint and expected `direction`/`sortkey` grammar. Raw CAL URLs must never be accepted.

One call must fetch at most one browse page. The caller explicitly follows continuation; no recursive/automatic pagination.

## No-match and drift

The existing browse parser already distinguishes explicit CAL no-match phrases from parser drift. #112 should preserve that distinction.

Tests should additionally pin navigation drift:

- zero or one recognized `NEXT PAGE` continuation is allowed;
- repeated/conflicting continuation controls fail closed;
- a continuation link to another endpoint or foreign origin fails closed;
- unrelated links remain ignorable;
- no continuation is represented as `None`, not as an inferred end based on result count.

## Response bounds

The HTTP client already enforces response-size and timeout limits. #112 must not increase those bounds or compensate for pagination by following links automatically.

A first-page browse request plus each explicit continuation call should each be one bounded CAL request.

## Current evidence

Rechecked 2026-09-09:

- `https://cal.huc.edu/searching/fullbrowser.html` — documents 2–3 consonant typed browsing, one-letter JUMP TO, supported scripts, underscore bound forms, and CAL-code conventions.
- Current `b` JUMP TO result — `browseSKEYheaders.php?first3="b"`; ordered lemma/gloss rows and `NEXT PAGE`.
- Current `b` continuation — `browseSKEYheaders.php?direction=1&sortkey=baoinjo+b`.
- Repository `tests/fixtures/cal/browse_br_unclosed_jump_2026_09_06.html` — reduced current-shape two-letter `br` page with ordered entries and `NEXT PAGE -> direction=1&sortkey=br`.
- Repository `src/cal_mcp/lexicon.py` — existing private initial browse request, `_browse_prefix()`, normalization/conversion fan-out, `parse_browse_page()`, exact filtering, and response parser semantics.

## Findings to carry into planning

1. Add a separate public browse/discovery operation; do not change exact lookup semantics.
2. Reuse existing normalization/conversion and `LemmaRef` parsing.
3. Do not flat-merge multiple ambiguous normalized prefix requests into a fabricated order.
4. Pagination is mandatory for correctness even for at least some two-consonant prefixes.
5. One public call fetches one CAL browse page; continuation is explicit and adapter-controlled.
6. Extend browse parsing to retain safe continuation state and fail closed on malformed/conflicting navigation.
7. Prefer 2–3-consonant prefix browsing as the initial required mode; one-letter JUMP TO can be included only if it shares the same bounded continuation contract cleanly.
8. Preserve CAL ordering and aliases; do not fetch returned lemma entries automatically.
9. Keep raw URLs and arbitrary CAL browse controls private.

## CAL load

This research used current indexed CAL pages plus already-committed reduced fixtures and source code. No additional automated CAL request was made from the repository or CI.
