# Issue #39 research — bounded CAL recent bibliography

**Rechecked:** 2026-09-07  
**Baseline:** `main` at `1aa9dd9cd7fe9e4592e586b5b117e271a47c03c8`

## Public surface

CAL's current Bibliographic Resources page exposes a separate task-level action labelled **“View the five most recent years of bibliographic records”**. It targets:

```text
GET https://cal.huc.edu/getrecentbib.php
```

The current UI exposes no caller-controlled year, page, offset, query, or continuation input for this operation. The returned page heading is exactly:

```text
CAL Recent Bibliography
```

A CAL-MCP operation can therefore be parameterless and perform exactly one fixed GET to `getrecentbib.php`.

## Current snapshot semantics

A bounded recheck on 2026-09-07 returned one aggregate page with **132 bibliography records**. The rendered record sequence progresses through publication citations for 2021, 2022, 2023, 2024, and 2025 in that order. No 2026 record is currently present even though the current calendar year is 2026.

Therefore CAL-MCP must not interpret the UI label as `current year - 4` through `current year`, and must not compute a local year window. “Recent” means the snapshot CAL itself currently selects.

The page preserves source order and currently contains at least one exact duplicate citation in the 2023 portion. Duplicate bibliography records must therefore be preserved rather than deduplicated.

## No safe year-group extraction

The current rendered semantic output exposes the records continuously; no verified year-heading or per-year grouping marker is part of the public page semantics at the transitions between years.

Inferring year groups from citation text is not safe. Existing current records include titles containing unrelated four-digit ranges (for example `2010–2015`) in a citation whose publication year is 2022. Choosing either the first or last four-digit token would be an adapter heuristic over bibliography prose rather than a CAL-supplied grouping contract.

Accordingly, the smallest faithful public model should preserve the ordered snapshot as returned and **not manufacture typed year buckets**. Documentation may describe the years observed in the researched snapshot, but the parser/result schema must not derive grouping metadata from citation text.

## Result shape and model reuse

The current snapshot uses the same record semantics already represented by:

- `BibliographyRecord` — citation text plus ordered links;
- `BibliographyLink` — same-origin CAL bibliography navigation with typed author/keyword/lemma semantics where applicable.

These should be reused unchanged. The recent operation needs only a dedicated result wrapper because it is parameterless and not query-shaped:

```text
RecentBibliographyResult(
    heading: str,
    records: tuple[BibliographyRecord, ...],
    provenance: BibliographyProvenance,
)
```

`BibliographyResult` should remain for targeted author/keyword/lemma queries.

`BibliographyProvenance` currently requires `original_query` and `submitted_query`. For a parameterless operation, fabricating an empty or synthetic query would be misleading. The narrow compatible change is to make those fields optional and return `None` for `bibliography_recent`, while preserving exact strings for all existing targeted bibliography operations.

## Pagination and request bound

The current snapshot is one aggregate response. The recheck found no `Next` marker, page control, continuation token, or caller-controlled year selector. CAL-MCP must not invent pagination or enumerate historical years.

Production request contract:

```text
CalRequest(method="GET", path="getrecentbib.php")
```

Exactly one CAL request per uncached operation. Returned record links are data only; the recent operation must not follow them automatically.

The shared HTTP response-size limit continues to bound this aggregate response, and the existing process-local cache/single-flight policy applies normally.

## Heading, empty, and drift semantics

The current non-empty page exposes the exact heading `CAL Recent Bibliography` and bibliography record cards.

No explicit researched marker for an empty recent snapshot has been found. Therefore:

- exactly one recognizable recent heading plus one or more valid records => success;
- recognized heading with zero records and no researched explicit empty marker => parser/upstream drift, not empty success;
- missing/duplicate recent heading => parser drift;
- malformed record or unsafe/cross-origin record link => parser drift through the existing bibliography link validation;
- duplicate valid records => preserve them in source order.

This avoids inventing empty semantics by analogy with targeted bibliography searches, whose no-data marker is query-specific.

## Public operation

Expose:

```text
cal_bibliography_recent()
```

with no scholarly/query arguments. It returns the exact CAL snapshot ordering, bibliography record/link data, and provenance. It performs no local year calculation, sorting, deduplication, pagination, or link traversal.

## Load impact

Research used only a tiny fixed inspection of the single public recent-bibliography endpoint. Normal tests remain offline and fixture-driven. Production is one fixed bounded request per uncached call and does not enumerate corpora or historical years.

## Sources

- `https://cal.huc.edu/bibliography/index.html`
- `https://cal.huc.edu/getrecentbib.php` — bounded recheck 2026-09-07
- `src/cal_mcp/bibliography.py`
- `tests/test_bibliography.py`
- issue #39
