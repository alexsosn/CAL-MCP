# Issue #67 plan — isolate followers from single-flight leader cancellation

Date: 2026-09-07
Research prerequisite: `docs/research/issue-67-single-flight-leader-cancel.md`

## Goal

Preserve single-flight request suppression while preventing cancellation of the caller that became leader from being misreported as cancellation of independent matching followers.

## Gate 1 — behavior-first RED

Modify tests only, preferably `tests/test_http_policy_review_regressions.py`.

Add deterministic injected-transport tests proving:

1. **Cancelled leader does not cancel one follower**
   - first identical call becomes leader and blocks in transport;
   - second identical call joins as follower;
   - cancel only the leader;
   - leader raises `asyncio.CancelledError`;
   - follower remains active, causes/joins exactly one replacement transport attempt, and returns its result;
   - total transport attempts: exactly 2.

2. **Many followers coalesce after leader cancellation**
   - leader + at least three identical followers join one blocked attempt;
   - cancel leader;
   - all followers remain active;
   - exactly one replacement attempt starts;
   - all followers receive the same replacement result;
   - total transport attempts: exactly 2, not 1 + follower count.

3. **Follower cancellation stays isolated**
   - leader active and blocked;
   - matching follower joins;
   - cancel follower only;
   - follower raises `CancelledError`;
   - leader continues and completes successfully after release;
   - only one transport attempt occurs.

Keep the existing cache-disabled stale-inflight cancellation regression.

RED acceptance: dependency/install, Ruff lint, Ruff format, and strict mypy GREEN; pytest failure limited to leader-cancellation propagation/replacement behavior. The follower-own-cancellation test may already be GREEN and serves as a preserved invariant.

## Gate 2 — minimal implementation

Change only `src/cal_mcp/client.py` unless documentation requires a narrow follow-up.

### Private turnover signal

Add a private ordinary exception, e.g. `_SingleFlightLeaderCancelled`, used only as the shared Future outcome when a leader caller is cancelled.

On leader `CancelledError`:

- do **not** call `future.cancel()`;
- if the shared Future is still pending, set the private turnover exception on it;
- immediately re-raise the leader's original `CancelledError` to the leader caller.

### Re-arbitration loop

Refactor the cache/inflight arbitration portion of `fetch()` into a bounded-by-events loop:

- validate request/key once;
- on each arbitration iteration, check completed cache before and inside `_inflight_guard` as today;
- if `_inflight[key]` refers to a done Future whose outcome is the private leader-cancelled signal, remove that stale generation while holding the guard;
- if no active Future remains, create a new Future and become replacement leader;
- otherwise await the active Future with `asyncio.shield()`;
- if that await raises the private turnover signal, loop to arbitrate again;
- do not catch the current task's own `CancelledError`, so follower cancellation still propagates immediately and shield still prevents it from cancelling the shared Future.

Avoid recursion and arbitrary retry counters. A loop iteration only follows an actual cancelled leader generation. With no surviving follower, no new request is started.

### Cleanup

Preserve existing leader cleanup and completed-result caching. Ensure leader `finally` only removes its own Future generation, never a replacement Future installed by a follower.

No new `asyncio.create_task()` or background work.

## Gate 3 — GREEN

Run full normal CI in deterministic/frozen and latest-compatible jobs:

- dependency/install checks;
- Ruff lint;
- Ruff format;
- strict mypy;
- full pytest.

No CAL access.

## Gate 4 — documentation

Update `docs/configuration.md` single-flight section to state the cancellation isolation contract:

- follower cancellation does not cancel leader/shared work;
- leader cancellation terminates that caller, while surviving independent followers re-elect one replacement leader and remain coalesced;
- no replacement request occurs without surviving demand;
- no background task is introduced.

Do not change endpoint/public-tool docs or schema count.

## Gate 5 — logically independent adversarial review

Review exact final SHA against issue #67, research, plan, whole diff, current `main`, CI, and relevant existing tests. Challenge at least:

- follower incorrectly inherits `CancelledError` from leader;
- own follower cancellation accidentally gets swallowed/retried;
- replacement creates one request per follower;
- stale cancelled generation causes a spin loop;
- original leader cleanup deletes a replacement Future;
- no-followers case accidentally starts background replacement work;
- ordinary parser/network/upstream exceptions accidentally trigger re-arbitration;
- cache-disabled later calls still work;
- completed cache behavior/provenance changes;
- request identity/retry/backoff/concurrency changes;
- overlap with draft converter PR #53;
- hidden background tasks or CAL access.

Any blocker requires review-regression TEST-ONLY RED, minimal fix, fresh full GREEN, and fresh exact-head adversarial review.

## Merge gate

Immediately before final review and merge:

1. refetch PR head and current `main`;
2. if `main` advanced, synchronize/reassess and rerun exact-head CI/review as required;
3. mark ready only after clean exact-head review;
4. guarded merge with `expected_head_sha` equal to the reviewed SHA;
5. verify issue #67 closes and merge is present on `main`.