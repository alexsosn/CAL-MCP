# CAL-MCP pre-v0.2 release checklist

**Maintainer handoff, 2026-11-15.** This page documents gates for a **future** `v0.2.0` release. The current `main` source reports `0.2.0.dev0`. The only published standalone release as of this audit is `cal-mcp==0.1.0` / GitHub `v0.1.0`, with 36 tools. A documentation PR merge is **not a release**. Never describe this candidate as published merely because the source, a changelog or a PR exists.

## 1. Source and documentation agreement — before a release branch/tag

- [ ] Confirm the latest GitHub [releases](https://github.com/alexsosn/CAL-MCP/releases) and [PyPI project](https://pypi.org/project/cal-mcp/) version against the actual registry; do not infer publication from `pyproject.toml`.
- [ ] Identify the exact source SHA for the proposed version and reconcile open blocking issues/PRs. Run review on that SHA rather than an older draft.
- [ ] Verify `src/cal_mcp/release_surface.py`: immutable `V01_PUBLIC_TOOLS` = **36**; current evolving source has **37**, including source-only (until release) `cal_bibliography_recent`. Keep v0.1.0 tagged files and release assets untouched.
- [ ] Inspect the candidate wheel/sdist **long description** sourced from the current README (including wheel `METADATA`). The PyPI v0.1.0 page still contains a stale *pre-release / no versioned release* historical description; do not copy that claim into v0.2.0 or mistake a repository README change for a retroactive update to published 0.1.0 artifacts.
- [ ] Inspect `README.md`, `CHANGELOG.md`, `docs/index.md`, `docs/getting-started.md`, `docs/installation.md`, `docs/tools/bibliography.md`, `docs/tools/targum.md`, `docs/limitations.md`, `docs/integrations/standalone-mcp.md` and `docs/integrations/agora.md` against executable tool schemas and actual release state. Published-vs-development examples and all relative links must remain correct.
- [ ] Ensure that the completed Targum example follow-ups are documented, and `cal_bibliography_recent()` is not advertised to v0.1.0 users. Agora PR #268 is **merged**, but its candidate v1.1 marketplace release is **not yet published**; it does not certify all clients or change the standalone CAL-MCP pin.
- [ ] Confirm downstream Agora metadata still pins the **published** package rather than an untagged development checkout. A future package upgrade in Agora requires its own version-pinned integration and verification.
- [ ] In a separate reviewed release-preparation PR, set the *intended final release* version (e.g. `0.2.0` replacing `0.2.0.dev0`) and adjust all future-tense version references deliberately, while preserving historical v0.1.0 evidence. Do not publish a development version as final by accident.

## 2. Deterministic test and adversarial review gate

- [ ] Run `ruff check .`, `ruff format --check .`, `mypy`, `pytest`; verify both the pinned **deterministic** and **latest-compatible** GitHub [CI](https://github.com/alexsosn/CAL-MCP/actions/workflows/ci.yml) jobs succeed on the **exact final SHA**.
- [ ] Ensure normal CI makes **zero** live CAL requests; inspect broken links and docs/manifest parity tests. Retain a 36-tool historical v0.1.0 manifest and the current 37-tool schema.
- [ ] Perform a logically **independent review** grounded in the exact GitHub diff, actual package metadata, versioned tool lists, smoke-runner code and checked-in documentation. Explicitly look for fabricated published status, stale 0.1.0 copy, release pin mistakes, missing tools and bypassed request-budget checks. Resolve findings and rerun tests after changes.
- [ ] Merge only after exact-head green CI and accepted review; re-check merged `main` SHA before tagging. All research-plan-TDD-test gates belong to the issue/PR, not to release publication.

## 3. Immutable artifact and live-smoke gate

The actual [.github/workflows/release.yml](https://github.com/alexsosn/CAL-MCP/blob/main/.github/workflows/release.yml) starts **only** on a pushed `v*` tag; do not create a tag until the code, docs and version changes above are approved.

- [ ] Create a signed-off, exact-commit `v0.2.0` tag only when ready to run the publication pipeline. Verify tag/version match.
- [ ] Let the release job build **one wheel and one sdist**, run frozen CI, validate both freshly installed artifacts and the installed stdio executable/tool schema.
- [ ] Let its separate live job install the **same built wheel** and run the **13-case** current-source MCP smoke: **12** CAL-backed cases, including `cal_bibliography_recent`; at least **12 actual CAL transport starts**, never more than **25**; no automatic retries, concurrency 1, at least 60 seconds completion-based inter-case spacing, stop on failures/HTTP 429. The full live gate is *not* a routine PR CI action.
- [ ] Investigate any `parser_drift`, content, upstream/network, runtime, or missing-tool error. No passing partial matrix, retry storm, unmeasured CAL traffic or silently skipped scenario qualifies for publication. Correct errors in a reviewed change before a new attempt.

## 4. Publication and post-release checks

- [ ] Confirm the tagged pipeline's gated **PyPI** trusted-publisher step succeeded before claiming a new distribution; then confirm the **GitHub Release** references the same distributions and exact tag. A passing repository PR alone is not evidence.
- [ ] In a fresh environment, install the final pin from PyPI (not from the checkout), verify `cal-mcp --version`, execute stdio `list_tools` against the installed package **without contacting CAL**, and compare exact tool identities to the approved release manifest (37 if the reviewed v0.2 contract is unchanged).
- [ ] Verify the actual wheel/sdist hashes and archive metadata against publication evidence. Verify installer constraints/launch documentation; do not redistribute CAL data.
- [ ] Only **after confirmed publication**, update user-facing default install recommendations and downstream marketplace pins in separately reviewed changes. Preserve historical v0.1.0 instructions and evidence where useful.
- [ ] Record release URL, PyPI version, commit/tag SHA, artifacts, CI and bounded live smoke evidence in the release record. If any gate fails, report release as **blocked** or **not published**, not successful.

## Referenced policy

See [release research #15](../docs/research/issue-15-publication.md), [current smoke gate #330](../docs/plans/issue-330-current-release-smoke.md), [installation](../docs/installation.md), [testing policy](testing.md), [Agora handoff](../docs/integrations/agora.md), and [issue #334](https://github.com/alexsosn/CAL-MCP/issues/334).