# Issue #103 plan — finalize the CAL page/workflow reachability audit

**Plan date:** 2026-09-10  
**Research:** `docs/research/issue-103-page-workflow-reachability.md`  
**Baseline:** `main` at `1e925b4ba016df7648228d1c8d0d81bfbfcaab89`

Sequence: current-source research → plan → deterministic documentation-contract RED → minimal documentation correction → dual-matrix GREEN → exact-head logically independent adversarial review → guarded merge / audit closure.

## Frozen scope

Issue #103 is a research/decomposition and capability-documentation ticket. It must not bundle independently reviewable child route implementations.

This PR may change only:

- the dated reachability matrix under `docs/research/`;
- this plan;
- one focused documentation-contract test;
- `docs/index.md` capability/reachability wording.

It must not change runtime source, request routing, parsers, server schemas, public tool count, or release artifacts.

## Current decomposition

Every current class 3/4/5 route family identified by the 2026-09-10 audit already has a focused issue:

- #39 — five-most-recent-years bibliography snapshot; class 5 and explicitly blocked by #15 / the frozen v0.1 contract;
- #108 — line comments/translations via `comment.php?coord=...`;
- #109 — Targum concordance/reflex supporting example pages;
- #112 — lexicon prefix browsing;
- #113 — KWIC target-centered full-context pages;
- #127 — lexicon citation full-context pages via `showachapter.php?fullcoord=...`.

Resolved route gaps that the public docs must no longer describe as open:

- #78 Mandaic catalogue discovery;
- #97 Mandaic direct/subdivided page routing;
- #101 Onkelos/Jonathan discovery;
- #105 grouped Syriac follow-up;
- #106 text-information metadata;
- #107 specialized gloss fields;
- #125 Syriac root discovery.

Cross-cutting/ergonomic tickets #77, #82, and #84 are not substitutes for these route classifications.

## Public-document contract

Keep the existing capability matrix, but make its scope explicit:

- an **Implemented** parent/task row does not imply that every navigation link rendered on the corresponding CAL page is MCP-followable;
- add a compact `Known current reachability gaps` section immediately after the matrix;
- list each open class 3/4/5 issue with the scholarly task that still terminates outside the adapter;
- state that #39 is intentionally blocked until #15 publishes v0.1 or the contract freeze changes;
- state that CAL's text-browser `show all` presentation is deliberately not exposed because the adapter's supported reading contract is bounded page retrieval;
- keep links to focused issues rather than duplicating implementation designs in user docs.

Do not describe resolved #78/#97/#101/#105/#106/#107/#125 work as open.

## Gate 1 — deterministic documentation-contract RED

After this plan commit, add `tests/test_reachability_docs_contract.py` before changing `docs/index.md`.

The focused test must require the public index to:

1. contain the heading `Known current reachability gaps`;
2. name all six current route-gap issues: `#39`, `#108`, `#109`, `#112`, `#113`, `#127`;
3. contain route/task language tying those issue numbers to recent bibliography, line comments/translations, Targum supporting examples, lexicon prefix browse, KWIC full context, and lexicon citation full context;
4. explicitly state that an `Implemented` capability does not mean every CAL follow-up link is MCP-followable;
5. explicitly document the deliberate bounded alternative to CAL's `show all` text presentation;
6. not reintroduce the resolved route issues as current gaps.

The test should read repository Markdown only and perform zero CAL/network I/O.

Accepted RED:

- dependency/environment checks GREEN;
- Ruff lint/format GREEN;
- strict mypy GREEN;
- full pytest fails only because current `docs/index.md` lacks the frozen reachability section/wording.

## Gate 2 — minimal documentation implementation

Update only `docs/index.md` to satisfy the frozen test and current research matrix.

Keep existing capability rows accurate. Do not weaken implemented parent-task claims merely because an independent child follow-up remains missing; instead state the distinction explicitly and link the child issue.

The new section should be concise enough for users to understand current boundaries without reproducing the full research matrix.

## Gate 3 — GREEN

Require both deterministic and latest-compatible matrices to pass on the exact candidate SHA:

- frozen/latest dependency checks;
- Ruff lint;
- Ruff format;
- strict mypy;
- full pytest including the new documentation contract.

Freeze changed-file scope before review. Any source/runtime file in the diff is a blocker for this ticket.

## Gate 4 — logically independent adversarial review

Review the exact GREEN head from current CAL navigation evidence, current `main`, the raw diff, the #103 issue, and focused child issues—not from the implementation narrative.

Challenge at least:

1. every major dynamic route family from the current search/module navigation is accounted for in the research matrix;
2. `composed` means a typed selector returned by one MCP result is actually consumable by another MCP operation;
3. a preserved URL alone is never called a supported follow-up;
4. all class 3/4/5 findings have focused issues and no current gap is silently omitted;
5. resolved issues are not presented as still broken;
6. Targum single-source browsing is genuinely reachable beyond only Onkelos/Jonathan;
7. static/reference and deliberately unbounded presentation pages have explicit non-operation reasons;
8. #39's v0.1 freeze blocker is represented accurately;
9. #127 is not prematurely collapsed into #113 without route-shape research;
10. docs describe current merged behavior only;
11. the PR contains no runtime/tool/schema changes and normal CI remains offline.

Any blocker must first receive a focused regression/doc-contract assertion where feasible, then a minimal correction, dual GREEN, and a fresh exact-head review.

## Merge / closure gate

Before merge:

- refetch `main` and PR head;
- if `main` advanced, synchronize and rerun both CI matrices plus exact-head review;
- mark the PR ready only after GREEN/review;
- squash-merge guarded by the exact reviewed head SHA.

After merge:

- add the merged research artifact to #103 and close #103 as completed because every current class 3/4/5 finding has a focused issue; child implementations may remain open;
- close #83 as completed if the merged matrix still confirms that ordinary, Onkelos/Jonathan, Mandaic, Syriac, and Targum single-source root/source discovery are all reachable;
- leave #39/#108/#109/#112/#113/#127 open for their own research-plan-TDD-review loops.

## CAL load impact

Zero additional CAL requests are needed for implementation/testing. The research phase already used a bounded set of current navigation pages and representative route-family links. Normal CI remains offline.