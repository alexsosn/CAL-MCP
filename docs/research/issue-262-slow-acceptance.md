# Issue #262 — measured slow installed-wheel MCP acceptance

Observed **2026-10-11 UTC**, 20:38:13–21:15:43 (2026-10-12 at completion in Europe/Helsinki). Source `970ffa29531238b428677d6f6e0a14b974073333`; installed `cal-mcp` 0.1.0 wheel SHA-256 `f11b2ff6106d6b2b16bc122467c225ed8566582093421255a25a8d762e56c325`. The wheel's 28 installed Python files were byte-compared against its archive before the trial. The MCP server advertised version 0.1.0 and the frozen 36-tool registry from an unrelated working directory, without Agora or checkout imports.

## Decision and controls

The user requested completion of release readiness. Independent source review approved one invocation under D-024 after the failed three-second trial; the decision was written outside the repository before any live request and is recorded in the [plan](../plans/issue-262-rate-pacing.md#independently-reviewed-slow-acceptance-invocation-2026-10-11). A temporary launcher imported the installed implementation with concurrency one, retries zero, bounded caching enabled, three-second minimum start spacing and eight starts per rolling 60 seconds. A private hook at the real transport boundary denied attempt 39 before I/O. The caller additionally waited at least 60 monotonic seconds **after completion** of each CAL-backed operation. Offline tests verified counting, completion spacing, partial sleeps and terminal-error stopping; startup was verified without CAL traffic. No runner or enlarged normal smoke budget is shipped.

## Measured result

One `cal_text_page` call retrieved Peshitta John chapter 1, file `62043`, subtext `01`, page 1. Only the 37 ordered unique token handles returned for `620430101`–`620430104` were selected, then each was analyzed exactly once over MCP. Every result was `found`, matched its coordinate/index, had a usable candidate or opaque unlinked summary, and passed its advertised output schema and CAL source-URL/retrieval-timestamp checks.

- **37/37 token analyses passed**, zero HTTP 429, local refusals or parser drift.
- **38/38 actual CAL transport starts**, including the chapter page; no retries.
- Minimum gap from prior operation completion to next invocation: **60.000115 s**.
- Minimum actual transport-start gap: **60.537098 s**.
- Total elapsed time: **2250.121 s**, approximately **37.5 minutes**.

The [sanitized measurement](issue-262-slow-acceptance.json) preserves only operation identities, outcomes, provenance, timing/counts, configuration and artifact binding. It contains no CAL lexical or textual content. A repaired startup-only launcher failure made zero CAL attempts before this single real trial; no failed CAL trial was repeated.

## Interpretation and release scope

This meets issue #262's literal live criterion under the recorded caller waits. It does **not** show that default three-second calls complete a passage safely, identify CAL's quota, or justify automatic repeated trials. The earlier three-second failure remains valid evidence. Clients doing extended analysis should use these completion waits and stop on backpressure.

The later cache-constructor fix in PR #318 (`41d4468f317b61d674db3259484354ad5cac6086` on main) rejects invalid direct constructor arguments. Independent review verified that valid server/acceptance configurations, cache behavior, CAL transport/pacing, parsers and public schemas are unchanged; it does not require another CAL passage trial. Final offline/artifact validation still applies to the selected release commit. The fixed 12-case/25-attempt smoke and publisher binding remain separate issue #15 gates.
