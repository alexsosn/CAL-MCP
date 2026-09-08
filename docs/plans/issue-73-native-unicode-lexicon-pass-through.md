# Issue #73 plan — restore CAL-native Hebrew/Syriac lexicon pass-through

Date: 2026-09-08
Research prerequisite: `docs/research/issue-73-native-unicode-lexicon-pass-through.md`

## Goal

Restore the pre-converter `cal_lexicon_lookup` compatibility contract for documented CAL-native pointed/vocalized Hebrew and Syriac, without weakening the standalone converter, admitting unverified base letters, or weakening the bounded ambiguity search added in issue #52.

## Gate 1 — behavior-first RED

Add one focused offline test module, `tests/test_lexicon_native_unicode_regression.py`.

Use an injected transport returning a synthetic explicit no-match browse page. Parameterize at least:

- pointed Hebrew `מֶלֶךְ`;
- vocalized Syriac `ܡܲܠܟܵܐ`.

For each case assert the intended legacy behavior:

1. lookup returns `LexiconLookupStatus.NOT_FOUND` rather than raising local conversion error;
2. exactly one request is made;
3. request path is `browseSKEYheaders.php`;
4. `first3` contains the Unicode browse prefix derived from the normalized query;
5. no entry request is made;
6. provenance has no CAL-code candidate fan-out fields for this legacy path.

Do not modify production in the initial RED commit.

### RED acceptance

Both deterministic and latest-compatible CI must reach pytest with dependency/install, Ruff lint, Ruff format, and strict mypy GREEN and failures confined to the new native-Unicode regression expectations.

## Gate 2 — initial minimal implementation

Keep the change local to `src/cal_mcp/lexicon.py`. Make conversion optional for Hebrew/Syriac only, while preserving successful ambiguity conversion and mandatory dedicated-script conversion.

## Review-regression gate — representation-only fallback is too broad

The initial implementation used `normalized.representation in {HEBREW, SYRIAC}` as the entire fallback test. Review-regression CI `34221362183` reached pytest with all static gates GREEN and finished with exactly 1 failure / 652 passes: unverified Syriac `ܞ` incorrectly reached the injected CAL transport.

Before revising production, strengthen the test-only regression to require **both**:

- `ܞ` fails with `UnsupportedQueryError` before CAL I/O;
- `ܞܲ` (the same unverified base plus a Syriac mark) also fails before CAL I/O.

This prevents a superficial “fallback if a mark exists” fix.

## Gate 3 — corrected minimal implementation

On `UnsupportedQueryError` from `convert_to_cal_code(query)`:

1. fallback eligibility remains restricted to normalized Hebrew/Syriac;
2. require the original query to contain at least one Unicode mark (`unicodedata.category(char).startswith("M")`);
3. build a **local eligibility probe only** by removing Unicode mark characters from the normalized query;
4. require `convert_to_cal_code(mark_stripped_probe)` to succeed;
5. if the probe is unsupported, re-raise the original `UnsupportedQueryError`;
6. if eligible, set `conversion = None` and use the existing legacy Unicode browse path with the original normalized pointed/vocalized query unchanged.

Do not send the stripped probe to CAL. Do not modify `convert_to_cal_code()` or normalization.

Do not catch `ConversionExpansionError` or arbitrary exceptions. A mark-stripped probe that does not cleanly pass the existing converter is not positive fallback evidence and must remain fail-closed.

Behavior requirements:

- documented pointed/vocalized Hebrew/Syriac with converter-supported bases -> existing normalized Unicode browse path;
- Hebrew/Syriac conversion succeeds with no ambiguity -> existing normalized Unicode browse path;
- Hebrew/Syriac conversion succeeds with finite ambiguity -> bounded CAL-code fan-out;
- unverified base letter, with or without marks -> fail before I/O;
- unsupported punctuation -> fail before I/O;
- dedicated-script conversion remains required;
- standalone converter behavior unchanged.

## Gate 4 — full GREEN

Run permanent CI in both dependency matrices.

Explicitly recheck existing tests for:

- pointed Hebrew/vocalized Syriac one-request legacy path;
- unverified Syriac with and without a mark, zero I/O;
- bare Hebrew shin ambiguity expansion;
- Syriac dotless dalath/resh ambiguity;
- dedicated Imperial/Palmyrene/Nabataean/Hatran/Samaritan/Mandaic lookup;
- 8-prefix pre-I/O cap and 64 complete-query cap;
- deterministic Hebrew/Syriac one-request behavior;
- lexicon provenance;
- converter fail-closed marks;
- release surface/tool count.

No live CAL traffic.

## Gate 5 — documentation

Review `docs/concepts/input-and-transliteration.md` and `docs/tools/lexicon.md`.

If current wording could imply that lexicon lookup requires local conversion for every Hebrew/Syriac query, update it to state:

- documented CAL-native Hebrew/Syriac pointing/vocalization can pass through unchanged when the base content is converter-supported;
- local conversion is used where needed for finite ambiguity or dedicated-script bridging;
- standalone conversion remains stricter and may reject marks that CAL-native lookup can pass through;
- unverified base characters do not gain pass-through merely by belonging to the Hebrew/Syriac Unicode blocks.

If docs already state this distinction accurately, avoid unnecessary changes.

## Gate 6 — logically independent adversarial review

Review the exact final SHA from scratch against issue #73, corrected research, issue #52 compatibility guarantees, whole diff, and exact-head CI.

Challenge at least:

- fallback restricted to Hebrew/Syriac only;
- fallback requires actual marks and converter-supported mark-stripped bases;
- `ܞ` and `ܞܲ` remain zero-I/O failures;
- unsupported punctuation cannot be stripped into acceptance;
- original pointed/vocalized query, not the probe, is sent to CAL;
- `ConversionExpansionError` and arbitrary converter bugs are not swallowed;
- pointed Hebrew/Syriac perform exactly one browse request;
- bare-shin / dotless-dalath ambiguity still expands;
- dedicated-script conversion cannot fall through to CAL;
- legacy match/provenance behavior remains unchanged;
- converter tool strictness remains unchanged;
- no CAL access in tests.

Any blocker requires a new review-regression RED → minimal fix → full GREEN → fresh exact-head review.

## Merge gate

Immediately before merge:

1. refetch `main` and PR head;
2. if `main` advanced, synchronize non-destructively and rerun exact-head CI/review where necessary;
3. record RED/GREEN/review evidence in PR body;
4. mark ready only after the exact-head review passes;
5. merge using `expected_head_sha` equal to the reviewed head.