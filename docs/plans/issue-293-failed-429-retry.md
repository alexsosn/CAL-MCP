# Issue #293 — implementation plan
2026-10-11. Research: [failed 429 retry](../research/issue-293-failed-429-retry.md).

1. RED: fake-clock/fake-transport retry sequence `429 Retry-After: 1 -> 503`, `429 -> exhausted TimeoutError`, and `429 -> non-retryable HTTP status`, then a distinct uncached call after >1 second. The original operation must report its *actual terminal failure*, but the next must be suppressed as a typed locally generated HTTP 429. Prove RED on CI with existing tests otherwise green. Retain a passing successful-short-hint-retry baseline.
2. GREEN: make all terminal exits from `_request_with_retries` after a previous short-hint 429 establish at least 60 seconds of per-client monotonic protection. Keep normal retry, pacing, cache and no-extra-transport semantics. Prefer a small shared guard over duplicating hard-to-audit state transitions.
3. Run frozen and latest-compatible CI offline, use an independent exact-SHA adversarial review to check all terminal paths, cancellation regression #291, and no fabricated source URL for subsequent local 429.
4. Update configuration guidance and D-024 clarification, close #293 only after merge. #262 live 37-token acceptance and #15 publication remain blocked.

No live CAL requests, no additional retry budget, no new MCP tool/contract.
