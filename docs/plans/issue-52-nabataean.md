# Issue #52 plan — Nabataean Unicode → CAL code

Date: 2026-09-07

## Goal

Implement the researched Nabataean Unicode consonantal mapping as one isolated TDD slice without changing existing request behavior or any CAL network path.

## Test-first gate

Add `tests/test_nabataean_conversion.py` before production changes. The RED commit must prove:

1. all researched U+10880–U+1089E letters map by explicit character identity;
2. contextual final forms converge to the same CAL code as their ordinary forms;
3. the attested `NabTomb 8:2` fixture `𐢅𐢕𐢇` maps to `dnh`;
4. Nabataean numbers fail closed;
5. mixed Nabataean with another supported script fails closed;
6. `cal_convert_to_code` exposes `representation=nabataean`, `strategy=nabataean_to_cal_code`, and performs no network I/O.

A valid RED requires lint/format/mypy GREEN and pytest failures only for missing Nabataean production support.

## Minimal implementation

In `src/cal_mcp/normalization.py` only:

- add `InputRepresentation.NABATAEAN`;
- add `CalCodeConversionStrategy.NABATAEAN_TO_CAL_CODE`;
- add the researched table for U+10880–U+1089E letters;
- detect the Nabataean block before generic non-ASCII handling;
- include it in mixed-script rejection;
- validate strictly against the researched letter table plus existing separators;
- convert each word deterministically to one candidate.

Do not accept numbers, reserved code points, punctuation, diacritics, or inferred linguistic values.

## GREEN gate

Require both CI jobs (`deterministic` and `latest-compatible`) to pass Ruff, format, mypy, and the full pytest suite. No live CAL request is necessary for this implementation gate.

## Next slice

Only after Nabataean GREEN, start Hatran research as a new committed research artifact and plan before adding tests or production code.