# Issue #52 plan — deterministic dedicated-script lexicon lookup

Date: 2026-09-07

## Problem found by acceptance audit

The converter supports deterministic Imperial Aramaic, Palmyrene, Nabataean, Hatran, Samaritan, and Mandaic Unicode input, but `LexiconLookupService.lookup()` currently switches to CAL-code candidates only when `conversion.words` contains explicit ambiguity metadata. A deterministic word in one of those dedicated scripts therefore follows the legacy normalized-query path and would send the dedicated Unicode characters to the CAL lexicon browser even though the issue #52 research established that CAL's documented browser input representations are CAL code, Unicode transliteration, Hebrew, and Syriac.

`docs/research/issue-52-ambiguity-expansion.md` already requires conversion where it is needed to represent a script while preserving ordinary deterministic Hebrew/Syriac request behavior.

## Test-first gate

Add regression tests before production changes proving:

1. a deterministic Imperial Aramaic lookup uses its converted CAL-code browse prefix and can resolve an entry;
2. a deterministic Mandaic lookup uses its converted CAL-code browse prefix, including CAL-specific uppercase code where present;
3. a deterministic dedicated-script lookup still performs exactly one browse request and at most one selected-entry request;
4. ordinary deterministic Hebrew and Syriac lookup request-count/prefix behavior remains unchanged;
5. ambiguous dedicated scripts continue to use the existing bounded candidate fan-out rather than a second path.

A valid RED must keep Ruff lint/format and mypy GREEN and fail pytest only on the missing deterministic dedicated-script conversion behavior.

## Minimal implementation

In `src/cal_mcp/lexicon.py`:

- define the set of dedicated input representations that CAL-MCP must convert before lexicon browsing: Imperial Aramaic, Palmyrene, Nabataean, Hatran, Samaritan, and Mandaic;
- select the conversion-candidate path when either finite ambiguity exists **or** the detected conversion representation belongs to that dedicated set;
- preserve the legacy normalized-query path for deterministic CAL code, shared Roman, Unicode transliteration, Hebrew, and Syriac inputs;
- reuse `_conversion_query_candidates()`, prefix deduplication, candidate matching, the eight-prefix pre-I/O cap, and the one-entry-fetch selection flow unchanged.

Do not add new CAL endpoints, requests, morphology, ranking, or script inference.

## GREEN gate

Require both deterministic and latest-compatible CI jobs to pass Ruff, format, mypy, and the full offline pytest suite. Then resume the issue-wide documentation/final acceptance audit.