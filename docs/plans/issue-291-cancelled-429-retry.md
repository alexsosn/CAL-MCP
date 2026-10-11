# Plan — issue #291: retain cooldown on cancelled CAL 429 retry
2026-10-11. Source analysis in [research](../research/issue-291-cancelled-429-retry.md); downstream of #262/D-024.

1. **RED / deterministic:** new `tests/test_cancelled_429_retry_cooldown.py` exercises a fake CAL 429 (`Retry-After: 1`), event-controlled injected sleep, cancellation before retry dispatch, fake monotonic advance past the hint, and a second *different* uncached request. Assert cancellation propagates, exactly one real transport has occurred, and the next call raises `CalRateLimitCooldownError` until the full 60-second safety window expires. Verify public classification for that second call reports 429, `upstream_reached=false`.
2. **GREEN / narrow source fix:** when cancellation interrupts only the sleep after an actual short-hint 429, extend the current per-client cooldown to the D-024 minimum (or longer validated hint) before re-raising `CancelledError`. Do not change the regular success path or inject a background task.
3. **Regression + full CI:** existing `test_successful_short_hint_retry_does_not_leave_terminal_cooldown` and all deterministic checks must still pass. Compare exact head of PR, including request accounting and stale clock edge conditions.
4. **Docs + review:** document cancellation behavior in `docs/configuration.md`; clarify D-024. Adversarial review must independently reason from implementation/tests, then request changes as needed and rerun CI.

CAL request volume: zero in research and tests; the source change can only avoid further CAL transport attempts after cancellation. No release approval or rate-window claim.
