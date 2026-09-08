# Issue #52 plan — Hatran Unicode → CAL code

Date: 2026-09-07

## Goal

Implement the researched Hatran Unicode consonantal mapping as an isolated ambiguity-aware TDD slice. Preserve the existing local-only converter contract and 32-candidate bound.

## Test-first gate

Add `tests/test_hatran_conversion.py` before production changes. The RED commit must prove:

1. the full researched Hatran letter repertoire maps by explicit character identity;
2. U+108E3 `DALETH-RESH` yields ordered alternatives `d`, `r` with explicit ambiguity metadata;
3. the attested H 71:.1 fixture `𐣪𐣫𐣡` maps deterministically to `klb`;
4. six U+108E3 characters exceed the shared 32-candidate bound and raise `ConversionExpansionError`;
5. Hatran numbers/unverified block characters fail closed;
6. mixed Hatran with another supported script fails closed;
7. `cal_convert_to_code` exposes `representation=hatran`, `strategy=hatran_to_cal_code`, all candidates/ambiguities, and performs no network I/O.

A valid RED requires Ruff lint/format and mypy GREEN, with pytest failures only for missing Hatran production support.

## Minimal implementation

In `src/cal_mcp/normalization.py` only:

- add `InputRepresentation.HATRAN`;
- add `CalCodeConversionStrategy.HATRAN_TO_CAL_CODE`;
- add a table from researched Hatran Unicode letters to ordered CAL-code tuples;
- map U+108E3 to `("d", "r")`, all other letters to one-element tuples;
- detect the Hatran block before generic non-ASCII handling and include it in mixed-script rejection;
- validate strictly against the researched table plus existing separators;
- convert each word via `_append_alternatives`, recording `CalCodeAmbiguity` for U+108E3;
- preserve the existing 32-candidate expansion ceiling.

Do not add lexical disambiguation, morphology, numbers, punctuation, or CAL network calls.

## GREEN gate

Require both CI jobs (`deterministic` and `latest-compatible`) to pass Ruff, format, mypy, and the full pytest suite.

## Next slice

Only after Hatran GREEN, start Samaritan research as a separate committed research artifact and plan.