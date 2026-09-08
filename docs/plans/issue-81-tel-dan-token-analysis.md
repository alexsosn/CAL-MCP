# Issue #81 plan — current CAL empty token-analysis state

Date: 2026-09-08
Baseline: `main` at `591d80cef54187efdbf74fdb5fbaaa21c8f108e1`
Research: `docs/research/issue-81-tel-dan-token-analysis.md`

## Goal

Make current CAL token-analysis responses for valid Tel Dan positions return the existing structured empty-analysis result instead of a generic parser failure, without broadening the public API or weakening fail-closed drift detection.

## Invariants

- `cal_token_analysis(coordinate, word_index)` still makes exactly one GET to `getlex.php`.
- Existing analyzed-token parsing and candidate order remain unchanged.
- Existing legacy `There is no data for this word` handling remains unchanged.
- The current CAL phrase `unrecognizable query or no such lemma found` is recognized only as a complete empty-analysis state when exactly one standard result marker is present and no lemma-entry link exists.
- A page mixing the new empty-state phrase with a lemma-entry path fails closed.
- A page containing the new phrase without the unique standard result marker fails closed.
- Unexplained marker-only pages remain parser drift; absence of candidates alone is not enough to infer `NOT_FOUND`.
- Public status remains the existing `TokenAnalysisStatus.NOT_FOUND`; this ticket does not invent a finer reason taxonomy that CAL itself does not provide.
- Coordinate/index validation and provenance remain unchanged.

## TDD sequence

### 1. Reduced fixture

Add `tests/fixtures/cal/token_analysis_current_no_lemma.html` containing only the semantics needed by the parser:

- standard analysis marker;
- exact current W.D. sentence;
- return-to-text-browser link.

Do not archive the full live page.

### 2. Test-only RED

Extend token-analysis regressions to prove:

- the reduced current response parses to `candidates == ()`;
- service analysis of coordinate `1325007`, word index `1` returns `status=NOT_FOUND`, preserves coordinate/index/source provenance, and sends exactly one request;
- adding a valid lemma-entry link to a page that also has the new empty-state phrase raises `TokenAnalysisParseError`;
- removing the standard analysis marker while retaining the phrase raises `TokenAnalysisParseError`;
- existing analyzed-token, legacy-no-data, and marker-only drift tests remain green.

A valid RED must pass dependency installation, Ruff lint, Ruff format, and strict mypy in both CI matrices. Pytest failures must be confined to the new current-empty-state expectations.

### 3. Minimal implementation

Add one exact lowercase marker constant for CAL's current phrase. In `parse_token_analysis_page()`:

1. keep legacy no-data handling first and unchanged;
2. detect the current no-lemma phrase;
3. accept it only when there is exactly one standard analysis marker and no lemma path;
4. otherwise raise a dedicated `TokenAnalysisParseError` for inconsistent mixed/current-empty markup;
5. return an empty candidate page for the recognized state;
6. leave the ordinary candidate loop unchanged.

Do not special-case Tel Dan coordinates or word indexes.

### 4. GREEN gates

Run the full repository CI in both deterministic and latest-compatible dependency matrices:

- Ruff lint;
- Ruff format check;
- strict mypy;
- full pytest suite.

Only a run reaching and passing pytest counts as behavioral GREEN evidence.

### 5. Documentation

Update token-analysis tool documentation to explain the two CAL-recognized explicit empty-analysis shapes and the meaning of public `status="not_found"`: CAL exposed a recognized no-candidate state, without claiming a finer cause.

Document that unexplained/malformed successful pages continue to fail as parser drift.

### 6. Independent adversarial review

Review the exact final SHA independently, with emphasis on:

- accidental conversion of marker-only parser drift into `NOT_FOUND`;
- broad substring matching that could swallow future drift;
- accepting the new phrase when lemma links are also present;
- regression of legacy no-data handling;
- regression of multi-candidate order/lemma parsing;
- hidden extra requests or changed cache/request identity;
- provenance or public-schema changes not required by the ticket.

Post the review directly to the PR. Any blocker returns to implementation/test gates and requires a fresh review of the corrected exact SHA.

## Cleanup

Remove the temporary live-research workflow before the RED commit so TDD and normal PR CI are fully offline.

## Non-goals

- No typed cross-tool error envelope (#84).
- No new token-analysis status/reason enum.
- No bulk/interlinear token expansion (#82).
- No changes to text-page token indexing or coordinates.
- No special casing of issue-reported word indexes that current CAL now analyzes.
- No additional live CAL requests after research.
