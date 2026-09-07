# Issue #39 plan — bounded CAL recent bibliography

**Plan date:** 2026-09-07

Gate order: research → committed plan → test-only RED → minimal implementation → focused/full offline GREEN → exact-head logically independent adversarial review → merge.

## Contract

Expose one parameterless public operation:

```text
cal_bibliography_recent()
```

It performs exactly one `GET getrecentbib.php` request and returns CAL's own current recent-bibliography window grouped by the publication years actually present in the response.

Do not accept a caller-supplied year/window/page. Do not compute “current year minus four.” Do not follow returned links or enumerate historical years.

## Models

Reuse `BibliographyRecord` and `BibliographyLink` unchanged.

Add:

- `RecentBibliographyYear` with `year: int` and ordered `records`;
- `RecentBibliographyResult` with ordered `years` and bibliography provenance.

Because this operation has no query, update `BibliographyProvenance.original_query` and `.submitted_query` to `str | None` and serialize them as null for the recent operation. Existing targeted operations must retain their exact string provenance values.

## Parser contract

Add a dedicated recent-page parser that reuses the existing record-card/link extraction but accepts exactly one heading `CAL Recent Bibliography`.

For every returned record:

1. require non-empty citation/link semantics via the existing parser;
2. extract the publication year as the last standalone four-digit year token in the citation;
3. reject a record without a representable year;
4. group adjacent records by year while preserving source order;
5. require year groups to be non-decreasing; do not silently re-sort a backwards year sequence;
6. require at least one record, because no explicit current empty marker has been researched.

Do not require exactly five groups. “Five most recent years” is CAL's UI description; the adapter preserves what CAL returns rather than fabricating missing years.

## Test-only RED

Before production changes add reduced fixtures/tests for:

- representative recent heading and records across ordered year groups;
- a citation title containing older year-like text (`2010–2015`) but publication year 2022, proving the last-year rule;
- same-origin subject/text and lemma links using existing typed link semantics;
- exact source order within/across groups;
- heading present but no records → parser drift;
- record without a publication year → parser drift;
- year sequence 2023 → 2022 → parser drift rather than sorting;
- malformed/cross-origin navigation link → parser drift through the existing link guard;
- service performs exactly one parameterless GET and returns provenance with operation `bibliography_recent` and null query fields;
- existing targeted bibliography service/request/provenance tests remain unchanged;
- MCP schema exposes the parameterless tool and documentation names it.

Establish behavioral RED with Ruff lint/format and strict mypy green; production code remains unchanged through this gate.

## Minimal implementation

- generalize only the internal bibliography record parser enough to share card extraction between targeted and recent pages;
- add the dedicated recent parser/models/service method;
- add `cal_bibliography_recent` to `server.py` and server instructions;
- update bibliography tool docs and docs index/capability matrix where required;
- do not change other bibliography query behavior;
- do not add CAL data, background polling, pagination, or cache policy changes.

## GREEN

Run focused bibliography/server/docs tests, then the complete deterministic suite:

```text
ruff check .
ruff format --check .
mypy
pytest
```

Also require the repository's latest-compatible/dependency CI jobs if present on the branch. Normal CI must remain CAL-independent.

## Independent adversarial review

Review the exact final head from sources and diff, attempting to falsify:

- the tool is truly parameterless and one-request;
- year grouping is CAL-derived, not current-date-derived;
- `2010–2015`-style title dates cannot steal the publication year;
- backwards/missing years fail rather than being silently normalized;
- records/links preserve existing semantics/order;
- provenance does not fabricate a query and existing query operations did not regress;
- no continuation/year traversal was invented;
- no explicit empty state was invented without evidence;
- documentation distinguishes this snapshot from targeted bibliography searches;
- CI is offline and exact-final-head green.

Any blocker receives a test-first review regression, full GREEN, and a fresh exact-head review.

## Merge

Merge only after exact-head GREEN and clean independent review. This feature is post-v0.1/non-blocking and does not alter the external publication blocker on #15 or the Agora dependency #16.
