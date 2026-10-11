# Issue #291 — Cancellation of a pending short-hint CAL 429 retry
2026-10-11 — source-only research, **zero CAL requests**.

## Grounded failure sequence
In `src/cal_mcp/client.py::_request_with_retries`, an HTTP 429 with a trusted one-second `Retry-After` and a retry slot remaining sets the per-client cooldown to the *hint only* (`_set_rate_limit_cooldown(hint)`) then awaits `_sleep(hint)` before the retry. No `try/finally` or cancellation-specific correction protects that await. Python `asyncio.CancelledError` propagates from the pending logical call, and so the later terminal-429 branch (minimum 60 seconds) is never reached. A second, different uncached `fetch` request can pass `_reject_during_cooldown()` shortly after the hint expires and reach CAL.

This is a logically derived offline race, **not** another observation of CAL's service. #262/D-024 already documents empirical HTTP 429 even at 3 s/attempt (10th transport in run 38083038703), so cancellation of an incomplete retry should not silently discard protection after CAL has signalled backpressure.

## Constraints
Preserve the single permitted short Retry-After retry when it *successfully completes*; its subsequent success must not leave a 60-s latch (existing regression test). Keep the existing 60-second lower bound, validated hints, typed upstream vs local rejection, cache-hit bypass, retry attempt budget, and no cross-process claims. Do not add live upstream requests.

## Risk to check independently
Cancellation can occur at the retry sleep, but also after this sleep while waiting for a paced attempt. The latter is already checked at reservation and was not observed to release another outbound attempt. Verify that introducing protection at the sleep boundary neither swallows cancellation nor blocks legitimate successful retries.
