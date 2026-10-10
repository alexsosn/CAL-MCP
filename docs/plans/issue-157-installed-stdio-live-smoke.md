# Issue #157 plan — bounded installed-stdio release smoke

**Date:** 2026-10-10
**Research:** `docs/research/issue-157-installed-stdio-live-smoke.md`
**Gate:** review and accept D-022 before behavior changes or live-run expansion

## Contract

The new release E2E driver invokes the **installed `cal-mcp` executable over stdio**, not direct
Python services, and reports every representative case as `ok`, `drift`, `unavailable`,
`harness`, or `skipped_dependency`. It checks the exposed `outputSchema` and CAL provenance.
A non-OK case makes the run fail; do not lose earlier failures by throwing on the first case.

A fixed operation matrix is shared by `release.yml` and weekly/manual `live-smoke.yml`.
Release validation installs and runs the **exact built wheel** from build-and-test. The scheduled
job builds/installs its checked-out revision (no claim of verifying already published artifacts).

Use no automatic pagination, no arbitrary URLs, no hidden candidate/range expansion, no concurrent
MCP calls, and no retries in the smoke subprocess.

## Hard upstream budget

D-022 specifies a maximum **25 actual transport attempts per run**. Implement an opt-in per-process
budget at the CAL transport boundary shared by all operations, enforcing before each attempt.
The smoke process explicitly enables it in its environment with concurrency 1, retries 0, and
the existing bounded completed-response cache. A client-side MCP call limit is secondary.

Do not leave the old nine-request live smoke running in the same schedule/release path on top of the
25-attempt suite. A local dry-run with request accounting must prove that the final selected matrix
fits within the cap before enabling the live workflow.

## Research → RED → GREEN gates

1. Land the reviewed D-022 decision and this plan; retain current nine-request behavior until the
   new driver and offline tests are ready.
2. **RED (offline)**:
   - fake stdio MCP server has one correct case, one `is_error` drift, one unavailable error,
     one malformed `outputSchema` response, and a dependency-skipped follow-up;
   - verify correct category and aggregate failure report, without leaking HTML/body;
   - show provenance/schema validation catches a nominally successful but corrupt result;
   - show cache hits cost zero and a 26th transport attempt is rejected *before* network I/O;
   - show retries, if accidentally reenabled, count each network attempt;
   - show no default production request cap from merely running `cal-mcp`.
3. **GREEN**: narrowly implement a smoke-only config surface, hard server-side transport guard, and
   stdio-driver orchestration/validation. Keep existing tool inputs/results unchanged.
4. Select representative fixed CAL cases under the measured 25-attempt budget; preserve exact
   returned selector usage for chained steps. Add a bounded verb lookup only after #237/#240.
5. Wire one E2E execution into both release and scheduled/manual live workflows. The publish job
   must depend on a passing E2E job; do not allow `continue-on-error`.
6. Run Ruff, mypy, pytest in both CI matrices with outbound CAL disabled.
7. **Live validation (explicit, capped)**: run the installed wheel via stdio against CAL once,
   capture per-case status and actual attempt count, verify exactly one active smoke suite and
   confirm total <= 25. Do not automatically rerun on failure without a new explicit decision.
8. Remove all temporary test/probe workflows. Rerun workflow-free exact-head CI.
9. Perform a fresh logically independent adversarial review of the exact SHA and only then merge.

## Non-goals

No v0.1 tag creation or PyPI upload; no external service; no CAL scrape/crawl; no corpus index;
no public MCP tool added; no unrelated parser work.

## User-facing documentation

Update `wiki/testing.md`, `docs/installation.md`,
`docs/integrations/standalone-mcp.md`, `wiki/decisions.md`, and #15 release notes for the
new exact artifact/transport/schema/error/budget gate.

## Release sequencing

Blocked for full live green by current verb issues #237/#240. The driver and its offline tests
can be implemented independently once D-022 is accepted; publication stays under #15.

## Fixed chained case

After the fixed `text_search("Tel Dan")` case succeeds, the runner calls
`cal_text_page` once using the first returned match that explicitly has
`follow_up_tool="cal_text_page"`. Preserve the exact returned `file_id` and
`subtext_id`; do not fetch any other rows, links, or catalogue pages.
If the parent failed, classify the step as `skipped_dependency` without a CAL
request. If a successful parent has no trustworthy direct hit, report `drift`
without constructing a synthetic selector. Use deterministic fake-client tests
before implementing. This adds one potential transport attempt within D-022's
**total** 25-attempt limit, not an extra budget.
