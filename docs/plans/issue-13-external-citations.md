# Issue #13 plan — bounded external/non-online-text citations

**Plan date:** 2026-09-05

This plan follows the repository gate sequence: research → plan → test-only RED → minimal implementation → GREEN → documentation → exact-SHA skeptical review → review-regression RED/GREEN when required → fresh whole-PR review → merge.

## Public contract

Expose three explicit operations matching CAL's current researcher workflow:

```text
cal_external_citation_dialects()
cal_external_citation_sources(dialect_id)
cal_external_citations(source_abbrev)
```

These are deliberately separate from `cal_citation_text_search`:

- `cal_citation_text_search(query)` searches English words inside CAL citations;
- the new workflow discovers cited-but-not-online source texts by CAL dialect/source and retrieves the citations for one exact CAL source abbreviation.

Do not expose a generic free-text search invented by CAL-MCP. Do not represent external source abbreviations as online CAL `file_id` values.

## Input contract and request bounds

### Dialect discovery

`cal_external_citation_dialects()` has no caller arguments and performs exactly one GET to CAL's current Citation Finder page.

Return CAL's current ordered dialect choices as opaque `dialect_id` + rendered `label`. Do not hard-code the current 19 dialects into the MCP schema because CAL owns this selector and may change it.

### Source discovery

`cal_external_citation_sources(dialect_id)` accepts one opaque decimal CAL dialect identifier returned by the discovery call.

Validation before transport:

- must be a string;
- trim ASCII spaces only;
- 1–6 ASCII decimal digits;
- no other whitespace/control characters.

Perform exactly one GET to the current source-list surface. Private CAL fields such as `dial` and fixed UI control `dial1=6` remain adapter internals.

### Citation retrieval

`cal_external_citations(source_abbrev)` accepts one exact source abbreviation returned by source discovery.

Validation before transport:

- must be a string;
- trim ASCII spaces only;
- nonempty;
- maximum 128 Unicode code points;
- reject line breaks, tabs, and other non-ASCII-space whitespace/control characters;
- otherwise preserve punctuation/case exactly rather than maintaining a speculative local abbreviation grammar.

Perform exactly one GET to the current citation-result surface. Private CAL field `abbrev` remains internal.

Every public operation performs one CAL request. No operation automatically invokes a later stage.

## Typed models

Add a focused `src/cal_mcp/external_citations.py` module rather than overloading English citation-text search models or online passage models.

Planned types:

- `ExternalCitationParseError(CalContentError)`;
- `ExternalCitationDialect(dialect_id, label)`;
- `ExternalCitationSource(abbreviation, description, citations_url)`;
- `ExternalCitationHit(lemma_key, lemma_label, part_of_speech, entry_url, reference, gloss, source_text, translation)`;
- page types for dialect/source/citation parsing;
- `ExternalCitationProvenance(source, source_url, retrieved_at, operation, dialect_id?, source_abbrev?)`;
- result types for each public operation with `to_dict()` serialization.

`ExternalCitationHit` must remain visibly different from an online-corpus passage/token reference. It carries CAL's rendered external-source `reference` string and optional citation content, but no `file_id`, subtext ID, online page, or guessed machine coordinate.

Required fields for a nonempty citation row:

- canonical CAL `lemma_key` from the lexical-entry URL;
- nonempty rendered `lemma_label`;
- same-origin CAL `entry_url`;
- nonempty rendered external-source `reference`.

Nullable rendered fields because current CAL rows may omit or leave them empty:

- `part_of_speech`;
- `gloss`;
- `source_text`;
- `translation`.

Do not fabricate absent values.

## Parser contracts

All new parsers must ignore `style` and `script` subtrees before semantic collection and fail closed on an unclosed ignored subtree, following the hardened existing parser pattern.

### Dialect page

Require the current semantic marker `Choose a Dialect`.

Parse ordered anchors from the current citation-source target family. For every accepted choice:

- target must resolve to CAL's origin;
- path must be exactly the expected source-list path;
- query must contain exactly one nonempty decimal `dial` identifier;
- duplicate dialect IDs are drift;
- visible label must be nonempty.

