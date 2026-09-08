# Issue #73 plan — restore CAL-native Hebrew/Syriac lexicon pass-through

Date: 2026-09-08
Research prerequisite: `docs/research/issue-73-native-unicode-lexicon-pass-through.md`

## Goal

Restore the pre-converter `cal_lexicon_lookup` compatibility contract for CAL-native pointed/vocalized Hebrew and Syriac, without weakening the standalone converter or the bounded ambiguity search added in issue #52.

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

Do not modify production in the RED commit.

### RED acceptance

Both deterministic and latest-compatible CI must reach pytest with:

- dependency/install checks GREEN;
- Ruff lint GREEN;
- Ruff format GREEN;
- strict mypy GREEN;
- failures confined to the new native-Unicode regression expectations.

The expected current failure is `UnsupportedQueryError` before transport.

## Gate 2 — minimal implementation

Modify only `src/cal_mcp/lexicon.py` initially.

After `normalized = normalize_query(query)`, make local conversion optional only for CAL-native Hebrew/Syriac:

```python
conversion: CalCodeConversion | None
try:
    conversion = convert_to_cal_code(query)
except UnsupportedQueryError:
    if normalized.representation not in {
        InputRepresentation.HEBREW,
        InputRepresentation.SYRIAC,
    }:
        raise
    conversion = None
```

Import `UnsupportedQueryError` if needed.

Then calculate ambiguity/search only when `conversion is not None`.

Behavior requirements:

- `conversion is None` -> existing normalized Unicode browse path;
- Hebrew/Syriac conversion succeeds with no ambiguity -> existing normalized Unicode browse path;
- Hebrew/Syriac conversion succeeds with finite ambiguity -> bounded CAL-code fan-out;
- dedicated-script conversion remains required;
- `ConversionExpansionError` and unrelated exceptions propagate unchanged.

Do not change `convert_to_cal_code()`.

## Gate 3 — full GREEN

Run permanent CI in both dependency matrices.

Explicitly recheck existing tests for:

- bare Hebrew shin ambiguity expansion;
- Syriac dotless dalath/resh ambiguity;
- dedicated Imperial/Palmyrene/Nabataean/Hatran/Samaritan/Mandaic lookup;
- 8-prefix pre-I/O cap and 64 complete-query cap;
- deterministic Hebrew/Syriac one-request behavior;
- lexicon provenance;
- converter fail-closed marks;
- release surface/tool count.

No live CAL traffic.

## Gate 4 — documentation

Review `docs/concepts/input-and-transliteration.md` and `docs/tools/lexicon.md`.

If current wording could imply that lexicon lookup requires local conversion for every Hebrew/Syriac query, update it to state:

- CAL-native Hebrew/Syriac can pass through unchanged;
- local conversion is used only where needed for finite ambiguity or dedicated-script bridging;
- standalone conversion remains stricter and may reject marks that CAL-native lookup can pass through.

If docs already state this distinction accurately, avoid unnecessary changes.

## Gate 5 — logically independent adversarial review

Review the exact final SHA from scratch against issue #73, the pre-converter behavior, issue #52 compatibility guarantees, whole diff, and exact-head CI.

Challenge at least:

- whether fallback is restricted to Hebrew/Syriac only;
- whether normalization happens before fallback eligibility is decided;
- whether unsupported dedicated-script conversion can accidentally fall through to CAL;
- whether `ConversionExpansionError` is swallowed;
- whether arbitrary converter bugs/exceptions are swallowed;
- whether pointed Hebrew/Syriac still perform exactly one browse request;
- whether bare-shin / dotless-dalath ambiguity still expands;
- whether legacy match/provenance behavior remains unchanged;
- whether converter tool strictness remains unchanged;
- no CAL access in tests.

Any blocker requires a review-regression RED → minimal fix → full GREEN → fresh exact-head review.

## Merge gate

Immediately before merge:

1. refetch `main` and PR head;
2. if `main` advanced, synchronize non-destructively and rerun exact-head CI/review where necessary;
3. record RED/GREEN/review evidence in PR body;
4. mark ready only after the exact-head review passes;
5. merge using `expected_head_sha` equal to the reviewed head.