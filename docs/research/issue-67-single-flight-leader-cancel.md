# Issue #67 research — isolate single-flight followers from leader cancellation

Date: 2026-09-07
Baseline: `main` at `f85611397e0a689523991e14eda9f4614cd09c02`

## Question

When identical CAL requests are coalesced, can cancellation of the caller that became the single-flight leader incorrectly cancel other independent callers that are only following the same upstream operation?

## Current implementation

`CalHttpClient.fetch()` uses a shared `asyncio.Future` per normalized request/cache key:

1. the first caller creates the Future, stores it in `_inflight`, and becomes leader;
2. later matching callers become followers and await `asyncio.shield(future)`;
3. the leader executes `_fetch_uncached()` directly, with no background task;
4. on normal success the leader sets the shared Future result;
5. on ordinary failure the leader sets the shared Future exception;
6. on `asyncio.CancelledError`, the leader currently calls `future.cancel()`;
7. the leader removes the map entry in `finally`.

This design correctly avoids hidden work: the upstream operation runs in the leader caller itself. It also correctly shields the shared Future from cancellation initiated by a follower.

The cancellation branch has a different effect. Cancelling the Future is observable by every follower. Those callers did not request cancellation, but awaiting the cancelled shared Future raises `CancelledError` for all of them.

## asyncio semantics

Python 3.11's `asyncio.shield()` documentation says that cancellation of the caller awaiting `shield()` does not cancel the shielded awaitable, but if the shielded awaitable "is cancelled by other means" then `shield()` is also cancelled. The `asyncio.Future` documentation says awaiting a cancelled Future raises `CancelledError`.

Sources, rechecked 2026-09-07:

- https://docs.python.org/3.11/library/asyncio-task.html#shielding-from-cancellation
- https://docs.python.org/3/library/asyncio-future.html

Therefore `shield()` only solves follower-initiated cancellation. It cannot isolate followers after the leader explicitly executes `future.cancel()`.

## Why this is a stability defect

Single-flight callers are independent higher-level requests that happen to share the same normalized CAL operation. One caller disappearing should not make another active caller look cancelled.

The current behavior is especially problematic because `CancelledError` has cancellation semantics rather than ordinary request-failure semantics. Higher layers may abort request scopes or suppress it as caller cancellation. The follower therefore receives the wrong reason for failure.

Simply allowing every follower to retry independently would be unsafe: a cancelled leader with many followers could turn one coalesced request into N replacement CAL requests. The replacement path must retain single-flight coordination.

## Desired boundary

Keep the no-background-work model. When a leader is cancelled:

- the leader itself must immediately propagate `CancelledError`;
- the shared in-flight marker must communicate "leader cancelled; this caller was not cancelled" without masquerading as successful/failed CAL content;
- an uncancelled follower should re-enter single-flight arbitration after the cancelled generation is removed/stale;
- exactly one surviving follower becomes replacement leader; the rest coalesce behind its new shared Future;
- if there are no followers, no replacement request occurs;
- if a follower itself is cancelled, its shielded await must still stop without cancelling the active leader/shared Future.

The cleanest representation is a private ordinary exception stored on the shared Future for leader cancellation, rather than cancelling the Future itself. Followers can catch that private sentinel and retry arbitration. The leader still raises its original `CancelledError` to its own caller. Because the sentinel is an ordinary internal exception and only followers receive it, the current caller's cancellation state remains distinguishable from shared-operation turnover.

A retry loop inside `fetch()` can then arbitrate again under `_inflight_guard`. It must not recurse unboundedly. Each iteration corresponds to a previous leader generation that actually got cancelled; no background request is created.

## Race considerations

The leader currently removes `_inflight[key]` in `finally` without awaiting. A follower awakened by the shared sentinel may run before or after that deletion.

A robust arbitration loop should treat a done shared Future carrying the private leader-cancelled sentinel as stale while holding `_inflight_guard`: if it is still the current map value, remove it and create/elect a fresh leader generation. This avoids immediately re-awaiting the same completed sentinel in a tight loop.

Multiple followers racing after leader cancellation still serialize through `_inflight_guard`, so one creates the replacement Future and all others follow it.

## Existing relevant coverage

`tests/test_http_policy_review_regressions.py` already proves:

- simultaneous identical requests are single-flight;
- a cancelled leader does not leave a completed/stale in-flight entry that suppresses a later call when cache is disabled.

It does **not** include an active independent follower at the moment the leader is cancelled, so it cannot detect cancellation propagation to that follower.

## Test strategy

Use only injected blocking transports; no CAL access.

1. **Two callers / leader cancelled**
   - first transport attempt blocks;
   - start leader then one identical follower;
   - cancel leader;
   - follower must not raise `CancelledError` and must become/await one replacement attempt;
   - release the replacement attempt and require follower success;
   - exactly two transport attempts total: cancelled original + one replacement.

2. **Multiple followers**
   - leader plus several followers on first blocked attempt;
   - cancel leader;
   - surviving followers must coalesce onto exactly one replacement attempt, not one each;
   - all followers receive the replacement result.

3. **Follower's own cancellation**
   - active leader remains blocked;
   - cancel one follower;
   - follower raises `CancelledError`;
   - leader/shared operation remains active and can complete;
   - no replacement/duplicate request occurs.

4. Preserve the existing cache-disabled stale-entry regression.

## Compatibility / non-goals

This change does not:

- alter normalized request identity;
- alter completed-result cache semantics;
- alter HTTP retry/backoff behavior;
- add background tasks or prefetch;
- alter endpoint services/parsers or the MCP schema;
- require CAL traffic.

## Research conclusion

Issue #67 is a real single-flight isolation defect. `asyncio.shield()` protects the shared Future from follower cancellation but cannot protect followers when the leader directly cancels that Future. The fix should use a private leader-cancelled signal plus bounded re-arbitration so surviving callers elect one replacement leader while the cancelled caller still terminates immediately.