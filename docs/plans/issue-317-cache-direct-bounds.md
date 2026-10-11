# #317 — direct cache limit validation

Research commit `5b687ed` ([source](../research/issue-317-cache-direct-bounds.md)) precedes this plan.

1. **RED:** add focused pytest parameterizations to `tests/test_request_policy.py` demonstrating cache constructor rejects `NaN`, `+/-infinity`, boolean/non-numeric TTL, boolean, fractional, string and negative capacity before any cache operation. Include valid `ttl_seconds=2.5` and `max_entries=0` to guard supported behavior. Observe RED in GitHub Actions with only the added tests.
2. **GREEN:** validate `type(max_entries) is int` and nonnegative. Validate TTL as real int/float excluding bool, finite and positive via `math.isfinite`. Raise deliberate `ValueError` for rejected values; do not modify `CalClientConfig`.
3. Confirm existing fake-clock TTL/provenance/LRU tests still pass; both full GitHub Actions CI matrices must pass from exact head.
4. Separate logically independent adversarial review based on the complete diff, existing cache semantics and actual RED/GREEN job logs; check that no user-facing CAL contract or request budget changed.
5. Merge only after successful exact-head CI + independent accept. Check #262 remains open afterward. Zero CAL traffic.

Scope is deliberately confined to directly instantiated process-local memory cache.
