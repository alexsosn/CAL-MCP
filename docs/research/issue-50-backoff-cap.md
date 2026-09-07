# Issue #50 research — clamp exponential retry backoff to the safety ceiling

Date: 2026-09-07
Baseline: `main` at `1d6292df06cc43a8a78c98ec37603d31dd489b25`

## Problem confirmed

The shared HTTP adapter already defines an absolute retry-backoff safety ceiling:

```python
_MAX_RETRY_BACKOFF_SECONDS = 1.0
```

`CalClientConfig.__post_init__` requires `retry_backoff_seconds` to be finite and between `0` and that ceiling. However, the runtime helper currently computes:

```python
delay = self.config.retry_backoff_seconds * (2**attempt)
```

with no clamp before `asyncio.sleep(delay)`.

The configuration validation therefore constrains only the *base* delay, while later retry attempts can exceed the repository's existing maximum-backoff constant.

Examples using currently valid configuration values:

- base `0.4`, `max_retries=3` schedules `0.4`, `0.8`, `1.6` seconds;
- base `1.0`, `max_retries=3` schedules `1.0`, `2.0`, `4.0` seconds.

The intended absolute ceiling is 1.0 second per retry sleep, so the first sequence should be `0.4`, `0.8`, `1.0` and the second should remain `1.0`, `1.0`, `1.0`.

## Existing retry paths

Both retry mechanisms share `_backoff(attempt)`:

1. retryable transport failures (`TimeoutError`, `httpx2.TimeoutException`, `httpx2.NetworkError`);
2. transient HTTP statuses (`500`, `502`, `503`, `504`).

Semantic 4xx responses and non-retryable transport errors bypass backoff because they are not retried. The existing bounded retry count remains `max_retries <= 3` and is not part of this fix.

## Existing test gap

`tests/test_http_client.py` verifies bounded request counts for retryable failures, but retry tests set `retry_backoff_seconds=0`. They therefore exercise retry branching without observing any scheduled delay and cannot detect exponential sleeps exceeding the safety ceiling.

The repository testing policy already requires bounded backoff. A regression test should make the scheduled delays observable without wall-clock sleeping.

## Deterministic test design

Use a scripted fake transport plus a monkeypatched `asyncio.sleep` in `cal_mcp.client` that records delays and returns immediately.

A representative configuration is:

```text
max_retries = 3
retry_backoff_seconds = 0.4
```

For three retryable failures followed by success, the expected sleep sequence is:

```text
[0.4, 0.8, 1.0]
```

Run the same assertion for:

- three transient `503` responses followed by HTTP 200;
- three retryable `TimeoutError`s followed by HTTP 200.

Also assert four transport attempts and successful parsing. This proves the cap without changing request-count semantics or introducing real waiting.

## Minimal implementation

Clamp the computed exponential delay in the shared helper:

```python
delay = min(
    self.config.retry_backoff_seconds * (2**attempt),
    _MAX_RETRY_BACKOFF_SECONDS,
)
```

This preserves exponential growth below the ceiling and applies identically to both retry paths because they already share `_backoff()`.

No additional finite/overflow handling is needed for `attempt`: repository configuration caps `max_retries` at 3, so the exponent is tightly bounded.

## Timeout interaction

`total_timeout_seconds` currently bounds each individual transport attempt through `_request_once`; it is not an aggregate wall-clock budget for the full retry sequence. That is outside this issue's scope, but it makes a hard per-sleep backoff ceiling important for keeping retry latency conservative and reviewable.

## Contract impact

No public MCP schema/model/provenance/normalization/request-shape changes.

No changes to:

- retryable exception/status classification;
- maximum retry count;
- cache/single-flight behavior;
- concurrency;
- request timeout configuration;
- CAL request volume beyond preserving the existing request-count behavior.

## CAL/load impact

None. Research and tests use source inspection, fake transports, and monkeypatched sleep only. No CAL request is necessary.
