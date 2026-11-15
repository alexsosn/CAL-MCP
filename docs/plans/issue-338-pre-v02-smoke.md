# Issue #338: research → plan → TDD → test → independent review

## Gate A: deterministic coverage evidence (test-only RED first)

- Add a no-network regression proving the 13-case live release runner does not imply coverage of the full 37-tool manifest; compute actual distinct covered and uncovered tool names from `DEFAULT_SMOKE_CASES` and `CURRENT_PUBLIC_TOOLS`, with 24 explicitly accounted for by identity.
- Assert that any all-feature status requires a per-tool outcome for every current manifest tool, not only 13 results. Fail if case names are duplicated or a missing/unattempted tool is called passing.
- Add an issue-scoped coverage report `docs/research/issue-338-coverage.md` with exact source SHA, fixed cases and uncovered names, clearly distinguishing offline test coverage from live.
- Verify RED in both CI dependency matrices before implementation; do not add live network in test suite.

## Gate B: controlled real smoke

- A disposable branch-scoped push-only workflow installs one wheel built from the exact branch revision in a fresh venv and runs `python -m cal_mcp.stdio_live_smoke --executable ...` from outside checkout. It has no PyPI credentials, no tags, no schedule, no concurrent jobs and a 30-minute timeout. Existing runner keeps concurrency 1, retries 0, completion-based 60-second gap, 25-attempt ceiling and stop on any 429.
- Save sanitized GitHub job/run IDs, exact tested commit and per-case results. No full CAL content in report.
- Reconcile exact SHA with any concurrently merged fixes (e.g. #336/#337) before a final *release* decision. Do not claim the pre-release test validates later source changes automatically.
- Remove temporary workflow from final PR; permanent repo workflow remains manual-only. If unavailable or blocked, report honest blocker rather than faking results.

## Gate C: review and release decision

- Offline `ruff check .`, `ruff format --check .`, `mypy`, `pytest` on pinned and latest-compatible GitHub CI, zero CAL I/O.
- Independent source-grounded adversarial review of exact PR head and real actions logs, with particular attention to case-count arithmetic, fake pass gaps, workflow budget and failure handling.
- Merge only after review and all deterministic gates. Do not tag/publish. A successful 13-case smoke is a **representative** gate, not evidence of all 37 live tools; additional live coverage may be a follow-up.
