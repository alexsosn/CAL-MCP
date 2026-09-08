# Issue #52 plan — Samaritan Unicode → CAL code

Date: 2026-09-07

## Goal

Implement the researched Samaritan Unicode consonantal mapping as an isolated ambiguity-aware TDD slice. Preserve the local-only converter contract and shared 32-candidate expansion bound.

## Test-first gate

Add `tests/test_samaritan_conversion.py` before production changes. The RED commit must prove:

1. all 22 researched Samaritan consonant letters map by explicit character identity;
2. U+0814 `SHAN` yields ordered alternatives `$`, `&` with explicit ambiguity metadata;
3. the attested Samaritan Targum Gen 37:2 fixture `ࠁࠓ` maps deterministically to `br`;
4. six U+0814 characters exceed the shared 32-candidate bound and raise `ConversionExpansionError`;
5. consonant modifiers, vowel/modifier characters, punctuation, and unassigned block characters fail closed;
6. mixed Samaritan with another supported script fails closed;
7. `cal_convert_to_code` exposes `representation=samaritan`, `strategy=samaritan_to_cal_code`, candidates/ambiguities, and performs zero network I/O.

A valid RED requires Ruff lint/format and mypy GREEN, with pytest failures only for missing Samaritan production support.

## Minimal implementation

In `src/cal_mcp/normalization.py` only:

- add `InputRepresentation.SAMARITAN`;
- add `CalCodeConversionStrategy.SAMARITAN_TO_CAL_CODE`;
- add an explicit table from U+0800–U+0815 consonant letters to ordered CAL-code tuples;
- map U+0814 to `("$", "&")`, all other researched consonants to one-element tuples;
- detect the Samaritan block before generic non-ASCII handling and include it in mixed-script rejection;
- validate strictly against the consonant table plus existing separators;
- convert each word via `_append_alternatives`, recording `CalCodeAmbiguity` for U+0814;
- preserve the existing 32-candidate ceiling.

Do not add support for Samaritan vowels, consonant modifiers, punctuation, pronunciation-driven rewriting, morphology, or CAL network calls.

## GREEN gate

Require both CI jobs (`deterministic` and `latest-compatible`) to pass Ruff, format, mypy, and the full pytest suite.

## Next slice

Only after Samaritan GREEN, start Mandaic research as a separate committed research artifact and plan.