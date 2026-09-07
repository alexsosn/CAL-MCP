# Issue #18 plan — reproducible CI constraints plus latest-compatible coverage

Date: 2026-09-07
Research: `docs/research/issue-18-reproducible-ci.md`

## Scope freeze

Implement only CI/release dependency reproducibility and refresh documentation. Keep `pyproject.toml` runtime/dev compatibility ranges broad and unchanged. No CAL behavior, schemas, live traffic, release publication, or Python-version matrix expansion.

## Gate 1 — test-only RED

Add a repository contract test that requires all of the following while production/workflow files are still unchanged:

1. a committed target/runtime-dev constraints file containing exact `==` pins for the resolved Python 3.11 validation environment;
2. a committed isolated-build constraints file with exact pins for Hatchling and editable/build dependencies;
3. primary CI explicitly bootstraps the frozen pip/setuptools pair, installs `.[dev]` using both target and build constraints, prints `pip freeze --all`, and runs `pip check`;
4. primary CI continues Ruff, format, mypy, and pytest;
5. a separate `latest-compatible` CI job uses Python 3.11, intentionally installs broad `.[dev]` without target/build constraints, emits resolution + `pip check`, and runs the same deterministic checks;
6. release `build-and-test` uses the same frozen bootstrap and both committed constraints for its validation environment;
7. contributor/testing documentation contains the explicit constraint refresh procedure and states that package metadata remains broad.

Run the focused test and confirm failure for absent constraints/job/docs, not syntax/import problems.

## Gate 2 — minimal implementation

Add:

- `constraints/ci-py311.txt` — full exact target environment pins from the researched clean resolution, excluding the local editable CAL-MCP requirement;
- `constraints/build-py311.txt` — exact isolated-build pins including Hatchling 1.32.0 and `editables==0.6`;
- CI workflow changes implementing `deterministic` and `latest-compatible` jobs;
- release build/test install changes consuming the deterministic constraints;
- dependency refresh documentation in `wiki/testing.md` (and only other docs if a failing contract requires them).

Use pip 26.2.1 explicitly before invoking `--build-constraint`; pin setuptools 79.0.1 as observed in the researched Python 3.11 runner environment.

Do not add hashes in this ticket: the acceptance contract is version-resolution reproducibility/reviewability, not artifact-hash locking. Do not introduce pip-tools/uv/Poetry solely to generate the first constraint set.

## Gate 3 — focused GREEN

Run the new dependency-policy contract test. If it exposes a real workflow-policy defect, fix the smallest issue and rerun.

## Gate 4 — execution validation

Use the permanent PR workflow, not CAL probes, to prove:

- deterministic job installs successfully under committed target + build constraints;
- its logged `pip freeze --all` matches the intended frozen set and `pip check` passes;
- latest-compatible resolves independently from broad ranges and passes `pip check` + Ruff/format/mypy/pytest;
- deterministic test suite remains fully offline with respect to CAL.

Also run the release-contract tests because `.github/workflows/release.yml` changes.

## Gate 5 — full GREEN

Require the exact candidate head to pass all normal checks. Expected test count is baseline 396 plus the new dependency-policy tests.

No live CAL smoke is required because this ticket changes dependency validation only. If latest-compatible exposes an actual incompatible dependency within declared ranges, stop and treat that as a discovered compatibility defect rather than weakening the job.

## Gate 6 — logically independent adversarial review

Freeze the exact final SHA and review from a fresh CI/release-maintenance perspective. Challenge at least:

1. whether the target constraint file actually covers all installed runtime/dev dependencies rather than just direct deps;
2. whether build isolation can still resolve unpinned Hatchling/editable dependencies;
3. whether the deterministic job can accidentally ignore either constraints file;
4. whether `latest-compatible` is truly unconstrained by the frozen target/build files;
5. whether both jobs use the same Python support policy;
6. whether release validation consumes the same deterministic policy without changing published runtime metadata;
7. whether bootstrap pip/setuptools drift remains hidden;
8. whether logs expose exact resolved versions and `pip check` failures;
9. whether the refresh procedure is actionable and reviewable;
10. whether the change accidentally introduces CAL/network dependence or expands release scope.

Any blocker enters review-regression RED → minimal fix → focused/full GREEN → fresh exact-head independent review.

## Merge

Merge only an exact independently reviewed GREEN head. Close #18 through the PR only after all acceptance criteria above are satisfied.
