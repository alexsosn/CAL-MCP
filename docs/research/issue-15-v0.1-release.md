# Issue #15 research — v0.1 standalone release and low-load live drift smoke

**Rechecked:** 2026-09-06

## Current release state

CAL-MCP has a complete frozen v0.1 application surface but is not yet published as a release artifact.

- `pyproject.toml` currently declares package `cal-mcp`, version `0.1.0.dev0`, Python `>=3.11`, Hatchling as the build backend, and the installed console script `cal-mcp = cal_mcp.server:main`.
- `python -m cal_mcp` delegates to the same server entry point.
- `tests/test_bootstrap.py` already proves that an **editable development install** exposes the package version, starts `cal-mcp` over stdio, and advertises the frozen 26-tool schema without contacting CAL.
- That is not yet a clean release-artifact test: normal CI installs the repository with `pip install -e ".[dev]"`; it does not build a wheel/sdist, install the wheel into a fresh environment, or launch the installed artifact there.
- GitHub currently has no repository releases and `.github/workflows/` contains only normal offline CI.
- `docs/installation.md` and `docs/integrations/standalone-mcp.md` correctly describe the project as pre-release and explicitly defer published-package instructions to issue #15.

Sources:

- `pyproject.toml`
- `src/cal_mcp/__main__.py`
- `src/cal_mcp/__init__.py`
- `tests/test_bootstrap.py`
- `.github/workflows/ci.yml`
- `docs/installation.md`
- `docs/integrations/standalone-mcp.md`
- GitHub releases API, rechecked 2026-09-06: no releases

**Implication:** release validation must test the built artifact in isolation rather than treating the existing editable-install stdio test as proof of a clean release.

## Previous capped live release probe

Issue #15 already performed one bounded branch-only live research probe before implementation. The temporary workflow was deleted immediately after the run.

Run `33995822616` used:

- one shared `CalHttpClient`;
- `max_concurrency=1`;
- `max_retries=0`;
- `cache_enabled=False`;
- a hard cap of **9 CAL requests total**.

It exercised eight representative released research families:

1. exact lexicon success: `cal_lexicon_lookup(query="br", lemma_key="br N")` — two CAL requests (bounded browser discovery + selected entry fetch);
2. text discovery: `cal_text_search(query="Tel Dan")`;
3. one-text concordance: `cal_text_concordance(text_id="13250")`;
4. bibliography: `cal_bibliography_lemma(lemma_key="cly V")`;
5. dictionary collation: `cal_dictionary_collation(source="jastrow", page="705")`;
6. external citations: `cal_external_citation_dialects()`;
7. Targum Studies: `cal_targum_parallel(book="Gen", chapter=1, verse=1)`;
8. Syriac Studies: `cal_syriac_peshitta_parallel(book="Gen", chapter=1, verse=1)`.

This exact selection totals nine requests because the lexicon success path is the only two-request case. It covers the major parser/service families without enumerating text catalogues, dialects, lemmas, verses, bibliography records, or result pages.

The probe found two genuine release-blocking current-CAL regressions:

- #41: current lexicon citation structure caused valid `br N` to fail;
- #42: current one-text concordance switched to a BR-delimited row stream.

Both issues have since completed focused research → plan → TDD → independent-review fixes and are closed. Current `main` includes the #42 merge at `5d4d57414adcf87607bc23e57d17b283102f6ea8`; #41 is also closed before this release resumption.

The earlier probe must **not** be repeated merely to rediscover those facts. The next live run should be the testable permanent smoke implementation after its offline RED/GREEN gate.

## Important MCP error-result finding

The research harness called public tools through the MCP client with `raise_exceptions=True`. When a server tool raised a parser exception, the server converted it to `UnexpectedToolError`; the client call returned a tool result marked `is_error` rather than necessarily raising in the caller. The original probe incorrectly printed such returned error results as `OK` because it only inspected `structured_content`.

**Implication:** any permanent MCP-boundary smoke must explicitly fail when `result.is_error` is true. A returned MCP result object alone is not success.

For release drift classification, the cleaner v0.1 design is to run the representative probes through the same public application **services** with one real bounded `CalHttpClient`, while separately validating the actual packaged stdio MCP process offline. The service layer preserves the exception taxonomy that the generic MCP boundary currently hides.

## Drift versus upstream failure classification

The shared request layer already separates:

- `CalNetworkError` — transport/network failure;
- `CalUpstreamError` — non-success CAL HTTP response;
- `CalContentError` — successful HTTP response unsafe to parse as expected CAL content;
- `CalResponseTooLargeError` — bounded response-size failure.

