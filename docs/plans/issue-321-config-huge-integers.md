# #321 — config integer overflow validation plan

Research commit `661bac6` ([source](../research/issue-321-config-huge-integers.md)) precedes this plan.

1. **RED**: focused parameterized offline test instantiating `CalClientConfig` with one of six scalar attributes set to `10**1000`, expecting a deliberate `ValueError` with the field name rather than uncaught Python `OverflowError`. Test normal `0.5` and `1` positive scalar values, `0` for retry/interval and preserve existing NaN/inf and boolean tests.
2. Run tests-only branch CI: require actual expected failures in pytest with other gates (Ruff lint, Ruff format, mypy) clean. No CAL traffic.
3. **GREEN**: avoid broad refactor. Introduce an internal `_is_finite_number` (or similar) catching the `OverflowError` from `math.isfinite`, reusing it in the positive-timeout/TTL loop and retry/interval validators; preserve original diagnostics and numeric bounds.
4. Both full deterministic and latest-compatible GitHub Actions matrices must pass on the exact implementation SHA.
5. Independently rederive all affected constructor paths from source, verify no altered runtime transport defaults or public schemas, review RED/GREEN logs, and post exact-head adversarial ACCEPT before merge.
6. After merge check issue #262 remains open; close #321, leave PyPI release/Agora blocked. No live CAL requests.
