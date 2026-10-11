# Issue #295 — Source audit: real CAL HTTP pacing versus documentation

Date: 2026-10-11. No CAL requests or corpus data collected.

- At merged main `eed5ac52`, `CalHttpClient.__init__` constructs `CalClientConfig(min_request_interval_seconds=3.0 if transport is None else 0.0)` when `config is None`.
- Therefore a plain `CalHttpClient()` using the actual `_Httpx2Transport` has 3-second attempt spacing. So does `server.app_lifespan` without smoke mode (`CalHttpClient()`).
- `CalHttpClient(transport=fake)` defaults to zero for offline testing; `CalHttpClient(config=CalClientConfig())` explicitly configures zero, even for real HTTP transport. A caller who explicitly overrides this config is responsible for conservative upstream pacing. The configuration class's zero default alone does **not** describe a plain real-transport client's effective default.
- `docs/configuration.md` still says direct clients get zero seconds in the table and a plain real-transport client gets one-second pacing in the prose. D-024 in `wiki/decisions.md` also retains one-second direct-client language. Both contradict the code and the explicit `tests/test_cal_rate_limit_policy.py::test_production_client_defaults_paced_and_injected_offline_transport_stays_fast`.
- Empirical #262: real CAL rejected a request on the tenth attempt even with >3.002s spacing. Neither 1 second nor 3 seconds may be advertised as a known CAL-accepted rate. Reaffirm that release/live acceptance stays blocked.

This ticket corrects documentation and enforces a deterministic docs/runtime sync test. It changes no transport behavior or CAL request volume.
