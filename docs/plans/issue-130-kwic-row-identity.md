# Issue #130 plan — fail closed on KWIC context row identity drift

**Plan date:** 2026-09-10  
**Research:** `docs/research/issue-130-kwic-row-identity.md`  
**Baseline:** `main` at `b745efad184302925c69e7fbbc796c00c7e2d6c2`

Sequence: research → committed plan → test-only RED → minimal implementation → focused/full GREEN → exact-head logically independent adversarial review → guarded merge.

## Frozen contract

For `get_a_kwicchapter.php` parsing, a table row that contains a recognized `comment.php` line-identity link must not be silently discarded merely because every lexical link in that row has drifted away from recognized `getlex.php` routes.

Required behavior:

- a row with no `getlex.php` links and no `comment.php` link remains ignorable presentation/non-context markup;
- a row with at least one `comment.php` link but no recognized `getlex.php` links raises `ConcordanceParseError`;
- rows with recognized lexical links keep all existing validation and serialization behavior unchanged.

Do not infer context identity from arbitrary two-cell table shape alone.

## Gate 1 — behavior-first RED

After this plan is committed, modify tests only.

Extend `tests/test_kwic_full_context_review_regressions.py` with one deterministic regression based on `kwic_full_context_tel_dan_roman.html`:

1. replace every `getlex.php?coord=1325002` route in the first non-target context row with `brokenlex.php?coord=1325002`;
2. leave `comment.php?coord=1325002`, rendered coordinate `02`, and rendered token labels/text intact;
3. parse with the normal requested selectors for target `1325003`;
4. require `ConcordanceParseError`.

No production file changes at RED.

Valid RED evidence requires CI environment/install, Ruff lint, Ruff format, and strict mypy GREEN, with pytest failing on the new regression because current production silently drops row `1325002`.

## Gate 2 — minimal implementation

Change only `src/cal_mcp/concordance.py`.

In `_parse_full_context_row()` classify comment identity before the existing `if not lexical: return None` exit. Equivalent minimal logic:

```python
comment_links = [link for cell in row.cells for link in cell.links if _is_path(link.href, "comment.php")]
if not lexical:
    if comment_links:
        raise ConcordanceParseError("CAL full-context context row has no recognized lexical links")
    return None
```

Avoid changing validation for rows that do have lexical links. Existing later coordinate-cell comment validation remains authoritative for link count, cell placement, selector identity, and coordinate consistency.

Do not generalize to arbitrary unknown links or arbitrary two-cell rows in this ticket.

## Gate 3 — focused GREEN

Require at least:

- `tests/test_kwic_full_context.py`;
- `tests/test_kwic_full_context_review_regressions.py`.

Verify the new malformed-row case raises while valid Roman/Hebrew/not-found behavior remains unchanged.

## Gate 4 — full GREEN

Require both normal CI matrices on the exact candidate head:

- deterministic frozen environment;
- latest-compatible environment;
- Ruff lint;
- Ruff format;
- strict mypy;
- complete pytest suite.

Normal CI remains offline with respect to CAL.

## Gate 5 — logically independent adversarial review

Review exact final SHA from scratch against #130, research, plan, diff, relevant parser/tests, and current `main`. Try to falsify at least:

1. comment-bearing context row can still disappear without error;
2. presentation/control row with no comment/getlex link is newly rejected;
3. valid Roman/Hebrew rows change shape or ordering;
4. Hebrew terminal empty-anchor tolerance is broadened or weakened;
5. comment links in wrong cells/multiple comment links escape existing strict validation;
6. target exactly-once and not-found semantics change;
7. arbitrary URLs/routes become executable;
8. request/cache/retry/public schema/release surface changes;
9. normal CI gains CAL traffic.

Any blocker requires a new test-only review regression → observed RED → minimal fix → full GREEN → fresh exact-head review.

## Merge gate

Immediately before final review/merge:

1. refetch current `main` and PR head;
2. synchronize if `main` advanced, then rerun exact-head CI/review as needed;
3. post explicit review verdict anchored to the reviewed SHA;
4. mark ready only after clean review;
5. guarded merge using `expected_head_sha`;
6. verify #130 closes and merged code is on `main`.

## CAL load impact

Zero CAL requests for research, tests, implementation, or review. Existing request behavior is unchanged.