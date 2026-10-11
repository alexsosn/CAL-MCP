# Issue #303: Installed-wheel smoke acceptance must prove case coverage

Date: 2026-10-11. No live CAL network.

## Research

1. `src/cal_mcp/stdio_live_smoke.py` fixes 12 smoke cases, one local-only `cal_convert_to_code` and 11 CAL-backed operations; `evaluate_smoke_cases` executes known cases sequentially. Missing tools and failed dependent selectors append non-OK outcomes. Real HTTP429 or `local_rate_limit` terminates further calls to protect upstream. A list of outcomes is therefore **sometimes intentionally a prefix**.
2. `_run_live` passes that list through unchanged, plus a private shutdown report of the measured `actual_cal_transport_attempts` with hard max 25. The count file verifies the bounds, not whether all 12 cases were attempted. A fresh real subprocess with a complete CAL-backed matrix should have **at least one actual CAL transport**.
3. `main()` currently sets `successful = all(item.category == "ok" for item in outcomes)`. The empty tuple passes vacuously. A prefix of successful outcomes also passes. Duplicate, wrong-name, or misordered outcomes remain undetected. Consequently the release workflow's `needs: live-smoke` publish gate could accept incomplete coverage if a future refactor or tool short-circuit returns only a successful subset.
4. The existing `tests/test_stdio_live_smoke_runner.py::test_stdio_cli_reports_actual_attempts` stubs `_run_live` with a single synthetic `ok` case and asserts pass; it must be updated to simulate the **full fixed matrix**. Other `evaluate_smoke_cases` tests use intentionally partial custom case matrices and should remain unrestricted. Avoid coupling the generic evaluator to v0.1's case count.
5. Need fail-closed acceptance with `tuple(outcome.case for outcome in outcomes) == tuple(case.name for case in DEFAULT_SMOKE_CASES)`, all categories `ok`, matrix shape pinned by existing `test_release_contract.py`, at least one CAL attempt and no extra release check calls. Reject an empty or duplicate planned matrix itself; don't let both sides become empty and pass. A minimal expected 12 cases / 11 CAL-backed operations protects against a future accidental downsizing without a corresponding release-contract change.
6. Reporting must preserve sanitized per-case outcomes and counts, and mark incomplete/mismatched outcome matrices as a harness failure. A genuine upstream failure still fails without retry or additional CAL traffic; make it visually obvious to operators whether the failed release test was incomplete.

No publication, upstream claims or new CAL GETs. #262 remains a separate unmet 37-token zero-429 live gate.
