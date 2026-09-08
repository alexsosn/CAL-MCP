# Issue #97 plan — narrow Mandaic text-page route classification

Date: 2026-09-08
Research prerequisite: `docs/research/issue-97-mandaic-route-scope.md`
Baseline: `main` at `88892f4054d470f2d7fa7e72b647ada13befbd11`

## Goal

Correct the overbroad collection-74 route introduced by #95 without changing the public `cal_text_page(file_id, subtext_id=None, page=1)` schema or adding a discovery request.

The adapter must distinguish current CAL Mandaic files that use the subdivided `sub=NNN` page-selector route from files that CAL exposes directly.

## Frozen routing policy

### Subdivided Mandaic files

When `subtext_id is None` and `file_id` is in the private current subdivided-file set, preserve #95's specialized one-request route:

```text
GET get_a_chapter.php?cset=M&file=<file_id>&sub=<public page padded to at least 3 digits>
```

Initial private set, grounded in issue-97 research:

```text
74401 74402 74410 74411 74421 74422 74423
74428 74430 74432 74700 74701 74923
```

The set is internal routing metadata, not a public taxonomy or stable CAL identifier promise.

### Direct Mandaic files

When `subtext_id is None`, `file_id` begins with `74`, and it is **not** in the subdivided set:

- `page=1` sends exactly one direct Mandaic request:

  ```text
  GET get_a_chapter.php?cset=M&file=<file_id>
  ```

- no `sub` or ordinary `page` field is invented;
- `page>1` fails locally before transport because no direct-text pagination contract is currently researched;
- parsing uses ordinary/unpaginated semantics, not the specialized Mandaic page-selector relaxation.

This means current direct examples such as `74501`, `74716`, and `74717` do not inherit Ginza's `sub=NNN` rule. Unknown/new `74...` IDs also default to this safer direct page-1 route until current CAL evidence proves they are subdivided.

### Existing routes that must not change

- an explicit public `subtext_id` keeps the pre-#95 ordinary `file/sub/page` request shape;
- non-`74...` files keep the ordinary request shape;
- public one-based page semantics remain unchanged;
- specialized adjacent-navigation validation for allowlisted subdivided files remains unchanged;
- token-link parsing (`bablex.php` and `getlex.php`) remains unchanged.

## Gate 1 — deterministic test-only RED

Before production or user-doc edits, add a focused offline regression module and only the minimum reduced fixture needed for a direct Mandaic result.

Freeze these expectations:

1. `TextService.page("74501", page=1)` emits exactly one request with params `(("cset", "M"), ("file", "74501"))`; no `sub` or `page` parameter is present.
2. A second current direct-family example (`74717`) receives the same direct classification, preventing a `744xx`-only patch.
3. `TextService.page("74501", page=2)` raises locally before any transport request.
4. `74410` and `74411` still use specialized `sub=001` routing.
5. At least one non-Ginza subdivided file, preferably `74401` or `74701`, uses specialized routing so the fix cannot collapse into a title-specific exception.
6. Existing explicit-public-`subtext_id` behavior remains byte-for-byte equivalent.
7. Existing ordinary non-Mandaic route remains byte-for-byte equivalent.
8. Direct result parsing does not synthesize specialized page/navigation metadata.

A valid RED requires both repository CI dependency matrices to pass installation/environment checks, Ruff lint, Ruff format, and strict mypy, while pytest fails only the new direct-route expectations caused by the current prefix predicate.

Normal CI remains offline.

## Gate 2 — minimal production implementation

In `src/cal_mcp/texts.py`:

- retain `_MANDAIC_COLLECTION_PREFIX = "74"` only to identify the Mandaic collection boundary;
- add a private immutable subdivided-file set with the researched IDs;
- derive separate `mandaic_page_route` and `mandaic_direct_route` booleans only when the caller did not provide `subtext_id`;
- preserve the current specialized branch for `mandaic_page_route`;
- add the direct page-1 branch with params `cset=M`, `file=<id>` only;
- reject direct page values greater than 1 before calling the client;
- pass `mandaic_page_route=False` into the parser for direct files;
- do not change cache namespace, public models, public server schema, token parsing, or ordinary routing.

Prefer the smallest explicit code over a generalized route abstraction unless tests demonstrate a genuine duplication problem.

## Gate 3 — documentation

Update `docs/tools/texts.md` in the same PR:

- state that CAL's Mandaic collection has mixed route shapes;
- give representative subdivided (`74410`/`74411`) and direct (`74501`/`74717`) examples;
- explain that only known subdivided files map public page to private `sub=NNN`;
- explain direct Mandaic page 1 uses the direct current CAL route and additional pages are rejected until a pagination contract is researched;
- preserve the one-request/no-discovery guarantee;
- keep private `cset`/allowlist details from becoming public tool parameters.

