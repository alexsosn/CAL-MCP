# Issue #52 plan — CPA/Syriac Unicode conversion edges

Date: 2026-09-07

## Goal

Close the final CPA/Syriac script-family gap in the CAL-code converter without inventing a separate CPA representation. Preserve the existing `syriac` representation and add only the researched Syriac-block characters whose CAL correspondence is deterministic or finitely ambiguous.

## Test-first gate

Add `tests/test_cpa_syriac_conversion.py` before production changes. A valid RED must keep Ruff lint/format and mypy GREEN and fail pytest only where the current Syriac converter lacks the researched behavior.

The tests must prove:

1. the attested CPAHor 407:3 fixture `ܕܝܢ` maps to `dyn` under `representation=syriac` / `strategy=syriac_to_cal_code`;
2. U+0716 `ܖ` returns ordered candidates `d`, `r` and one `CalCodeAmbiguity` at the correct input index;
3. six U+0716 characters exceed the shared 32-candidate ceiling and raise `ConversionExpansionError` rather than truncate;
4. U+0724 `ܤ` maps deterministically to `s`;
5. U+0727 `ܧ`, the CPA reversed pe / pi character, remains deterministic `P`;
6. U+071E `ܞ` remains fail-closed because direct current-CAL mapping evidence is absent;
7. the public `cal_convert_to_code` tool returns the structured ambiguity schema for U+0716 and performs zero network I/O.

Existing Syriac mark/punctuation rejection tests remain part of the full regression gate.

## Minimal implementation

In `src/cal_mcp/normalization.py` only:

- replace the scalar Syriac mapping with ordered CAL-code tuples;
- retain all existing researched consonant mappings as one-element tuples;
- add U+0716 as `("d", "r")`;
- add U+0724 as `("s",)`;
- retain U+0727 as `("P",)`;
- make `_convert_syriac_word()` return `CalCodeWordCandidates`, recording ambiguity metadata for multi-valued graphemes;
- expand candidates with the existing `_append_alternatives()` helper so the 32-candidate bound remains shared;
- leave U+071E, combining marks, punctuation, and unverified Syriac/Syriac-Supplement characters unsupported.

Do not add lexical or dialect inference and do not alter CAL request behavior.

## GREEN gate

Require both CI jobs (`deterministic` and `latest-compatible`) to pass Ruff, format, mypy, and the full pytest suite.

## After GREEN

Run the issue-wide documentation/acceptance audit. Any missing public contract documentation must itself go through a docs test-first RED before edits. Then synchronize with current `main`, obtain exact-head full CI, perform a logically independent adversarial review against issue #52 and repository policy, iterate on blockers, and only then mark PR #53 ready for merge.