# Issue #107 plan — expose CAL specialized gloss-field search

**Plan date:** 2026-09-08
**Research:** `docs/research/issue-107-specialized-gloss-fields.md`

Sequence: research → plan → deterministic test-only RED → minimal implementation → full GREEN → docs → logically-independent exact-head review → guarded merge.

## Frozen public contract

Add one task-level operation:

```text
cal_gloss_field(field: GlossField)
```

`GlossField` is a `StrEnum` with these public values in CAL's current displayed order:

```text
alchemy, anatomy, architecture, astronomy, botany, cantillation,
chemistry, geography, geology, geometry, grammar, liturgy, logic,
magic, mathematics, medicine, music, philosophy, topography, zoology
```

Do not change the existing `cal_gloss_search(query, all_glosses=False)` signature or semantics.

The enum makes current field choices discoverable in the MCP schema. User docs must additionally show CAL's human labels for `botany` (`botany, flora`), `geology` (`geology, gemology`), and `zoology` (`zoology, fauna`).

## Private mapping

Keep CAL's private field-query tokens internal in `search.py`. The mapping is the exact researched table in the issue-107 research artifact.

The public operation maps one enum value to exactly one current CAL GET:

```text
GET newsearchmngs.php?English=<private field token>&secondary=true
```

No caller can supply a raw token. No hidden fallback to free-text search is allowed.

## Result contract

Add a dedicated result wrapper rather than overloading ordinary gloss-search `all_glosses` semantics:

```text
GlossFieldSearchResult
  field: GlossField
  label: str
  matches: tuple[LemmaRef, ...]
  provenance: SearchProvenance
```

Serialize `field` as its string value, preserve CAL's current human label, and reuse the existing ordered `LemmaRef` serialization.

Provenance uses:

- `original_query`: public readable field slug;
- `submitted_query`: exact current CAL private field token;
- `search_kind`: `gloss_field`;
- actual CAL source URL/retrieval time.

This records exact request semantics without turning private tokens into public inputs.

## TDD RED gate

Commit tests after this plan and before production/server changes.

### Service request RED

Parameterize at least:

- `alchemy` -> `(alchem`, label `alchemy`;
- `geology` -> `(geol`, label `geology, gemology`;
- `zoology` -> `(zool`, label `zoology, fauna`.

For each, assert `EnglishSearchService.search_gloss_field(...)` performs exactly one:

```text
CalRequest(
    method="GET",
    path="newsearchmngs.php",
    params=(("English", token), ("secondary", "true")),
)
```

and returns the field/label plus existing ordered lemma results/provenance. Current code lacks this service operation and enum, so the tests are RED.

### Parser/result reuse RED

Use a deliberately reduced existing-shaped gloss result fixture, not a captured full field result. Assert the field operation reuses the same lemma result semantics/order and does not trigger a second request.

### Public schema RED

Extend bootstrap/schema coverage to require public `cal_gloss_field` with `field` required and the twenty enum values visible in the generated input schema.

The existing `cal_gloss_search` schema must remain unchanged.

### Validation RED

Unsupported field values should be rejected by the MCP enum/schema boundary or by direct service validation before transport. Do not interpret unknown values as ordinary English.

A valid RED requires install, Ruff lint/format, and strict mypy to remain green in both dependency matrices, with pytest failures confined to the new absent field-search contract.

## Minimal implementation

In `src/cal_mcp/search.py`:

1. add `GlossField(StrEnum)`;
2. add private immutable field config mapping: public enum -> CAL label/private token;
3. add `GlossFieldSearchResult` and serialization;
4. add `EnglishSearchService.search_gloss_field(field)` using one GET and the existing `parse_gloss_search_page` parser;
5. keep ordinary search query preparation and POST behavior unchanged;
6. export only the intended public model/enum/service symbols.

In `src/cal_mcp/server.py`:

- register `cal_gloss_field(field: GlossField)` with structured output;
- describe it as CAL's specialized indexed field search, not fuzzy/semantic search;
- update server instructions so agents choose it instead of guessing private field syntax.

Do not add a separate network `cal_gloss_fields` discovery operation; the enum schema is the bounded discovery surface.

## Documentation

Update:

- `docs/tools/english-search.md` (or the existing gloss/citation search tool page) with field slugs/labels and distinction from ordinary gloss search;
- `docs/index.md` / getting-started capability guidance if required by current docs-contract tests;
- limitations/concepts only if they currently imply ordinary gloss search covers every CAL gloss workflow.

Examples should demonstrate one field selection and explicitly state one request/no result prefetch.

## GREEN gate

Require both CI dependency matrices green on the exact implementation/docs head:

```text
ruff check .
ruff format --check .
mypy
pytest
```

Normal CI performs zero CAL requests.

## Independent adversarial review

Review the exact final SHA from scratch against current CAL navigation and the committed research/plan. Challenge at least:

- all 20 public enum values and labels match current CAL navigation;
- token mapping is exact and private;
- no raw field token is accepted from callers;
- field request uses current GET semantics and exactly one request;
- ordinary `cal_gloss_search` POST/schema behavior did not change;
- field result order/parser semantics match ordinary lemma-list parsing without invented normalization;
- `botany`, `geology`, and `zoology` synonym labels are preserved rather than conflated with public slugs;
- invalid field values cannot fall through to literal search;
- docs distinguish indexed specialized-field search from semantic/fuzzy search;
- no all-fields result traversal or background enumeration exists.

Any blocker enters a review-regression RED/GREEN loop and requires a fresh exact-head review.

## Merge gate

Immediately before merge:

1. refetch current `main` and PR head;
2. synchronize non-destructively if main advanced;
3. rerun both CI matrices on the exact synchronized head;
4. ensure no unresolved review blocker remains;
5. mark ready only after the fresh exact-head review is clean;
6. merge with `expected_head_sha` equal to the reviewed head;
7. confirm #107 closes.

## CAL load impact

Research is restricted to the current navigation page and representative field links/results. Production is exactly one request for one explicit selected field; no operation enumerates all field result sets.

## Execution record

- Test-only RED head `91b90a7cadab51dc32d4f74d02b26c37a3e2b55d`, CI `34265133157`: both matrices passed installation, Ruff lint/format, and strict mypy; deterministic pytest finished **687 passed / exactly 4 intended failures** covering the absent field service/tool/schema.
- Minimal implementation adds only the readable 20-value enum, private current CAL token mapping, one-request field service, public MCP wrapper, focused tests, and synchronized user documentation; ordinary `cal_gloss_search` remains unchanged.
- Pre-sync implementation/docs head `e8a3b5b60314279ecded4e1e297718439544afe1`, CI `34282757568`: both dependency matrices green.
- After #104 merged, this branch was non-destructively synchronized with current `main` at `756529c99f92fe1b4f0dba5bb3314a3a826f8c4d`. The temporary sync helper removed itself and is absent from the PR diff.
- This execution-record commit exists to trigger the required exact-head CI after the bot-authored merge commit was administratively marked `action_required`; no production behavior changes here.
