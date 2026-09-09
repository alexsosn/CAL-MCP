# Issue #105 plan — followable Syriac grouped text categories

**Plan date:** 2026-09-09  
**Research:** `docs/research/issue-105-syriac-group-followup.md`  
**Baseline:** `main` at `4ba30d701750f2d14444812ef977e77c95f10b86`

Sequence: research → plan → test-only RED → minimal implementation → docs → dual-matrix GREEN → exact-head logically independent adversarial review → guarded merge.

## Frozen public contract

Add exactly one specialist operation:

```text
cal_syriac_group(group_id: string)
```

`group_id` must be a positive decimal GROUP selector returned by `cal_syriac_texts`. It is not a generic text `file_id` or generic catalogue `subtext` identifier.

One valid explicit operation submits at most one new logical CAL request to the shared client:

```text
GET showsubtexts.php?keyword=<group_id>
```

Do not add `cset`, `script`, `file`, `subtext`, arbitrary URL, recursion, batch expansion, or automatic child fetching.

Shared completed-cache-hit, single-flight, retry, origin, redirect, timeout, concurrency, and response-size semantics remain unchanged.

## Data model

Reuse `SyriacTextItem` and `SyriacTextNavigationKind` for returned child rows.

Add:

```python
@dataclass(frozen=True, slots=True)
class SyriacTextGroupResult:
    group_id: str
    items: tuple[SyriacTextItem, ...]
    provenance: SyriacProvenance
```

Extend `SyriacProvenance` with optional `group_id: str | None = None` and serialize it alongside the existing fields.

Do not add a public group-page label: research did not establish a stable current heading contract.

## Parser design

Refactor only the current Syriac navigation-row extraction from `parse_syriac_text_category_page()` into a private helper, conceptually:

```python
_parse_syriac_navigation_items(lines, source_url) -> tuple[SyriacTextItem, ...]
```

The helper must preserve the existing category semantics exactly:

- direct `get_a_chapter.php?file=<id>` -> `TEXT`;
- `showsubtexts.php?keyword=<id>` -> `GROUP`;
- `showsubtexts.php?subtext=<id>` -> `CATALOGUE`;
- optional child-link `cset` / `script` remains presentation metadata only;
- same-origin enforcement;
- exactly one semantic selector per subtext link;
- positive decimal identifiers;
- ordered rows and labels;
- optional matching file-info link;
- duplicate/ambiguous/detached/contradictory rows fail closed.

Existing category parser keeps its exact category response URL and heading checks, then delegates row extraction.

Add a focused group parser:

```python
parse_syriac_text_group_page(response, *, group_id)
```

It must:

1. validate `group_id` as a positive decimal string before semantic comparison;
2. require response endpoint `showsubtexts.php`;
3. parse the response URL query with blank values preserved;
4. allow exactly one query key: `keyword`;
5. require exactly one nonempty `keyword` value equal to `group_id`;
6. reuse the shared row parser;
7. fail closed when no recognized rows exist.

No guessed empty-group state is introduced.

## Service design

Add `SyriacService.group(group_id)`:

1. validate input locally;
2. call `CalHttpClient.fetch()` once with:
   - method `GET`;
   - path `showsubtexts.php`;
   - params `(("keyword", group_id),)`;
3. use `parse_syriac_text_group_page`;
4. use a stable cache namespace such as `syriac-group-v1`;
5. return `SyriacTextGroupResult` with operation `syriac_group` and `group_id` provenance.

No parent category call is made inside the group operation. The caller controls the two-step workflow.

## Server surface

Add one MCP tool adjacent to `cal_syriac_texts`:

```text
cal_syriac_group(group_id)
```

Description requirements:

- consume a GROUP selector returned by `cal_syriac_texts`;
- distinguish it from generic text/catalogue IDs;
- never recurse or fetch returned children automatically;
- one explicit call submits at most one new logical CAL request;
- a completed cache hit performs no new upstream I/O.

Update the `cal_syriac_texts` description only enough to name this explicit GROUP follow-up. Existing direct/catalogue behavior stays intact.

## Gate 1 — test-only RED

Create a focused test file, preferably `tests/test_syriac_group_followup.py`, without production changes.

The RED suite must be type/lint/format clean and prove:

1. `SyriacService` exposes a callable group follow-up and consumes a known parent GROUP identifier.
2. Exact request construction is:
   ```python
   CalRequest(method="GET", path="showsubtexts.php", params=(("keyword", "60420"),))
   ```
   with no `cset` or other synthesized field.
