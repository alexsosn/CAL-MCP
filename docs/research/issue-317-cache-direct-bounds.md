# #317 — direct cache constructor admits nonfinite lifetime

Source inspection on 2026-10-11, before any change. No CAL HTTP traffic.

- `src/cal_mcp/request_policy.py`: `MemoryResponseCache.__init__` only checks `max_entries < 0` and `ttl_seconds <= 0`. NaN compares false for both `<= 0` and `age >= ttl_seconds`, so a direct cache with NaN TTL **never expires**, contrary to its documented TTL guarantee. Positive infinity also has no expiry; negative infinity is rejected by the old lower bound. Fractional `max_entries`, booleans, and type-confused values evade intended integer count semantics (or leak native TypeError rather than explicit validation).
- `src/cal_mcp/client.py` `CalClientConfig.__post_init__` validates finite positive TTL and integral cache capacity, and limits cache TTL to 86400s / max entries to 4096. `CalHttpClient` always constructs `MemoryResponseCache` through validated config. Thus normal shipped server defaults are already guarded; defect is in the reusable direct cache primitive and any future direct caller.
- `tests/test_request_policy.py` covers LRU, TTL, disabled zero-capacity, provenance preservation and a small invalid set: negative count, zero/negative TTL.
- Existing issue search found no open issue/PR addressing direct constructor finite/type validation.

**Scope:** reject NaN, infinity, bool, non-numeric TTL, bool/fractional/nonintegral capacity at cache boundary without adding any network traffic or changed API schema. Preserve valid zero and positive integer capacities and valid finite positive numeric TTL. Do not create an extra globally arbitrary upper bound inconsistent with the existing direct-cache API.
