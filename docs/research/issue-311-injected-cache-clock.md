# Issue #311 — injected clock and cache TTL drift

2026-10-11 — static/offline source research; no CAL requests.

## Evidence
- `src/cal_mcp/client.py`: `CalHttpClient.__init__(clock=time.monotonic)` uses `self._clock` to schedule transport spacing, rate-limit cooldown, and rolling-window admission.
- The same constructor instantiates `MemoryResponseCache(max_entries=..., ttl_seconds=...)` **without a clock**, so the cache receives its unrelated default `time.monotonic`.
- `src/cal_mcp/request_policy.py`: `MemoryResponseCache.get` computes age with its own `_clock`, expiring only at `age >= ttl_seconds`.
- Production with the default clock generally sees equivalent elapsed time. Injected clocks (supported by `CalHttpClient` for deterministic request-policy tests) do not: advancing the client's fake monotonic clock leaves the cache on wall time.
- In the client, `fetch` checks cache **before** cooldown and transport admission. A wrongly unexpired cached result can therefore bypass a simulated protective cooldown and misrepresent data freshness.

## Constraint
Use exactly one supplied clock for all local monotonic policy state. Preserve the default production clock; no CAL endpoint changes, no additional automatic requests or background work. All verification offline. This fixes injected-clock behavior; it does **not** establish a safe real CAL quota or complete #262.
