# Issue #8 research — CAL token-at-coordinate lexical analysis

**Rechecked:** 2026-09-04

This note records the bounded live evidence used before implementing issue #8. It is a ticket-level research artifact; the stable architectural conclusions can be folded into `research.md` before merge.

## Current request contract

CAL's current text-browser lexical-analysis operation is:

```text
GET /getlex.php?coord=<CAL machine coordinate>&word=<zero-based word index>
```

The coordinate is the decimal machine coordinate already exposed by `cal_text_page` token links. `word` is zero-based, matching the `TextToken.word_index` model from issue #7.

Representative current page:

- `coord=4400137054005&word=0` returns HTTP 200 and an analysis page headed `Click on a headword to see a complete lexicon entry`.
- The page renders CAL's compact analysis label (`xd n02`) separately from the linked lexicon header (`ḥd (ḥaḏ) num. one`, lemma key `xd b`).
- `word=1` on the same coordinate similarly renders `mll verb D` and lemma key `mll V`.

## Multiple analyses are ordered upstream alternatives

A bounded probe of a token already represented in the issue #7 BT AZ fixture confirmed a genuinely ambiguous token:

```text
coord=7102601002203&word=0
```

The current page renders the candidates as ordered pairs:

1. analysis label `w_ c` → lemma key `w_ c`, rendered header `w_ (wə_) conj. and, also`;
2. analysis label `my c` → lemma key `my c`, rendered header `my (mī) conj. interrogative particle`.

The compact analysis label is therefore per candidate, not merely a token-level heading. CAL-MCP must preserve every candidate in CAL order and must not rank or collapse them.

## No-data and malformed-success shapes

Two syntactically valid requests currently return the same explicit HTTP-200 no-data message:

- an out-of-range word index (`coord=4400137054005&word=99`);
- a nonexistent decimal coordinate (`coord=9999999999999&word=0`).

The rendered message is:

```text
there is no data for this word — it may be undecipherable or simply not Aramaic
```

That explicit marker is safe to map to a typed `not_found` result.

By contrast, a malformed coordinate such as `coord=abc&word=0` currently returns HTTP 200 with the analysis-page shell but neither a lemma analysis nor the explicit no-data marker. Public CAL-MCP callers must never issue that request: malformed coordinates are rejected locally. If equivalent unexplained successful markup reaches the parser through upstream drift, it must raise parser drift rather than silently become `not_found`.

## Model and request implications

- One explicit MCP call performs exactly one CAL `getlex.php` request.
- No lexicon entry is fetched automatically. Candidate links compose with the existing `LemmaRef` model from issue #4.
- Each candidate preserves the exact CAL compact `analysis_label` plus its `LemmaRef`.
- The result preserves requested machine `coordinate`, zero-based `word_index`, CAL source URL, and timezone-aware retrieval timestamp.
- Decimal coordinates remain opaque strings; CAL-MCP does not decode their digits.
- `word_index` is a non-negative integer; booleans and negative/non-integer values are invalid locally.
- A malformed coordinate is a caller-validation error; CAL's explicit no-data marker is `not_found`; transport/content failures remain shared client errors; an unexplained HTTP-success page is parser drift.
- Normal CI stays offline and uses reduced semantic fixtures rather than archived CAL pages.

## Research load

The live audit used three temporary branch-only workflows and a total of ten bounded GET requests: five request/error-shape probes, four existing fixture-token multiplicity probes, and one structural probe of the confirmed ambiguous token. The temporary workflows were deleted immediately after each research phase and are not part of normal CI.
