# Issue #50 plan — clamp exponential retry backoff

Date: 2026-09-07
Research: `docs/research/issue-50-backoff-cap.md`

## Scope freeze

Change only retry-delay calculation and its deterministic regression coverage. Preserve retryable status/exception classes, retry counts, request construction, timeouts, cache/single-flight behavior, concurrency, public MCP contracts, and CAL request volume.

No CAL live traffic is needed.

## Gate 1 — test-only RED

Add a parameterized async regression to `tests/test_http_client.py` that exercises the public `CalHttpClient.fetch()` retry path rather than calling `_backoff()` directly.

Use `CalClientConfig(max_retries=3, retry_backoff_seconds=0.4)` and monkeypatch `cal_mcp.client.asyncio.sleep` with an async recorder that does not actually wait.

Cover both shared retry branches:

1. three HTTP 503 responses followed by 200;
2. three `TimeoutError`s followed by 200.

For each case assert:

- fetch succeeds and parses the final response;
- exactly four transport requests occur;
- scheduled sleeps equal `[0.4, 0.8, 1.0]`.

Confirm RED on current production code because the third scheduled sleep is `1.6`, with static gates otherwise clean.

## Gate 2 — minimal implementation

Modify only `_backoff()` in `src/cal_mcp/client.py` so the exponential delay is clamped by `_MAX_RETRY_BACKOFF_SECONDS` before sleeping:

```python
delay = min(
    self.config.retry_backoff_seconds * (2**attempt),
    _MAX_RETRY_BACKOFF_SECONDS,
)
```

Do not change the existing `if delay > 0` behavior.

## Gate 3 — focused GREEN

Run the new regression together with existing HTTP/request-policy tests. Verify:

- both retry branches schedule the same bounded delays;
- retry counts remain unchanged;
- zero-backoff existing tests remain valid;
- semantic 4xx still does not retry.

## Gate 4 — full GREEN

Require the exact candidate head to pass both permanent CI jobs introduced by #18:

- deterministic constrained environment + exact-environment verifier + Ruff/format/mypy/pytest;
- latest-compatible broad-range environment + `pip check` + Ruff/format/mypy/pytest.

Expected suite count is baseline 402 plus two parameter cases = 404 tests.

## Gate 5 — logically independent adversarial review

Freeze the exact final SHA and re-evaluate from request-policy/stability boundaries. Challenge at least:

1. cap applies to both transient-status and transport-exception paths;
2. exponential growth below the ceiling is preserved;
3. zero base backoff still produces no sleep;
4. no retry count/status classification changes occurred;
5. max per-sleep delay cannot exceed the same constant validated by config;
6. cancellation/error propagation remains unchanged;
7. tests would fail if the clamp were removed or applied only to one retry branch;
8. no public schema/request/provenance/cache behavior changed;
9. no CAL traffic was added to CI.

Any blocker enters review-regression RED → minimal fix → full GREEN → fresh exact-head review.

## Merge

Merge only the exact independently reviewed GREEN head with an expected-head guard. `Closes #50` should close the maintenance ticket on merge.
