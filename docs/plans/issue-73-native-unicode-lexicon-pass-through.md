# Issue #73 plan — restore CAL-native Hebrew/Syriac lexicon pass-through

Date: 2026-09-08
Research prerequisite: `docs/research/issue-73-native-unicode-lexicon-pass-through.md`

## Goal

Restore the pre-converter `cal_lexicon_lookup` compatibility contract for documented CAL-native Hebrew/Syriac Unicode, including pointing/vocalization and bound-form separators, without weakening the standalone converter, admitting unverified base letters, or weakening issue #52's bounded ambiguity search.

## Gate 1 — behavior-first RED

Add focused offline regressions around `LexiconLookupService` with an injected transport and synthetic explicit no-match browse page.

Positive CAL-native compatibility cases must include:

- pointed Hebrew `מֶלֶךְ`;
- vocalized Syriac `ܡܲܠܟܵܐ`;
- Hebrew bound form `ו_`;
- Syriac bound form `ܘ_`.

For each positive case assert:

1. lookup returns `LexiconLookupStatus.NOT_FOUND` rather than a local conversion error;
2. exactly one request is made;
3. request path is `browseSKEYheaders.php`;
4. `first3` contains the Unicode browse prefix from the normalized query;
5. no entry request is made;
6. provenance contains no CAL-code candidate fan-out fields for the legacy path.

The initial RED preceded production changes and established the pointed/vocalized compatibility regression in both CI matrices.

## Gate 2 — initial minimal implementation

Keep production changes local to `src/cal_mcp/lexicon.py`. Make whole-query CAL-code conversion optional only for CAL-native Hebrew/Syriac while preserving successful conversion, finite ambiguity expansion, and mandatory dedicated-script conversion.

## Review-regression gate — representation-only fallback is too broad

The first implementation used Hebrew/Syriac representation alone as the fallback predicate. Review-regression CI `34221362183` reached pytest with dependency/static/type gates GREEN and failed exactly the new zero-I/O case: unverified Syriac `ܞ` incorrectly reached transport.

Strengthen the regression boundary before the corrected implementation:

- `ܞ` fails with `UnsupportedQueryError` before I/O;
- `ܞܲ` also fails before I/O, proving that a mark does not legitimize an unverified base;
- unsupported Syriac punctuation fails before I/O;
- an unattached Syriac combining mark fails before I/O.

## Gate 3 — corrected component-level eligibility

When `convert_to_cal_code(query)` raises `UnsupportedQueryError`:

1. fallback eligibility is limited to `InputRepresentation.HEBREW` / `SYRIAC`;
2. scan `normalized.normalized` locally without changing it;
3. allow space and underscore as documented CAL-native separators;
4. allow a Hebrew/Syriac base letter only if `convert_to_cal_code(char, representation=normalized.representation)` succeeds;
5. allow Unicode marks only when attached to a preceding verified base letter;
6. reject any unsupported punctuation, unattached mark, unverified base letter, or other syntax by re-raising the original `UnsupportedQueryError`;
7. if the scan is eligible, set `conversion = None` and use the existing Unicode browse path with the original normalized query unchanged.

The CAL-native bound-form `_` separator is explicitly preserved by this gate: it is documented by CAL's current lexicon browser and is allowed only alongside verified Hebrew/Syriac base content.

Do not require an actual combining mark. CAL's current lexicon browser explicitly documents underscore bound forms (`w_`) and accepts Unicode Hebrew/Syriac on the same browser surface. A review-time `has_mark` proposal was therefore rejected before production modification; positive `ו_` / `ܘ_` regressions freeze the documented bound-form behavior.

The eligibility scan is a safety predicate only. Do not strip marks, reinterpret separators, send a probe to CAL, or modify `convert_to_cal_code()` / normalization.

Do not catch `ConversionExpansionError` or arbitrary exceptions.

## Gate 4 — full GREEN

Require both permanent CI jobs on the exact implementation candidate:

- deterministic Python 3.11 constraints + exact-environment verification + Ruff/format/mypy/pytest;
- latest-compatible resolution + `pip check` + Ruff/format/mypy/pytest.

Explicitly recheck:

- four positive native-Unicode cases above;
- `ܞ`, `ܞܲ`, punctuation, and unattached-mark zero-I/O failures;
- bare Hebrew shin ambiguity expansion;
- Syriac dotless dalath/resh ambiguity;
- dedicated Imperial/Palmyrene/Nabataean/Hatran/Samaritan/Mandaic lookup;
- 8-prefix pre-I/O cap and 64 complete-query cap;
- deterministic Hebrew/Syriac one-request behavior;
- lexicon conversion provenance;
- standalone converter fail-closed behavior;
- frozen release surface/tool count.

No live CAL traffic in normal CI.

## Gate 5 — user documentation

Update `docs/concepts/input-and-transliteration.md` and `docs/tools/lexicon.md` if needed so users can see the distinction:

- `cal_lexicon_lookup` can preserve documented CAL-native Hebrew/Syriac marks and bound-form separator syntax when all base letters are verified;
- conversion remains responsible for finite ambiguity and dedicated-script bridging;
- `cal_convert_to_code` remains stricter and may reject native-query syntax that lookup can safely pass through;
- unverified base letters, unsupported punctuation, and unattached marks remain local errors before CAL I/O.

## Gate 6 — logically independent adversarial review

Freeze the exact final SHA and review the whole diff from scratch against current `main`, issue #73 research, issue #52 compatibility guarantees, and exact-head CI.

Challenge at least:

- fallback restricted to Hebrew/Syriac only;
- every fallback base letter comes from the researched converter inventory;
- space/underscore are the only native separators admitted by this fallback;
- marks must remain attached to a verified base;
- `ܞ`, `ܞܲ`, unsupported punctuation, and unattached marks remain zero-I/O failures;
- `ו_` and `ܘ_` remain one-request native browse cases;
- original pointed/vocalized/bound-form query is sent to CAL unchanged;
- `ConversionExpansionError` and arbitrary converter bugs are not swallowed;
- bare-shin / dotless-dalath ambiguity still expands;
- dedicated scripts cannot fall through to native browse;
- provenance and request cardinality remain correct;
- standalone converter strictness remains unchanged;
- no temporary workflow/helper survives in the final diff;
- normal tests make no CAL requests.

Any blocker requires a new test-first review regression, minimal fix, full exact-head GREEN, and fresh exact-head review.

## Merge gate

Immediately before merge:

1. refetch `main` and PR head;
2. synchronize non-destructively if `main` advanced;
3. require exact-head dual-matrix GREEN;
4. record the RED/GREEN/review evidence and superseded review correction in the PR body;
5. mark ready only after the fresh adversarial PASS;
6. merge using `expected_head_sha` equal to the reviewed head.
