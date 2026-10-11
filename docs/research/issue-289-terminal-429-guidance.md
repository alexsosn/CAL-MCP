# Issue #289 — first 429 error can misreport the enforced wait

2026-10-11; verified against current `src/cal_mcp/client.py::_request_with_retries`, `src/cal_mcp/errors.py::classify_public_tool_error`, and offline fake-clock regressions `tests/test_cal_rate_limit_circuit_breaker.py`.

The client sets a **minimum 60-second** monotonic local cooldown for a terminal HTTP 429, or longer when CAL supplies a valid longer Retry-After. But it raises `CalUpstreamError(status_code=429, retry_after_seconds=hint)` without the effective client cooldown. The public MCP classifier displays `Retry-After 1 seconds` for hint=1 even when the local client will reject uncached operations for 60 seconds. For a missing/malformed hint, the first error gives no wait duration at all. Agents following the first message can immediately retry during locally enforced suppression.

This is an attribution bug, **not** evidence that CAL's true request quota is 60 seconds. The message must distinguish the server's header from the locally enforced cooldown and avoid inventing a cooldown for independently constructed `CalUpstreamError` instances. For deadline-canceled 429 retry attempts, `_request_with_retries` rethrows an already constructed `CalUpstreamError`; the effective duration must be attached there as well.

Proposal: additive optional `cooldown_seconds` metadata inside `CalUpstreamError`, set at the two existing cooldown sites, rendered in a bounded public message; no new public JSON fields, no changed interval/attempt count, no 429 traffic. Preserve the original `retry_after_seconds` to distinguish source and policy. The source's 10th-request 429 at three-second spacing (#262) is already sufficient evidence not to run another live probe.
