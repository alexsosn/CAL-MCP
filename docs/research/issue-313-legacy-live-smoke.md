# Issue #313 — legacy direct live-smoke request policy

Evidence check: 2026-10-11, current `main` at merge commit `d4cf3dff`. All findings are source-level; **zero CAL network calls**.

## Competing smoke paths
- The supported v0.1 release workflow and manual installed-wheel test invoke `python -m cal_mcp.stdio_live_smoke`. Its actual transport attempts are capped at 25 inside the MCP child process, with 3-second pacing and a local rolling ceiling of eight per minute. Cross-case gaps are 60 seconds.
- `src/cal_mcp/live_smoke.py` is a second, importable and command-line executable legacy runner (`python -m cal_mcp.live_smoke`), with eight fixed CAL-backed service probes and `MAX_CAL_REQUESTS=9`. It does **not** occur in either `.github/workflows/release.yml` or `.github/workflows/live-smoke.yml`. Removing or changing it cannot waive installed-wheel release smoke.

## Confirmed implementation defect
- `BudgetCalHttpClient.__init__` explicitly passes `CalClientConfig(max_concurrency=1, max_retries=0, cache_enabled=False)`. Explicit configuration bypasses the **real-transport** safe defaults in `CalHttpClient.__init__`: `min_request_interval_seconds=3` and `max_cal_attempts_per_60s=8`. The direct path can issue all eight cases as fast as CAL responds, contrary to the observed upstream HTTP429 burden in #262.
- Its overridden `fetch` increments `request_count` before `super().fetch` validation, cache checks and actual request reservation, so malformed local input counts as CAL I/O. Reported totals can overstate actual starts.
- `classify_smoke_exception` maps locally raised `CalLocalRequestBudgetError` and `CalRateLimitCooldownError` to `harness` instead of backpressure/unavailability. These typed failures do not represent a broken runner.
- Each legacy case already fails the suite on its first exception and `max_retries=0` prevents transparent retries. The safety fix should preserve these.

## Design constraints
Use the existing `CalHttpClient` admission scheduler, per-process rolling quota, and `before_transport_attempt` hook. Count only admitted actual transport starts; no new request routes, crawling, background polling, or changes to frozen 36-tool MCP schemas. Keep the legacy smoke outside release/publication acceptance. An 8/60 cap is protective only and does not prove CAL accepts that rate. Test all behavior with synthetic transport/fake clock offline. Keep #262's true live 37-token gate open.
