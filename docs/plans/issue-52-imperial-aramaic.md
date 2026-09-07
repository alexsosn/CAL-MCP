# Issue #52 plan — Imperial Aramaic Unicode → CAL code

Date: 2026-09-07

## Goal

Add one narrowly scoped, deterministic dedicated-script conversion slice for Unicode Imperial Aramaic, backed by the committed research artifact and a citation-sized CAL fixture.

## TDD gate

Before production changes, add tests that require:

1. automatic detection of Imperial Aramaic input as `imperial_aramaic`;
2. exact table conversion for all 22 researched consonants to the documented CAL codes;
3. the attested TAD C1.1(Ahiqar) .139 fixture `𐡌𐡍 -> mn`;
4. one candidate per supported word and no ambiguity metadata;
5. explicit rejection of U+10857 section sign and U+10858 numeric one;
6. explicit rejection of mixed Imperial Aramaic + another script;
7. `cal_convert_to_code` structured output exposes the new representation/strategy without network access;
8. existing Hebrew/Syriac/transliteration/CAL-code tests remain unchanged.

Confirm RED because the representation, strategy, detector, validator, and mapping do not yet exist. Static gates must pass so the RED is behavioral.

## Minimal implementation

In `src/cal_mcp/normalization.py` only:

- add `InputRepresentation.IMPERIAL_ARAMAIC = "imperial_aramaic"`;
- add `CalCodeConversionStrategy.IMPERIAL_ARAMAIC_TO_CAL_CODE`;
- add a table for U+10840..U+10855 letters using the researched consonant-name correspondence;
- detect presence of researched Imperial Aramaic letters before generic unsupported-Unicode handling;
- reject mixed-script combinations;
- validate only the 22 supported letters plus existing script separators;
- convert each word deterministically to one candidate.

No lexicon/search changes should be needed because deterministic dedicated-script input should flow through the existing converter-backed lookup path and preserve prior request counts.

## Documentation / fixture record

Extend the existing conversion/lexicon user documentation with Imperial Aramaic as a supported consonantal script and record the TAD C1.1 fixture locator. Do not add copied CAL page content.

## Verification

Run full deterministic and latest-compatible CI. Expected suite count increases only by the new offline tests. No CAL traffic is allowed in normal CI.

After GREEN, do not merge or mark ready: continue the remaining script-by-script research gates required by #52.
