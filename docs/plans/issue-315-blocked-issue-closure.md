# #315 — prevent accidental blocked-issue closure

Source audit [issue-315-blocked-issue-closure.md](../research/issue-315-blocked-issue-closure.md), committed in `433a72e` before this plan.

1. TDD **RED**: add offline test asserting contributor guidance exists in both `AGENTS.md` and `wiki/agentic-dev-loop.md`; require explicit blocked-dependency wording, negation warning, permitted closure example for finished issues, and a post-merge issue-state verification rule. Test deliberately requires a couple of precise invariant phrases instead of banning valid GitHub references across all docs.
2. Record the failing test-only CI, with no network from the test.
3. **GREEN**: update both markdown instruction files to make the distinction concrete: closure-keyword + issue number only for verified complete acceptance; a blocked issue must use neutral `Issue #N remains open` wording even if the sentence contains negation; audit PR description, final review, and squash/merge message; verify blocker state after merge and reopen/report immediately if unintentionally closed.
4. Run full offline CI in deterministic and latest-compatible matrices; docs only, no new MCP tools, CAL request/policy changes, or release.
5. Logically independent exact-head adversarial review: evaluate wording for overreach (should not ban ordinary cross-references), check issue-state proof vs speculation, ensure test cannot pass on incomplete guidance, verify latest-main SHA and both checks before merge.

Incident concerns workflow safety only. Issue #262 remains open until its real zero429 acceptance gate is satisfied.
