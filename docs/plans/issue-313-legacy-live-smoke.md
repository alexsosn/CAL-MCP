# Issue #313 — safe legacy direct smoke execution

Research commit: `885b229` ([source evidence](../research/issue-313-legacy-live-smoke.md)). This plan precedes new code/tests.

1. **RED:** offline tests with a synthetic transport and injectable monotonic clock. Verify the legacy client selects real-path-equivalent 3s minimum pacing plus 8 transport starts per rolling 60s, eighth start succeeds but ninth is refused with no outbound I/O, and local rejections do not increment `request_count`. Independently require typed local admission and cooldown failures to classify as backpressure (`upstream`, the pre-existing smoke category) rather than `harness`. Confirm a true HTTP429 stops subsequent smoke cases.
2. Observe offline expected failures on the tests-only commit with Ruff/format/mypy otherwise green (test-first gate).
3. **GREEN:** keep exact eight fixed case operations and `MAX_CAL_REQUESTS=9`. Construct `CalClientConfig(min_request_interval_seconds=3.0,max_cal_attempts_per_60s=8,max_concurrency=1,max_retries=0,cache_enabled=False)`; use the existing `before_transport_attempt` to count real transport starts. Remove pre-validation fetch accounting; preserve the public `request_count` report. Allow clock/sleep injection solely for offline deterministic tests while retaining system defaults.
4. Document the legacy direct path as an optional/manual diagnostic, never the installed-wheel release gate. Full frozen + latest-compatible CI offline on the final SHA.
5. Exact-head skeptical independent review: assess real request count, rejection ordering, cooldown, safety of legacy CLI default, no hidden retries, error classification, and no release-contract change. Fix new issues test-first and re-run all gates before merging.

**No live CAL I/O in this issue.** #262's actual zero429 37-token proof is out of scope and remains unfulfilled.
