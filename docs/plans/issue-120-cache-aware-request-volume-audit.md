# Issue #120 plan — cache-aware request-volume wording outside core text tools

**Plan date:** 2026-09-09  
**Research:** `docs/research/issue-120-cache-aware-request-volume-audit.md`  
**Baseline:** `main` at `c8dc0be2b73cd575775e26a6ad34b96f53f635c8`

Sequence: research → plan → test-only RED → wording-only implementation → dual-matrix GREEN → exact-head logically independent adversarial review → guarded merge.

## Frozen scope

Correct request-volume contracts for non-core-text one-fetch CAL-backed operations in:

- `src/cal_mcp/server.py` public tool descriptions;
- `docs/tools/search.md`;
- `docs/tools/token-analysis.md`;
- `docs/tools/concordance.md`;
- `docs/tools/bibliography.md`;
- `docs/tools/dictionary-collation.md`;
- `docs/tools/targum.md`;
- `docs/tools/syriac.md`;
- `docs/tools/external-citations.md`;
- centralized offline regression tests.

Protected files/contracts:

- `docs/tools/lexicon.md` keeps its explicit bounded multi-request workflow (up to eight browser requests plus one entry request);
- `cal_convert_to_code` keeps its exact zero-network contract;
- `docs/tools/texts.md` and the corrected core text descriptions are already owned by #117 and should not be churned.

Do not change `CalHttpClient`, services, parsers, models, schemas, provenance, cache, retry, single-flight, route selection, CAL form construction, or release surface.

## Gate 1 — test-only RED

After this plan is committed, add tests only.

Create one centralized contract file, e.g. `tests/test_request_volume_docs_contract.py`, that:

1. introspects the actual MCP tool descriptions locally, without network access;
2. covers affected single-fetch tools whose current descriptions contain unconditional one-request wording;
3. requires cache-aware semantics equivalent to:
   - at most one new logical CAL request;
   - completed cache hit can perform no new upstream I/O;
4. reads each affected `docs/tools/*.md` file and requires family-level cache/single-flight/retry wording while rejecting the known stale unconditional exact-count phrases;
5. protects `cal_convert_to_code` as a zero-CAL-request local tool;
6. protects `docs/tools/lexicon.md` as a bounded multi-request exception by requiring the existing successful-two-request and eight-plus-one upper-bound semantics;
7. does not require every prose sentence to use identical wording; tests semantic anchors, not formatting/line wrapping;
8. leaves all production/runtime/user docs unchanged in the RED commit.

The accepted RED must pass:

- environment/dependency validation;
- Ruff lint;
- Ruff format;
- strict mypy;

in both dependency matrices before pytest reaches only the intended stale wording failures.

Normal CI remains offline.

## Gate 2 — minimal implementation

### Server descriptions

For only the descriptions that currently promise one CAL request, replace that promise with equivalent wording:

> One explicit call submits at most one new logical CAL request. A completed cache hit performs no new upstream I/O.

Retain each tool's existing no-traversal/no-prefetch boundary.

Do not add request-count prose to descriptions that currently make no stale count claim unless needed to remove an inconsistency proven by RED. This keeps the diff minimal.

Expected server-description targets from research:

- `cal_gloss_search`;
- `cal_gloss_field`;
- `cal_citation_text_search`;
- `cal_token_analysis`;
- `cal_text_concordance`;
- `cal_kwic_texts`;
- `cal_kwic_dialect`;
- `cal_bibliography_authors`;
- `cal_bibliography_author`;
- `cal_bibliography_keyword`;
- `cal_bibliography_lemma`;
- `cal_targum_parallel`;
- `cal_syriac_missing_words`;
- `cal_syriac_peshitta_parallel`;
- `cal_external_citation_dialects`;
- `cal_external_citation_sources`;
- `cal_external_citations`;
- `cal_dictionary_collation`.

Descriptions without an exact-count claim (`cal_kwic_dialects`, `cal_targum_concordance`, `cal_targum_hebrew_lemmas`, `cal_targum_hebrew_reflexes`, `cal_syriac_texts`) remain unchanged unless the test-only RED establishes a concrete inconsistency.

### Family docs

