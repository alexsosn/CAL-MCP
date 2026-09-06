# Issue #41 plan — fix current lexicon citation-count drift

**Plan date:** 2026-09-06

This ticket follows research → plan → fixture/test-only RED → minimal parser fix → full GREEN → logically independent exact-head review → review-regression RED/GREEN if needed → guarded merge.

## Frozen scope

Restore faithful parsing of the current CAL full-entry citation component for `br N` without changing the public MCP schema or request flow.

The existing strict rendered citation-count check remains an invariant. The fix must recover CAL's current semantic citation boundaries instead of weakening that check.

No MCP error-envelope change, lexicon crawl, fallback request, neighboring-entry probe, or public citation-model redesign is in scope.

## TDD RED gate

Before production changes, add a deliberately reduced current-shape fixture and regression tests.

### Reduced fixture

Add `tests/fixtures/cal/entry_br_current_citations.html` containing only:

- a recognizable `br N` header and one complete sense;
- a rendered `3 citations` marker;
- three current-style `span.cit-item` citation elements;
- `span.cit-sep` between the three items;
- one explicit unlinked `span.cit-ref-plain` reference;
- linked citation references;
- one visible default citation representation;
- at least one hidden alternate `span.cit-script` with `style="display:none"` containing a semicolon;
- a visible citation/translation whose content contains an internal semicolon.

The fixture is a semantic reduction of the 2026-09-06 `br N` markup, not an archived CAL page.

### Regression tests

Add a focused test module that:

1. exercises `LexiconLookupService.lookup("br", lemma_key="br N")` using the existing browse fixture plus the new current-shape entry fixture;
2. proves the public success path still performs exactly two CAL requests;
3. expects exactly three citations in CAL order;
4. expects the plain reference to be preserved as a reference with `url is None`;
5. expects internal visible semicolon punctuation to remain inside one citation;
6. proves hidden alternate-script text is absent from returned citation text;
7. includes a structurally current group whose rendered count disagrees with its citation items and asserts `LexiconParseError` still raises.

A valid RED requires install, Ruff lint, Ruff format check, and strict mypy green while pytest fails only because current production loses the current citation DOM semantics.

## Minimal implementation

Modify only the semantic extraction/citation parsing needed for the observed current component.

### Structural citation boundary

- Recognize `span.cit-sep` from CAL's current markup.
- Preserve it internally as a citation-boundary signal rather than ordinary punctuation text.
- `_parse_citations` / `_split_citation_segments` must prefer that structural signal when present.
- Retain the existing semicolon fallback for legacy/reduced markup with no structural separator marker.

### Hidden alternate citation scripts

- Ignore current `span.cit-script` subtrees only when the inline style explicitly declares `display:none`.
- Do not build a general CSS visibility engine.
- Visible/default `cit-script` content and `cit-xlat` text remain part of the returned citation.
- Hidden-subtree handling must be nesting-safe and must fail/cleanly terminate rather than leak hidden content into following lines.

### Plain references

- Recognize current `span.cit-ref-plain` as a semantic citation reference even though it has no href.
- Reuse the existing reference extraction path where practical.
- Preserve its rendered reference string and set `url=None`; never invent a CAL URL.

### Count integrity

Do not relax `_SenseBuilder.freeze()` citation-count equality. The regression fix succeeds only when semantic extraction again yields the number of citations CAL rendered.

## Compatibility checks

GREEN must retain:

- existing linked and mixed citation fixtures;
- legacy semicolon splitting when no `cit-sep` structure exists;
- citation-count mismatch/truncation failures;
- recursive sense parsing and current script/POS/dialect regressions;
- ignored global `style`/`script` behavior from issue #32;
- exactly two CAL requests for an exact successful lexicon lookup and one request for ambiguous/not-found lookup.

No public tool arguments, result fields, source URLs, cache namespace, or request count changes are planned.

## Documentation / research

Focused research is in `docs/research/issue-41-lexicon-citation-count-drift.md`; root research records the changed invariant as R-021.

Update `docs/tools/lexicon.md` only if the implementation changes a user-visible semantic claim. The intended result is already consistent with the documented promise to preserve unlinked citation fragments/references and fail on count mismatch, so no broad docs rewrite is expected.

## Test / GREEN gate

Require the normal deterministic offline suite:

```text
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy
pytest
```

Normal CI makes zero CAL requests.

## Implementation checkpoint

The valid test-only RED is commit `e2439ac792b50e866ef208a04cdbc0f5338a1de1`, CI run `34024538803`: install, Ruff lint, Ruff format, and strict mypy passed; pytest reported **376 passed / exactly 1 intended failure**, reproducing the current `br N` citation-count drift through `LexiconLookupService.lookup`.

The first helper-free implementation checkpoint `d4d36f98011e76e0e3cb9285053220ac10cf5d3f` kept static/type gates green but correctly failed pytest with two focused regressions: the final citation slice re-entered legacy semicolon splitting, so the happy path produced four citation pieces and a deliberately wrong rendered count of four accidentally matched. This was not accepted as GREEN.

The correction makes structural citation mode a property of the complete semantic citation line and carries that mode through every reference-delimited slice. Consequently, if CAL supplied any `cit-sep` boundary for the group, no slice may reactivate punctuation-only splitting; legacy semicolon fallback remains only for lines with no structural boundary signal at all.

The first corrected checkpoint then stopped at Ruff format before behavioral tests. The only subsequent change to production code is the exact formatting Ruff reported; no parser semantics changed. The current helper-free, Ruff-formatted branch head is the authoritative GREEN candidate to validate before adversarial review.

## Adversarial review gate

Freeze the exact final SHA and review from current-source and fail-closed boundaries, not from implementation history. Challenge specifically:

1. Does structural `cit-sep` take precedence without breaking legacy fixtures?
2. Can an internal semicolon still be misclassified as a citation boundary when current structural markers exist?
3. Can hidden alternate `cit-script` content leak through nested elements or malformed markup?
4. Is `cit-ref-plain` preserved without inventing a URL or swallowing its citation text?
5. Does the strict count guard still reject genuinely truncated/contradictory groups?
6. Are actual `<a>` links and their text still segmented correctly when multiple citations share a line/container?
7. Did the fix accidentally make CSS classes or current DOM layout part of the public contract?
8. Did request volume, cache identity, provenance, or MCP schemas change?

Any blocker found in review gets a focused review-regression RED, minimal fix, full GREEN, and fresh exact-head review.

## Merge gate

Merge only when research and plan predate production changes, the RED is valid, full CI is green, the exact head has a clean logically independent adversarial review, no helper workflow remains, and guarded merge pins the reviewed SHA.

## CAL access / load impact

Research is complete. It made three fixed requests to the single `br N` entry, with the final request using production's User-Agent to obtain the current full-entry representation. No further live CAL access is planned for implementation or CI; there was no neighboring-entry enumeration or traversal.
