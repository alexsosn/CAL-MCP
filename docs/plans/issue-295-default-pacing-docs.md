# Issue #295 — Plan: enforce truthful pacing documentation

Source evidence: [issue #295 research](../research/issue-295-default-pacing-docs.md).

1. RED: add a zero-CAL-request test comparing actual `CalHttpClient()` and `CalHttpClient(transport=fake)` and `CalHttpClient(config=CalClientConfig(), transport=fake)` effective intervals against documented exact distinctions. Enforce 3 seconds for the real default and zero only for explicit/unconnected offline paths; guard against stale one-second prose. CI must pass lint/format/type gates and then fail only the new docs assertions.
2. GREEN: update `docs/configuration.md` table and prose and correct D-024's present-tense claim about direct clients. Keep the historical notes about one-second experimental pacing and live 429 measurement, and clarify that passing 3-second spacing does **not** prove a safe CAL rate.
3. Run both deterministic and latest-compatible full offline CI. Review the exact diff independently against source and past CAL evidence, especially that no new code or unsafe live defaults are introduced. Correct review findings before merge.
4. No real CAL requests, no new tool, no changed request counts, no publishing. #262 still blocks v0.1 acceptance.
