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

Therefore documented pointed/vocalized Hebrew/Syriac forms accepted by the existing normalization tests could reach CAL unchanged.

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

Lookup should use conversion only as an optional enhancement for documented pointed/vocalized CAL-native Hebrew/Syriac and as a required bridge for dedicated scripts that CAL lookup cannot consume directly.

## Review-regression correction: script detection is not mapping validation

The first minimal implementation caught every `UnsupportedQueryError` for inputs classified as Hebrew or Syriac and fell back to CAL-native browse. Review-regression CI `34221362183` disproved that boundary: the unverified Syriac base letter `ܞ` is classified as Syriac by normalization but is intentionally absent from the researched converter mapping. The broad fallback therefore sent an unverified character to CAL instead of failing before I/O.

This shows that `normalized.representation in {HEBREW, SYRIAC}` is necessary but not sufficient evidence for fallback. Script-block detection must not be treated as a whitelist of locally verified base letters.

The narrow fallback condition is **mark-only conversion loss over verified base letters**:

- the original query is normalized as Hebrew or Syriac;
- local conversion fails with `UnsupportedQueryError`;
- the query actually contains at least one Unicode combining mark (`General_Category` beginning with `M`);
- a local scan permits only spaces/underscores, verified Hebrew/Syriac base letters, and combining marks attached to a preceding verified base letter;
- each base letter is validated through `convert_to_cal_code(char, representation=normalized.representation)`, so eligibility reuses the researched converter inventory rather than Unicode-block membership;
- unsupported punctuation, unattached marks, or unverified base letters make the fallback ineligible;
- the original pointed/vocalized query is then sent unchanged through the legacy Unicode browse path.

The scan is only a local safety predicate. It does not transliterate, strip marks, or send a probe to CAL. An unverified base such as `ܞ`, including `ܞ` plus a vowel mark, still fails because the base letter itself is unsupported. Unsupported punctuation and an unattached combining mark likewise remain local failures before I/O.

## Required compatibility behavior

For Hebrew/Syriac:

- If local conversion succeeds and exposes finite ambiguity (for example bare Hebrew `ש` or Syriac `ܖ`), keep the bounded CAL-code fan-out added by issue #52.
- If local conversion fails only because Unicode pointing/vocalization marks sit on converter-supported Hebrew/Syriac base characters, fall back to the legacy one-prefix Unicode browse path.
- If any base character is unsupported, punctuation is unverified, or a combining mark is unattached, fail before CAL I/O.
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

After catching `UnsupportedQueryError`, perform the verified marked-letter eligibility scan above. If that scan does not positively establish supported base content plus attached marks, re-raise the original error.

## TDD strategy

Use offline regressions around `LexiconLookupService` with injected transport.

Test at least:

1. pointed Hebrew `מֶלֶךְ` performs exactly one browse request using the Unicode browse prefix and returns explicit `not_found` from a synthetic no-match page;
2. vocalized Syriac `ܡܲܠܟܵܐ` does the same;
3. no entry request occurs for those no-match cases;
4. unverified Syriac `ܞ` fails before I/O;
5. unverified Syriac plus a mark (`ܞܲ`) also fails before I/O, proving that the fallback is not merely “has a mark”;
6. Syriac punctuation after otherwise supported marked letters fails before I/O;
7. an unattached Syriac combining mark fails before I/O;
8. existing bare-Hebrew-shin ambiguity tests remain unchanged and continue to fan out;
9. existing dedicated-script tests remain unchanged and continue to require conversion.

## Implementation boundary

Keep the fix local to `src/cal_mcp/lexicon.py`. The eligibility check may use `unicodedata.category()` and `convert_to_cal_code()` only to validate the original normalized query's character classes and base-letter inventory; it must never alter the query sent to CAL.

## Conclusion

Issue #73 is a release-blocking compatibility regression caused by conflating CAL-native pointed/vocalized Unicode acceptance with the stricter standalone converter contract. The first representation-only fallback was also too broad. The corrected safe boundary is to permit legacy Hebrew/Syriac pass-through only when the conversion failure is demonstrably mark-only over converter-supported base content, with marks attached to verified letters and no unsupported punctuation; all unverified base characters remain fail-closed before I/O.