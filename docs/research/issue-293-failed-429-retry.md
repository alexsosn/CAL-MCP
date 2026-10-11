# Issue #293 — Missing terminal cooldown after failed 429 retry
2026-10-11, offline code and incident review; **zero CAL HTTP requests**.

D-024 documents a measured CAL HTTP 429 after nine successful Peshitta calls spaced ≥3 s (workflow 38083038703). The shared client retries a 429 **once** only when CAL supplies a trusted short positive Retry-After within its bounded budget. Until that retry completes, `src/cal_mcp/client.py::_request_with_retries` sets `_rate_limited_until` to the short hint (e.g. one second) and `rate_limit_retry_used=True`.

On the retry attempt, code paths for terminal `_TRANSIENT_STATUS_CODES`, an ordinary non-429 status (including 3xx), exhausted `_RETRYABLE_TRANSPORT_EXCEPTIONS`, and non-retryable `HTTPError/OSError` raise an exception without upgrading that short cooldown to the 60-second protection established for terminal 429. This is unlike a completed success (which has no 60-s latch) and unlike issue #291 cancellation hardening (which now retains a 60-s latch). A new distinct uncached operation could reach CAL when the initial one-second hint elapses, although the original CAL rate-limit signal never resolved in a successful retry.

This is a source-derived gap, not evidence that CAL publishes a one-second quota or any renewal policy. Later errors should keep their true classification and source metadata: a 503 remains a 503 for the failed original request; only new distinct calls during cooldown receive typed local 429 with `upstream_reached=false`.
