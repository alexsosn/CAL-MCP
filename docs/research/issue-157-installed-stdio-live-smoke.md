# Issue #157 research — installed-stdio MCP smoke before publishing

**Date:** 2026-10-10
**Base:** `main` at `c092f89f6c14ffb14e845826d82bde70b6728f9c`
**Mode:** offline repository research; no CAL requests

## Current release execution

The tag-triggered `.github/workflows/release.yml` currently has four stages:
1. `build-and-test`: frozen Python 3.11 environment, Ruff, mypy, pytest, wheel/sdist build and `scripts/verify_release_artifact.py`;
2. `live-smoke`: a source checkout installs `python -m pip install .`, then runs `python -m cal_mcp.live_smoke`;
3. `publish-pypi`: trusted-publisher OIDC upload of the distributions built by stage 1;
4. `github-release`: release of those same artifacts.

The Monday `.github/workflows/live-smoke.yml` runs the same direct-service smoke.
`cal_mcp.live_smoke` calls eight Python service methods directly rather than the installed stdio
MCP endpoint. Its guard `BudgetCalHttpClient` limits calls to nine logical `fetch` operations
(sequential, retries disabled, cache disabled). It fails on the first exception and never validates
MCP `outputSchema`, tool argument validation, serialized errors, or result provenance after MCP
transport. The existing release artifact verifier starts the stdio server and enumerates tools but
does not call representative live tools.

The two code paths therefore fail to cover real user behavior in a release gate, as documented by
the 2026-09-24 and 2026-09-25 end-to-end audits on #15. A returned MCP tool result is not success
unless `is_error` is false. The Python MCP client's stdio child environment must explicitly
receive proxy and certificate variables when present; the SDK's restricted default environment can
strip `HTTPS_PROXY`.

## Request-budget boundary

The nine-request service smoke has a pre-fetch budget inside its own
`BudgetCalHttpClient`. A new process-boundary stdio driver does not own the `CalHttpClient`
instance created in `server.app_lifespan`. The parent process cannot enforce an upstream GET/POST
request cap merely by counting MCP calls: one tool may perform multiple CAL requests, retries may
occur, cache hits perform none, and a parser failure can happen only after transport.

Consequently the release E2E needs an **enforced server-side budget on actual CAL transport
attempts**, configured only for the explicitly opt-in smoke process, in addition to a cap on tool
calls. Count at the transport request boundary, before each attempt, not after returned responses.
The test environment can set concurrency one, retries zero, and retain per-run completed-response
cache. Reject a would-be request before exceeding the cap. Normal CAL-MCP operation must retain the
existing client behavior and public tool schemas.

For a single release/scheduled live run, replace rather than stack the old nine-request smoke so
the documented new ceiling is a true **total** bound. The target is no more than **25 upstream
attempts** across the complete run, including any failed attempts and explicit follow-ups; running
both the old nine-request suite and a new 25-request suite would silently enlarge the load to 34.

## Schema and error boundary

The driver should obtain the public tool catalogue using `list_tools`, select only explicit known
tool names, check `is_error`, and validate `structured_content` against each tool's declared
`outputSchema`. It must also check that successful CAL-backed results contain an HTTPS CAL source
URL and retrieval timestamp. Failed results must be reported without copying CAL response bodies.

The public structured error category, after #156, is the trustworthy discriminator:
`parser_drift` indicates a changed CAL shape; HTTP/network/timeout indicates upstream
unavailable; unexpected MCP protocol failures or a missing declared schema indicate harness
failures. An explicit `not_found` can be success if expected for a specific case.

Run all independently selected cases sequentially to collect failures, but never continue after
the fixed transport-attempt budget is exhausted. Do not follow arbitrary returned URLs or enumerate
all result pages.

## Candidate coverage (not yet a request-count claim)

Build a fixed representative set including lexicon noun and verb lookup, gloss/search, catalogue
and subtext page, a linked token analysis, one concordance/KWIC workflow, bibliography, one
dictionary source, external citations, Targum comparison, and Syriac Peshitta comparison. Reuse
identifiers returned by earlier *successful* calls for typed follow-ups where appropriate. One
non-Roman query and one current CAL verb are high-value regressions. #237 and #240 must land before
a verb exact-lookup acceptance case can be green.

Use a trial run with accounting logs to set and verify the final fixed matrix within 25 attempts.
Don't assume the count from the number of MCP calls; cache behavior and service fan-out determine
the actual attempts.

## Scope / dependencies

This is a release-policy change. A new D-022 decision recording the total hard ceiling,
one-at-a-time behavior, caching, retry policy, selected operations, and run cadence must be
reviewed and committed **before implementation**. Keep the regular offline CI network-independent.

Other known dependencies: #237/#240 current verb coverage; the PyPI Trusted Publisher and
immutable tag verification in #15. No tag or PyPI publication is part of #157.

## Follow-up chain chosen from existing typed repository evidence

2026-10-10 repository check, without additional CAL requests:
`TextSearchResult.to_dict()` returns ordered `matches` with `file_id`,
`subtext_id`, `category_id` and `follow_up_tool`. A directly readable hit has
`follow_up_tool="cal_text_page"`; a collection hit instead names
`cal_text_catalogue`. Existing deterministic tests for the current `Tel Dan`
search include a direct readable `13250` hit. A smoke follow-up must read the
**returned** file/subtext identifiers, not submit a guessed or hard-coded ID.
The parent text-search call never prefetches the page. One chosen direct hit
yields at most one explicit `cal_text_page` request.

Do not silently choose a catalogue hit and pretend it is a readable text. A
missing/invalid direct selector is a drift result; if the parent failed, record
a dependency skip without making a new upstream request. Live acceptance of
this selected chain has not yet been measured.


## 2026-10-10 live acceptance, bibliography minimum-cardinality review

One one-time installed-wheel stdio run, GitHub Actions `38050083896`,
from candidate `84c1139b`, **completed with a failure**. Its machine-readable
summary reports 13 actual CAL transport attempts out of 25, and 11/12 cases
`ok`: noun/verb lexicon, gloss, text search, the returned-selector page
follow-up, concordance, dictionary, external citations, Targum, Peshitta,
and local conversion. The **only** `drift` classification is
`bibliography: missing representative CAL result rows`. All 13 live HTTP
requests returned 200; this particular error came from the smoke's
`_has_representative_content` cardinality/identity check, *not* from the
bibliography parser or the public schema.

The smoke request was exactly `cal_bibliography_lemma(lemma_key="cly V")`
(`getbiblemma.php?myauthor=cly+V`). Pre-existing CAL snapshot
`tests/fixtures/cal/bibliography_lemma_cly_v.html` contains **exactly one**
record (Millard, *Cognates Can Be Deceptive*) and three related lemma links.
The existing parser regression `test_lemma_bibliography_preserves_linked_lemma_keys`
asserts `len(page.records) == 1` for this exact source. Requiring at least
**two** records is therefore demonstrably inconsistent with our selected
representative fixture, and cannot establish current upstream drift. The
sanitized live report did not disclose the returned records, so the live
failure **cannot alone prove** whether CAL currently returned zero or one.

Correction strategy: keep the same exact one-request CAL lemma and accept
**one or more nonblank citation records**, rejecting zero/empty placeholders.
Do not weaken the identity or schema checks. If multi-record coverage is
needed in the future, create a separately researched *different* fixture-
backed query known to return multiple records, rather than imposing a
fabricated cardinality on `cly V`. Do not perform another live CAL run
without a distinct explicit acceptance decision; the existing 13-attempt
trace remains evidence of all other functioning surfaces.
