# Issue #73 research — preserve CAL-native Unicode lexicon lookup after converter integration

Date: 2026-09-08
Baseline: `main` at `b99bb356cf25026ca5852c5cdabfc007120b0aad`

## Question

Did the CAL-code conversion integration make `cal_lexicon_lookup` stricter than CAL's existing Unicode query contract for Hebrew/Syriac input, and what is the narrowest safe fix?

## Established CAL-native contract

CAL's current lexicon browser explicitly accepts four query representations: CAL code, Unicode transliteration, Unicode Hebrew, and Unicode Syriac:

- `https://cal.huc.edu/searching/fullbrowser.html` (rechecked 2026-09-08).

The same current browser documentation states two pieces of query syntax that matter here:

- use a space for CAL `@` combinations;
- use underscore for bound forms, for example `w_`.

`tests/test_normalization.py` already freezes pointed Hebrew `מֶלֶךְ` and vocalized Syriac `ܡܲܠܟܵܐ` as accepted Hebrew/Syriac pass-through input. The shared normalization tables also permit the locally documented script separators space and underscore.

Therefore the CAL-native lookup contract is wider than the local Roman-code converter contract in two relevant ways: native Hebrew/Syriac may contain pointing/vocalization marks, and documented browser separator syntax such as `_` may be valid even when the dedicated script-to-CAL-code converter does not itself encode the whole string.

## Pre-converter lexicon behavior

Before issue #52, `LexiconLookupService.lookup()` did:

1. `normalize_query(query)`;
2. `_browse_prefix(normalized.normalized)`;
3. exactly one `browseSKEYheaders.php` request;
4. local match/filter;
5. at most one selected entry fetch.

Thus CAL-native Unicode accepted by normalization could reach CAL unchanged without first proving a lossless local CAL-code conversion.

## Regression introduced by converter integration

Issue #52 added local conversion before lookup decides whether CAL-code candidate expansion is needed:

```python
normalized = normalize_query(query)
conversion = convert_to_cal_code(query)
```

The standalone converter intentionally fails closed outside its researched mapping. In particular, it rejects Hebrew/Syriac combining marks and does not treat every normalized native-query separator as a script-to-code conversion primitive. That strictness is correct for `cal_convert_to_code`, but requiring it unconditionally for `cal_lexicon_lookup` made the native lookup surface stricter than CAL's documented browser contract.

## Separate contracts

There are two distinct responsibilities:

1. **CAL-native query normalization** — preserve documented Unicode Hebrew/Syriac forms and browser syntax that CAL accepts.
2. **Local CAL-code conversion** — convert only the researched deterministic/finitely ambiguous subset and fail closed outside it.

Lookup may use conversion to expose finite ambiguity or bridge dedicated scripts. It must not make successful local conversion a prerequisite for every CAL-native Hebrew/Syriac query.

## Review-regression correction: script detection alone is too broad

The first compatibility implementation caught every `UnsupportedQueryError` for inputs classified as Hebrew or Syriac and fell back to CAL-native browse. Review-regression CI `34221362183` showed that this was unsafe: unverified Syriac base letter `ܞ` is detected as Syriac by normalization but intentionally absent from the researched converter inventory. A representation-only fallback therefore allowed an unverified base character to reach CAL.

The safe eligibility check must distinguish **documented CAL-native syntax layered on verified base letters** from arbitrary code points in the Hebrew/Syriac Unicode blocks.

For a Hebrew/Syriac query whose whole-query CAL-code conversion raises `UnsupportedQueryError`, the fallback scan may accept only:

- spaces and underscores, because they are documented/local CAL-native separators;
- Hebrew/Syriac base letters that individually pass `convert_to_cal_code(char, representation=...)`;
- Unicode combining marks attached to a preceding verified base letter.

It must reject:

- unverified base letters such as `ܞ`, whether bare or marked;
- unsupported punctuation;
- unattached combining marks;
- any other non-letter/non-mark/non-separator syntax.

The scan is only a local safety predicate. It does not strip marks, transliterate the query, or send a probe to CAL. If eligible, lookup sends the original normalized Unicode query unchanged through the legacy browse path.

## Bound-form review correction

A later skeptical review proposed requiring at least one combining mark before fallback and added mark-free `מ_ל` as a zero-I/O regression. Rechecking the current CAL browser documentation showed that this condition was too narrow: CAL explicitly documents underscore for bound forms (`w_`), and Unicode Hebrew/Syriac are supported browser representations on the same interface.

The invalid `has_mark` helper was removed before it could modify production. The regression was corrected to positive CAL-native bound-form cases (`ו_` and `ܘ_`) that must retain the one-request Unicode browse path. This keeps the safety boundary tied to verified components rather than to one particular reason whole-query conversion may fail.

## Required compatibility behavior

For Hebrew/Syriac:

- converter-supported deterministic input keeps the existing deterministic lookup path;
- finite ambiguity (for example bare Hebrew `ש` or Syriac `ܖ`) keeps bounded CAL-code fan-out;
- documented native pointing/vocalization over verified bases keeps the legacy one-prefix Unicode browse path;
- documented native bound-form separators over verified bases likewise keep that path;
- unverified bases, unsupported punctuation, and unattached marks fail before CAL I/O;
- `convert_to_cal_code()` itself remains unchanged and strict.

For dedicated scripts (Imperial Aramaic, Palmyrene, Nabataean, Hatran, Samaritan, Mandaic), conversion remains required. Unsupported dedicated-script input must never fall through to CAL-native browse.

For CAL code, Unicode transliteration, and shared Roman input, existing behavior remains unchanged.

## Error boundary

Catch only `UnsupportedQueryError` from optional Hebrew/Syriac conversion. Do not catch `ConversionExpansionError`, normalization ambiguity, arbitrary exceptions, or dedicated-script conversion failures.

If the component-level eligibility scan does not positively establish a CAL-native query made only from documented separators, verified base letters, and attached marks, re-raise the original conversion error before transport.

## TDD / review evidence

Offline injected-transport regressions cover:

1. pointed Hebrew `מֶלֶךְ` — one Unicode browse request;
2. vocalized Syriac `ܡܲܠܟܵܐ` — one Unicode browse request;
3. Hebrew bound form `ו_` — one Unicode browse request;
4. Syriac bound form `ܘ_` — one Unicode browse request;
5. unverified Syriac `ܞ` — zero I/O failure;
6. marked unverified Syriac `ܞܲ` — zero I/O failure;
7. unsupported Syriac punctuation — zero I/O failure;
8. unattached Syriac mark — zero I/O failure;
9. existing Hebrew/Syriac ambiguity and dedicated-script conversion regressions remain unchanged.

Normal CI performs no CAL requests.

## Implementation boundary

Keep the production fix local to `src/cal_mcp/lexicon.py`. Eligibility may use `unicodedata.category()` plus single-character `convert_to_cal_code()` calls as a researched-base-letter whitelist. It must not change normalization, the standalone converter, the query sent to CAL, public MCP schemas, or request-volume limits.

## Conclusion

Issue #73 is a release-blocking compatibility regression caused by conflating CAL-native Unicode acceptance with the stricter standalone converter contract. The corrected fallback is component-based: verified Hebrew/Syriac bases may retain CAL-native documented marks and separators, while unverified bases and unsupported syntax remain fail-closed before I/O.