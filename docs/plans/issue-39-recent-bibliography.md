# Issue #39 plan — bounded CAL recent bibliography

**Plan date:** 2026-09-07  
**Research:** `docs/research/issue-39-recent-bibliography.md`

Gate order: research → committed plan → behavior-first test-only RED → minimal implementation → full deterministic/latest-compatible GREEN → documentation → exact-head logically independent adversarial review → guarded merge.

## Contract

Expose one parameterless public operation:

```text
cal_bibliography_recent()
```

It performs exactly one fixed:

```text
GET getrecentbib.php
```

per uncached call and returns CAL's ordered recent-bibliography snapshot.

Do not accept a caller-supplied year/window/page. Do not compute a local five-year range. Do not infer year groups from citation prose. Do not sort, deduplicate, paginate, enumerate historical years, or follow returned bibliography links automatically.

## Models

Reuse unchanged:

- `BibliographyRecord`;
- `BibliographyLink`;
- the existing typed link/query semantics.

Add:

```text
RecentBibliographyResult(
    heading: str,
    records: tuple[BibliographyRecord, ...],
    provenance: BibliographyProvenance,
)
```

Do not force the parameterless snapshot into query-shaped `BibliographyResult`.

Make `BibliographyProvenance.original_query` and `.submitted_query` `str | None`. Existing author/keyword/lemma operations must continue returning their exact strings. `bibliography_recent` returns `None` for both fields rather than fabricated empty/synthetic queries.

## Parser contract

Add `parse_recent_bibliography_page(response)` returning the existing internal `BibliographyPage` shape (`heading`, ordered `records`). Reuse `_BibliographyHTMLParser` so record/card/link extraction and same-origin navigation validation stay shared.

Require:

1. parsing completes with no open record/heading state;
2. exactly one heading equals `CAL Recent Bibliography`;
3. at least one valid record is present;
4. record order and duplicate records are preserved exactly;
5. all existing record/link safety checks remain active.

A recognized recent heading with zero records is parser drift because no explicit current empty marker has been researched. Do not reuse the targeted query-specific `NO data FOR ...` marker as a fabricated recent-snapshot empty contract.

No citation-year extraction belongs in the parser.

## Service contract

Add `BibliographyService.recent()`:

```text
CalRequest(method="GET", path="getrecentbib.php")
```

with no params/data, `cache_namespace="bibliography-recent-v1"`, and provenance:

```text
operation="bibliography_recent"
original_query=None
submitted_query=None
```

The operation returns one `RecentBibliographyResult` and never follows record links.

## Test-only RED

With production untouched, add a reduced semantic fixture and tests that prove the missing behavior:

- recognized `CAL Recent Bibliography` heading parses representative ordered records;
- exact duplicate records remain duplicated and ordered;
- a citation containing unrelated year-like text such as `2010–2015` is preserved verbatim, with no inferred year field/grouping;
- existing same-origin text/subject and lemma link typing is reused;
- recognized heading with zero records fails as `BibliographyParseError`;
- missing/duplicate/wrong recent heading fails as parser drift;
- malformed/cross-origin record links fail through existing guards;
- service performs exactly one parameterless GET and returns `bibliography_recent` provenance with null query fields;
- existing targeted bibliography provenance still contains exact string queries;
- MCP exposes `cal_bibliography_recent` with no public input arguments;
- existing bibliography tools remain present and unchanged.

Write the RED tests so collection, Ruff lint/format, and strict mypy stay green; pytest failures must be limited to the intentionally missing recent-snapshot behavior.

Normal CI remains offline.

## Minimal implementation

Only after a valid RED:

1. generalize provenance query fields to optional without changing existing values;
2. add `RecentBibliographyResult` serialization;
3. add the dedicated recent parser using `_BibliographyHTMLParser`;
4. add `BibliographyService.recent()`;
5. expose `cal_bibliography_recent` in `server.py` and update server instructions;
6. make no changes to request policy, cache behavior, existing bibliography query semantics, pagination, or CAL load.

## Full GREEN

Require both permanent CI jobs on the exact implementation/docs head:

- deterministic constrained dependency environment;
- latest-compatible dependency environment;
- Ruff lint;
- Ruff format check;
- strict mypy;
- complete pytest suite.

No live CAL request belongs in normal CI.

## Documentation gate

Update `docs/tools/bibliography.md` and any capability/index wording that still says four bibliography operations or says the recent snapshot is deferred.

Document explicitly:

- parameterless one-request behavior;
- CAL-selected moving snapshot rather than a client-computed five-year range;
- current researched 2021–2025 observation as an observation, not a schema invariant;
- ordered records and duplicate preservation;
- no year grouping inferred from citation text;
- no pagination/traversal;
- no explicit empty-success marker currently researched;
- null query provenance for this parameterless operation.

If current documentation creates a deterministic contract gap, add a docs regression test before changing prose.

## Independent adversarial review

Freeze the exact final SHA and independently attempt to falsify:

1. the MCP tool is truly parameterless;
2. one uncached tool call creates exactly one GET with no params/data;
3. no current-date or citation-year heuristic influences the result;
4. duplicate records and source order survive;
5. malformed/cross-origin links still fail closed;
6. heading-only output is drift, not invented empty success;
7. existing author/keyword/lemma parsing, request shapes, and provenance do not regress;
8. optional provenance fields do not weaken existing query operations;
9. no hidden link traversal/pagination/year enumeration exists;
10. docs match the actual contract and normal CI remains offline.

Any blocker enters review-regression RED → minimal fix → full GREEN → fresh exact-head review.

## Merge

Immediately before review/merge, re-read PR head and current `main` to detect concurrent work. Integrate current main if needed, repeat full GREEN, and review the exact integrated head.

Merge only the independently reviewed GREEN SHA with an expected-head guard. `Closes #39` should close the issue.
