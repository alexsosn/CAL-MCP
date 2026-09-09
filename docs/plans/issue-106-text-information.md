# Issue #106 plan — expose CAL text-information metadata

**Plan date:** 2026-09-09
**Research:** `docs/research/issue-106-text-information.md`

Sequence: research → plan → synchronize current main → deterministic test-only RED → minimal implementation → docs → full GREEN → logically-independent exact-head adversarial review → guarded merge.

## Frozen public contract

Add one bounded operation:

```text
cal_text_information(
    file_id: str,
    subtext_id: str | None = None,
)
```

Both values use the existing CAL decimal identifier validation rules. Do not expose CAL's private `coord` parameter or accept an arbitrary URL.

Private selector construction:

```text
subtext_id is None  -> coord=<file_id>
subtext_id provided -> coord=<file_id><subtext_id>
```

Preserve the exact validated strings; do not convert to integers or invent padding.

One public call performs exactly one:

```text
GET get_file_info.php?coord=<composed selector>
```

## Result contract

Keep the heterogeneous scholarly metadata faithful instead of inventing a normalized bibliography schema.

```text
TextInformationStatus
  FOUND = "found"
  NOT_FOUND = "not_found"

TextInformationResult
  status: TextInformationStatus
  file_id: str
  subtext_id: str | null
  metadata: ordered tuple[str, ...]
  provenance: TextProvenance-compatible metadata
```

For `found`, `metadata` contains the ordered nonempty semantic text lines/paragraphs rendered below CAL's `Text Information` heading after deterministic whitespace cleanup. Preserve CAL wording and ordering.

For CAL's explicit `No information on record for this text.` marker, return `not_found` with `metadata=()`.

Do not create fields such as `edition`, `findspot`, `manuscript`, `bibliography`, or `warning` unless future research establishes stable explicit CAL markup for them.

Returned URLs inside free-form CAL metadata are text/navigation evidence only; this tool follows none of them.

## Missing / drift boundary

The direct research probe demonstrated that plain automated requests can return CAL's generic anti-scrape page with HTTP 200 for both known-valid and invalid selectors. HTTP success alone is never a metadata success.

The subsequent indexed-current-page recheck established an explicit missing marker at `get_file_info.php?coord=00000639`:

```text
Text Information
No information on record for this text.
```

Parser rules:

- require the semantic `Text Information` heading;
- exact current missing marker maps to `not_found` with empty metadata;
- otherwise require at least one nonempty metadata line for `found`;
- heading with neither metadata nor the explicit marker is `TextParseError`;
- generic anti-scrape/maintenance/unrecognized successful HTML is parser/content failure, never `not_found`;
- do not infer missing state from HTTP status, body size, selector shape, or an unrecognized body.

## TDD RED gate

Commit tests only after this plan and after synchronizing the branch to current `main`.

### Direct selector RED

For `file_id="6042013"`, assert exactly one request:

```text
GET get_file_info.php?coord=6042013
```

Parse a reduced semantic Ephrem fixture, return `status="found"`, and preserve its ordered metadata lines and provenance.

### Subdivided selector RED

For `file_id="43200", subtext_id="336"`, assert exactly one request:

```text
GET get_file_info.php?coord=43200336
```

Use a reduced Hatran fixture preserving corpus-level and item-level lines in order. This pins string concatenation without numeric normalization or inferred padding.

Add a second composition edge such as `file_id="56000", subtext_id="128"` at request-construction level to prevent a Hatran-specific implementation. Preserve leading zeroes in a synthetic request-construction case.

### Validation RED

Malformed/blank/non-decimal `file_id` or `subtext_id` fails locally before transport.

### Missing / parser-drift RED

Reduced fixtures must cover:

- genuine `Text Information` page with ordered metadata -> `found`;
- genuine `Text Information` page containing exactly `No information on record for this text.` -> `not_found`, empty metadata;
- page with heading but no metadata/missing marker -> `TextParseError`;
- generic CAL anti-scrape body -> `TextParseError` or the shared content error path;
- unrelated successful HTML -> `TextParseError`.

