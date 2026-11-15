# Issue #338: pre-v0.2 smoke coverage audit (2026-11-15)

- Source baseline at task start: `6e472808dc82c06dbfe5e3f8cf3942933a4242a4`; `pyproject.toml` is `0.2.0.dev0`; only v0.1.0 published. No release tag/publishing action is authorized by this ticket.
- Authoritative code inventory: `src/cal_mcp/release_surface.py` defines 36 frozen v0.1.0 tools and 37 current development tools (37th: `cal_bibliography_recent`).
- Executable `src/cal_mcp/stdio_live_smoke.py` implements **13 fixed cases / 13 unique tool names**: 1 no-network `cal_convert_to_code` and 12 CAL-backed cases. These cases check both noun and verb lexicon lookup, so the distinct CAL-backed tool count is **11**; 13 cases are not proof of 37 live functions. A full pre-release audit needs to account for 24 tools that do not have individual fixed-case coverage.
- The actual release workflow (`.github/workflows/release.yml`) triggers on version tags and runs the 13-case smoke on one installed wheel with hard 25 actual-CAL-attempt ceiling and at least 12 starts. Running the tag workflow is not acceptable before a complete release candidate review because it can publish to PyPI.
- The manual `.github/workflows/live-smoke.yml` uses `workflow_dispatch` and the same runner, but the connected GitHub actions tool does not expose manual dispatch, only approved read/PR/file actions. The local execution container cannot resolve github.com. A **temporary branch-scoped push-only** GitHub Actions workflow can run the same installed-wheel smoke without adding permanent scheduling or a release tag; remove it from the PR before merge and link the recorded run.
- CAL rate limiting: `docs/research/issue-262-slow-acceptance.md` records 38/38 successful starts once under >=60-second completion-based waits and zero retry. Three-second-only pacing previously triggered HTTP 429. Do not increase current server/request budgets or run parallel batches against CAL.
- Source tests and `wiki/testing.md` require zero live CAL calls in normal CI, fail-closed upstream drift, no hidden pagination or automatic traversal, exact live attempt counting, strict source provenance and safe error classification.

## Evidence tiers

1. 37-tool **registered MCP surface** and offline parser/service/schema tests can be verified in normal CI without live CAL.
2. 13-case exact installed-wheel **representative** smoke verifies only its own tool paths; report 13/37 and do not claim 37/37 live verification.
3. Additional live probes covering remaining 24 tools would require separate source-grounded test cases and independently reviewed quotas/dependencies, not an unreviewed change in the release smoke.

## Research decision

Run the **existing exact nonpublishing 13-case smoke** as a bounded acceptance test, and record its outcomes; add a permanent offline guard on representation of the 37-tool manifest and the uncovered-tool report. Treat missing full live coverage as explicit remaining release risk. Avoid unnecessary CAL traffic and avoid conflating a smoke with full semantic correctness.
