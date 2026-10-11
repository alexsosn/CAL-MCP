# #315 — blocked-issue closure incident research

Checked 2026-10-11 against GitHub's repository event API, actual PR descriptions, and current contributor instructions; no CAL I/O.

## Evidence
- `GET /repos/alexsosn/CAL-MCP/issues/262/events` records **closed** at 2026-10-11 09:42:10 UTC and **reopened** at 09:58:13, then **closed** at 17:13:06 UTC and **reopened** at 17:15:34.
- PR #298 merged 09:42:08 UTC; PR #312 merged 17:13:04 UTC. The closures happened about two seconds after the respective merges. The existing record demonstrates undesirable issue-state transitions, **not** a proven mechanism or actor intent.
- The merged PR #312 body ended `This PR must not close #262.` It also included ordinary `#262` references. GitHub issue-closing automation, third-party automation, or an actor action are not distinguishable from these event timestamps alone. Do not assert a definitive cause.
- The `AGENTS.md` and `wiki/agentic-dev-loop.md` instructions require links to dependencies/blocked issues but never warn that a closure directive in a *negated sentence* may still be interpreted unsafely.
- A blocked release issue should not be closed by a protective partial PR, regardless of automation mechanism: verified current #262 status is **open**, live 37-token zero-429 acceptance still unmet.

## Decision scope
Adopt text-only fail-closed authoring rules: `Fixes #N` / `Closes #N` / `Resolves #N` are appropriate only for issues whose acceptance criteria have actually passed, and never for blocked issues (even negated). For blocked prerequisites, use neutral references like `Issue #262 remains open`, and inspect critical issue states after merging. Cover PR bodies, final review and merge-commit messages. No GitHub bot or broad repository text-lint scanning; no CAL changes, no scholarly contract changes.
