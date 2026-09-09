# Issue #117 plan — make core text request-volume contracts cache-aware

**Plan date:** 2026-09-09  
**Research:** `docs/research/issue-117-cache-aware-text-request-volume.md`  
**Baseline:** `main` at `f3e84cd2032773a9b96c5145e5baa63c8a76889a`

Sequence: research → plan → test-only RED + preserved behavior invariant → wording-only implementation → dual-matrix GREEN → exact-head logically independent adversarial review → guarded merge.

## Frozen scope

This ticket covers the four `TextService` operations and the `cal_text_information` regression that triggered #117.

Change only:

- executable descriptions/docstrings for the affected core text tools in `src/cal_mcp/server.py`;
- `docs/tools/texts.md` request-volume wording;
- deterministic documentation/MCP-description contract tests;
- one focused endpoint-level cache-reuse test for `TextService.information()`.

Do not change `CalHttpClient`, `TextService`, parsers, models, schemas, provenance, retry policy, cache policy, single-flight behavior, route selection, or CAL request construction.

Cross-domain request-wording debt is tracked by #120.

## Gate 1 — test-only RED

After research and plan are committed, add tests only.

The accepted RED must:

1. inspect the public `cal_text_information` MCP description through local MCP introspection and require cache-aware wording that states an at-most-one-new-logical-request ceiling and a zero-new-upstream-I/O completed-cache-hit case;
2. require `docs/tools/texts.md` to state the same family-level cache/single-flight distinction and to stop claiming that every text operation always performs exactly one new CAL request;
3. preserve the no-prefetch/no-recursive-traversal contract;
4. add a focused `TextService.information()` cache test proving two identical calls on one shared `CalHttpClient` produce one transport request total and identical scholarly result/provenance values;
5. leave production/runtime/docs unchanged in the RED commit.

The endpoint cache test is expected to pass immediately and is a preserved invariant, not the intended failing behavior. The accepted RED should fail only on stale wording contracts.

Static gates must be clean before pytest reaches the intended documentation/MCP-description failures:

- environment/dependency validation;
- Ruff lint;
- Ruff format;
- strict mypy.

Normal CI remains offline.

## Gate 2 — minimal implementation

Update wording only.

### Runtime descriptions

For core text tools whose docstrings currently claim an exact request count, replace that claim with language equivalent to:

- one explicit call submits at most one new logical CAL request to the shared client;
- a completed shared-client cache hit performs no new upstream I/O;
- no related result/navigation is followed automatically.

Do not describe retries as extra user operations. Refer transport retry details to the shared request policy rather than promising exactly one HTTP attempt.

### `docs/tools/texts.md`

Normalize request-volume statements for catalogue, search, information, page, and the family Request bounds section:

- ordinary cache miss: the bounded upstream request is performed;
- completed cache hit: zero new upstream I/O;
- identical simultaneous follower: no duplicate active upstream request;
- shared retry policy remains applicable on transient failure;
- invalid inputs may fail locally before transport;
- no recursion, prefetch, metadata-link traversal, route-discovery preflight, show-all, token expansion, or background indexing.

Avoid changing unrelated scholarly/parser/route documentation.

## Gate 3 — GREEN

Require both deterministic and latest-compatible matrices to pass:

- environment verification;
- Ruff lint;
- Ruff format;
- strict mypy;
- full pytest.

The final diff must contain no production request/cache/service implementation changes.

## Gate 4 — independent adversarial review

Freeze the exact GREEN SHA and review from scratch. Challenge:

1. **Runtime unchanged:** no request/cache/single-flight/retry implementation changed to satisfy prose.
2. **Request identity:** each core text operation still constructs one bounded logical request identity and performs no hidden preflight/follow-up.
3. **Cache correctness:** completed identical calls can perform zero new upstream I/O and preserve original retrieval provenance.
4. **Single-flight correctness:** wording does not imply followers create background or duplicate requests.
5. **Retry accuracy:** wording does not falsely promise one raw HTTP attempt when the shared retry whitelist can consume bounded retries.
6. **Local validation:** invalid calls are not described as necessarily reaching CAL.
7. **Docs/description agreement:** executable description and `docs/tools/texts.md` express compatible semantics.
8. **Scope:** cross-domain wording remains explicitly tracked by #120 rather than partially changed here.
9. **Offline CI:** no CAL request is introduced into tests.
10. **Repository hygiene:** no helper workflows or unrelated cleanup.

Any blocker enters a focused review-regression RED → minimal fix → dual GREEN → fresh exact-head review loop.

## Merge gate

Before merge:

1. refetch `main` and exact PR head;
2. synchronize if `main` advanced;
3. require dual-matrix GREEN on the synchronized exact tree;
4. require clean exact-head independent review and no unresolved threads;
5. mark ready;
6. squash merge guarded by `expected_head_sha`;
7. confirm #117 closes;
8. re-triage maintenance regressions, with #120 now available for the broader audit.

## CAL load impact

Zero. All tests use local MCP introspection and injected transports.