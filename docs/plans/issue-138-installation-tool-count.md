# Issue #138 plan — keep installation tool count in sync

Date: 2026-09-16. Research: `docs/research/issue-138-installation-tool-count.md` (committed before this plan).

1. Test-only RED: add `tests/test_installation_release_surface_contract.py`; read `docs/installation.md`, require exactly one explicit numeric `N-tool MCP surface` assertion, and check `N == len(cal_mcp.release_surface.V01_PUBLIC_TOOLS)`. A missing or duplicate numeric claim fails closed; no duplicated expected count in the test. The test should expose the existing 29 vs 34 discrepancy while install, lint, formatting and mypy remain green.
2. Minimal GREEN: update that one sentence to 34. Preserve all publication caveats and runtime contracts; do not touch release artifact code or add a tool.
3. Run complete offline deterministic and latest-compatible CI on the exact resulting head.
4. Independent adversarial review: ensure test is not tautological, count comes only from authoritative release manifest, no false assertion PyPI publication happened, no CI/network changes, and no unrelated docs edits. Fix any blocker by another RED/GREEN subloop.
5. With both CI jobs green, reviewed head unchanged, no review threads and mergeable `main`, post independent review, mark ready and squash merge with expected-head SHA; issue #138 closes.

CAL load impact: zero.
