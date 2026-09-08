# Issue #74 research — stale dependency status in v0.1 release notes

Date: 2026-09-08
Baseline: `main` at `b99bb356cf25026ca5852c5cdabfc007120b0aad`

## Question

Do the v0.1 release notes accurately describe the current dependency reproducibility and compatibility policy, or do they still present completed work as an outstanding limitation?

## Current release-note claim

`CHANGELOG.md` currently states under **Known limitations**:

> Dependency reproducibility/latest-compatible CI policy remains the separate non-blocking issue #18; v0.1 does not narrow reviewed runtime dependency ranges merely for release packaging.

The second clause remains directionally correct: downstream dependency declarations stay intentionally broad. The first clause is stale.

## Issue #18 status

Issue #18, **Add reproducible CI constraints plus latest-compatible dependency job**, is closed with state reason `completed` (closed 2026-09-07).

Its accepted contract was to keep broad package dependency ranges while adding:

- a reproducible primary CI environment;
- a separate latest-compatible validation environment;
- a documented refresh procedure;
- release validation aligned with the same constraint policy.

Those capabilities are now implemented.

## Implemented deterministic CI policy

`.github/workflows/ci.yml` contains a `deterministic` Python 3.11 job that:

1. bootstraps reviewed exact pip/setuptools versions;
2. installs `.[dev]` with `constraints/ci-py311.txt` and `--build-constraint constraints/build-py311.txt`;
3. reports `pip freeze --all` and runs `pip check`;
4. runs `scripts/verify_ci_environment.py constraints/ci-py311.txt`, excluding only the local editable package and the separately exact-pinned bootstrap packages;
5. runs Ruff lint, Ruff format check, strict mypy, and pytest.

The exact-environment verifier is fail-closed: an unexpected installed distribution, missing pin, or version mismatch makes the deterministic job fail.

## Implemented latest-compatible policy

The same workflow has a separate `latest-compatible` Python 3.11 job. It intentionally installs `.[dev]` without the committed project constraint files, reports the actual resolution, runs `pip check`, and executes the same Ruff/format/mypy/pytest gates.

This preserves two distinct guarantees:

- reproducibility of the reviewed primary validation environment;
- active compatibility checking against the broad dependency ranges declared for downstream users.

## Release workflow alignment

`.github/workflows/release.yml` reuses the deterministic target/build policy in its `build-and-test` job:

- the same committed target and build constraints are used for the validation environment;
- the same exact-environment verifier runs;
- the actual `python -m build` step sets `PIP_BUILD_CONSTRAINT=constraints/build-py311.txt`.

Therefore release validation no longer has the divergence that issue #18 was intended to prevent.

## Documentation source of truth

`wiki/testing.md` section **Dependency resolution policy** already documents the implemented design and its explicit refresh procedure:

- broad `pyproject.toml` ranges remain the downstream compatibility contract;
- committed target/build constraints make the deterministic environment reviewable;
- the release job consumes the same policy;
- latest-compatible remains deliberately unconstrained by those project constraints.

The changelog is the stale document, not the implementation or testing guide.

## User-facing consequence

A reader of the v0.1 release notes is currently told that dependency reproducibility/latest-compatible validation is still pending, even though it is part of the release candidate's actual validation guarantees. This understates the shipped validation policy and makes the known-limitations section factually wrong.

The correction must not overstate what is guaranteed. In particular, CAL-MCP does **not** pin downstream users to one exact runtime environment. The package metadata intentionally retains reviewed broad compatibility ranges.

## Research conclusion

Issue #74 is a documentation correctness defect.

The v0.1 changelog should remove #18 from Known limitations and describe the implemented policy under release validation:

- deterministic CI and release validation use committed Python 3.11 target/build constraints plus exact-environment verification;
- a separate latest-compatible job checks the broad declared dependency ranges;
- downstream runtime ranges remain intentionally broad.

No dependency declarations, constraint files, workflows, runtime code, CAL behavior, public MCP schema, or publication mechanics need to change.