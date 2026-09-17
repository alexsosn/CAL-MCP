# Issue #140 plan — synchronize user-facing v0.1 tool counts

Date: 2026-09-17. Research is frozen in `docs/research/issue-140-user-facing-tool-counts.md` and was committed first.

1. Add a test-only docs-contract change that imports `V01_PUBLIC_TOOLS`, derives `expected_count = len(V01_PUBLIC_TOOLS)`, and checks intentional current user-facing count claims rather than embedding `34` as an expected value. Cover README, docs index, installation guide, standalone integration guide, and changelog. Preserve existing tool-name coverage assertions.
2. Valid RED requires dependency/install checks, Ruff lint/format, and mypy GREEN with pytest failing only because `docs/integrations/standalone-mcp.md` says 29 while the manifest contains 34.
3. Minimal GREEN changes only the stale standalone count to the manifest's current value. Do not edit historical research/plans, runtime code, release workflows, package metadata, public schemas, or publication claims.
4. Run complete deterministic and latest-compatible CI on the exact candidate head.
5. Perform a logically independent adversarial review of the whole PR: challenge duplicated magic numbers, over-broad regexes that could match unrelated numbers, accidental removal/change of publication caveats, historical-doc rewriting, and any public-surface/runtime changes.
6. Any blocker gets a focused regression/fix and fresh full GREEN. With no unresolved threads, exact reviewed SHA unchanged, and PR mergeable against current `main`, mark ready and squash merge with expected-head SHA.

CAL load impact: zero.