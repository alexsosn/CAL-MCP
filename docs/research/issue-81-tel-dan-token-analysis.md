# Issue #81 research — current Tel Dan empty token-analysis state

Date: 2026-09-08
Baseline: `main` at `591d80cef54187efdbf74fdb5fbaaa21c8f108e1`

## Reported failure

`cal_token_analysis` raises a generic tool execution error for some token positions that are valid links on CAL text pages. The existing adapter already has a structured `TokenAnalysisStatus.NOT_FOUND`, but the parser recognizes only CAL's older explicit sentence `There is no data for this word` as an empty analysis.

Issue #81 reported Tel Dan coordinate `1325007`, where word indexes 1–3 failed while neighboring positions resolved.

## Current CAL evidence

Two bounded branch-only research runs made four fixed GET requests total on 2026-09-08. No returned lemma/text link was followed.

The first run requested exactly:

- `getlex.php?coord=1325007&word=0`
- `getlex.php?coord=1325007&word=1`
- `getlex.php?coord=1325007&word=2`

All returned HTTP 200 and `text/html; charset=UTF-8`.

### Word 0 — ordinary analyzed token

CAL returned its normal analysis marker:

```text
Click on a headword to see a complete lexicon entry
```

and a `oneentry.php` lemma link for `rkb, rkbˀ ... chariotry`.

### Word 2 — currently analyzed

Contrary to the earlier issue reproduction, current CAL now returns two lemma links for word 2:

- `w_ ... and, also`
- `ˀlp ... thousand`

This means the bug should not hard-code specific Tel Dan word indexes as empty. The adapter must follow the semantics CAL returns for each request.

### Word 1 — explicit current empty-analysis state

Word 1 returned the normal analysis marker, no `oneentry.php` / `cal_entry_web.php` lemma link, and not the legacy `There is no data for this word` phrase.

A fourth fixed GET inspected its complete semantic line sequence. The relevant lines are:

```text
Click on a headword to see a complete lexicon entry
| W.D. "unrecognizable query or no such lemma found"
← Return to the Text Browser ·
```

The response contains exactly one normal result marker and no lemma-entry link. The middle line is therefore CAL's current explicit no-lemma/empty-analysis state for this valid token position.

## Root cause

`parse_token_analysis_page()` currently does the following:

1. recognizes the legacy no-data phrase before candidate parsing;
2. otherwise requires exactly one analysis marker;
3. expects the line after that marker to begin a two-line candidate pair;
4. when the following content is not a lemma candidate and no candidate has yet been parsed, raises `TokenAnalysisParseError("CAL token-analysis result marker is not followed by a candidate")`.

The current Tel Dan word-1 response reaches step 4. The public MCP layer therefore converts a semantically explicit CAL empty analysis into a generic execution failure.

## Smallest compatible repair

Keep the existing public schema, endpoint, request count, and `TokenAnalysisStatus.NOT_FOUND` state.

Recognize CAL's exact current phrase:

```text
unrecognizable query or no such lemma found
```

as a second explicit empty-analysis marker only when the page is internally consistent:

- exactly one normal token-analysis result marker is present;
- no lemma-entry path is present;
- the current empty-analysis phrase is present.

Return `TokenAnalysisPage(candidates=())` for that state. `TokenAnalysisService` already maps an empty candidate tuple to `status="not_found"` and preserves coordinate/word-index/source provenance.

Fail closed when the new phrase is mixed with lemma links or appears without the unique normal result marker. Do not generalize to arbitrary phrases containing words such as `unrecognizable`, `query`, `lemma`, or `not found`.

The older `There is no data for this word` contract remains unchanged: it is an explicit empty page that must not be mixed with analysis markup.

## Public semantics

`NOT_FOUND` means CAL returned a recognized explicit state with no lexical candidates for the requested coordinate/index. It does not assert whether the underlying reason is an unanalysed valid token, an otherwise unrecognized CAL query, or an absent lemma; CAL's current sentence itself conflates those cases.

Issue #84 owns any future richer typed error/empty-state taxonomy. This ticket should remove the generic execution failure without inventing a distinction CAL does not expose here.

## TDD target

Add a reduced fixture containing only:

- the unique analysis marker;
- the exact current W.D. no-lemma sentence;
- the return-to-text-browser link.

Before production changes, tests must prove:

- the new current state parses to zero candidates;
- `TokenAnalysisService.analyze("1325007", 1)` returns `status=not_found`, preserves the requested coordinate/index/provenance, and performs exactly one `getlex.php` request;
- mixing the current empty-state sentence with any lemma-entry link fails closed;
- the current empty-state sentence without the unique analysis marker fails closed;
- existing analyzed, legacy no-data, and unexplained marker-only fixtures retain their current behavior.

A valid RED requires both CI matrices to pass dependency setup, Ruff lint, Ruff format, and strict mypy, with pytest failures confined to the new explicit-empty-state expectations.

## CAL load and cleanup

Research used four GETs total, all for the fixed Tel Dan coordinate `1325007`: word 0 once, word 1 twice, and word 2 once. Each response was capped at 512 KiB with a 15-second timeout. No lemma link, text page, catalogue, or additional token position was followed.

The temporary branch-only research workflow is removed before TDD. Normal CI remains offline.

## Evidence

- issue #81 reproduction;
- research workflow runs `34244503096` and `34244620672`;
- current `src/cal_mcp/token_analysis.py` on the baseline above;
- existing `tests/test_token_analysis.py` contracts.
