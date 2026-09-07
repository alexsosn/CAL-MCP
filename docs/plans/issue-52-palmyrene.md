# Issue #52 plan — Palmyrene Unicode → CAL code

Date: 2026-09-07

## Goal

Add one deterministic Palmyrene Unicode conversion slice, backed by the committed script-specific research and a citation-sized CAL fixture.

## TDD gate

Before production changes, add tests requiring:

1. automatic detection as `palmyrene`;
2. exact character-identity conversion for all researched Palmyrene letters U+10860–U+10876;
3. both FINAL NUN and NUN map deterministically to `n`;
4. PAT992 fixture `𐡳𐡯𐡬 -> qsm`;
5. one candidate per word and no ambiguity metadata;
6. explicit rejection of a fleuron and a number from the same Unicode block;
7. explicit rejection of mixed Palmyrene plus another detected script;
8. local-only `cal_convert_to_code` structured output exposes `palmyrene` / `palmyrene_to_cal_code`;
9. all existing conversion and lookup behavior remains unchanged.

Confirm a behavioral RED with Ruff/format/mypy GREEN before touching production.

## Minimal implementation

Change `src/cal_mcp/normalization.py` only:

- add `InputRepresentation.PALMYRENE`;
- add `CalCodeConversionStrategy.PALMYRENE_TO_CAL_CODE`;
- add the exact table from the research artifact;
- add Palmyrene-block detection to the existing mutually exclusive script detector;
- validate only researched letters plus existing separators;
- deterministically convert each Palmyrene word to one CAL candidate.

Do not introduce image/glyph inference for the historical daleth/resh palaeographic problem; typed Unicode DALETH and RESH are distinct inputs.

## Documentation

After GREEN, update user-facing conversion documentation to list Palmyrene and record the PAT992 fixture/provenance boundary. No CAL page copying.

## Verification

Run full deterministic and latest-compatible CI. Normal CI must perform no CAL traffic.

After GREEN, keep PR #53 draft and proceed to the next dedicated-script research gate.