# Issue #89 plan — preserve CAL first-page route fidelity

Date: 2026-09-08
Research: `docs/research/issue-89-first-page-route.md`
Baseline branch: `issue-89-first-page-route`

## Scope freeze

Fix only `TextService.page()` request construction for public page 1. Close #79 and #89 together if the exact reviewed implementation proves the live-route regression is addressed.

Preserve parser behavior, page models, provenance, token extraction, cache namespace, request count, public MCP schema, and page >= 2 mapping. Do not add Mandaic/specialized collection routing.

## Gate 1 — behavior-first RED

Add a focused offline regression module with injected transports/semantic fixtures.

Require:

1. **Tel Dan / unpaginated page 1**
   - `service.page("13250", page=1)` succeeds against the existing Tel Dan fixture;
   - exactly one request;
   - request is `GET get_a_chapter.php` with params `(("file", "13250"),)` — no synthetic `page=0`.

2. **BT AZ / paginated page 1**
   - `service.page("71026", page=1)` succeeds against the existing paginated fixture;
   - exactly one request;
   - params `(("file", "71026"),)`.

3. **Later page invariant**
   - retain or extend the existing page-two test so public page 2 with explicit subtext still sends `(("file", "71026"), ("sub", "4"), ("page", "1"))`.

4. Assert representative provenance/page metadata so the regression cannot be satisfied by bypassing parsing.

Valid RED: install/dependency gates, Ruff, format, and mypy GREEN; pytest failures limited to the two new page-1 request-shape expectations, whose actual request still contains `("page", "0")`.

## Gate 2 — minimal implementation

In `src/cal_mcp/texts.py`, append the upstream `page` parameter only when public `page > 1`:

```python
if page > 1:
    params.append(("page", str(page - 1)))
```

Do not reorder `file` / optional `sub` parameters.

No parser/model/documentation change is expected unless a regression proves a user-facing statement is stale.

## Gate 3 — focused/full GREEN

Require the focused text tests and then permanent dual CI:

- deterministic constrained environment + environment verification;
- latest-compatible environment + `pip check`;
- Ruff lint/format;
- strict mypy;
- full pytest.

No CAL traffic.

## Gate 4 — logically independent adversarial review

Freeze exact final SHA and challenge:

- page 1 really omits `page` for both unpaginated and paginated fixtures;
- page 2+ still maps to upstream `page=n-1`;
- optional `sub` remains ordered/preserved;
- exactly one CAL request per page operation;
- no route fallback/probing was added;
- page parser still rejects mismatched requested later pages;
- unpaginated page >1 still fails closed;
- provenance `page` remains the public page number;
- no effect on catalogue/search/token analysis;
- no specialized Mandaic behavior slipped into this fix;
- no normal-CI CAL access.

Any blocker requires review-regression TEST-ONLY RED, minimal fix, full GREEN, and fresh exact-head review.

## Merge gate

Immediately before merge:

1. refetch current `main` and PR head;
2. synchronize if main advanced and rerun CI/review if needed;
3. mark ready only after exact-head PASS;
4. guarded merge with `expected_head_sha` equal to reviewed head;
5. verify both #79 and #89 close and main contains the merge.
