# Issue #62 plan — machine-readable live-smoke failures

Date: 2026-09-07
Research prerequisite: `docs/research/issue-62-live-smoke-failure-json.md`

## Goal

Make failed release-smoke runs emit a stable JSON diagnostic with consumed request count while preserving the existing nine-request safety policy, case set, success output, and programmatic failure API.

## Gate 1 — behavior-first RED

Modify tests only.

Add deterministic tests in `tests/test_release_contract.py` proving:

1. A synthetic smoke case that consumes one allowed request and then raises a parser/drift error is wrapped as `LiveSmokeFailure` carrying `request_count == 1`.
2. CLI `main()` catches a synthetic `LiveSmokeFailure`, writes exactly one JSON object to stderr with `status`, `case`, `category`, `cause`, `request_count`, and `max_cal_requests`, and terminates with `SystemExit(1)` rather than propagating `LiveSmokeFailure`.
3. Unrelated exceptions from `_async_main()` are not converted to the normal failure JSON path.
4. Existing success/report/budget tests remain unchanged.

RED acceptance: install, Ruff lint, Ruff format, and strict mypy green; pytest failures limited to the missing request-count/failure-CLI behavior.

## Gate 2 — minimal implementation

Change only `src/cal_mcp/live_smoke.py` unless a documentation contract requires otherwise.

- Add `request_count: int` to `LiveSmokeFailure`.
- Capture `smoke_client.request_count` when `run_live_smoke()` wraps a case failure.
- Add a deterministic `to_dict()` or equivalent formatter for `LiveSmokeFailure` containing:
  - `status: "failed"`;
  - `case`;
  - `category`;
  - `cause` as `str(cause)`;
  - `request_count`;
  - `max_cal_requests`.
- In `main()`, catch only `LiveSmokeFailure`, serialize that dictionary with stable key ordering to stderr, and raise `SystemExit(1) from None`.
- Leave `_async_main()` success JSON behavior unchanged.
- Do not catch unrelated exceptions, `KeyboardInterrupt`, or `SystemExit`.

## Gate 3 — GREEN

Run normal CI in both deterministic/frozen and latest-compatible environments:

- dependency/install checks;
- Ruff lint;
- Ruff format;
- strict mypy;
- full pytest.

## Gate 4 — documentation

Update `wiki/testing.md` only if needed so live-smoke operator docs state the failure contract accurately: success JSON on stdout; classified failure JSON on stderr with consumed/max request counts; non-zero exit status; no traceback for expected `LiveSmokeFailure`.

Do not modify public tool docs or schema counts.

## Gate 5 — logically independent adversarial review

Review exact final SHA against issue, research, plan, whole diff, tests, current `main`, and CI. Challenge at least:

- accidentally swallowing unrelated harness bugs as ordinary smoke failures;
- cancellation/interrupt semantics;
- request count captured before vs after the failing fetch;
- budget-exhaustion count remaining exactly 9;
- success output moving to stderr or changing meaning;
- failure output leaking a traceback or becoming non-JSON;
- unstable/non-serializable cause values;
- altered case list, request ceiling, retries/cache/concurrency;
- public MCP schema changes;
- overlap with active converter PR #53.

Any code/behavior blocker requires a review-regression test RED, minimal fix, fresh full GREEN, and fresh exact-head review.

## Merge gate

Immediately before review and merge, refetch current `main` and PR head. If `main` has advanced, verify mergeability and rerun/reassess exact-head CI as needed. Merge only with `expected_head_sha` equal to the independently reviewed head.