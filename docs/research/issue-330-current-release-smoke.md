# Issue #330 — current release smoke coverage research

**Checked 2026-11-07 against main after merged #39 and #328; code inspection only, no new CAL traffic.**

## Concrete acceptance gap

The source package metadata now identifies `0.2.0.dev0`; `release_surface.CURRENT_PUBLIC_TOOLS` lists 37 tools, while the published `V01_PUBLIC_TOOLS` remains the immutable 36-tool v0.1.0 interface. `scripts/verify_release_artifact.py` correctly verifies the **current** tool schema in fresh installed wheel/sdist. A future tagged release also runs `python -m cal_mcp.stdio_live_smoke` against the exact tested wheel.

But `src/cal_mcp/stdio_live_smoke.py` currently runs only the fixed **12 cases / 11 CAL-backed calls** first reviewed for v0.1.0; its `DEFAULT_SMOKE_CASES`, `_REVIEWED_V01_SMOKE_IDENTITIES`, and `_complete_release_smoke_matrix` do not cover the post-v0.1 `cal_bibliography_recent()` operation. Its minimum actual CAL attempts remains 11. The entire existing suite could pass without a release-gating live test of the new scholarly operation, even though the package exposes it. This is a concrete release gate hole, not evidence that v0.1 release checks were insufficient for v0.1.

## Bounded upstream and prior acceptance evidence

Issue #39's single explicit installed-wheel CAL smoke [run 42310066016](https://github.com/alexsosn/CAL-MCP/actions/runs/42310066016) proved the new zero-argument tool returned a structured `CAL Recent Bibliography` page containing **126 nonempty records**, correct source URL and timezone-aware provenance, from **exactly one actual CAL transport attempt** with retries disabled. The inspected current CAL public listing presented 2021–2025 in Nov 2026. No raw CAL data was archived by the smoke. The new operation already respects the shared 2 MiB body cap, request pacing and 429 stop policy. Research needs no new live request.

The immutable v0.1 12-case reviewed identities appear in `_REVIEWED_V01_SMOKE_IDENTITIES`; the newer matrix may extend those with one explicit recent-bibliography identity while keeping the original tuple untouched. Preserve the existing 25-actual-attempt cap, sequential execution, no retries, and minimum 60-second waits between CAL-backed operations. The new case requires *one additional* CAL-backed start only when a caller explicitly triggers a future release/smoke. No normal CI CAL access, hidden traversal, or repeated recent-book year enumeration.

## Release-contract implications

The current 37-tool package should have a reviewed **13-case / 12 CAL-backed** release gate. Keep `_REVIEWED_V01_SMOKE_IDENTITIES` immutable for historical reference; add a distinct current reviewed tuple and fail closed if any case is renamed/deleted/reordered, the schema is missing/invalid, a new case returns an error, provenance is malformed, the recent listing has missing or empty citations, or the measured actual transport attempts are fewer than 12. An error or HTTP 429 must stop the run as with every other CAL-backed case. Work stays in release-smoke validation and offline tests/docs; publishing a new package version is a separately gated operation.

## Code and tests inspected

- `src/cal_mcp/stdio_live_smoke.py`: `DEFAULT_SMOKE_CASES`, `_has_representative_content`, `evaluate_smoke_cases`, `_REVIEWED_V01_SMOKE_IDENTITIES`, `_complete_release_smoke_matrix`.
- `src/cal_mcp/release_surface.py`: frozen v0.1 and current tool sets.
- `scripts/verify_release_artifact.py` and `.github/workflows/release.yml`: installed package verification and gated release smoke.
- `tests/test_smoke_release_matrix_completeness.py`, `tests/test_smoke_transport_count_floor.py`, `tests/test_stdio_live_smoke_runner.py`, `tests/test_release_contract.py`, `tests/test_stdio_live_smoke_content_invariants.py`: fixed count and content oracles.
- `docs/research/issue-39-recent-bibliography.md`: dated one-operation clean-wheel evidence.

No CAL data or HTML is needed in new test fixtures.
