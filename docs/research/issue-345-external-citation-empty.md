# Issue #345 — CAL external citations empty positive-case investigation

Date 2026-11-15. Baseline main `93eba20b2fd0d2d098eac76a9e226f5e3ae0e330`.

## Measured evidence

[Installed-wheel smoke run #43736509616](https://github.com/alexsosn/CAL-MCP/actions/runs/43736509616), exact candidate `1bb67d50e2c153e16f326d34a5cb5dc58ae6b261`: 15 paced real CAL starts, 14 first cases succeeded, then the CAL-returned external-source abbreviation `1CorH` produced a **schema-valid empty citations list** and the positive-result smoke stopped with `drift: missing representative CAL result rows`. No 429, parser exception or failed transport. The current `src/cal_mcp/external_citations.py::parse_external_citations_page` rejects empty lists *unless* CAL presents a source-matching explicit no-citations marker. Therefore successful empty is a valid CAL response, not evidence of malformed HTML.

The older 2026-09-05 fixture `tests/fixtures/cal/external_citations_1corh.html` contains three historical citations for `1CorH`; the 2026-09-24 source-list fixture `external_citation_sources_syriac_current.html` includes `1CorH`, `EbPar` (twice, same URL) and `JS` (twice, same URL). Source-list membership does not guarantee that any given citation page remains populated. Documentation currently claims `1CorH` yields a nonempty list; this claim is stale against the live 2026-11-15 response and must be corrected with explicit dated evidence.

## Research hypothesis and narrow probe

A live current Syriac source list may offer another abbreviation with actual citations; `EbPar` is a **candidate**, not a guaranteed positive result. We must not use unverified guesses in a followup. Select only `EbPar` if it is present in the **fresh typed result** of one `ExternalCitationService.sources("6")` call, and verify its canonical `citations_url` equals the same-origin `https://cal.huc.edu/displaycits.abbrev.php?abbrev=EbPar`; otherwise stop without attempting citations.

On a fresh wheel and with explicit nonpublishing, one process makes max 2 CAL transport attempts, concurrency=1, retries=0, cache disabled, >=60s spacing; no other CAL jobs concurrently. The read-only report includes candidate selector, typed result status/count, transport attempts, and sanitized error category only, **no CAL lexical/citation bodies or raw HTML**. If `EbPar` yields nonempty citations, update issue #340's smoke to source-select the *measured* example rather than relaxing the positive contract; if it yields empty, keep #345 blocked and research a different source separately.

## Evidence caveats

These runs demonstrate behavior at particular source SHAs, not final all-37 exact-release-wheel acceptance. v0.2.0 must remain untagged/unpublished until an end-to-end installed-wheel check verifies all 37 tool contracts on one candidate. Do not automatically retry 429 or parse failures.


## Live result: CAL-derived EbPar is positive (2026-11-15)

[One-off GitHub Actions run #43744820854](https://github.com/alexsosn/CAL-MCP/actions/runs/43744820854), tested exact source SHA `5936ddc5486f830b6feef13d56a2f947f7d78f4b` via fresh installed development wheel. One live `cal_external_citation_sources("6")` response included the candidate `EbPar` with matching canonical same-origin citation URL; a second, independently paced `cal_external_citations("EbPar")` returned **26** typed citation records. Sanitized report: `{"status":"positive","source_abbrev":"EbPar","total_citations":26,"actual_cal_transport_attempts":2,"max_cal_transport_attempts":2}`. No retries, no lexical text or full CAL HTML in logs. This resolves the positive fixture candidate, but **does not** prove all MCP calls until the separate stdio MCP path is re-tested.

The previously returned `1CorH` empty response is not a CAL parser regression: the current parser requires CAL's explicit no-citations marker for an empty successful result and validates source identity. The release acceptance should no longer choose a nonempty historical fixture as its positive live exemplar. Use the exact currently discovered `EbPar` link, reject any contradictory duplicate, and require nonempty citation records in the stdio tool result.


## Contradictory current MCP result — positive probe does not release the blocker (2026-11-15)

[Installed-wheel MCP run #43758789410](https://github.com/alexsosn/CAL-MCP/actions/runs/43758789410), source SHA `41b89ba5f41a0d3df2e7fc0ff5cf8626d8482fc7`: `external_dialects` **ok**, `external_sources` **ok**, `external_citations` **drift / missing representative CAL result rows**; exactly **3 real CAL starts**, paced by 60 seconds, no retries, no raw lexical data in logs. The validated source selector was changed from stale `1CorH` to exact CAL-returned `EbPar`, and offline adversarial tests prove that any other source or incorrect URL must be rejected.

This is a **cross-path discrepancy**: one earlier **two-request** service-only probe (sources → EbPar citations; cache disabled) returned 26; a **three-request** stdio MCP sequence (dialects → sources → EbPar citations; process-local cache enabled) returned a schema-valid empty list. A process-local cache *hit* is unlikely to explain the latter because 3 actual transport starts were counted for 3 tools; however the extra upstream `citfinder.html` request and HTTP session cookies may affect upstream state, or CAL may be temporarily inconsistent. The MCP server and direct probe call the **same** `ExternalCitationService.citations()` parser. Do not attribute this failure to a stale fixture, source caching, cookie state, or parser bug without discriminating evidence; none is established.

**Next TDD-gated bounded discriminator:** run one additional three-request service-only probe with the actual dialect discovery first, then sources, then EbPar citations, in a fresh installed wheel with the same no-retry/max-concurrency-one, >=60s spacing, source-derived canonical target, and sanitized output. Compare only `status`, `total_citations`, and actual CAL attempt count; no CAL body, lemma or cookie values. If its output is empty, session/order dependence or upstream variability remains; if positive, investigate stdio/server differences. Keep #345 and the all-37 release gate #340 open.
