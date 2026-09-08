# Issue #52 plan — Mandaic Unicode → CAL code

Date: 2026-09-07

## Goal

Implement the researched Mandaic Unicode mapping as an isolated TDD slice, including CAL's Mandaic-specific `D`, `H`, and `S` codes and deterministic KAD expansion. Keep borrowed AIN and unverified marks fail-closed.

## Test-first gate

Add `tests/test_mandaic_conversion.py` before production changes. The RED commit must prove:

1. U+0840–U+0856 map in exact CAL Mandaic-set order to `abgdhuzHTiklmns(pSqr$tD`;
2. JohnBook 24:3 fixture `ࡔࡅࡌࡇ` maps to `$umH`;
3. JohnBook 24:3 fixture `ࡖࡌࡀࡍࡃࡀ` maps to `Dmanda`;
4. U+0857 KAD maps deterministically to `kD` with no ambiguity metadata;
5. U+0858 borrowed AIN, U+0859–U+085B combining marks, U+085E punctuation, and an unassigned block character fail closed;
6. mixed Mandaic with another supported script fails closed;
7. `cal_convert_to_code` exposes `representation=mandaic`, `strategy=mandaic_to_cal_code`, the exact deterministic candidate, and performs zero network I/O.

A valid RED requires Ruff lint/format and mypy GREEN, with pytest failures only for missing Mandaic production support. Rejection cases may already pass under the current generic unsupported-Unicode boundary.

## Minimal implementation

In `src/cal_mcp/normalization.py` only:

- add `InputRepresentation.MANDAIC`;
- add `CalCodeConversionStrategy.MANDAIC_TO_CAL_CODE`;
- add a strict mapping table for U+0840–U+0857;
- map inherited Mandaic letters using CAL's exact Mandaic Roman set, not the generic Semitic table;
- map DUSHENNA to `D`, IT to `H`, ASZ to `S`, ASH to current `$`;
- map KAD to the two-character output `kD`;
- detect the Mandaic block before generic non-ASCII handling and include it in mixed-script rejection;
- validate only researched U+0840–U+0857 plus existing separators;
- convert each word deterministically to one candidate.

Do not add support for U+0858 AIN, Mandaic combining marks, punctuation, phonological rewriting, or CAL network calls.

## GREEN gate

Require both CI jobs (`deterministic` and `latest-compatible`) to pass Ruff, format, mypy, and the full pytest suite.

## Next slice

Only after Mandaic GREEN, complete the CPA/Syriac evidence/fixture gate and then the public documentation contract for the full issue #52 surface.