For each affected family, preserve operation-specific endpoint/workflow shape and no-traversal guarantees, but distinguish:

- one logical request identity per valid one-fetch operation;
- zero new upstream I/O on completed cache hit;
- no duplicate active I/O for identical single-flight follower;
- bounded retry transport attempts on eligible transient failure;
- local validation may stop before transport.

Where the docs describe a multi-step scholarly workflow (Targum chooser → reflexes, Syriac category → catalogue/page, external citation dialect → source → citation), preserve the number of explicit caller actions while avoiding claims that each action necessarily contacts CAL anew.

Fixture/test statements such as “exact one-request service mapping” may remain only when clearly referring to first-miss/fresh-client request construction, not every public invocation.

## Gate 3 — GREEN

Require both deterministic and latest-compatible matrices to pass:

- dependency/environment checks;
- Ruff lint;
- Ruff format;
- strict mypy;
- full pytest.

The final diff must show zero service/client/parser/request implementation changes.

## Gate 4 — independent adversarial review

Freeze the exact GREEN SHA and review from scratch. Challenge:

1. **Coverage:** every stale non-text exact-count claim discovered in research is corrected or explicitly justified.
2. **Protected exceptions:** local conversion still promises zero network I/O; lexicon still documents bounded multi-request behavior rather than being flattened.
3. **Runtime unchanged:** no request/cache/retry/single-flight implementation changed.
4. **One-fetch accuracy:** affected services still construct at most one logical request identity after validation.
5. **Retry accuracy:** no wording promises a single raw transport attempt.
6. **Cache accuracy:** completed cache hits can perform zero new upstream I/O and preserve provenance.
7. **Single-flight accuracy:** followers do not duplicate active I/O and are not described as background requests.
8. **Workflow integrity:** multi-step scholarly workflows remain separate explicit caller actions; no hidden traversal is implied.
9. **Docs/server agreement:** executable descriptions and family docs are compatible.
10. **Test robustness:** semantic tests normalize whitespace and do not freeze incidental wrapping.
11. **Offline CI:** no CAL access added.
12. **Repository hygiene:** no temporary helpers remain.

Any blocker gets focused review-regression RED → minimal fix → dual GREEN → fresh exact-head review.

## Merge gate

Before merge:

1. refetch `main` and exact PR head;
2. synchronize if `main` advanced;
3. require fresh dual-matrix GREEN on the synchronized exact tree;
4. require clean exact-head independent review and no unresolved threads;
5. mark ready;
6. squash merge guarded by `expected_head_sha`;
7. confirm #120 closes;
8. re-triage open feature/maintenance tickets before selecting the next lane.

## CAL load impact

Zero. All research and tests are repository/local-introspection based.

## Execution checkpoint

Accepted test-only RED head `4aa429a32a9c4f5dc5273fadb13a756ed337f438` passed dependency/environment validation, Ruff lint, Ruff format, and strict mypy in both deterministic (`mcp 2.1.1`) and latest-compatible (`mcp 2.2.0`) matrices. Full pytest produced **757 passed / exactly 2 failures** in each matrix: the aggregate stale executable-description audit and the aggregate stale family-document audit. The protected local-converter zero-network test and lexicon bounded multi-request exception test both passed unchanged.

Implementation changed only the 18 stale public MCP docstrings in `src/cal_mcp/server.py` and the eight audited `docs/tools/*.md` files. It distinguishes one logical request identity from completed-cache-hit/single-flight suppression and bounded retry transport attempts, preserves explicit multi-step scholarly workflow boundaries, and rewords fixture notes to refer to single-fetch request construction rather than unconditional invocation counts. No client, service, parser, model, schema, provenance, cache, retry, single-flight, route, request-construction, or release-surface implementation changed. Temporary implementation helpers self-deleted and are absent from the PR diff.

The first API-authored GREEN candidate `29b97ed9301a1aa001df852913a616905cc723de` was rejected before tests because deterministic CI found one Ruff E501 violation in the rewritten `cal_text_concordance` docstring. The repair only wrapped that sentence; no semantic or runtime behavior changed. The repaired tree again contains no helper workflow and remains within the frozen 12-file scope.
