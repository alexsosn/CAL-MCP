# Issue #16 — upstream release contract and downstream Agora handoff

Research commit `6c69d55` ([source](../research/issue-16-agora-release-contract.md)) precedes this plan.

1. **RED:** add offline `tests/test_agora_release_contract.py` to verify package identity/version/entrypoint/runtime in `pyproject.toml`; expected fixed real one-call lexicon smoke selectors from `DEFAULT_SMOKE_CASES`; `docs/integrations/agora.md` documenting exact `cal-mcp==0.1.0`, `cal-mcp`, stdio, Python >=3.11, 36 published tools, remote CAL provenance/terms, upstream-vs-marketplace ownership, one-call downstream smoke, no hosted CAL-MCP; current `docs/index.md` must no longer call the released v0.1 surface pre-release. Preserve docs/contracts without introducing CAL traffic.
2. **GREEN:** add the smallest version-pinned handoff document with client-neutral installation and sample launch metadata (mark unverified Agora-specific launch until downstream CI). Correct the visible pre-release text in `docs/index.md` and `docs/installation.md`, preserving known feature deferrals and provenance.
3. Run both deterministic and latest-compatible offline CI on exact PR head; ensure no new CAL GETs, no code/runtime/public schema changes.
4. Independent adversarial review from released tag/workflow and Agora's current generator/registry boundary, not solely from the draft description. Check that the documented single read exists in shipped smoke cases, and that this PR **does not claim** a downstream Agora registration or cross-platform proof.
5. Merge only after exact-head CI green and independent accept; keep CAL issue #16 and Agora#222 open until a separate downstream Agora PR actually passes generator+launch verification. Do not mark issue complete by docs alone.
