# Issue #336 — Legacy citation semicolons

Base: remote `main` at `6e47280`. Related structural parser: #41 / #43.

## Evidence and scope

The 2026-11-15 bounded recheck of
<https://cal.huc.edu/cal_entry_web.php?lemma=%29lh+N> still shows
`mˀlhˀ; snynˀ lkw` within a single BT Yom 9b(41) citation. Current HTML
uses structural citation markup; the saved local fixture is a composite legacy
compatibility case, not an exact current entry. Do not infer a general CAL
punctuation contract from that fixture. R-021's structural precedence remains.

Only change the legacy fallback: require whitespace on both sides of a semicolon
and split reference-delimited slices before trimming their boundary whitespace.
Keep structural parsing, strict count validation, public schemas, provenance,
and request policy intact. Whitespace-surrounded punctuation inside legacy text
is still ambiguous; structural markup is the authoritative boundary when present.

## Execution and validation

1. Restore the saved local fixture/tests without applying the production patch.
   Initial RED on current main: all five tests fail with citation-count mismatch.
2. Isolate Unicode/internal punctuation, inter-reference separators, plain/linked
   mixtures, structural precedence, and incorrect-count cases in focused tests.
   Verify the expanded test-only RED and commit it before production changes.
3. Apply the two small fallback changes; run focused citation tests, then the
   full offline Ruff lint/format, mypy and pytest suite.
4. Update lexicon user docs, fixture metadata and research with the compatibility
   boundary. Open a focused PR for #336; leave merge to a separate review.

## Load, provenance and rights

One exact-entry web recheck was requested; no neighboring entries or context
links were followed. All regression tests are offline. Runtime request count,
timeouts/retries/cache/pacing and result provenance remain unchanged. Retain only
minimal fixture fragments; CAL content rights remain upstream. No architecture
decision is needed for this internal parser correction.

## Validation record

- Test-only commit `24ddae3`: expanded focused run had eight intended failures
  (citation-count mismatches) and twelve passing controls on unchanged production code.
- With both fallback changes, the focused run passes all twenty cases.
- Full offline local validation: Ruff lint and format pass (559 Python files),
  mypy passes (28 source files), and pytest passes all 2,409 tests.
- The first full run had 2,408 passes and one stdio version mismatch caused by
  selecting a different installation from the shell path. Refreshing this checkout's
  editable install to `0.2.0.dev0` and putting `.venv/bin` first resolved it; no
  product/test workaround was introduced.
- Review state: implementation ready for PR review; no merge or release performed.
