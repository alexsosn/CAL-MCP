# Issue #39 — current CAL recent-bibliography surface

**Research checked:** 2026-11-04 (public CAL browser page), with raw-HTML structural evidence from bounded GitHub Actions probes 2026-10-10. No new bulk fetch or link traversal.

## Provenance and observed upstream contract

- The official [Bibliographic Resources index](https://cal.huc.edu/bibliography/index.html) links “View the five most recent years of bibliographic records” directly to [GET /getrecentbib.php](https://cal.huc.edu/getrecentbib.php), with no request parameters, form inputs, user-selected years, or archive offset.
- The rendered page is headed **CAL Recent Bibliography**; on 2026-11-04 its ordered citations cover 2021–2025 (in increasing years), despite the calendar year being 2026. The adapter MUST NOT calculate the five-year window, promise 2026, or infer a record's publication year from arbitrary four-digit substrings.
- The listing includes repeated-looking works and multilingual titles, plus linked CAL text/subject tags and lemma keys. Preserve every record, citation, its ordered links and the upstream order without deduplication or local subject classification.
- Prior explicitly bounded raw-HTML one-GET checks, [run 38067292589](https://github.com/alexsosn/CAL-MCP/actions/runs/38067292589) and [run 38067387758](https://github.com/alexsosn/CAL-MCP/actions/runs/38067387758), recorded HTTP 200, 63,520 response bytes, 126 <p> blocks, 362 links and CAL's legacy bibliographic title tags. There were no HTML forms or obvious pagination links. The second check reported 2021–2025 order, a 2010 year-token outlier inside one paragraph, and cross-year citations. The paragraph count is **not** assumed to prove the record count, nor is any year regex a grouping schema. This is dated *structural evidence*, not a captured full HTML fixture.
- The browser-visible page shows no next/previous control. Raw structural checks also found no obvious pagination. No documented CAL continuation token or result limit is available. If a material continuation control appears later, reject it as drift rather than silently returning the first page.
- CAL exposes a source-specific explicit no-data marker on some **targeted** bibliography result pages, but no explicit empty marker has been established for the recent snapshot. Do **not** reuse the query-specific empty rule to turn a blank recent page into successful empty results. Until observed otherwise, missing records are parser drift.
- HTTP budget: one fixed GET per operation, with the shared default 2 MiB decoded body limit, timeout, same-origin redirects, cache, retry and pacing rules. No extra record-link requests or downstream archive enumeration.

## Model decision grounded in evidence

The page exposes ordered bibliographic paragraphs, not a typed year-group field or stable year selector. Reuse existing `BibliographyRecord` (citation + ordered `BibliographyLink`) and existing provenance information. Return a recent-specific result with its CAL heading and ordered record sequence; **do not** create a synthetic year-grouping key. Use empty `original_query`/`submitted_query` provenance strings to indicate the zero-argument operation, and name it `bibliography_recent`.

## Residual uncertainty / verification gate

The 2026-10-10 raw counts and 2026-11-04 rendered view are complementary, not proof that markup never changes. Test the reduced structural shape and fail closed on missing/incomplete cards, unexpected result heading, and an explicit pagination control. Before a new release, run one bounded installed-wheel live call of this operation to validate actual current parsing, with no automatic retries beyond the approved client policy and no traversal.
