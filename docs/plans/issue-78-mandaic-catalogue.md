# Issue #78 plan — Mandaic catalogue reachability

**Plan date:** 2026-09-09  
**Research:** `docs/research/issue-78-mandaic-catalogue.md`  
**Baseline:** `main` at `219d070d997386bef6a0fb9aad66b51545858411`

Sequence: research → plan → test-only RED → minimal implementation → docs → dual-matrix GREEN → exact-head logically independent adversarial review → guarded merge.

## Frozen public contract

Do not add a new MCP tool or alter existing result schemas.

Extend the existing operation:

```text
cal_text_catalogue(category_id: string | null = null)
```

so that:

- root discovery includes `TextCategoryRef(category_id="74", label=<CAL rendered label>)` for CAL's exact Mandaic branch;
- `category_id="74"` performs exactly one logical request:

```text
GET show_Mandaic.php?R1=74
```

- the dedicated response returns ordered `TextRef` entries for both subdivided and direct Mandaic files;
- no returned child is fetched automatically.

Shared cache/single-flight/retry/origin/timeout/response-size behavior remains unchanged.

## Routing constants

Add private constants adjacent to the existing collection-route constants:

```python
_MANDAIC_CATEGORY_ID = "74"
_MANDAIC_CATALOGUE_PATH = "show_Mandaic.php"
_MANDAIC_ROOT_LABEL = "Mandaic"
```

The existing `_MANDAIC_COLLECTION_PREFIX = "74"` and `_MANDAIC_SUBDIVIDED_FILE_IDS` continue to own text-page routing. Catalogue discovery must not duplicate or expand that routing table.

## Root parser design

Extend `_category_from_link()` narrowly:

1. parse the link once;
2. recognize only a relative `show_Mandaic.php` target whose query contains exactly one `R1=74` and no extra fields;
3. require a nonempty rendered label and return `TextCategoryRef("74", label)`;
4. if the rendered label is exactly `Mandaic` but the route/query does not match, raise `TextParseError` rather than silently omitting the branch;
5. otherwise preserve existing Onkelos/Jonathan and ordinary `showsubtexts.php` behavior unchanged.

Do not make the generic root parser reinterpret Mandaic child `showsubtexts` rows. Those are handled only by the dedicated parser below.

## Dedicated Mandaic parser

Add:

```python
parse_mandaic_catalogue_page(response: CalResponse) -> TextCataloguePage
```

Validation before row parsing:

- response endpoint must be exactly `show_Mandaic.php`;
- response query keys must be exactly `{R1}`;
- `R1` must have exactly one nonempty value equal to `74`.

Parse `_parse_lines(response)` in rendered order. For every semantic row:

### Subdivided file

Recognize `showsubtexts.php` only when the resolved link is same-origin CAL and its query keys are exactly:

```text
cset=M
subtext=<positive decimal file id>
```

Return:

```python
TextRef(file_id=<subtext>, subtext_id=None, label=<rendered row label>)
```

### Direct file

Recognize `get_a_chapter.php` only when the resolved link is same-origin CAL and its query keys are exactly:

```text
cset=M
file=<positive decimal file id>
```

Return the same public `TextRef` shape using `<file>` as `file_id`.

### Row rules

- zero recognized Mandaic navigation links on a row: ignore the row (for script toggles, headings, return navigation, etc.);
- more than one recognized Mandaic navigation link on one row: fail as ambiguous;
- linked numeric anchor must be attached to the rendered row;
- remove the linked identifier text once from the row; the nonempty remainder is the public human-readable label;
- duplicate file IDs across either route family fail closed;
- a recognized endpoint lookalike on another origin fails closed;
- malformed expected selector/cset/query shape fails closed rather than being skipped;
- after all rows, no recognized items -> `TextParseError`;
- return `TextCataloguePage(categories=(), texts=tuple(items))`.

No full page/group heading is required because the current dedicated page exposes no researched stable semantic heading that should become API data.

## Service dispatch

Update `TextService.catalogue()`:

```text
root -> GET newtextmenu.html, generic parser
51   -> GET targum_onkelos_jonathan.html, generic parser
74   -> GET show_Mandaic.php?R1=74, dedicated Mandaic parser
other decimal -> GET showsubtexts.php?subtext=<id>, generic parser
```

Preserve one request per explicit call and existing provenance fields. `category_id="74"` remains in provenance; no private `R1` field is added publicly.

## Gate 1 — test-only RED

Create `tests/test_mandaic_catalogue.py` with reduced semantic fixtures only.

