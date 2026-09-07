# Issue #18 research — reproducible CI constraints plus latest-compatible coverage

Date: 2026-09-07
Baseline: `main` at `90a90e371533319979820fb1426e758c89bf688e`

## Problem confirmed

`pyproject.toml` intentionally declares broad supported ranges (`httpx2>=2.12,<3`, `mcp>=2,<3`, and broad dev-tool ranges). Both normal CI and the v0.1 release build currently run `python -m pip install -e ".[dev]"` without constraints. Therefore the same repository commit can resolve different dependency versions over time.

This issue should make the primary deterministic CI environment reviewable/reproducible without narrowing downstream runtime dependency declarations. A separate compatibility job should continue resolving the newest versions allowed by `pyproject.toml` so broad compatibility remains tested deliberately.

## Current runner resolution

Two temporary branch-only research runs were used and removed before implementation:

- run `34106460382`: Python 3.11.16, pip 26.2.1, broad `.[dev]` resolution, `pip freeze --all`, `pip check`;
- run `34106531223`: repeated the runtime/dev resolution and separately resolved the Hatchling build-backend closure.

Both dependency checks reported no broken requirements.

Observed runtime/dev target environment (excluding the editable CAL-MCP line) includes:

- direct/dev: `httpx2==2.12.0`, `mcp==2.1.1`, `build==1.6.0`, `mypy==1.20.2`, `pytest==8.4.2`, `ruff==0.16.6`;
- representative transitive pins: `anyio==4.15.1`, `httpcore2==2.12.0`, `mcp-types==2.1.1`, `pydantic==2.13.5`, `pydantic-core==2.46.5`, `jsonschema==4.26.0`, `starlette==1.6.0`, `uvicorn==0.52.4`, `cryptography==50.0.1`, `typing-extensions==4.16.0`;
- runner tooling observed: `pip==26.2.1`, `setuptools==79.0.1`.

The complete frozen target set should be committed, not reconstructed from this abbreviated list.

Observed Hatchling install-time build closure:

- `hatchling==1.32.0`;
- `packaging==26.3`;
- `pathspec==1.1.1`;
- `pluggy==1.6.0`;
- `tomlkit==0.15.1`;
- `trove-classifiers==2026.6.1.19`.

Hatchling's current `get_requires_for_build_editable` also adds its `editables` requirement. Current PyPI latest is `editables==0.6`, compatible with Hatchling's editable requirement, so the build constraint set must include it as well.

## Pip constraint semantics

Current pip documentation matters to the architecture:

- ordinary constraints restrict versions selected for the target environment but do not themselves trigger installation;
- build constraints were added in pip 25.3;
- from pip 26.2, ordinary constraints (including `PIP_CONSTRAINT`) no longer affect isolated build environments; build dependencies require `--build-constraint` or `PIP_BUILD_CONSTRAINT`.

Sources:

- https://pip.pypa.io/en/latest/user_guide/#constraints-files
- https://pip.pypa.io/en/latest/user_guide/#build-constraints
- https://pip.pypa.io/en/latest/cli/pip_install/
- https://github.com/pypa/hatch/blob/master/backend/src/hatchling/build.py
- https://pypi.org/project/editables/

Implication: one constraints file is insufficient for reproducible editable CI on current pip. The deterministic job needs a target/runtime-dev constraints file and a separate isolated-build constraints file.

## Proposed contract

### Primary deterministic job

Use Python 3.11, matching the repository's current support/test policy. Explicitly install the pinned pip/setuptools bootstrap versions, then install `.[dev]` with:

- committed target constraints for the complete runtime/dev environment;
- committed build constraints for Hatchling and its build/editable dependencies.

After installation, print the resolved environment and run `pip check` before Ruff/mypy/pytest. This makes dependency changes visible in logs and committed diffs.

### Latest-compatible job

Use the same Python 3.11 policy but intentionally install `.[dev]` without project dependency constraints (apart from GitHub runner/bootstrap mechanics), print the resolved environment, run `pip check`, and execute the same deterministic checks. Its purpose is compatibility drift detection, not reproducibility.

This job should be clearly named so a fresh resolver outcome is expected rather than accidental.

### Release workflow

The release build/test job should consume the same committed target/build constraints as deterministic CI for its validation environment. The built wheel remains governed by broad runtime metadata from `pyproject.toml`; no runtime pinning is added to package metadata. The live-smoke install path should remain a released-source/runtime-compatibility check rather than silently gaining dev constraints unless a separate release requirement demands it.

## Refresh policy

Constraint refresh must be explicit and reviewable:

1. start from current broad `pyproject.toml` ranges on Python 3.11;
2. resolve a clean unconstrained latest-compatible environment;
3. capture the full target environment and separate isolated-build closure;
4. update both committed constraint files in one PR;
5. require deterministic constrained GREEN and latest-compatible GREEN;
6. review dependency/version diffs before merge.

No automatic job should rewrite constraints on `main`.

## Non-goals / boundaries

- Do not narrow `project.dependencies` or dev ranges merely to make CI reproducible.
- Do not add CAL behavior or network tests.
- Do not introduce a second lock/package manager unless constraints prove insufficient.
- Do not create a broad Python-version matrix in this issue; repository policy currently uses Python 3.11 for deterministic CI and release validation.
- Do not change v0.1 publication behavior or PyPI Trusted Publisher configuration.

## Testable acceptance shape

A repository contract test can fail on current `main` by requiring:

- committed target and build constraint files with exact pins;
- primary CI install command to consume both constraint sets;
- an explicitly named latest-compatible job that installs from broad `pyproject.toml` ranges without the target constraints;
- both jobs to use Python 3.11 and emit `pip freeze --all` plus `pip check`;
- release build/test installation to consume the same deterministic constraints;
- documentation of the refresh procedure.

Normal CI remains fully offline with respect to CAL; package-index access for dependency installation is unchanged from current CI behavior.
