# Issue #297 — CAL local rolling transport budget: source audit

2026-10-11. Analysis uses checked-in code and existing #262 live evidence; **no new CAL network requests**.

## Evidence and boundaries

- The installed-wheel real Peshitta John 1:1–4 acceptance run 38083038703 made exactly nine successful CAL HTTP requests (chapter text plus token indices 0–7) then got HTTP 429 on attempt 10 (word index 8), despite minimum measured 3.002 s inter-start spacing. The 37-token zero-429 gate remains unmet. The actual upstream quota/window is unpublished/unknown, and the experiment cannot establish any sustainable rate.
- As of main 9dbd61f, `CalHttpClient._reserve_attempt` serializes reservations only when the minimum interval is positive, through `_pace_lock`; its only shared server budget is `min_request_interval_seconds=3.0` and the >=60-s **reactive** circuit breaker after a terminal CAL 429. The cache and single-flight short circuit occur earlier in `fetch`.
- The `before_transport_attempt` hook runs immediately after successful reservation in `_request_once`; smoke budget deliberately raises when its absolute count 25 would be exceeded, **before** real transport. A rolling-window limiter must preserve this count and must not claim a failed hook consumed a CAL start.
- The explicit smoke config currently has max_retries=0, max_concurrency=1, min interval=3 and smoke attempt cap25. Existing smoke expects 11-12 representative calls; a fail-fast local 8/min cap may block a full smoke run; that change must not be hidden or labelled a successful release gate.
- `errors.py` maps a real CAL 429 or cooldown after observing one to kind `upstream_http`. A locally exhausted policy cap with no CAL HTTP response must **not** reuse 429/status or claim upstream was reached.
- The current direct `CalClientConfig()` has interval=0, so additions should preserve offline deterministic injection and require explicit opt-in to rolling safety for programmatic calls. A bare `CalHttpClient()` uses real HTTP and should auto-enforce a safe local precaution.

## Design exploration

A leaky bucket or only 3-second spacing does not exclude a 10-request ~30s burst. An 8-attempt rolling 60-second local budget would have refused the observed tenth request (indeed the ninth) **locally**, with no additional CAL attempts. This is NOT an upstream CAL rate assertion; a CAL 429 could still arrive on any permitted request and continue activating the separate fail-closed cooldown.

A bounded deque recording timestamps of actual starts (including retries) is sufficient. Under one per-client asyncio lock, discard starts at or before `now - 60`; if eight remain, raise a local typed policy error and return a truthful wait estimate without calling transport. Capacity uses O(8) memory. Cached hits and single-flight followers never reach this path. The existing `before_transport_attempt` smoke hook must run before start bookkeeping. The interval<=0 path must still take the lock when a window cap is enabled to prevent concurrent over-admission.

This is a protective stage, **not** a release readiness claim. The live 37-token gate needs a separately justified CAL access strategy and a bounded acceptance design.
