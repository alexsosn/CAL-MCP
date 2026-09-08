# Issue #73 research — preserve CAL-native Unicode lexicon lookup after converter integration

Date: 2026-09-08
Baseline: `main` at `b99bb356cf25026ca5852c5cdabfc007120b0aad`

## Question

Did the CAL-code conversion integration make `cal_lexicon_lookup` stricter than CAL's existing Unicode query contract for Hebrew/Syriac input, and what is the narrowest safe fix?

## Established normalization contract

`tests/test_normalization.py` explicitly freezes these as CAL-supported Unicode pass-through inputs:

- pointed Hebrew `מֶלֶךְ`;
- vocalized Syriac `ܡܲܠܟܵܐ`.

`normalize_query()` accepts them as `HEBREW` / `SYRIAC`, preserves them unchanged, and does not perform local linguistic interpretation. This reflects the pre-converter design: CAL itself accepts Unicode Hebrew/Syriac, so the adapter should not require local lossless Roman-code conversion before lookup.

## Pre-converter lexicon behavior

Before issue #52, `LexiconLookupService.lookup()` did:

1. `normalize_query(query)`;
2. `_browse_prefix(normalized.normalized)`;
3. exactly one `browseSKEYheaders.php` request;
4. local match/filter;
5. at most one selected entry fetch.

Therefore any Hebrew/Syriac form accepted by `normalize_query()` could reach CAL unchanged.

## Regression introduced by converter integration

Current lookup now does:

```python
normalized = normalize_query(query)
conversion = convert_to_cal_code(query)
```

before deciding whether CAL-code search is required.

The standalone converter intentionally has a **stricter** contract than normalization. It rejects Hebrew vowels/accents/dagesh and Syriac vowel/diacritic marks because no lossless v0.1 CAL-code mapping is claimed for them. That strictness is correct for `cal_convert_to_code`, but it is not a valid prerequisite for CAL-native lookup.

Result: pointed/vocalized Hebrew/Syriac that `normalize_query()` accepts now raises `UnsupportedQueryError` locally before the legacy browse request.

## Important distinction

There are two separate contracts:

1. **CAL-native query normalization**: preserve documented Unicode forms CAL accepts.
2. **Local Roman-code conversion**: convert only the researched lossless/finitely ambiguous subset; fail closed outside it.

Lookup should use conversion only as an optional enhancement for CAL-native Hebrew/Syriac and as a required bridge for dedicated scripts that CAL lookup cannot consume directly.

## Required compatibility behavior

For Hebrew/Syriac:

- If local conversion succeeds and exposes finite ambiguity (for example bare Hebrew `ש` or Syriac `ܖ`), keep the bounded CAL-code fan-out added by issue #52.
- If local conversion is unsupported but normalization already proved the Unicode query is CAL-native, fall back to the legacy one-prefix Unicode browse path.
- Do not weaken `convert_to_cal_code()` itself.

For dedicated scripts (Imperial Aramaic, Palmyrene, Nabataean, Hatran, Samaritan, Mandaic):

- conversion remains required;
- unsupported/unverified characters must still fail closed;
- do not fall back to sending dedicated palaeographic Unicode directly to CAL browse.

For CAL code / scholarly Unicode transliteration / shared Roman:

- preserve existing deterministic behavior;
- unsupported non-native input must remain an error.

## Error-boundary choice

Catch only `UnsupportedQueryError` from optional Hebrew/Syriac conversion. Do not catch:

- `ConversionExpansionError` (bounded ambiguity overflow must remain explicit);
- mixed-script ambiguity from normalization;
- arbitrary exceptions;
- dedicated-script conversion errors.

This preserves fail-closed behavior and avoids hiding implementation bugs.

## TDD strategy

Add offline regression tests around `LexiconLookupService` with injected transport.

Test at least:

1. pointed Hebrew `מֶלֶךְ` performs exactly one browse request using the Unicode browse prefix and returns explicit `not_found` from a synthetic no-match page;
2. vocalized Syriac `ܡܲܠܟܵܐ` does the same;
3. no entry request occurs for those no-match cases;
4. existing bare-Hebrew-shin ambiguity tests remain unchanged and continue to fan out;
5. existing dedicated-script tests remain unchanged and continue to require conversion.

The test-only RED should fail before I/O on current `main`, proving the regression directly.

## Implementation boundary

Keep the fix local to `src/cal_mcp/lexicon.py` unless tests prove otherwise.

A minimal shape is:

```python
conversion: CalCodeConversion | None
try:
    conversion = convert_to_cal_code(query)
except UnsupportedQueryError:
    if normalized.representation not in {InputRepresentation.HEBREW, InputRepresentation.SYRIAC}:
        raise
    conversion = None
```

Then require CAL-code search only when `conversion is not None` and it is ambiguous or a dedicated-script representation; otherwise use the existing normalized Unicode path.

## Conclusion

Issue #73 is a release-blocking compatibility regression caused by conflating CAL-native Unicode acceptance with the stricter standalone converter contract. The safe fix is not to loosen conversion; it is to make Hebrew/Syriac conversion optional inside lookup while keeping dedicated-script conversion mandatory and all ambiguity/request bounds intact.