3. A reduced synthetic group page returns ordered child `TEXT`, `GROUP`, and `CATALOGUE` items through the same public item model.
4. Only one transport request occurs even when returned rows contain follow-up navigation.
5. Invalid group identifiers (`""`, non-decimal, zero/negative-shaped strings, non-string values) fail before transport.
6. Response endpoint mismatch, repeated/mismatched `keyword`, extra response query controls, cross-origin/ambiguous child links, duplicate IDs, and no recognized rows fail closed.
7. Existing `cal_syriac_texts` parent parsing remains unchanged; reuse current tests rather than duplicating them unless a focused coexistence assertion is useful.
8. MCP introspection exposes `cal_syriac_group` with public `group_id` and no private `keyword`, `cset`, `file`, `subtext`, `script`, or URL input.
9. Normal CI opens no CAL socket.

The accepted RED must pass dependency/environment validation, Ruff lint, Ruff format, and strict mypy in both deterministic and latest-compatible matrices before pytest fails only because the new operation is absent.

Tests may use dynamic `getattr` at the initial RED boundary so importing a not-yet-created symbol does not turn the intended behavior failure into a collection/type failure.

## Gate 2 — minimal implementation

Modify only what the RED proves necessary, expected files:

- `src/cal_mcp/syriac.py`;
- `src/cal_mcp/server.py`;
- focused tests/fixture as needed;
- `docs/tools/syriac.md`;
- possibly a server/tool-count documentation contract only if an existing test proves one must be synchronized.

Do not modify `CalHttpClient`, generic text services/parsers, route policy, cache behavior, retry behavior, lexicon behavior, release machinery, or unrelated Syriac operations.

Prefer an inline reduced semantic fixture in the focused test if it is small; do not imply synthetic child IDs are current CAL corpus data.

## Gate 3 — documentation

`docs/tools/syriac.md` must:

- say four specialist operations;
- list `cal_syriac_group(group_id)` in the tool table;
- document GROUP -> explicit group operation;
- state that `keyword` group identity is distinct from `file` and `subtext` identity;
- state no `cset` is synthesized by the group operation;
- preserve direct TEXT -> `cal_text_page` and CATALOGUE -> `cal_text_catalogue` guidance;
- include the group operation in request/traversal bounds and provenance;
- preserve cache/single-flight/retry wording established by #120.

## Gate 4 — GREEN

Require both deterministic and latest-compatible matrices to pass:

- dependency/environment checks;
- Ruff lint;
- Ruff format;
- strict mypy;
- full pytest.

Verify exact candidate SHA and changed-file scope before review.

## Gate 5 — logically independent adversarial review

Freeze exact GREEN SHA and review from scratch against issue/research/current diff. Challenge at least:

1. **Selector identity:** does any code incorrectly reinterpret `group_id` as file/subtext ID?
2. **Request shape:** is `keyword` the only semantic request field, with no invented `cset`?
3. **Response identity:** does mismatched/repeated/extra response query state fail closed?
4. **Parser reuse:** did refactoring preserve all existing category navigation semantics and error cases?
5. **No recursion:** are returned child links preserved only, never fetched?
6. **Input validation:** do malformed/non-string identifiers fail before transport?
7. **Origin safety:** are child links still same-origin and route-bounded?
8. **Order/fidelity:** are CAL order, labels, identifiers, kinds, and info links preserved?
9. **Empty/drift:** is an unrecognized successful page rejected rather than guessed empty?
10. **Public schema:** does MCP expose only the bounded selector and no arbitrary URL/private controls?
11. **Request-volume wording:** logical request/cache/single-flight/retry semantics remain technically correct.
12. **Compatibility:** existing top-level category, direct text, catalogue, Peshitta, and missing-word contracts are unchanged.
13. **Tests:** RED actually exercises production behavior after implementation rather than only checking prose or symbol existence.
14. **Offline CI / hygiene:** no CAL calls, helper workflows, or temporary files remain.

Any blocker gets focused review-regression RED → minimal fix → dual GREEN → fresh exact-head independent review.

## Merge gate

Before merge:

1. refetch `main` and exact PR head;
2. synchronize if `main` advanced;
3. require fresh dual-matrix GREEN on the synchronized tree;
4. require clean exact-head review and no unresolved threads;
5. mark ready;
6. squash merge guarded by `expected_head_sha`;
7. confirm #105 closes;
8. re-triage reachability issues from #103 before selecting the next lane.

## CAL load impact

Zero for normal tests. Production performs at most one new logical CAL group request per explicit operation, subject to the existing shared cache/single-flight/retry policy. No recursive traversal is added.