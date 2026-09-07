# Issue #55 research — request-policy count runtime types

**Rechecked:** 2026-09-07

## Existing contract

Issue #2 established one bounded request-policy layer with configuration validated before CAL traffic. Its acceptance criteria require finite/tested concurrency, retry, cache, timeout, and backoff bounds. `docs/configuration.md` documents the count-valued settings as discrete bounds:

- maximum concurrency: `1–8`;
- retry count: `0–3`;
- cache entries: `0–4096`.

`CalClientConfig` is also used programmatically, so Python annotations alone do not enforce runtime values.

## Current implementation gap

`CalClientConfig.__post_init__` explicitly type-checks `max_response_bytes`:

```python
if isinstance(self.max_response_bytes, bool) or not isinstance(
    self.max_response_bytes, int
):
    raise ValueError(...)
```

The three other count-valued fields only receive numeric range comparisons:

```python
if not 1 <= self.max_concurrency <= 8: ...
if not 0 <= self.max_retries <= 3: ...
if not 0 <= self.cache_max_entries <= 4096: ...
```

Consequences under normal Python runtime semantics:

- `max_retries=1.5` passes construction, then the first request later fails in `range(self.config.max_retries + 1)` with `TypeError`;
- `max_concurrency=1.5` can reach `asyncio.Semaphore` as a fractional capacity rather than a discrete request count;
- `cache_max_entries=1.5` reaches `MemoryResponseCache` even though entry capacity is conceptually integral;
- `True`/`False` are instances of `int`, so booleans can silently act as count values unless rejected explicitly.

Strings fail during range comparison, but with Python's generic `TypeError` rather than a stable configuration `ValueError`. Thus invalid policy values are not consistently rejected at the configuration boundary.

## Required invariant

The three count-valued fields should follow the same runtime-type policy already used for response-byte count:

1. require `int`;
2. reject `bool` explicitly;
3. then apply the existing numeric bounds unchanged.

No coercion is appropriate. A float such as `2.0` should not be silently converted to integer because configuration validation should make caller mistakes explicit.

## Scope consequence

This is a constructor-validation correction only. It does not change:

- valid defaults;
- allowed integer ranges;
- retryable failure classes or retry count behavior;
- backoff behavior (#50 owns the independent backoff-ceiling issue);
- concurrency semantics for valid integers;
- cache behavior for valid integers;
- HTTP requests, MCP schemas, or CAL load.

All evidence is local and deterministic; no CAL request is needed.

## Sources

- issue #2, `Implement CAL HTTP client and conservative request policy`
- `src/cal_mcp/client.py`
- `src/cal_mcp/request_policy.py`
- `docs/configuration.md`
- `wiki/testing.md` §6
