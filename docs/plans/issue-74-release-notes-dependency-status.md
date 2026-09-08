# Issue #74 plan — correct v0.1 dependency-status release notes

Date: 2026-09-08
Research prerequisite: `docs/research/issue-74-release-notes-dependency-status.md`

## Scope freeze

Correct only the user-facing v0.1 dependency-validation status and protect it with a deterministic documentation contract test.

Do not change dependency declarations, constraint files, CI/release workflow behavior, package version, public MCP tools, request policy, parsers, or CAL traffic.

## Gate 1 — behavior-first RED

Add a small dedicated test module, `tests/test_release_notes_dependency_status.py`, with production/docs unchanged.

The regression must assert that `CHANGELOG.md`:

1. no longer says dependency reproducibility/latest-compatible policy "remains the separate non-blocking issue #18";
2. explicitly states that deterministic CI and release validation use committed Python 3.11 target/build constraints;
3. explicitly states that the separate latest-compatible job checks the broad dependency ranges declared for downstream users.

Keep the test focused on factual release-note semantics rather than incidental paragraph layout.

Valid RED requires:

- install/dependency checks GREEN;
- Ruff lint GREEN;
- Ruff format GREEN;
- strict mypy GREEN;
- pytest failure limited to the new release-note contract.

No CAL access.

## Gate 2 — minimal documentation fix

Change only `CHANGELOG.md` unless the RED exposes another directly related stale release-note assertion.

Under **Release and drift validation**, add a concise statement equivalent to:

> Deterministic CI and release validation use committed Python 3.11 target/build constraints with exact-environment verification; a separate latest-compatible job checks the broad dependency ranges declared for downstream users.

Remove the stale #18 bullet from **Known limitations**.

Preserve the important compatibility boundary: broad downstream dependency ranges remain intentional; the release does not impose the deterministic CI environment on package consumers.

## Gate 3 — GREEN

Require both permanent CI jobs on the exact candidate head:

- deterministic constrained environment + exact-environment verifier + Ruff/format/mypy/pytest;
- latest-compatible unconstrained resolution + `pip check` + Ruff/format/mypy/pytest.

Expected change to the suite is one documentation-contract test.

## Gate 4 — logically independent adversarial review

Freeze the exact final SHA and independently challenge:

- release notes no longer present completed #18 as outstanding;
- wording matches the actual CI and release workflows;
- deterministic constraints are not falsely described as downstream runtime pins;
- latest-compatible remains clearly separate from deterministic constraints;
- release publication is not falsely claimed to have completed;
- v0.1 version and 27-tool surface are unchanged;
- no dependency/constraint/workflow/runtime/CAL behavior changed;
- the regression would fail if the stale #18 wording returned or the implemented validation guarantee disappeared from the changelog.

Any blocker requires a new review-regression TEST-ONLY RED, minimal fix, full GREEN, and fresh exact-head review.

## Merge gate

Immediately before final review and merge:

1. refetch PR head and current `main`;
2. synchronize/reassess if `main` advanced;
3. require fresh exact-head CI and independent review;
4. mark ready only after PASS;
5. merge with `expected_head_sha` equal to the reviewed SHA;
6. verify issue #74 closes and the correction is present on `main`.