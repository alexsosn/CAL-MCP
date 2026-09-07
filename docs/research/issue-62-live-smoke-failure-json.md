# Issue #62 research — machine-readable live-smoke failures

Date: 2026-09-07
Baseline: `main` at `11051b529129bf6741939550fdada6158917de7f`

## Question

Can the release live-smoke CLI report a failed representative probe as a stable machine-readable record, including the CAL request budget already consumed, without changing probe behavior or the public MCP surface?

## Current implementation

`src/cal_mcp/live_smoke.py` already has a strong bounded execution contract:

- `MAX_CAL_REQUESTS = 9`;
- eight fixed representative `DEFAULT_SMOKE_CASES`;
- one `BudgetCalHttpClient` with concurrency 1, retries 0, and completed-result cache disabled;
- sequential case execution;
- `BudgetCalHttpClient.fetch()` increments `request_count` before each permitted CAL fetch and raises before a tenth fetch;
- `run_live_smoke()` wraps a case exception in `LiveSmokeFailure(case_name, category, cause)` while preserving cancellation;
- successful `_async_main()` prints JSON containing completed cases, request count, and maximum request count.

The current failure path is less explicit:

1. `LiveSmokeFailure` retains only `case_name`, `category`, and `cause`.
2. `run_live_smoke()` has the active `smoke_client.request_count` when it constructs that failure, but does not retain it.
3. `_async_main()` does not handle the failure.
4. `main()` calls `asyncio.run(_async_main())` without handling `LiveSmokeFailure`.
5. `python -m cal_mcp.live_smoke` therefore exits non-zero through an uncaught Python exception and traceback.

The exception text contains the case/category/cause, but there is no stable failure JSON and no consumed-request count in the failure object.

## Existing deterministic coverage

`tests/test_release_contract.py` already verifies:

- release version/artifact/workflow contracts;
- the fixed 9-request budget and eight cases;
- failure-category classification;
- safe smoke-client config;
- tenth-request rejection without incrementing beyond 9;
- programmatic `run_live_smoke()` wrapping a parser failure as `LiveSmokeFailure`.

It does not test CLI failure output or request-count retention on `LiveSmokeFailure`.

## Required boundary

The smallest safe change is internal to release-smoke diagnostics:

- extend `LiveSmokeFailure` with `request_count` captured from the active `BudgetCalHttpClient` at the case failure boundary;
- provide a deterministic failure dictionary containing:
  - `status: "failed"`;
  - `case`;
  - `category`;
  - human-readable `cause`;
  - `request_count`;
  - `max_cal_requests`;
- have `main()` catch only `LiveSmokeFailure`, write that JSON to stderr, and terminate with exit status 1 without an exception traceback;
- leave successful `_async_main()` output on stdout unchanged in meaning;
- let unrelated exceptions from `_async_main()` propagate normally, so programming/configuration bugs are not disguised as ordinary smoke failures;
- do not catch `KeyboardInterrupt`/`SystemExit`; `run_live_smoke()` already preserves `asyncio.CancelledError` rather than wrapping it.

## Request-count semantics

`request_count` is a safety-budget counter, not a claim that CAL returned a completed HTTP response. It counts each allowed `BudgetCalHttpClient.fetch()` invocation before delegation to the shared client. With smoke configuration retries disabled and cache disabled, each valid live smoke fetch corresponds to at most one transport attempt. The existing hard ceiling remains authoritative and is not changed by diagnostic reporting.

If a case fails before any fetch, the recorded count is 0. If a CAL-backed operation fails after its first fetch begins, the recorded count includes that fetch. A budget-exhaustion failure records 9 because the rejected tenth fetch does not increment the counter.

## Compatibility / non-goals

This work does not:

- add or remove smoke cases;
- increase CAL traffic or the request ceiling;
- alter retry/cache/concurrency policy;
- alter parsers or service calls;
- change successful smoke semantics;
- change the MCP server or public tool schemas;
- publish/tag the release;
- require a live CAL request.

The change is testable entirely with injected transport and monkeypatched async CLI execution.