Do not imply the current allowlist is a permanent scholarly classification.

## Gate 4 — GREEN

Require the permanent full CI suite in both dependency matrices. Verify at least:

- dependency/environment validation and `pip check` where configured;
- Ruff lint;
- Ruff format check;
- strict mypy;
- full pytest;
- no live CAL traffic from normal tests.

Record exact final SHA, workflow run IDs, and test counts in the PR body.

## Gate 5 — logically independent adversarial exact-head review

Review the complete final diff from scratch, not from the implementation narrative. Challenge at least:

1. **Route evidence:** no remaining prefix-only assumption; both direct and subdivided examples inside `744xx`/`747xx` are accounted for.
2. **Allowlist scope:** every allowlisted ID has current menu/browser evidence; `74700`'s browser/index evidence is clearly distinguished from the 20-row live-runner snapshot.
3. **Unknown/new IDs:** default-direct page 1 is safer than inventing `sub=NNN`; docs do not promise unknown files will succeed.
4. **Direct pagination:** page >1 fails before transport and no hidden `page`/`sub` request is sent.
5. **Subdivided compatibility:** Ginza Right/Left plus a non-Ginza subdivided file still use `sub=NNN`; large pages are not truncated.
6. **Parser mode:** direct files do not receive specialized page-number synthesis or relaxed navigation validation.
7. **Existing public subtext:** explicit `subtext_id` remains the ordinary route and is not reinterpreted as specialized pagination.
8. **Ordinary texts:** non-Mandaic request construction and parsing are unchanged.
9. **Request bound:** supported page calls make exactly one CAL request; no runtime menu lookup or fallback probing exists.
10. **Rendering selector:** current raw menu uses `cset=R/J` while #95's text-page route uses researched `cset=M`; this ticket intentionally changes only route classification. If review finds concrete evidence that `cset=M` itself is invalid for direct pages, treat that as a blocker/focused regression rather than silently broadening assumptions.
11. **Public schema:** no private allowlist, `cset`, route kind, or CAL form parameter leaks into MCP arguments/results.
12. **Repository hygiene:** no temporary research/helper workflow survives in the final diff; normal CI is offline.

Any blocker requires a review-regression test-only RED, minimal fix, both CI matrices green, and a fresh exact-head review.

## Merge gate

Immediately before merge:

1. refetch `main` and PR head;
2. synchronize non-destructively if main advanced;
3. rerun both CI matrices on the exact final head after synchronization;
4. ensure no unresolved review threads or stale review verdicts remain;
5. mark ready only after clean exact-head review;
6. merge with `expected_head_sha` equal to the reviewed head;
7. confirm issue #97 closes;
8. re-triage open bugs before starting release #15 or new feature work.

## CAL access / load impact

Research used four fixed menu GETs total while resolving raw rendering/link-shape ambiguity, each capped at 512 KiB and 15 seconds. Production remains one CAL request per supported `cal_text_page` call and adds no discovery, fallback probing, prefetch, traversal, or background work.

## Execution record

- Research and routing classification were committed before the plan and implementation.
- Valid test-only RED: `64c40fcd100e9278c22687e1605f5668db8f55b4`, CI run `34243957093`. Both dependency matrices passed installation/environment validation, Ruff lint, Ruff format, and strict mypy before pytest. The deterministic matrix finished **677 passed / exactly 3 failed**, all three new route-scope regressions: direct `74501`/`74717` incorrectly received `sub=001`, and direct page 2 reached transport instead of failing locally.
- Minimal production routing fix: `f091528ad40a46dc005981a51b642a3b0b36c060`.
- Direct-parser-mode regression coverage was then added at `d4bbc9db25dc085eefd51e923b019001e592cf80` to prove a direct Mandaic page uses ordinary/unpaginated semantics rather than specialized page synthesis.
- Post-fix GREEN at `d4bbc9db25dc085eefd51e923b019001e592cf80`: CI run `34244501560`, both deterministic and latest-compatible matrices green; deterministic pytest **691 passed**.
- Earlier issue #85 research independently records a current direct Mandaic page (`74713`) using `get_a_chapter.php?cset=M&file=74713`, so retaining `cset=M` for direct Mandaic page retrieval is grounded in upstream evidence rather than inherited solely from the Ginza subdivided route.
- This execution-record commit intentionally changes no production behavior. Exact-head CI and logically independent adversarial review remain required before merge.