The missing fixture is now evidence-backed by current CAL indexed output and is no longer fabricated.

### Public MCP schema RED

Require a new `cal_text_information` tool with only `file_id` and optional `subtext_id`. Assert no `coord`, URL, page, recursive, or fetch-all parameter leaks into the schema.

A valid RED requires both CI dependency matrices to pass install/environment validation, Ruff lint, Ruff format, and strict mypy while pytest fails only for the missing new operation/parser/service contract.

## Minimal implementation

Prefer a focused text-information parser/service in `texts.py` unless source size/cohesion clearly justifies a separate `text_information.py`; do not refactor unrelated text-page code merely to add the operation.

Implementation steps:

1. add `TextInformationStatus`, immutable page/result model(s), and serialization;
2. add helper that composes the private decimal `coord` from validated public identifiers;
3. add parser requiring the `Text Information` semantic heading, recognizing only the exact current missing marker as `not_found`, and otherwise requiring nonempty ordered metadata;
4. add `TextService.information(...)` making one request;
5. expose `cal_text_information` in `server.py`;
6. update exact public-tool bootstrap/docs contracts from 28 to 29 tools;
7. keep all existing text catalogue/search/page behavior unchanged unless a separate regression proves otherwise.

## Documentation

Update:

- `docs/tools/texts.md` with text -> explicit metadata follow-up, selector composition, free-form metadata semantics, explicit `found`/`not_found`, request bound, and drift boundary;
- `docs/index.md` / README current tool count and text capability description;
- provenance/error docs only if the new explicit missing state needs cross-linking.

Explicitly state that CAL's metadata can contain source/edition/editorial/bibliographic/quality notes but CAL-MCP preserves the rendered information rather than normalizing it into inferred fields.

## Existing page-parser concern

Research suggests current CAL info selectors can be composite while `_page_text_ref()` currently compares a returned `coord` directly with the requested base `file_id`. Do **not** alter that code under #106 without a dedicated failing regression grounded in a current page fixture/link.

If TDD or independent review confirms the existing page parser rejects a real subdivided page because of this distinction, file a focused bug issue and handle it through its own research/RED/GREEN loop (or explicitly make it a blocking dependency) rather than silently broadening #106.

## GREEN gate

Require exact-head success in both CI matrices:

```text
ruff check .
ruff format --check .
mypy
pytest
```

Normal CI remains fully offline.

## Independent adversarial review

Freeze the final SHA and independently challenge:

- public selector can be derived from returned `TextRef` identifiers without private `coord` knowledge;
- direct and subdivided selector composition is deterministic and string-preserving;
- no arbitrary URL/coord execution is exposed;
- explicit CAL missing-information markup is distinct from generic/anti-scrape/parser drift;
- parser does not accept CAL anti-scrape/generic HTTP-200 pages;
- heterogeneous metadata is preserved in order without invented bibliographic categories;
- metadata links are not followed;
- one explicit call performs exactly one request;
- existing text catalogue/search/page contracts are unchanged;
- public tool count/docs/schema are synchronized;
- no temporary live-probe or write-enabled workflow remains in the final diff.

Any blocker gets a regression RED/GREEN loop and a fresh exact-head review.

## Merge gate

Immediately before merge:

1. refetch current `main` and exact PR head;
2. synchronize non-destructively if main advanced;
3. rerun both CI matrices on the synchronized exact head;
4. ensure no unresolved review blocker/helper workflow remains;
5. mark ready only after clean exact-head independent review;
6. merge with `expected_head_sha` equal to reviewed head;
7. confirm #106 closes.

## CAL load impact

No further direct live probe is required for initial TDD. The completed research used four fixed, capped automated requests; the indexed missing-state follow-up did not add another automated CAL request. The probe workflow has been removed. Production remains one request per explicit metadata lookup with no follow-up traversal.
