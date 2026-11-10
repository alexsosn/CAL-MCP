# Issue #332 — scoped research–plan–TDD–review gates

**Research first:** `docs/research/issue-332-agora-install-status.md` at `9d0f62a` (2026-11-10).

## RED
Add a focused deterministic test in `tests/test_agora_release_contract.py` reading the literal installation page and requiring current status anchors: exact merged Agora PR link, word **merged**, candidate v1.1 **not yet published**, the distinction between verified Codex and still-community Claude, and continued standalone `cal-mcp==0.1.0` pin. Explicitly reject both stale strings "registration remains downstream work" and "unverified downstream client-launch proposal". Existing tests for the canonical Agora integration handoff must remain unchanged.

Commit the test **without** changing docs, run both normal CI jobs and record at least one expected assertion failure after successful Ruff/mypy.

## GREEN
Replace only the stale `## Agora status` paragraph in `docs/installation.md` with an accurate concise update, linking to merged Agora PR and the detailed handoff. Keep original data rights and independently usable stdio installation guidance. Do not claim marketplace v1.1 is published, generated Claude live CAL has been verified, or ChatGPT/mobile availability.

## Gates
Both deterministic and latest-compatible full offline CI green on exact PR head. Independent adversarial review compares final diff and exact merged Agora #268/handoff evidence, specifically challenges scope confusion, false publication, missing verification asymmetry and loss of standalone install. No new live CAL call or package changes; merge guarded by reviewed SHA, close #332 only afterward.