The current fixed `dial1=6` is a private UI field. The parser may validate the current observed value if present, but it must never enter the public model.

A page with the marker but no valid choices is parser drift; no explicit empty state is known for the root selector.

### Source-list page

Require the current external-source semantics (`Texts With Citations, No Full Text Yet` and/or the equivalent instruction that the listed texts have citations in the database).

Parse ordered `cit-row` semantic records. Each accepted source requires:

- exactly one `cit-abbrev` navigation link;
- same-origin target resolving to the exact citation-result path;
- exactly one nonempty `abbrev` query value;
- nonempty rendered abbreviation matching that query value;
- optional rendered `cit-defined` description preserved as text without attempting bibliographic decomposition.

Reject duplicate abbreviations, contradictory/multiple citation targets, cross-origin targets, malformed query values, or successful-looking pages lacking both rows and CAL's explicit empty marker.

Current explicit empty marker:

```text
No extra citations for that dialect are currently found.
```

That marker with source rows is contradictory drift.

### Citation-result page

Require a rendered heading equivalent to `Citations for <source_abbrev>` and preserve the parsed source abbreviation. The service must verify that it matches the exact submitted abbreviation rather than accepting a wrong-source response.

Current explicit empty marker:

```text
No citations for "<source_abbrev>" are currently stored.
```

A valid nonempty page parses ordered `cit-entry` records. For every entry:

- exactly one `a.cit-lemma` link;
- same-origin target resolving to CAL's exact lexical-entry path;
- exactly one `lemma` query value;
- current `cits=all` navigation semantics accepted/validated but not exposed publicly;
- returned lemma key validated through neutral shared `validate_lemma_key`; `ValueError` from returned markup is translated to `ExternalCitationParseError`;
- rendered lemma label required;
- rendered `cit-coord` external-source reference required;
- `cit-pos`, `cit-gloss`, `cit-text`, and `cit-xlation` are nullable rendered fields.

If CAL renders `result-count`, require it to equal the number of parsed entries. A count/entry mismatch is drift. Duplicate citation rows are preserved in document order rather than deduplicated.

Reject empty-marker + record contradictions, wrong-source headings, cross-origin lexical links, wrong endpoint families, duplicate lemma query values, malformed returned lemma keys, and pages with neither recognized entries nor explicit empty marker.

Never follow a lexical-entry link automatically.

## Service/request contracts

Add `ExternalCitationService` using only the shared `CalHttpClient`:

```text
dialects()
  -> GET citation finder
  -> cache namespace external-citation-dialects-v1

sources(dialect_id)
  -> GET one source list with private current CAL fields
  -> cache namespace external-citation-sources-v1

citations(source_abbrev)
  -> GET one exact source citation page
  -> cache namespace external-citations-v1
```

Each service method validates caller input before transport, performs one `fetch()`, invokes one parser, and returns provenance from the actual response URL/retrieval time.

No service method loops, fetches the next stage, opens lexical entries, or calls the online text browser.

## Public MCP schema

Register exactly:

```text
cal_external_citation_dialects()
cal_external_citation_sources(dialect_id)
cal_external_citations(source_abbrev)
```

MCP schemas must not expose current CAL-private names or controls including:

```text
dial
dial1
abbrev
cits
lemma
```

Top-level server instructions must explain the distinction from `cal_citation_text_search`, and describe the explicit discovery → source → citation composition.

## Test-first RED sequence

Before production code, add reduced semantic fixtures/tests covering at minimum:

1. ordered dialect discovery with opaque IDs/labels;
2. duplicate/cross-origin/wrong-target/missing-marker dialect drift;
3. ordered source rows with exact abbreviation, rendered description, and citation URL;
4. source row with missing optional description;
5. explicit no-sources marker → empty success;
6. source-row/empty-marker contradiction, duplicate abbreviation, malformed/cross-origin target, and unrecognized-empty page → drift;
7. multiple citation entries preserving canonical lemma keys, rendered labels/POS/references/gloss/source text/translation and Unicode;
8. a valid citation entry with optional POS/gloss/source/translation absent;
9. explicit no-citations marker → empty success;
10. rendered count mismatch, wrong-source heading, marker/data contradiction, cross-origin or wrong-family lemma link, duplicate/malformed lemma query, malformed returned lemma key, and unrecognized-empty page → drift;
11. style/script semantic contamination ignored and unclosed ignored subtree rejected;
12. service request mapping/provenance for all three operations and exact one-request behavior;
13. invalid `dialect_id` / `source_abbrev` rejected before transport;
14. no hidden follow-up request from source discovery or citation parsing;
15. MCP introspection exposes exactly the three public tools and hides CAL-private fields;
16. top-level server instructions distinguish this workflow from English citation-text search.