Endpoint/parser drift uses dedicated `CalContentError` subclasses, including:

- `LexiconParseError`;
- `SearchParseError`;
- `TextParseError`;
- `TokenAnalysisParseError`;
- `ConcordanceParseError`;
- `BibliographyParseError`;
- `DictionaryCollationParseError`;
- `ExternalCitationParseError`;
- `TargumParseError`;
- `SyriacParseError`.

The permanent smoke runner can therefore classify, without changing the public MCP contract:

- **drift** — a domain parser exception after a successful CAL response;
- **upstream/network** — `CalNetworkError` or `CalUpstreamError`;
- **content/policy** — other `CalContentError` such as maintenance/unexpected content or response-size rejection;
- **harness/other** — caller validation or unexpected local failure.

This is operational diagnosis, not a claim about CAL scholarly correctness.

## Permanent live-smoke boundary

The permanent v0.1 smoke should retain the researched cap of **9 CAL requests** and the same eight representative families unless a test proves a smaller equivalent set. It must:

- be opt-in/manual and scheduled separately from normal CI;
- use concurrency 1, retries 0, cache disabled;
- abort before request 10;
- require every selected operation to return its normal semantic success state and provenance;
- never follow links or paginate automatically;
- report a failure category useful for distinguishing CAL unavailability from parser drift;
- never run as part of ordinary pull-request CI.

A weekly schedule is sufficient for drift detection at this project's scale; release validation may also run the same capped smoke once before publication.

## Publication authentication boundary

PyPI's current official documentation recommends Trusted Publishing with GitHub Actions OIDC rather than a long-lived API token. For GitHub Actions:

- the publishing job needs `permissions: id-token: write`;
- `pypa/gh-action-pypi-publish@release/v1` is the recommended publishing action;
- a dedicated GitHub environment such as `pypi` is optional but strongly recommended;
- PyPI must be configured to trust the repository owner, repository, workflow filename, and (if used) environment;
- a pending Trusted Publisher can create a new PyPI project on first publication, but it does **not** reserve the project name before that upload.

Official sources, rechecked 2026-09-06:

- https://docs.pypi.org/trusted-publishers/
- https://docs.pypi.org/trusted-publishers/using-a-publisher/
- https://docs.pypi.org/trusted-publishers/adding-a-publisher/
- https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/

The repository connection available to the development loop cannot inspect or configure the user's PyPI Trusted Publisher/account state. Repository code must therefore provide a least-privilege `release.yml` compatible with Trusted Publishing, but it must not claim that PyPI trust is configured until an actual publication succeeds.

**Implication:** issue #15 can fully implement and test the release artifact, release workflow, and live-smoke machinery in-repository. Actual PyPI publication remains gated on the one-time external PyPI Trusted Publisher setup if it has not already been configured.

## Release workflow security constraints

Trusted Publisher configuration effectively grants the selected workflow authority to publish. The release workflow should therefore be isolated from normal CI, use job-level OIDC permission only for the publish job, build/test artifacts before that permission is needed, and publish only an immutable version/tag whose version matches package metadata. Pull-request code must never obtain publish credentials.

GitHub release assets and PyPI distributions should come from the same built artifact set rather than rebuilding independently after publication.

## Relationship to issue #18

Issue #18 tracks reproducible dependency constraints plus a latest-compatible job. It is explicitly non-blocking for current domain development but should not be accidentally solved by pinning runtime dependencies in #15. The v0.1 package retains its reviewed semantic dependency ranges; release packaging can install/build deterministically enough to validate artifact structure without changing the separate dependency-policy scope.

## No CAL data in the artifact

D-001 remains unchanged: the release contains software and documentation only. It must not bundle CAL lexicon entries, text pages, fixtures beyond the already reviewed minimal test material, a cache, or any live-smoke response body.

## Research conclusion

Issue #15 should proceed with two independently testable release layers:

1. **offline release artifact / stdio validation** — build wheel/sdist, install the wheel in a fresh environment, verify version + `cal-mcp` stdio introspection and the frozen 26-tool schema without contacting CAL;
2. **separate capped live drift smoke** — the researched 9-request service-level probe with typed failure classification, invoked manually/scheduled and once at release time.

Publication automation should use a dedicated OIDC Trusted Publishing workflow. Documentation changes from “pre-release” to a stable package-index command only after the publication step is known to succeed; until then, repository truth must describe the external publisher prerequisite explicitly.