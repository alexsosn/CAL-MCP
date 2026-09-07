# Issue #65 research — verify the sdist before publication

Date: 2026-09-07
Baseline: `main` at `3e3d1846bc4e22e9973bffac24115b7bcc23d825`

## Question

Does the v0.1 release gate validate every distribution artifact that it publishes, specifically the source distribution, or can a filename-correct but broken/divergent sdist pass because only the wheel is exercised?

## Current repository behavior

`scripts/verify_release_artifact.py` currently performs these steps:

1. `_find_distributions()` requires exactly one wheel and one `*.tar.gz` in `dist/`.
2. `_distribution_version()` opens the wheel, reads its `.dist-info/METADATA`, requires `Name: cal-mcp`, and returns the wheel version.
3. `_find_distributions()` checks only that the sdist filename equals `cal_mcp-{wheel_version}.tar.gz`.
4. `verify_release_artifact()` binds the returned source archive to `_sdist` and never opens or installs it.
5. A temporary virtual environment installs the wheel and `_verify_stdio()` checks the installed server name/version and the frozen 26-tool schema.

`.github/workflows/release.yml` then uploads the complete `dist/` directory and the publish job sends those exact distributions to PyPI. Both the deeply verified wheel and the filename-only-checked sdist are therefore publication candidates.

No existing test file independently exercises sdist metadata or sdist installation. `tests/test_release_contract.py` verifies that the release verifier exists and textually contains wheel/stdio contract markers, but it does not create or validate distribution archives.

## Packaging-standard requirements

The current PyPA source-distribution specification states that a modern `.tar.gz` sdist:

- has filename `{name}-{version}.tar.gz`;
- contains one top-level `{name}-{version}` directory;
- contains `pyproject.toml` and `PKG-INFO` inside that root;
- uses `PKG-INFO` for core metadata;
- requires the filename name/version to match the metadata stored in the archive;
- must be readable as gzip-compressed tar with Python's `tarfile` support.

Source: <https://packaging.python.org/en/latest/specifications/source-distribution-format/> (rechecked 2026-09-07).

PyPA/pip documentation also confirms that pip can install directly from an sdist by invoking its build backend, whereas a wheel is installed as a built distribution. This gives the two formats meaningfully different failure modes; a valid wheel does not prove that the sdist can build/install.

Sources:

- <https://pip.pypa.io/en/latest/cli/pip_install/>
- <https://packaging.python.org/en/latest/tutorials/installing-packages/#source-distributions-vs-wheels>

## Concrete defect

A source archive named `cal_mcp-0.1.0.tar.gz` can currently contain, for example, `PKG-INFO` declaring version `9.9.9`, omit `pyproject.toml`, contain corrupt gzip/tar bytes, or otherwise be unable to build. `_find_distributions()` does not inspect any of those conditions. If the wheel is valid, the current verifier can proceed successfully even though the sdist later uploaded by the release workflow is invalid.

This violates the release design recorded in issue #15: GitHub release assets and PyPI distributions are intended to be the same built artifact set that was validated before publication.

## Smallest strong boundary

The verifier should validate the exact sdist independently at two layers.

### 1. Archive identity / structure

Before creating install environments, inspect the tarball without extracting it and require:

- readable `tar.gz`;
- one top-level directory matching the canonical sdist filename stem;
- exactly one root `PKG-INFO` and one root `pyproject.toml`;
- `PKG-INFO` `Name` is `cal-mcp`;
- `PKG-INFO` `Version` equals the wheel version;
- the source filename is therefore consistent with both wheel and embedded sdist metadata.

Tar member inspection does not require unsafe extraction. If later code ever extracts the archive, it must follow the PyPA/Python `tarfile` data-filter safety rules; extraction is unnecessary for the metadata gate proposed here.

### 2. Independent clean install

Run the existing clean-install + stdio verification twice in separate temporary virtual environments:

- once with the exact wheel path;
- once with the exact sdist path.

Installing the sdist path forces pip to process/build that source archive. The installed server must then report the same expected version and exact frozen 26-tool schema. Separate environments prevent the valid wheel installation from masking source-build/install problems.

The existing verifier already permits package-index access for wheel runtime dependencies. The sdist path may additionally need the declared Hatchling build backend through normal pip build isolation; this does not broaden release privileges or add CAL access.

## Test strategy

Behavior-first tests can be fully local and must not create real release uploads or contact CAL.

1. Build a tiny synthetic wheel ZIP whose `METADATA` declares `cal-mcp` version `0.1.0`.
2. Build a synthetic `cal_mcp-0.1.0.tar.gz` containing the expected root paths but `PKG-INFO` version `9.9.9`. Current `_find_distributions()` accepts it; the new verifier must reject it before installation.
3. Build a structurally/metadata-correct synthetic sdist and monkeypatch virtualenv/install/stdio execution so `verify_release_artifact()` can be observed deterministically. Require two independent pip install targets in order: the exact wheel and the exact sdist.
4. Preserve the existing release-contract tests and frozen 26-tool constants.

The production release workflow itself need not rebuild artifacts. It should continue to upload/publish the same `dist/` files after the strengthened verifier has validated both.

## Non-goals / compatibility

This work does not:

- change package name/version;
- change the v0.1 MCP schema or tool count;
- change dependency ranges or the Trusted Publisher configuration;
- add a release tag or publish anything;
- contact CAL;
- rebuild a second artifact set after validation.

## Research conclusion

Issue #65 is a real release-integrity defect. The current gate proves the wheel but not the sdist, even though both are published. The minimal robust fix is to validate sdist archive identity/required metadata and then run the same clean installed-stdio contract independently against both exact distribution files.