The primary RED is valid only when install, Ruff lint/format, and strict mypy are green while pytest fails solely because the new external-citation module/tools do not yet exist.

## Minimal GREEN implementation

Implement only the models, validators, three small fail-closed HTML parsers, service methods, MCP registrations, and serialization required by the RED suite.

Reuse only neutral shared helpers where semantics genuinely match. `validate_lemma_key` is a neutral shared helper. Do not import private parsing/validation functions from English search, concordance, lexicon, Targum, or Syriac modules merely to reduce a few lines.

Do not add:

- an alternate HTTP stack;
- automatic dialect/source enumeration;
- lexical-entry expansion;
- online-text lookup for the external reference;
- source-text reconstruction or third-party corpus fallback;
- fuzzy source-abbreviation matching;
- invented pagination;
- a local citation index.

## Documentation gate

Before independent review:

- add `docs/tools/external-citations.md`;
- update README Citations row/status, current-development-state list, and documentation map;
- update server routing instructions;
- explain the distinction from `cal_citation_text_search` and online text browsing;
- document the three explicit caller-controlled stages and one-request bound for each;
- document external-source reference semantics and nullable citation fields;
- document explicit empty states, parser drift, provenance, no pagination, and no automatic lexical-entry traversal;
- update fixture provenance metadata.

No architecture decision update is expected unless implementation discovers a durable boundary change not already covered by D-001/D-004/D-006/D-008.

## Independent skeptical review gate

Review the exact final SHA from the issue/research outward, specifically checking:

- whether this accidentally duplicates or conflates English citation-text search;
- whether external source abbreviations/references are falsely represented as online CAL text IDs/passages;
- hidden dialect/source/lexical-entry traversal or more than one request per operation;
- leaking `dial`, `dial1`, `abbrev`, `cits`, endpoint paths, or DOM classes into public MCP schemas;
- hard-coded dialect selector state that should be live;
- loss/reinterpretation of CAL bibliographic source descriptions;
- nullable current citation fields being fabricated or required incorrectly;
- count mismatches or empty-marker contradictions being silently accepted;
- malformed/cross-origin lexical links and returned lemma keys;
- Unicode/script/style handling;
- provenance inconsistent with the actual requested result page;
- fixtures cleaner than the live structures recorded in research;
- docs/tool instructions that could cause an agent to use the broader/wrong citation operation.

Any blocker must first receive a test-only review-regression RED, then a minimal fix/GREEN, full CI, and a fresh exact-SHA whole-PR review.

## CAL load bound

Production: exactly one CAL request per public operation. Users explicitly choose whether to proceed from dialect → source → citations and whether to follow a lexical entry in another later action.

Research for this issue used seven fixed bounded branch-only requests across three runs; temporary workflows were removed before this plan was frozen. Normal tests are offline fixtures only.

## Execution record

- Primary test-only RED: `8d9e3978f351eb9c3dc913e540ace5c909f50112`.
- First documented GREEN: `b94dc404e9ed94877735ae3fd9449d9168c2cdad`, with 327 tests passing.
- First skeptical review found source-abbreviation format-control validation and missing concrete documentation-example gaps. The review-regression RED had 327 passing / 2 failing tests; minimal fixes reached 329 passing tests.
- Fresh whole-PR review then found a composability gap for CAL-returned source abbreviations containing Unicode format controls. A dedicated review-regression RED had 329 passing / 1 failing test.
- The minimal returned-identifier parser fix is applied; this checkpoint exists to trigger authoritative full CI on the exact helper-free review candidate before the final whole-PR review.
