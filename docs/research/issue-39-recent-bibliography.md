# Issue #39 research — CAL recent-bibliography snapshot

**Rechecked:** 2026-09-07

## Public surface

CAL's current Bibliographic Resources page exposes a separate task-level link labelled **“View the five most recent years of bibliographic records”**:

- https://cal.huc.edu/bibliography/index.html
- target: https://cal.huc.edu/getrecentbib.php

The target is a parameterless GET surface. No caller-controlled year, offset, page, or query input is exposed by the current UI.

## Current returned window

The current page heading is exactly `CAL Recent Bibliography` and its returned records span publication years:

```text
2021, 2022, 2023, 2024, 2025
```

No 2020 record was found on the current snapshot. The current date is 2026-09-07, so CAL's label cannot safely be interpreted as “current calendar year minus four.” The observable contract is instead CAL's own five most recent bibliography years presently represented in this result. CAL-MCP must preserve those returned years and must not calculate or inject a year window locally.

The current order is oldest returned year to newest returned year (2021 → 2025). Within each year, CAL's record order is source order. The adapter should preserve both rather than re-sort by author/title/date.

## Result shape and existing model reuse

The recent page uses the same bibliography-record semantics already represented by `BibliographyRecord` and `BibliographyLink`: citation text plus same-origin CAL navigation links to subject/text tags and lemma bibliography searches. Representative current records include:

- a 2021 record linked to `history`;
- records with multiple text/subject links;
- lemma-specific links such as `$r$yp N`;
- a 2022 record whose title itself contains `2010–2015` but whose publication year is 2022.

That last shape is important for year extraction: selecting the first four-digit token would misgroup a valid citation. For current CAL citation formatting, the publication year is the **last standalone four-digit year token** in the rendered citation. A reduced regression should pin this distinction. If a returned card lacks any representable publication-year token, the snapshot parser should fail closed rather than guess.

The current bibliography record/link parser already enforces:

- non-empty record citation text;
- non-empty link labels/targets;
- same-origin CAL links;
- typed navigation semantics for the three existing bibliography query endpoints.

Those semantics should be reused rather than duplicated.

## Pagination and boundedness

The current snapshot is one aggregate response. Inspection found no `Next` marker, continuation token, page control, or caller-controlled year selector. CAL-MCP therefore has no evidence for a pagination contract and must not invent one.

The production operation can be exactly one fixed GET to `getrecentbib.php`. It must not enumerate historical years, follow record links, or issue one request per returned year.

The shared HTTP response-size policy continues to bound the aggregate page. Normal CI remains offline and fixture-driven.

## Empty/drift semantics

The current non-empty page exposes records but no researched explicit “no recent bibliography” marker. CAL-MCP must not invent an empty-success phrase from analogy with targeted bibliography search. A page with the recognized recent heading but no parseable records is therefore parser/upstream drift until CAL exposes and research verifies an explicit empty state.

Likewise, a recent-looking page with:

- no single recognizable `CAL Recent Bibliography` heading;
- malformed record/link semantics;
- no publication year for a record;
- a year sequence that moves backwards after a newer year has begun;

should fail explicitly rather than silently drop or re-sort content.

## Public model decision

Do not force this parameterless snapshot into `BibliographyResult`, whose public contract is query-shaped (`query_kind`, `query`, targeted result heading).

Add a dedicated recent result with typed year groups:

- `RecentBibliographyYear(year: int, records: tuple[BibliographyRecord, ...])`;
- `RecentBibliographyResult(years: tuple[RecentBibliographyYear, ...], provenance: BibliographyProvenance)`.

The provenance operation is `bibliography_recent`; because the upstream operation is parameterless, `original_query` and `submitted_query` should not be fabricated. If the shared provenance type remains query-shaped, make those fields optional rather than emitting fake values.

Public MCP tool: `cal_bibliography_recent()` with no scholarly/query arguments. One tool call performs exactly one CAL request.

## Sources

- https://cal.huc.edu/bibliography/index.html
- https://cal.huc.edu/getrecentbib.php
- current page rechecked 2026-09-07
