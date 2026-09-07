# Issue #57 research — remaining request-policy scalar runtime types

**Rechecked:** 2026-09-07
**Baseline:** `main` at `4c474c4836edb04947fdf860484388f247bc002a`

## Existing constructor boundary

`CalClientConfig` is the programmatic request-policy boundary. Issue #55 established that Python annotations alone are insufficient runtime validation and that invalid policy values should fail deterministically during configuration construction rather than surfacing later in request/cache/transport code.

Current discrete count fields now explicitly reject `bool` and non-`int` values. `max_response_bytes` follows the same fail-early pattern.

## Remaining scalar gaps

The remaining numeric policy fields are:

- `connect_timeout_seconds`
- `read_timeout_seconds`
- `total_timeout_seconds`
- `retry_backoff_seconds`
- `cache_ttl_seconds`

Their current validation calls `math.isfinite(value)` and numeric comparisons directly. This checks ranges for normal numbers but does not establish a stable runtime type contract:

- `bool` is accepted as numeric in Python; `True` therefore acts as `1` and can pass positive timeout/TTL checks;
- `False` currently passes the allowed zero `retry_backoff_seconds` check;
- strings and unrelated objects can fail with incidental `TypeError` from `math.isfinite` or comparisons instead of a field-specific configuration `ValueError`.

These settings are conceptually continuous numeric quantities, unlike count fields. Preserve ordinary Python `int` and `float` values when range-valid, while rejecting `bool` explicitly. No string-to-number coercion is appropriate.

## Boolean cache switch

`cache_enabled` is annotated `bool` but is not runtime validated. `CalHttpClient.__init__` later uses its truthiness:

```python
cache_entries = self.config.cache_max_entries if self.config.cache_enabled else 0
```

Thus values such as `1`, `"yes"`, or arbitrary truthy objects silently enable retention, while falsy non-booleans disable it. This should be an explicit boolean policy choice, not generic truthiness.

## User-Agent

`user_agent` is annotated `str`, but current validation immediately calls `.strip()`. An integer/list/etc. therefore leaks `AttributeError` rather than a stable configuration error. The existing semantic rule is only that the string must not be empty/whitespace; preserve that rule after adding the type guard.

## Required runtime contract

1. Numeric timeout/TTL/backoff fields accept only non-boolean `int` or `float` values, then retain existing finite/range checks and range messages.
2. `cache_enabled` accepts only actual `bool` values.
3. `user_agent` accepts only `str`, then retains the existing non-empty-after-strip rule.
4. Wrong runtime types raise stable field-specific `ValueError` during `CalClientConfig` construction.
5. No coercion is introduced.

## Compatibility boundary

This correction does not change valid defaults or valid request behavior. In particular:

- integral numeric values such as `5` remain valid for float-valued timeout settings;
- finite float values remain valid under existing ranges;
- retry backoff remains `0–1` seconds and retains the absolute runtime cap added by #50;
- cache TTL remains `>0` and `<=86400`;
- count fields and `max_response_bytes` are unchanged;
- MCP tools do not expose these low-level configuration fields.

## Test strategy

Use constructor-only table-driven tests. For each numeric scalar, prove representative `bool`, string, and unrelated-object values fail with the intended type error before any client is constructed. Separately pin valid `int`/`float` values and the existing finite/range error messages.

For `cache_enabled`, reject integer/string stand-ins and accept both booleans. For `user_agent`, reject non-strings, retain whitespace-only rejection, and accept an ordinary non-empty string.

All tests are offline; no injected transport or CAL access is required.

## Sources

- `src/cal_mcp/client.py`
- `docs/configuration.md`
- `wiki/testing.md` §6
- issue #2 request-policy contract
- issue #55 / PR #56 constructor runtime-type precedent
- issue #50 / PR #51 retry-backoff contract
