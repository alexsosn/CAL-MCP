# Issue #110 plan — restore current Syriac Peshitta subtext routing

Date: 2026-09-09
Research prerequisite: `docs/research/issue-110-syriac-peshitta-subtext-routing.md`
Baseline: `main` at `381fb95725322640ed81302f8ca5bfa092920d4d`

RED harness note: the first test-only attempt reached Ruff lint but stopped at `ruff format --check`; the subsequent correction changed only test formatting and left production code unchanged. The accepted RED is the later human-authored checkpoint on that corrected test-only state.

## Goal

Make the existing `cal_syriac_texts("ot-peshitta")` and `cal_syriac_texts("nt-peshitta")` results faithfully represent CAL's current Peshitta book links and provide a clear MCP-native explicit follow-up to the existing generic text catalogue, without adding a new tool or automatic chapter traversal.

## Frozen public design

Extend the existing `SyriacTextNavigationKind` enum with:

```text
catalogue
```

A Peshitta category item whose current CAL link is `showsubtexts.php?...&subtext=<book-id>` returns:

- `upstream_id`: the decimal `subtext` value;
- `label`: CAL's rendered book label, preserving order/text;
- `navigation_kind`: `catalogue`;
- `navigation_url`: the validated same-origin CAL URL;
- `info_url`: matching file-information URL when present.

Public follow-up:

```text
cal_syriac_texts("ot-peshitta")
cal_text_catalogue(category_id="62001")
cal_text_page(file_id="62001", subtext_id="01")
```

No private `subtext`, `keyword`, `cset`, or `script` control becomes a new MCP argument.

Existing kinds remain:

- `text` for direct `get_a_chapter.php` items;
- `group` for current Syriac `showsubtexts.php?keyword=<id>` grouped navigation.

## Gate 1 — fixture correction + deterministic RED

After this plan is committed, change only reduced fixtures/tests.

### Current-shape fixtures

1. Replace stale OT Peshitta fixture navigation with current semantic rows:
   - `62001 P Gn` -> `showsubtexts.php?cset=Syriac&subtext=62001`;
   - `62002 P Ex` -> the same family for `62002`;
   - matching `get_file_info.php?coord=<id>` links.
2. Add a reduced NT Peshitta fixture:
   - `62040 P Mt` -> `showsubtexts.php?cset=Syriac&subtext=62040`;
   - `62041 P Mk` -> same family for `62041`;
   - matching info links.
3. Add a reduced representative Peshitta chapter-selector fixture for generic `parse_text_catalogue_page()` / `cal_text_catalogue(category_id="62001")` composition only if existing generic catalogue coverage does not already prove `file + sub` parsing sufficiently. Keep it minimal.

### RED assertions

The test-only RED must prove:

- OT and NT current Peshitta `subtext=` links parse to the new `catalogue` navigation kind with exact IDs/labels/order/URLs;
- current code fails those expectations before production change;
- existing `keyword=` group fixture still parses as `group`;
- existing direct `get_a_chapter.php` Syriac fixture still parses as `text`;
- `showsubtexts.php` with both `keyword` and `subtext` fails closed;
- repeated `subtext`, repeated `keyword`, blank/non-decimal selector, or no recognized selector fails closed;
- `cset=Syriac` is tolerated as presentation metadata on the Peshitta link but not used as the item identity;
- mismatched/detached info links still fail closed;
- generic `cal_text_catalogue(category_id="62001")` remains a one-request explicit follow-up and returns chapter `TextRef` values with `file_id=62001`, `subtext_id=01`, etc.; no chapter page is prefetched.

A valid RED requires both CI matrices to pass environment/install checks, Ruff lint, Ruff format, and strict mypy before pytest fails only the new `catalogue` expectations. Normal CI remains offline.

## Gate 2 — minimal implementation

In `src/cal_mcp/syriac.py` only, unless tests prove another file is genuinely required:

1. add `CATALOGUE = "catalogue"` to `SyriacTextNavigationKind`;
2. refactor only the `showsubtexts.php` branch so it distinguishes exactly one of:
   - `keyword` -> `GROUP`;
   - `subtext` -> `CATALOGUE`;
3. use existing decimal-ID and same-origin validation;
4. fail closed on both/duplicate/missing semantic selectors;
5. leave `get_a_chapter.php` direct navigation unchanged;
6. do not add network requests or follow returned links.

Do not generalize route parsing beyond what current CAL evidence requires.

## Gate 3 — documentation

Update `docs/tools/syriac.md`:

- document the three navigation kinds and their explicit follow-up semantics;
- state that current OT/NT Peshitta books are `catalogue` items;
- show fixture-backed `62001` / `62040` examples;
- distinguish `catalogue`/`subtext` from `group`/`keyword` without exposing raw upstream controls as public arguments;
- document the composition through `cal_text_catalogue` and then `cal_text_page`;
- preserve one-request-per-operation / no-prefetch guarantees.

Update root `research.md` with a dated amendment/record before final review because this ticket corrects a durable prior assumption about static Peshitta category routing.

## Gate 4 — GREEN

Require both deterministic and latest-compatible CI matrices:

- frozen/latest dependency validation;
- Ruff lint;
- Ruff format check;
- strict mypy;
- full pytest;
- zero live CAL traffic from normal tests.

Record exact GREEN head/run/test counts in the PR body.

## Gate 5 — logically independent adversarial review

Freeze an exact helper-free SHA and review from scratch. Challenge at least:

1. **Current route fidelity:** fixtures/model match current OT and NT Peshitta `showsubtexts.php?cset=Syriac&subtext=...` links rather than the stale direct-link assumption.
2. **Semantic selector:** `subtext` controls book/catalogue identity; `cset`/`script` are not exposed as identity.
3. **No conflation:** `subtext` catalogue navigation and `keyword` group navigation stay distinct.
4. **Fail closed:** both selectors, repeated values, blank/non-decimal values, unknown selector shapes fail rather than being guessed.
5. **Direct compatibility:** ordinary direct Syriac `get_a_chapter.php` items remain `text`.
6. **Composition:** `catalogue` has a real MCP-native follow-up through existing `cal_text_catalogue`; no arbitrary URL execution is needed.
7. **Request bound:** category and follow-up each perform exactly one request; no chapter/book prefetch.
8. **Schema ergonomics:** enum extension is minimal and tool arguments remain unchanged.
9. **Provenance/order:** CAL IDs, labels, order, navigation URLs, info links, and category provenance are preserved.
10. **Repository hygiene:** no temporary probe/helper workflow or full CAL page survives in final diff.

Any blocker enters review-regression RED -> minimal fix -> both matrices GREEN -> fresh exact-head review.

## Merge gate

Before merge:

1. refetch `main` and exact PR head;
2. synchronize if main advanced;
3. rerun both matrices on the synchronized exact head;
4. require clean exact-head independent review and no unresolved threads;
5. mark ready;
6. guarded squash merge with `expected_head_sha` equal to the reviewed head;
7. confirm #110 closes;
8. re-triage regressions before returning to feature work.

## CAL load impact

Research was bounded to the two static Peshitta category pages and one representative immediate chapter-selector destination from each, plus inspection of the destination's already-rendered script-toggle targets. No chapter content, token analysis, neighboring book, or recursive traversal was fetched. Production remains exactly one CAL request per explicit operation.
