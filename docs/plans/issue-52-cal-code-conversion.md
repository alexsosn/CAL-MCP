# Issue #52 plan — deterministic Aramaic/Unicode → CAL code conversion

Date: 2026-09-07

## Goal

Add a local, explicit `cal_convert_to_code` MCP capability for the v0.1 contract without changing existing live-query normalization behavior or CAL request volume.

Research gate: `docs/research/issue-52-cal-code-conversion.md`.

This plan supersedes the initial Hebrew/Syriac-only implementation scope after corpus/script inventory showed that CAL also covers corpus families with dedicated Unicode scripts (Imperial Aramaic, Palmyrene, Nabataean, Hatran, Samaritan, Mandaic, plus CPA under Syriac). Existing implementation work completed under the earlier research remains valid only for the already-researched subset; no additional script mapping may be implemented until its evidence/test gate below is complete.

## Gate 1 — script inventory before new implementation

For every candidate dedicated Unicode script relevant to a CAL corpus family:

1. verify the Unicode block/character inventory from Unicode;
2. verify the CAL corpus/dialect exists and select one or more tiny attested words/sequences;
3. establish the exact CAL Roman-code correspondence from CAL's own displayed Roman/transliteration data;
4. document extra letters, combining marks, punctuation, or ambiguous values;
5. classify the script as:
   - supported deterministic mapping for v0.1; or
   - explicitly unsupported with a concrete reason.

Candidate inventory to resolve:

- Imperial Aramaic;
- Palmyrene;
- Nabataean;
- Hatran;
- Samaritan;
- Mandaic;
- CPA/Syriac;
- Hebrew-script Jewish Aramaic;
- any additional CAL corpus family whose ordinary source script has a dedicated Unicode block and a deterministic CAL-code mapping.

Do not add Elymaic/Manichaean/etc. merely because Unicode has a block; require actual CAL relevance first.

## Gate 2 — corpus-derived fixtures

Build a tiny offline fixture set from CAL itself. For each supported script family, store only enough data for deterministic regression tests:

- dialect/corpus family;
- CAL locator (text ID, coordinate, or stable entry URL);
- retrieval date;
- short attested CAL Roman/transliteration form;
- corresponding Unicode-script form used as input;
- expected CAL code.

The fixtures must be ordinary short scholarly quotations, never a corpus dump. No test should access CAL live.

## Gate 3 — test-first RED for expanded scope

Before implementing each newly supported script, add focused tests that fail because the mapping is absent.

### Pure conversion tests

`tests/test_cal_code_conversion.py` must cover:

1. Unicode scholarly transliteration exact mapping;
2. Hebrew consonants/finals, `שׁ` vs `שׂ`, bare `ש` ambiguity;
3. Syriac consonants and fail-closed marks;
4. every additionally supported dedicated script with:
   - first/middle/last alphabet-edge mapping cases;
   - at least one attested corpus-derived fixture;
   - rejection of unsupported marks/punctuation;
5. Mandaic-specific extra letters/codes separately rather than pretending it is a 22-letter Aramaic alphabet if CAL documents additional distinctions;
6. valid CAL/shared-Roman pass-through;
7. supported round trips where bijective;
8. mixed-script/control/unsupported Unicode failures.

A valid RED must reach behavioral pytest failures. Formatting/lint-only failures do not count.

### MCP contract tests

Require:

- public tool `cal_convert_to_code` exists;
- input schema contains `value` and optional `representation` only;
- representation enum includes every supported input script;
- structured result contains `original`, `cal_code`, `representation`, `strategy`;
- calling the tool is local-only and opens no socket / creates no CAL request.

## Gate 4 — minimal implementation

### `src/cal_mcp/normalization.py`

Add or extend only table-driven deterministic conversion machinery proven by RED tests:

- explicit representation enum values for supported Unicode scripts;
- transformation strategy values;
- frozen/slotted conversion result;
- explicit per-script code tables;
- `convert_to_cal_code(value, *, representation=None)`.

Rules:

- do not modify `normalize_query()` semantics unless a separate regression proves that is required;
- trim only ordinary ASCII boundary spaces;
- preserve internal spaces;
- never infer CAL `@` from whitespace;
- never strip combining marks silently;
- reject ambiguities rather than infer phonology or historical spelling;
- preserve explicit valid CAL code unchanged;
- script detection must be based on Unicode ranges/characters, not dialect guessing.

### `src/cal_mcp/server.py`

Register `cal_convert_to_code` as structured output and keep it independent of `Context`, `CalHttpClient`, or any CAL request.

Update server instructions to advertise the converter as a local helper, not a live CAL operation.

## Gate 5 — docs

Document:

- supported representations/scripts;
- representative corpus-derived examples;
- zero-network behavior;
- explicit ambiguity/rejection policy;
- distinction between script conversion and CAL query normalization;
- exact unsupported scripts/marks and why.

Do not claim complete coverage of every historical Aramaic writing system unless the inventory actually proves it.

## Gate 6 — GREEN

Require both permanent CI jobs GREEN:

- deterministic/frozen;
- latest-compatible.

Existing normalization/query/request-count contracts must remain green. No live CAL CI is required for this local feature.

## Gate 7 — exact-head logically independent adversarial review

Freeze the exact candidate SHA and challenge at least:

- completeness of the CAL corpus/script inventory;
- correctness of every per-script alphabet table;
- whether any script was omitted merely because CAL normalizes its display to Hebrew/Syriac;
- whether corpus fixtures truly correspond to attested CAL forms;
- Mandaic extra-letter handling;
- Hebrew shin/sin ambiguity;
- combining-mark/punctuation loss;
- mixed-script detection;
- accidental `@` inference;
- round-trip validity claims;
- MCP schema/error surface/local-only behavior;
- regressions to existing query normalization/request counts;
- documentation overclaiming.

Any blocker requires a new regression RED, fix, GREEN, and fresh exact-head review.

## Merge/release gate

After independent PASS, mark the PR ready and merge only the reviewed exact head. Then resolve remaining release-blocking maintenance PRs (currently #51/#50) against the new main. `v0.1.0` remains blocked until #52, #50, and the final release-readiness audit all pass.