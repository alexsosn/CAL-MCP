# Issue #65 plan — verify the sdist before publication

Date: 2026-09-07
Research prerequisite: `docs/research/issue-65-verify-sdist.md`

## Goal

Strengthen the v0.1 release verifier so every distribution artifact that can be published is independently validated: wheel and source distribution must agree on package identity/version, and both exact files must clean-install to the same frozen stdio MCP surface.

## Gate 1 — behavior-first RED

Modify tests only. Add `tests/test_release_artifact_verifier.py` with local synthetic archives and no CAL/network dependency.

Required RED cases:

1. **Embedded sdist metadata mismatch**
   - synthetic wheel metadata: `Name: cal-mcp`, `Version: 0.1.0`;
   - filename-correct `cal_mcp-0.1.0.tar.gz`;
   - sdist root contains `PKG-INFO` declaring `Version: 9.9.9` and a `pyproject.toml`;
   - expected behavior: verifier rejects before install.
   - current behavior: passes distribution discovery because only the sdist filename is checked.

2. **Both exact distributions are independently installed**
   - synthetic wheel and structurally correct sdist for the same version;
   - monkeypatch virtualenv creation, pip subprocess invocation, executable discovery, and stdio verification so the test is deterministic/offline;
   - expected behavior: `verify_release_artifact()` invokes the install verification once for the exact wheel and once for the exact sdist, in separate temporary install roots/environments;
   - current behavior: only the wheel path is installed.

3. Preserve existing tag/version mismatch behavior and all frozen release-contract tests.

RED acceptance: dependency/install checks, Ruff lint, Ruff format, and strict mypy remain green; pytest failures are limited to the missing sdist identity/install behavior.

## Gate 2 — minimal implementation

Change `scripts/verify_release_artifact.py` only unless tests/docs require a narrowly scoped update.

### Archive validation

Add a small source-distribution metadata helper using the standard-library `tarfile` module without extraction.

Require:

- gzip tar is readable;
- archive members are rooted under exactly one top-level directory;
- the root directory name equals the expected sdist stem from the filename;
- root contains exactly one `PKG-INFO` regular file;
- root contains a `pyproject.toml` regular file;
- `PKG-INFO` parses as core metadata;
- `Name` is exactly the expected `cal-mcp` project identity;
- `Version` equals the wheel version.

Do not extract tar members and do not add a custom archive extraction implementation.

### Independent install verification

Refactor the existing wheel-only temporary-venv install block into a helper that accepts one distribution path plus expected version and runs:

- create isolated venv;
- pip install the exact path;
- require installed `cal-mcp` console script;
- run existing `_verify_stdio()` against expected version and exact 26-tool schema.

Call that helper independently for the wheel and for the sdist, using distinct temporary environment directories. Do not copy/rebuild a second publishable artifact set.

Keep tag/version matching based on the validated shared version.

## Gate 3 — GREEN

Require full normal CI in both jobs:

- frozen/deterministic install and exact-environment verification;
- latest-compatible install;
- Ruff lint;
- Ruff format;
- strict mypy;
- full pytest.

No CAL access.

## Gate 4 — documentation / workflow consistency

Re-read `.github/workflows/release.yml` and issue #15 release docs after implementation.

Expected outcome: no workflow code change is necessary because the workflow already builds once, calls `verify_release_artifact.py`, then uploads/publishes that same `dist/` directory. If wording currently implies only wheel verification, make only the minimal documentation correction needed.

Do not change public tool documentation or the frozen 26-tool count.

## Gate 5 — logically independent adversarial review

Review the exact final SHA from scratch against issue #65, research, plan, whole diff, current `main`, and exact-head CI. Challenge at least:

- sdist filename correct but `PKG-INFO` name/version wrong;
- corrupt/non-tar `*.tar.gz`;
- missing or duplicate root `PKG-INFO`;
- missing root `pyproject.toml`;
- multiple top-level roots / path tricks that evade the root check;
- directory entries vs regular files;
- valid wheel masking a broken sdist;
- accidentally installing the wheel twice instead of wheel + sdist;
- using one environment for both installs;
- tag check becoming disconnected from embedded metadata;
- changing or weakening the existing wheel stdio 26-tool verification;
- rebuilding different files after validation;
- accidental overlap with active PR #53 or the frozen public schema.

Any blocker requires a review-regression test-only RED, minimal fix, fresh full GREEN, and a fresh exact-head adversarial review.

## Merge gate

Immediately before final review and again before merge:

1. refetch PR head;
2. refetch current `main`;
3. if `main` advanced, synchronize/reassess against the new base and rerun exact-head CI/review as required;
4. merge only with `expected_head_sha` equal to the exact independently reviewed SHA;
5. verify issue #65 closes and `main` contains the guarded merge.