# Issue #311 — injected-clock cache expiry plan

Research gate: [docs/research/issue-311-injected-cache-clock.md](../research/issue-311-injected-cache-clock.md), committed before this plan.

1. **RED first.** Add focused async tests using an injected fake monotonic clock and synthetic CAL responses: a within-TTL hit causes no transport; at exact TTL expiry re-fetches with new upstream retrieval timestamp. Verify independently that an expired result cannot bypass the pre-existing terminal-429 cooldown while a valid cached hit still succeeds.
2. **Record failing offline CI** at the test-only branch head; do not make CAL requests.
3. **GREEN.** Pass the existing `clock` argument to `MemoryResponseCache` inside `CalHttpClient.__init__`. No separate fallback clocks, new API, traffic, or semantic parser changes.
4. Run both required offline matrices (Ruff, format, mypy, pytest); synchronize the clock-injection contract in docs.
5. Review the complete exact SHA independently against the issue invariants, including post-expiry transport count, cache provenance, cooldown suppression, default production behavior, and cancellation. Address adversarial findings with new RED tests, then re-run checks. Merge only after green checks and a fresh ACCEPT review.

Non-goal: solving #262's live 37-token zero429 acceptance.
