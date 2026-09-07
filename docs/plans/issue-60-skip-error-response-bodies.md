# Issue #60 plan — stop consuming rejected HTTP response bodies

Date: 2026-09-07
Research prerequisite: `docs/research/issue-60-skip-error-response-bodies.md`

## Goal

Reduce failed-request bandwidth and latency by closing production HTTPX2 response streams without body iteration for statuses >=300, while preserving the existing retry/status policy and every successful-response/body-size contract.

## Gate 1 — behavior-first RED

Add production-boundary tests using the existing HTTPX2 `MockTransport` and counting byte streams. Production code remains unchanged in this commit.

Required assertions:

1. Representative non-retry statuses (302, 404, 429):
   - exactly one upstream request even with retries configured;
   - typed `CalUpstreamError` preserves the status;
   - response body stream yields zero chunks;
   - response stream closes.
2. Representative transient 503 with one retry:
   - exactly two attempts;
   - neither failed response body stream yields a chunk;
   - both streams close;
   - final error remains `CalUpstreamError(503, ...)`.
3. Existing 2xx exact-limit and over-limit streaming tests remain unchanged and green after implementation.

RED acceptance: Ruff lint, Ruff format, and mypy green; pytest failures confined to the new non-success body-consumption assertions.

## Gate 2 — minimal implementation

Change only `_Httpx2Transport.__call__`:

- after entering `self._client.stream(...)`, if `response.status_code >= 300`, return `CalResponse` with `body=b""` and existing status/url/content-type/retrieval metadata;
- leave the existing 2xx chunk-size calculation, decoded-byte accumulation, size exception, and metadata unchanged;
- leave `_request_with_retries` untouched so retry/status policy has one owner.

Do not add configuration, public APIs, status-code changes, parser behavior, cache behavior, or live requests.

## Gate 3 — GREEN

Run normal PR CI in both environments:

- deterministic/frozen dependency environment;
- latest-compatible dependency environment;
- Ruff lint;
- Ruff format check;
- strict mypy;
- full pytest.

All existing tests plus the new regression tests must pass.

## Gate 4 — documentation

Update `docs/configuration.md` only if needed to state the observable request-layer guarantee accurately: non-success production responses are status-classified without consuming application response bodies, while 2xx decoded streaming remains size-bounded.

Do not change tool documentation or public schema counts.

## Gate 5 — logically independent adversarial review

Review the exact final SHA against the issue, research, plan, diff, tests, and current main. Challenge at least:

- accidentally treating 300 as success or moving the threshold;
- accidentally changing which 5xx statuses retry;
- retry attempts leaking unread streams/connections;
- redirects being followed or parsed;
- 4xx/429 acquiring retries;
- successful 2xx bodies being skipped or no longer size-limited;
- metadata/provenance timestamp or URL changes;
- injected/custom transport behavior changing;
- tests asserting only helper behavior rather than production `_Httpx2Transport` behavior;
- overlap with PR #53 or public 26-tool v0.1 schema changes.

Any blocker requires a test-first review-regression RED, minimal fix, fresh full GREEN, and fresh exact-head review.

## Merge gate

Immediately before review/ready/merge, refetch current main and PR head. If main has advanced, verify mergeability/current-main CI behavior and re-review any changed final SHA. Merge only with `expected_head_sha` matching the independently reviewed exact head.