The RED must be lint/format/type clean and prove:

1. root parser preserves ordinary + Mandaic + Onkelos branches in CAL order;
2. exact Mandaic root route accepts a changed nonempty label while preserving it;
3. a `Mandaic`-labelled root link with wrong path, wrong/missing/repeated `R1`, extra query field, nested suffix-lookalike path, or foreign absolute lookalike fails closed;
4. `TextService.catalogue(category_id="74")` emits exactly:
   `CalRequest(GET, "show_Mandaic.php", params=(("R1", "74"),))`;
5. dedicated response returns representative `74401` subdivided and `74501` direct rows as ordered texts, not categories, with human-readable labels;
6. no child fetch occurs;
7. wrong response endpoint/query identity fails closed;
8. child wrong/missing/repeated `cset`, wrong selector, both selectors, extra query controls, nondecimal/zero identifiers, cross-origin recognized endpoint, duplicate file ID, multiple recognized links in one row, detached/empty label, and no recognized rows fail closed;
9. existing ordinary category and category-51 dispatch remain unchanged (reuse existing tests; add only focused coexistence assertion if useful);
10. normal CI opens no CAL socket.

The accepted RED must pass dependency/environment checks, Ruff lint, Ruff format, and strict mypy in both CI matrices; pytest should fail only because the Mandaic catalogue behavior is absent.

## Gate 2 — minimal implementation

Expected production changes:

- `src/cal_mcp/texts.py` only.

No changes to:

- shared HTTP client;
- text-page routing table from #97;
- generic text page/search/information/token/concordance behavior;
- public server function signature;
- release tool count/surface.

## Gate 3 — documentation

Update `docs/tools/texts.md` to document:

- root Mandaic category `74` discovery;
- one explicit category-74 catalogue call;
- dedicated page returns both direct and subdivided entries as text references;
- following an entry remains a separate `cal_text_page` call;
- route classification is internal and does not require an extra probe;
- request/cache/single-flight/retry wording remains consistent with current shared policy.

Do not claim exhaustive corpus contents beyond what the live catalogue returns.

After merge, update #83/#103 issue status with the completed child route rather than broadening this PR into the umbrella audit.

## Gate 4 — GREEN

Require both deterministic and latest-compatible matrices to pass:

- dependency/environment validation;
- Ruff lint;
- Ruff format;
- strict mypy;
- full pytest.

Freeze the exact candidate SHA and changed-file scope before review.

## Gate 5 — logically independent adversarial review

Review the exact GREEN head from issue/research/current diff. Challenge at least:

1. **Root identity:** can a lookalike/changed Mandaic route be silently accepted or dropped?
2. **Collection identity:** is category 74 routed only through exact `show_Mandaic.php?R1=74`?
3. **Semantic typing:** are Mandaic `showsubtexts` child links returned as texts rather than generic categories?
4. **Direct/subdivided coexistence:** are both route families preserved in CAL order without consulting the page-routing table?
5. **cset fidelity:** is `cset=M` validated rather than invented or exposed publicly?
6. **Origin safety:** do recognized child endpoint lookalikes outside CAL fail closed?
7. **Query strictness:** repeated/extra/ambiguous selectors fail closed?
8. **Labels/order:** rendered names and order are preserved without numeric-anchor leakage?
9. **No traversal:** exactly one catalogue request; no child fetch/probe?
10. **Compatibility:** ordinary catalogue, category 51, Mandaic page routing, and public schemas unchanged?
11. **Empty/drift:** successful-looking unrecognized dedicated page fails rather than returns guessed empty success?
12. **Docs:** user workflow is actionable and bounded without overclaiming corpus contents?
13. **Offline hygiene:** normal CI has no CAL call and no temporary helper files/workflows remain.

Any blocker gets focused review-regression RED → minimal fix → dual GREEN → fresh exact-head review.

## Merge gate

Before merge:

1. refetch `main` and exact PR head;
2. synchronize if `main` advanced;
3. require fresh dual-matrix GREEN on the synchronized tree;
4. require clean exact-head adversarial review and no unresolved threads;
5. mark ready;
6. squash merge guarded by exact expected head SHA;
7. confirm #78 closes;
8. update #83/#103 audit status and re-triage next reachability gap.

## CAL load impact

Zero for normal tests. Production adds no new kind of background traffic: one explicit `cal_text_catalogue(category_id="74")` call maps to one logical CAL request, subject to existing shared cache/single-flight/retry behavior.