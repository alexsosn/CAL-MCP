# Issue #351 — stable v0.2.0 release preparation research

**Date:** 2026-11-18. Baseline main `61038b7988e23df120a9ea8c168f142f30b35b68` (subject to merging the reviewed acceptance-evidence PR #349).

## Factual starting point

- The latest GitHub Release is `v0.1.0`, published 2026-10-11 22:07 UTC, with Python package `cal-mcp==0.1.0` on PyPI and 36 public tools. The immutable v0.1.0 `V01_PUBLIC_TOOLS` / tagged distributions are historical and must not change.
- `pyproject.toml` says `version = "0.2.0.dev0"`; `src/cal_mcp/__init__.py` uses installed-package metadata. The current public manifest has 37 tools including `cal_bibliography_recent()`. Existing README, docs/index, installation, bibliography, limitations and getting-started distinguish published v0.1.0 from unreleased source, and many mention `0.2.0.dev0`. For a stable *unpublished candidate*, the source metadata should become `0.2.0` but public install instructions must **continue to recommend the actually published 0.1.0 pin until verified publication**.
- The [nonpublishing full-MCP dev-wheel run #43978495435](https://github.com/alexsosn/CAL-MCP/actions/runs/43978495435) tested **37/37 public tools and 47/47 distinct cases** on the same wheel, from source SHA `8e7b1aa79404af2dfd30ac295504e26ed62a3436`; observed **49 actual CAL starts** (22+13+14, each process capped at 25) vs **46 CAL-backed tool invocations**. [Paired CI #43978509089](https://github.com/alexsosn/CAL-MCP/actions/runs/43978509089) passed 2464 pytest cases/matrix, Ruff and mypy. This tests a dev wheel, not the future stable tagged wheel.
- Existing `.github/workflows/release.yml` triggers exclusively on pushed `v*` tags, builds a single wheel/sdist, runs pinned checks, validates tag/version and installed tool names, then only the 13-case representative MCP CAL live smoke, then PyPI trusted publishing and GitHub Release. The full 37-tool evidence runner has already shown that **47 cases require about 46 minutes and 49 CAL starts**, meaning a full release-tag gate must raise its live job timeout from 30 to at least 90 minutes and execute all three suites serially from the *same* downloaded wheel with >=60 seconds between batches and zero retries.
- Existing `scripts/verify_release_artifact.py` requires wheel and sdist metadata and tag match and launches installed stdio MCP without CAL I/O. No new package metadata parser or unsafe bypass is needed. The release workflow must never run live CAL in routine pull-request CI.
- `docs/research/issue-15-publication.md` is the immutable v0.1.0 publication record. Downstream Agora candidate v1.1 registration is merged but not published; do not silently upgrade its pin or claim marketplace availability.

## Non-goals and possible blockers

No new CAL research endpoint, parallel requests, automatic retries, source-body or corpus archive, version signing infrastructure, licenses rewrite, or downstream Agora release work. The authorized connected GitHub actions can create branches/PRs and merge commits, **but expose no tag-creation or release-dispatch operation**; do not call a push to main a release. If tag publication remains unsupported, hand off the exact reviewed SHA and explicit maintainer tag action instead.

Keep separate research PR #348 and issues #347/#350 out of this release's critical path. No need to add speculative capabilities before releasing a demonstrated 37-tool package.
