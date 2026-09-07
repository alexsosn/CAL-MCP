# Issue #52 plan — deterministic Aramaic/Unicode → CAL code conversion

Date: 2026-09-07

## Goal

Add a local, explicit `cal_convert_to_code` MCP capability for the v0.1 contract without changing existing live-query normalization behavior or CAL request volume.

Research gate: `docs/research/issue-52-cal-code-conversion.md`.

## Gate 1 — test-first RED

Add focused tests before production code.

### Pure conversion tests

Create `tests/test_cal_code_conversion.py` covering:

1. Unicode scholarly transliteration:
   - `šˀl ḥṭˁ ṗṣś` → `$)l xT( Pc&` using exact table-driven mapping;
   - shared Roman consonants remain byte-for-byte identical;
   - surrounding ordinary spaces are trimmed consistently with current normalization while internal spaces remain spaces.
2. Hebrew consonants:
   - medial/final letters map to the same CAL code;
   - `שׁ` → `$`, `שׂ` → `&`;
   - bare `ש` raises `AmbiguousQueryError`;
   - vowel points, dagesh, accents, punctuation, and unsupported combining marks raise `UnsupportedQueryError` rather than being removed.
3. Syriac consonants:
   - the ordinary 22-letter consonantal inventory maps exactly;
   - vowel/diacritic/punctuation marks raise `UnsupportedQueryError` rather than disappearing.
4. Existing CAL/shared-Roman inputs:
   - explicit simple CAL code passes through unchanged;
   - broader currently valid CAL-code syntax remains pass-through rather than being reinterpreted;
   - plain `mlk` converts to `mlk` without requiring a guessed representation.
5. Round-trip invariant:
   - for the bijective simple consonantal CAL subset (excluding `@` because it collapses to a space in the existing CAL→Unicode helper), `CAL code → existing Unicode normalization → new converter` returns the original code.
6. Mixed scripts/control/unsupported Unicode fail under the same fail-closed policy as normalization.

### MCP contract tests

Extend `tests/test_bootstrap.py` and/or add a focused MCP contract test to require:

- public tool `cal_convert_to_code` exists;
- input schema contains `value` and optional `representation` only;
- structured result contains `original`, `cal_code`, `representation`, `strategy`;
- calling it opens no network socket and does not construct/use a CAL request.

Run CI on the test-only commit. Valid RED means behavioral failures due to the missing conversion primitive/tool. Formatting/lint-only failures do not count as RED and must be corrected before implementation.

## Gate 2 — minimal implementation

Implement only what the RED tests require.

### `src/cal_mcp/normalization.py`

Add:

- a conversion strategy enum (or extend the existing strategy enum only if doing so keeps the normalization contract clear);
- a frozen/slotted conversion result dataclass with `to_dict()`;
- explicit inverse scholarly-transliteration map;
- explicit Hebrew consonant map including finals;
- explicit Syriac consonant map;
- `convert_to_cal_code(value, *, representation=None)`.

Rules:

- reuse `_reject_controls`, representation detection concepts, and current CAL-code whitelist where safe;
- do not modify `normalize_query()` semantics;
- trim only ordinary ASCII boundary spaces, preserve internal spaces;
- do not synthesize `@` from spaces;
- treat bare Hebrew `ש` as ambiguous;
- accept only shin/sin dot as Hebrew combining marks in the v0.1 conversion path; reject all other Hebrew combining marks;
- reject all Syriac combining marks/punctuation in v0.1 conversion;
- preserve valid explicit CAL code unchanged;
- plain shared Roman consonants pass through because conversion output is identical.

### `src/cal_mcp/server.py`

Register `cal_convert_to_code` as a structured-output MCP tool that calls only the pure local converter. Optional representation input uses the existing representation vocabulary. The tool must not access `ctx`, the shared HTTP client, or CAL.

Update server instructions so clients know to use the converter when they need CAL Roman code.

## Gate 3 — docs

Document in the smallest existing user-facing location(s):

- purpose and examples;
- supported representations;
- zero-network/local-only behavior;
- Hebrew shin/sin ambiguity rule;
- explicit rejection of unsupported vocalization/diacritics/editorial syntax;
- distinction between conversion and normal CAL queries, which already accept Unicode.

Do not claim complete transliteration of all CAL historical codes.

## Gate 4 — GREEN

Run full permanent CI and require both:

- deterministic/frozen environment GREEN;
- latest-compatible environment GREEN.

Existing normalization/query tests must remain unchanged and green. No live CAL workflow is needed because this feature is purely local.

## Gate 5 — exact-head logically independent adversarial review

Freeze the exact candidate SHA and review it skeptically against the research, issue, and actual patch. Challenge at least:

- whether every documented core consonant maps correctly;
- Hebrew final-letter handling;
- whether bare `ש` can be silently misencoded;
- whether any vowel/diacritic is silently dropped;
- Syriac punctuation/combining marks;
- accidental `@` inference;
- CAL-code pass-through validation and round trips;
- mixed-script and control handling;
- MCP schema stability and error surface;
- whether the local tool can accidentally instantiate/use the HTTP client;
- whether existing query normalization/request-count contracts changed;
- docs overclaiming beyond the supported subset.

Any blocker discovered in review requires a new regression RED before the fix, a fresh GREEN run, and a new exact-head review.

## Merge/release gate

After independent PASS, mark the PR ready and merge only the reviewed exact head. Then rebase/resolve any remaining release-blocking maintenance PR (currently #51/#50) as needed. `v0.1.0` remains blocked until both #52 and all other acknowledged release-blocking defects are merged and the final release-readiness audit passes.