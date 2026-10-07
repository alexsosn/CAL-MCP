# Issue #155 plan — separate CAL MT verse labels from Hebrew text

**Date:** 2026-10-08  
**Research:** `docs/research/issue-155-mt-verse-labels.md`

## Goal

Return only CAL's Masoretic Text in `mt_text` for both `cal_targum_parallel` and
`cal_syriac_peshitta_parallel`, while preserving support for the older clean span shape and
failing closed when CAL's coordinate-label structure becomes contradictory.

No public schema field is added.

## Evidence-backed parsing rule

Both route families already validate one page heading against the requested
book/chapter/verse. After validation, keep CAL's own displayed coordinate suffix from that heading
(for example `Gen 1:1`, `Ps 23:1`, or `Sam1 1:10`).

Preserve `<br>` boundaries inside script spans as internal line separators.

For the MT Hebrew span:

1. split only on those preserved `<br>` boundaries;
2. trim/normalize whitespace using the existing parser convention;
3. if no non-empty line ends in coordinate-like presentation metadata, preserve the legacy clean
   MT text unchanged;
4. if one line ends in the exact validated CAL coordinate, require every non-empty MT display line
   to end in that exact coordinate and strip that suffix from each line;
5. if a line ends in another coordinate-like suffix, if labeled and unlabeled lines are mixed, or
   if stripping leaves an empty MT line, fail closed with the route's parser-drift error;
6. join the cleaned MT lines with one space, preserving all Hebrew characters/punctuation.

Do not remove arbitrary Latin substrings, infer a coordinate from the Hebrew text, or normalize
vocalization/punctuation.

## Shared helper boundary

Use one small pure helper in `biblical.py` so Targum and Peshitta cannot diverge on the
line/suffix rule. The helper accepts the raw line-preserving script text plus the already validated
display coordinate and returns either the cleaned MT string or an explicit invalid result/exception
that each domain parser converts to its own `TargumParseError` / `SyriacParseError`.

The route-specific HTML parsers remain responsible for preserving `<br>` as an internal newline.
Other script/source text continues through existing whitespace normalization; no public line model
is introduced.

## TDD gate

### RED — commit before production changes

Pin current behavior with fixture-backed tests:

1. Targum current Ps 23:1 fixture:
   - current parser returns `... Ps 23:1`;
   - desired exact `mt_text` contains only the Hebrew MT and no `Ps 23:1`.
2. Peshitta current Gen 1:1 fixture:
   - desired exact `mt_text` joins its two Hebrew display lines;
   - neither repeated `Gen 1:1` survives;
   - the second Hebrew line remains separated rather than glued to the label.
3. Peshitta current Ps 23:1 fixture also strips `Ps 23:1`.
4. Existing legacy clean Targum Gen 1:1 fixture remains byte-for-semantic-text compatible.
5. Malformed structural cases fail closed:
   - one exact-labeled MT line followed by an unlabeled MT line;
   - one line carrying a different coordinate suffix;
   - a coordinate-only MT line after stripping;
   - coordinate-looking text embedded before the end of a line is not silently removed.

The RED must reach pytest with lint/format/mypy green and fail only because labels still leak or
malformed shapes are accepted.

### GREEN

Make only the minimum line-boundary/helper changes required by the RED.

Do not change:

- request construction;
- page-heading validation;
- Targum source-reading text;
- Peshitta Syriac text;
- chapter-link validation;
- result schemas.

## Documentation

Update:

- `docs/tools/targum.md`;
- `docs/tools/syriac.md`;
- `CHANGELOG.md`;
- R-062 only if implementation/live evidence changes the research conclusion.

Document that `mt_text` excludes CAL's repeated display coordinate labels.

## Validation

1. full offline CI in deterministic and latest-compatible matrices;
2. bounded installed-wheel/stdio live acceptance with exactly two explicit MCP calls:
   - `cal_targum_parallel(book="Gen", chapter=1, verse=1)`;
   - `cal_syriac_peshitta_parallel(book="Gen", chapter=1, verse=1)`;
3. assert both return `found`, contain Hebrew MT, contain no `Gen 1:1`, and retain the expected
   target-language reading;
4. exactly one CAL request per explicit tool call; no chapter-link follow-up;
5. remove any temporary live workflow and rerun workflow-free CI;
6. logically independent adversarial review of the exact final SHA before merge.

## Request/load impact

Production request volume is unchanged. Final acceptance is two sequential CAL requests with no
pagination or returned-link traversal.
