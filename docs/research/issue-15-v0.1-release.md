# Issue #15 research — v0.1 standalone release gate

**Rechecked:** 2026-09-11  
**Issue:** #15

## Current release state

The formal v0.1 prerequisites named by #15 are complete: issues #12, #13, and #14 are closed. Current `main` already contains the release engineering built during earlier #15 work and later hardening tickets.

Current package metadata declares:

- package: `cal-mcp`;
- version: `0.1.0`;
- Python: `>=3.11`;
- build backend: Hatchling;
- installed command: `cal-mcp = cal_mcp.server:main`;
- equivalent module entry point: `python -m cal_mcp`;
- runtime dependencies: `httpx2>=2.12,<3` and `mcp>=2,<3`.

The executable release contract is `cal_mcp.release_surface.V01_PUBLIC_TOOLS`, currently **32 public tools**. Current CI after #77 is green on `main`.

GitHub's releases collection is still empty. Therefore `0.1.0` is prepared in source but has not yet been published as a versioned release.

## Existing release machinery

`.github/workflows/release.yml` is a tag-triggered release pipeline for `v*` tags. It already:

1. installs the frozen Python 3.11 validation environment;
2. verifies the deterministic dependency set;
3. runs Ruff lint/format, strict mypy, and the complete pytest suite;
4. builds one wheel and one sdist;
5. runs `scripts/verify_release_artifact.py` with the tag;
6. uploads those exact distributions as an Actions artifact;
7. runs the bounded live CAL smoke;
8. publishes those same distributions to PyPI through OIDC trusted publishing (`environment: pypi`, job-level `id-token: write`);
9. creates a GitHub release from the same artifacts and committed `CHANGELOG.md`.

The artifact verifier checks:

- one wheel + one sdist only;
- package name/version metadata consistency;
- tag version equals built distribution version;
- safe/expected sdist root metadata;
- independent installation of wheel and sdist into fresh virtual environments;
- installed `cal-mcp` executable exists;
- stdio server name and version match the distribution;
- installed tool names equal `V01_PUBLIC_TOOLS` exactly.

Artifact verification performs no CAL request.

## Live-smoke boundary and historical finding

Earlier #15 research established that release smoke must use service-layer exceptions for useful drift/upstream classification rather than treating any MCP tool-result object as success. That work produced `cal_mcp.live_smoke`, with:

- hard maximum: **9 CAL requests**;
- concurrency: 1;
- retries: 0;
- cache: disabled;
- eight representative families: lexicon, text search, text concordance, bibliography, dictionary collation, external citations, Targum, Syriac;
- explicit failure categories: parser drift, upstream/network, other content/policy failure, harness failure.

The original bounded research probe discovered real current-CAL regressions #41 and #42; both were subsequently fixed through focused TDD/review loops. The permanent smoke implementation incorporates those lessons and is separately available through `.github/workflows/live-smoke.yml` via manual dispatch or a weekly schedule. It is not ordinary PR CI.

## Fresh bounded live evidence — 2026-09-11

Because no scheduled run exists yet in the repository history, the release gate was rechecked once on the current release candidate with a temporary branch-only workflow. It installed the source candidate against latest-compatible dependencies (including MCP 2.2.0) and ran the permanent smoke unchanged.

GitHub Actions run `34589005460` succeeded with exactly:

```json
{
  "completed_cases": [
    "lexicon",
    "text_search",
    "text_concordance",
    "bibliography",
    "dictionary_collation",
    "external_citations",
    "targum",
    "syriac"
  ],
  "max_cal_requests": 9,
  "request_count": 9
}
```

The temporary workflow removed itself immediately after the run. No additional CAL traversal/probe was performed.

**Implication:** current CAL compatibility does not block release. The immutable release workflow will deliberately repeat this same capped smoke once for the actual tag before publication.

## Release-truth defects found in the current tree

The executable release machinery is ahead of user-facing release text:

1. `docs/installation.md` says the clean artifact exposes a frozen **29-tool** MCP surface; actual frozen surface is 32.
2. `docs/integrations/standalone-mcp.md` says v0.1 contains **29 public tools**; actual frozen surface is 32.
3. `tests/test_release_contract.py` checks 32 tools in the changelog/verifier but does not detect those stale 29-tool user-doc statements.
4. `README.md` says `active pre-release development` and `No versioned release has been published yet`. That is currently true, but if left in the tagged artifact it becomes false at the moment the release workflow succeeds.
5. `CHANGELOG.md` dates 0.1.0 as `2026-09-06` and calls it a `release candidate`. The actual intended first publication is now 2026-09-11 (or a later tag date if an external publishing prerequisite delays it).

These are release blockers because #15 requires the released docs to match the released executable surface and publication state.

## Publication authentication boundary

The release workflow already follows the correct least-privilege Trusted Publishing shape:

- no stored PyPI password/token;
- `id-token: write` only on the publish job;
- GitHub environment `pypi`;
- build/test/live smoke complete before publication;
- GitHub release happens only after PyPI publication succeeds.

Actual PyPI trusted-publisher/environment configuration is account-side state and cannot be proven from repository code. If it is absent, the tag workflow will fail at publication and #15 must remain open with that exact external blocker rather than claiming success.

A current web search found no existing public PyPI project page for `cal-mcp`, but package-name availability is conclusively established only by the first successful upload.

## Safe tag execution with available automation

The repository workflow is correctly tag-triggered. The connected GitHub actions available to this development loop do not expose creation of arbitrary tag refs directly. After a reviewed release-preparation merge, a temporary **non-merged trigger branch** can safely perform only:

```text
git fetch origin main
git tag v0.1.0 <reviewed main SHA>
git push origin v0.1.0
```

The helper exists only on the trigger branch. The tag points to reviewed `main`, whose tree contains the normal `release.yml` but not the helper. This preserves the immutable release boundary and avoids committing release-trigger machinery into the package.

## Scope conclusion

No new CAL feature, parser, public tool, request policy, or release workflow redesign is needed for #15.

Remaining repository work should be test-first and narrow:

- strengthen release-contract tests so the released user docs cannot regress to a stale tool count or permanently pre-release wording;
- correct `docs/installation.md`, `docs/integrations/standalone-mcp.md`, `README.md`, and `CHANGELOG.md` to be truthful both immediately before tagging and after successful publication;
- keep package version `0.1.0`, 32-tool surface, artifact verifier, release workflow, and 9-request live-smoke behavior unchanged unless a failing regression proves otherwise;
- independently adversarially review the exact release-preparation head;
- merge; tag the reviewed main commit; observe the real release workflow end-to-end;
- close #15 only after GitHub release + PyPI publication are verified. If external trusted-publisher configuration blocks publication, record that blocker and leave #15 open.
