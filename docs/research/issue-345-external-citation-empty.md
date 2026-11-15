# Issue #345 — source-backed external citation acceptance and false smoke drift

Date 2026-11-15. Baseline main `93eba20b2fd0d2d098eac76a9e226f5e3ae0e330`.

## Measured evidence

[Installed-wheel smoke run #43736509616](https://github.com/alexsosn/CAL-MCP/actions/runs/43736509616), exact candidate `1bb67d50e2c153e16f326d34a5cb5dc58ae6b261`: 15 paced real CAL starts, 14 first cases succeeded, then the smoke case for CAL-returned `1CorH` stopped with `drift: missing representative CAL result rows`. No 429 or failed transport was reported. **The structured payload contents were not logged**, so this trace does not establish whether CAL returned any `1CorH` citations. The later source review below proved the smoke outcome was caused by a shared-validator case-name collision. The parser itself only returns a successful empty list when CAL presents an explicit source-matching no-citations marker.

The older 2026-09-05 fixture `tests/fixtures/cal/external_citations_1corh.html` contains three historical citations for `1CorH`; the 2026-09-24 source-list fixture `external_citation_sources_syriac_current.html` includes `1CorH`, `EbPar` (twice, same URL) and `JS` (twice, same URL). Source-list membership does not guarantee that any given citation page remains populated. The historical `1CorH` fixture is valid as a September capture, but **current `1CorH` content was not measured** by the November smoke due to the test-case collision; documentation must avoid asserting either a current positive count or an explicit empty state.

## Research hypothesis and narrow probe

A live current Syriac source list may offer another abbreviation with actual citations; `EbPar` is a **candidate**, not a guaranteed positive result. We must not use unverified guesses in a followup. Select only `EbPar` if it is present in the **fresh typed result** of one `ExternalCitationService.sources("6")` call, and verify its canonical `citations_url` equals the same-origin `https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar`; otherwise stop without attempting citations.

On a fresh wheel and with explicit nonpublishing, one process makes max 2 CAL transport attempts, concurrency=1, retries=0, cache disabled, >=60s spacing; no other CAL jobs concurrently. The read-only report includes candidate selector, typed result status/count, transport attempts, and sanitized error category only, **no CAL lexical/citation bodies or raw HTML**. If `EbPar` yields nonempty citations, update issue #340's smoke to source-select the *measured* example rather than relaxing the positive contract; if it yields empty, keep #345 blocked and research a different source separately.

## Evidence caveats

These runs demonstrate behavior at particular source SHAs, not final all-37 exact-release-wheel acceptance. v0.2.0 must remain untagged/unpublished until an end-to-end installed-wheel check verifies all 37 tool contracts on one candidate. Do not automatically retry 429 or parse failures.


## Live result: CAL-derived EbPar is positive (2026-11-15)

[One-off GitHub Actions run #43744820854](https://github.com/alexsosn/CAL-MCP/actions/runs/43744820854), tested exact source SHA `5936ddc5486f830b6feef13d56a2f947f7d78f4b` via fresh installed development wheel. One live `cal_external_citation_sources("6")` response included the candidate `EbPar` with matching canonical same-origin citation URL; a second, independently paced `cal_external_citations("EbPar")` returned **26** typed citation records. Sanitized report: `{"status":"positive","source_abbrev":"EbPar","total_citations":26,"actual_cal_transport_attempts":2,"max_cal_transport_attempts":2}`. No retries, no lexical text or full CAL HTML in logs. This resolves the positive fixture candidate, but **does not** prove all MCP calls until the separate stdio MCP path is re-tested.

The purported `1CorH` empty response was never established: its smoke result went through the colliding case-name predicate. The historical `1CorH` fixture alone does not justify selecting it as a current positive exemplar. Use the exact currently discovered `EbPar` link, reject any contradictory duplicate, and require nonempty citation records in the stdio tool result.


## Contradictory current MCP result — positive probe does not release the blocker (2026-11-15)

[Installed-wheel MCP run #43758789410](https://github.com/alexsosn/CAL-MCP/actions/runs/43758789410), source SHA `41b89ba5f41a0d3df2e7fc0ff5cf8626d8482fc7`: `external_dialects` **ok**, `external_sources` **ok**, `external_citations` **drift / missing representative CAL result rows**; exactly **3 real CAL starts**, paced by 60 seconds, no retries, no raw lexical data in logs. The validated source selector was changed from stale `1CorH` to exact CAL-returned `EbPar`, and offline adversarial tests prove that any other source or incorrect URL must be rejected.

At this investigation stage, the **two-request** service probe (sources → EbPar citations) returned 26, whereas the **three-request** stdio MCP sequence (dialects → sources → EbPar citations) reported a false `drift` without exposing citation counts. We initially considered HTTP session and cache differences, but the later source inspection below found a deterministic *case-name collision* in the smoke validator. **The trace did not demonstrate any real empty response from MCP or CAL.**

**Next TDD-gated bounded discriminator:** run one additional three-request service-only probe with the actual dialect discovery first, then sources, then EbPar citations, in a fresh installed wheel with the same no-retry/max-concurrency-one, >=60s spacing, source-derived canonical target, and sanitized output. Compare only `status`, `total_citations`, and actual CAL attempt count; no CAL body, lemma or cookie values. If its output is empty, session/order dependence or upstream variability remains; if positive, investigate stdio/server differences. Keep #345 and the all-37 release gate #340 open.


## Root cause: a *test-case name collision*, not confirmed CAL emptiness (2026-11-15)

Inspection after [direct three-request run #43759573999](https://github.com/alexsosn/CAL-MCP/actions/runs/43759573999) proved that the **same** dialects→sources→EbPar citations sequence returns **26** records through `ExternalCitationService` with 3/3 paced starts, even after explicitly requesting `citfinder.html`. The suspected order-dependent CAL session/cookie effect is **not supported** by this controlled test.

Source review identified a deterministic local smoke-harness bug:
- `src/cal_mcp/stdio_live_smoke.py::DEFAULT_SMOKE_CASES` has `SmokeCase("external_citations", "cal_external_citation_dialects", {})`. Its `_has_representative_content("external_citations", payload)` requires a nonempty `dialects` array with `dialect_id`.
- `src/cal_mcp/pre_release_followup_smoke.py::STEPS` independently named a **different tool** `cal_external_citations` with the *same* test-case name `"external_citations"`. Its `run_cases` calls the shared `evaluate_tool_result` **before** checking the step's own `positive_field="citations"`.
- Consequently any valid successful external-*citations* result (even 26 real citations) necessarily fails the wrong `dialects` predicate with exactly the observed message `drift: missing representative CAL result rows`. The unlogged MCP payload's actual `citations` count is **unknown**, so the earlier report **cannot establish** that MCP returned an empty list.

Remedy is narrow: rename the dependent smoke case to a globally unique internal name (e.g. `external_citation_records`) without changing the public `cal_external_citations` tool or CAL parser, add RED tests for cross-batch case-name uniqueness and a schema-valid synthetic nonempty external-citations payload, then rerun the **same exact 3-MCP-step** installed-wheel acceptance. Release v0.2.0 remains blocked until the rebuilt MCP smoke and an all-37 exact-candidate gate succeed. No code change to the actual CAL adapter is justified by the false drift.


## Three cross-suite case IDs were reused

The cross-matrix collision test also identified `kwic_dialects` and `targum_concordance` as names shared between the independent 13-tool extra smoke and the 21-step dependent smoke. Those did not trigger the current false error because `_has_representative_content` has no special predicates for those two names; the collision nonetheless exposes future regressions when one suite adds an assertion for that name. The repair renames *only the internal dependent smoke case IDs* to `kwic_dialects_selector`, `targum_concordance_followup` and `external_citation_records`, retaining the underlying public MCP tool names, opaque CAL selectors, dependency parents and request budgets unchanged. A new offline test requires **globally disjoint case names across all three live smoke matrices** and checks the two renamed parent links.

Initial RED for this root cause: [CI #43760033363](https://github.com/alexsosn/CAL-MCP/actions/runs/43760033363) had 2 intentional failures and 2462 passed in both matrices (collision and nonexistent new case ID). The successful rebuilt-wheel live MCP report is still needed before accepting the change; do not infer an empty CAL response from the earlier bug.


## Fixed installed-wheel MCP acceptance (2026-11-15)

The [nonpublishing stdio MCP run #43760566728](https://github.com/alexsosn/CAL-MCP/actions/runs/43760566728) on source SHA `a7d64209a54671547d175dfbcd4e2e4342a1c6d4` reported `status: passed`, exactly **3 actual CAL transport starts**, no retries, `external_dialects: ok`, `external_sources: ok`, `external_citation_records: ok`. The final tool's own positive-field check required a **nonempty structured `citations` list**; its exact record count was deliberately not printed in MCP smoke logs. The separate source-only studies yielded 26 `EbPar` records twice (2-request and 3-request flows). This validates the real MCP tool's success path, not just a low-level parser.

The public names `cal_external_citation_dialects`, `cal_external_citation_sources` and `cal_external_citations` remain unchanged; only internal smoke case names were deconflicted. The old v0.1.0 frozen smoke identities remain unchanged. No unsupported claim about current `1CorH` content remains in user-facing docs. The temporary one-off workflows and source-only diagnostic module/tests were deleted after collecting evidence; the committed research record and case-identity regression tests remain.

This closes the isolated false-drift failure after independent review. The broader **all-37 installed-wheel exact-candidate pre-v0.2.0 release gate** remains in issue #340; do not publish based solely on this 3-tool PASS.
