# Issue #116 plan — synchronize the frozen release surface and runtime registry

**Plan date:** 2026-09-09  
**Research:** `docs/research/issue-116-release-surface-sync.md`  
**Baseline:** `main` at `9223a760a323e893b79208b02eba59e1eeaef22a`

Sequence: research → plan → deterministic test-only RED → minimal manifest/refactor → dual-matrix GREEN → exact-head logically independent adversarial review → guarded merge.

## Frozen design

Add one import-safe internal module:

```text
src/cal_mcp/release_surface.py
```

It owns the explicit v0.1 frozen public tool-name set:

```python
V01_PUBLIC_TOOLS: frozenset[str]
```

Do not store a separately editable count; use `len(V01_PUBLIC_TOOLS)` wherever a count is required.

This manifest is deliberately not derived from `server.mcp`. Runtime registration and release intent remain independent inputs whose equality is enforced by CI.

## Gate 1 — deterministic RED

After this plan is committed, add tests only.

The RED must:

1. dynamically import `cal_mcp.release_surface` so static/type gates remain valid while the module is still absent;
2. introspect the actual source `cal_mcp.server.mcp` registry through a local MCP `Client` with network socket connection denied;
3. require exact equality between runtime tool names and `V01_PUBLIC_TOOLS`;
4. prove mismatch detection is name-sensitive rather than count-only with synthetic equal-size differing sets, or equivalent explicit assertions;
5. require the release verifier to consume the shared manifest rather than define its own independent full tool set/count.

The accepted RED must have installation/environment validation, Ruff lint, Ruff format, and strict mypy green in both matrices. Pytest failures must be confined to the absent shared manifest/refactor contract.

Do not alter `src/`, verifier behavior, release workflow, or user docs in the RED commit.

## Gate 2 — minimal implementation

1. Create `src/cal_mcp/release_surface.py` containing the exact current 29-tool v0.1 name set and no runtime/network imports.
2. Refactor `scripts/verify_release_artifact.py` to import `V01_PUBLIC_TOOLS` and compare installed stdio names against it. Derive the expected count from the set or eliminate the count constant entirely.
3. Refactor the top-level name assertion in `tests/test_bootstrap.py` to reuse `V01_PUBLIC_TOOLS`, while retaining every existing per-tool schema/private-parameter assertion.
4. Update `tests/test_release_artifact_verifier.py` so it verifies use of the shared frozen manifest and does not duplicate the complete tool list/count.
5. Keep `tests/test_docs_contract.py`'s explicit 29-tool user-facing assertions unless a focused failing test proves they should be derived; those assertions test release documentation, not machine registry identity.
6. Do not change public tool registration, schemas, CAL clients, release workflow ordering, wheel/sdist installation, or stdio verification.

## Gate 3 — GREEN

Require both CI matrices to pass:

- frozen/latest dependency environment validation;
- Ruff lint;
- Ruff format;
- strict mypy;
- full pytest.

Normal CI must make zero CAL requests.

The exact GREEN head must show that the release verifier still installs and verifies wheel and sdist independently in its unit contract.

## Gate 4 — independent adversarial review

Freeze the exact helper-free GREEN SHA and review from scratch. Challenge:

1. **Freeze integrity:** expected release names are explicit and cannot silently derive from current runtime registration.
2. **Runtime drift:** adding/removing/renaming a server tool without manifest update fails normal CI.
3. **Manifest drift:** changing manifest without runtime fails normal CI.
4. **Equal-count mismatch:** same cardinality with different names fails.
5. **Artifact boundary:** wheel/sdist installed stdio verification still checks the built artifact, not merely the source-tree server.
6. **Packaging:** the constant-only manifest is present/importable in the release environment and introduces no runtime side effects.
7. **No network:** source registry synchronization uses local MCP introspection only; normal CI does not contact CAL.
8. **Bootstrap coverage:** per-tool schemas/private-parameter checks are not weakened by replacing only the duplicated top-level name set.
9. **Scope:** no tool/schema/request behavior or release workflow semantics changed.
10. **Repository hygiene:** no temporary workflows/helpers remain.

Any blocker enters focused review-regression RED → minimal fix → dual GREEN → fresh exact-head review.

## Merge gate

Before merge:

1. refetch `main` and exact PR head;
2. synchronize if `main` advanced;
3. require fresh dual-matrix GREEN on the synchronized exact tree;
4. require the clean exact-head independent review artifact and no unresolved threads;
5. mark ready;
6. squash merge guarded by `expected_head_sha`;
7. confirm #116 closes;
8. re-triage regressions before returning to feature work.

## CAL load impact

Zero. This ticket uses source-tree MCP introspection and local/fake release-verifier tests only.