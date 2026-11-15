# Issue #334 — documentation parity execution plan

**Date:** 2026-11-15. Research in `docs/research/issue-334-pre-v02-doc-parity.md` must be committed before tests/production docs.

## Contract and acceptance

1. `README.md` published v0.1.0 tool table enumerates all **36** manifest tools, including `cal_targum_reflex_examples`; the **37th** tool is explicitly source-only until a versioned release. Fix misleading Agora *future* diagram while preserving standalone separation.
2. `docs/index.md` accurately lists Targum follow-up tools and does not list completed #109 as unfollowable; #39 and new bibliography are described as implemented in source but **not released**.
3. `docs/getting-started.md` provides a bounded source-only `cal_bibliography_recent()` workflow and mentions supported explicit Targum example, KWIC and Syriac group follow-ups without inventing selectors.
4. `docs/limitations.md` and `docs/integrations/standalone-mcp.md` reflect merged Agora registration and its **unpublished** marketplace v1.1 candidate. Preserve published CAL-MCP v0.1.0 instructions and asymmetric Codex/Claude verification.
5. Add a concise `wiki/release-checklist.md` grounded in the actual tagged workflow and documentation parity gates; link it from maintainer index. Update `CHANGELOG.md` under **Unreleased**. Neither tag nor publish packages in this issue.

## RED — offline tests first

Add `tests/test_docs_pre_v02_parity.py` against the **real** `V01_PUBLIC_TOOLS`, not duplicated handwritten lists. Check missing README tool, closed-issue gap wording, deferred new bibliography guidance, stale Agora integration claims, and the release-checklist guardrails. Commit test-only and record failing checks *before* documentation fixes. Preserve existing `tests/test_docs_contract.py` and its Markdown-relative-link walk.

## GREEN

Small surgical edits to README, index, getting-started, limitations, standalone integration, changelog; no broad rewrite of accurate detailed tool docs. Document current vs released contract separately. Add checklist and maintainer link. Ensure all relative links resolve.

## Validation and independent review

Run/observe `ruff check .`, `ruff format --check .`, `mypy`, `pytest` in both pinned and latest-compatible CI environments; normal CI must make **zero** CAL calls. Independently review the final exact SHA *from scratch* against the manifest and actual GitHub release/closed-issue statuses, attempt to find false new-publication or Agora-certification claims, broken links, misleading user examples, and overfitted tests. Merge only with green exact-head checks and review ACCEPT. Release publication remains a separate operator-gated task.
