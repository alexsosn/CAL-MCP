# Issue #116 research — keep the frozen release surface synchronized with the MCP registry

**Research date:** 2026-09-09  
**Baseline:** `main` at `9223a760a323e893b79208b02eba59e1eeaef22a`

## Question

How can normal offline CI detect drift between CAL-MCP's actual public MCP tool registry and the frozen tool surface used to validate release artifacts, while preserving the release pipeline's stronger wheel/sdist-installed stdio verification?

## Current sources of truth

### Runtime MCP registry

`src/cal_mcp/server.py` registers the public tool surface on the `mcp` server. The authoritative runtime set is therefore what `await Client(server_module.mcp).list_tools()` returns after local server import/introspection.

This introspection is already proven offline by `tests/test_bootstrap.py::test_server_import_and_introspection_do_not_require_network`, which installs a socket-connect guard before importing `cal_mcp.server` and listing tools. Tool registration itself does not contact CAL.

### Bootstrap/public-schema contract

`tests/test_bootstrap.py::_assert_public_tools()` independently duplicates the complete expected public name set and validates each public input schema. It runs both against the in-process server and against the installed `cal-mcp` stdio entry point in the normal editable development environment.

This catches unintended runtime/schema changes, but it does not reference the release verifier's frozen set.

### Release artifact verifier

`scripts/verify_release_artifact.py` currently owns another manual copy:

- `EXPECTED_TOOL_COUNT = 29`;
- `EXPECTED_TOOLS = frozenset({...29 names...})`.

For a tagged release it finds exactly one wheel and one sdist, validates their metadata, installs each distribution independently in a fresh virtual environment, launches the installed `cal-mcp` executable over stdio, obtains `list_tools()`, and rejects any name/count difference from those constants.

That installed-artifact boundary is valuable and must remain. The defect is that the frozen set can drift from the source runtime registry until the tagged release workflow reaches this late check.

### Current verifier unit regression

`tests/test_release_artifact_verifier.py::test_release_verifier_frozen_tool_surface_matches_current_public_tools` currently verifies only that the verifier says 29, that its set length is 29, and that three recently relevant tool names are included. It never lists the actual runtime registry.

Consequently these changes can pass normal CI:

- runtime adds a tool while verifier remains unchanged, provided bootstrap/docs are updated;
- verifier replaces one expected name with a wrong name while retaining the same count and the three asserted names;
- runtime removes one tool while verifier substitutes another name and all duplicated count assertions happen to remain consistent.

The test's name overstates what it proves.

### Documentation/release-count contracts

`tests/test_docs_contract.py` lists the actual runtime tools and currently asserts `len(tool_names) == 29`, then checks every public tool name occurs in tool documentation. It also checks README/index wording for the 29-tool release surface.

Those tests protect user documentation, but they do not compare the runtime name set to the release artifact verifier.

### Release workflow boundary

`.github/workflows/release.yml` runs deterministic lint/type/tests, builds one wheel and one sdist, and only then invokes `python scripts/verify_release_artifact.py dist --tag ...`. The verifier installs each exact artifact separately and checks its stdio server.

A source/runtime-versus-frozen comparison in normal CI therefore complements rather than replaces the installed-artifact check.

## Architectural options

### A. Derive release expectations dynamically from `server.mcp`

Rejected. If the verifier simply asks the current source registry what it should expect, an accidental public-tool addition automatically becomes an accepted release surface. That weakens the explicit frozen release contract and does not protect intentional release review.

### B. Keep verifier constants and add one runtime-vs-verifier test

This would catch current drift and is smaller in lines changed, but it leaves the frozen name list owned by a release script while bootstrap tests keep a second full copy. Future code can still duplicate the list elsewhere, and `EXPECTED_TOOL_COUNT` remains separately editable from `EXPECTED_TOOLS`.

It is acceptable as a narrow regression but not the cleanest source-of-truth architecture requested by #116.

### C. Introduce one explicit frozen release manifest and compare runtime against it in normal CI

Preferred.

Create a small import-safe module, e.g. `cal_mcp.release_surface`, containing only an immutable `V01_PUBLIC_TOOLS` name set. Derive the count from `len(V01_PUBLIC_TOOLS)` rather than storing a second integer constant.

Then:

1. `scripts/verify_release_artifact.py` imports the frozen manifest and uses it to validate each freshly installed wheel/sdist stdio server;
2. normal offline CI introspects the actual source `server.mcp` registry and asserts exact set equality with the manifest;
3. `tests/test_bootstrap.py` may reuse the manifest for its top-level exact-name assertion while retaining all per-tool schema checks;
4. documentation tests may keep explicit `29` wording checks because those protect user-facing release text rather than machine identity.

This deliberately preserves two conceptually distinct things:

- **runtime registry** — what the server actually exposes;
- **frozen release manifest** — what v0.1 is allowed to expose.

Normal CI mechanically requires equality. Release validation separately requires each built artifact's installed stdio registry to equal the same frozen manifest.

## Import / packaging boundary

The manifest must be import-safe: no `server` import, MCP client construction, network client, or CAL module initialization. A constant-only `src/cal_mcp/release_surface.py` is suitable and will be included in wheel/sdist by normal package discovery.

The release verifier is executed from the checked-out tagged source after the project has passed tests and been built. Importing the constant-only manifest does not inspect the editable runtime server and does not replace artifact verification: `_verify_stdio()` still launches the independently installed artifact and compares its returned names to the frozen manifest.

Normal CI's registry comparison uses local `Client(server_module.mcp)` introspection, already covered by the socket-denial test as network-free.

## Failure classes after the change

- runtime adds/removes/renames a tool without updating the frozen manifest -> normal CI fails exact set equality;
- frozen manifest changes without matching runtime -> normal CI fails;
- count stays equal but names differ -> set equality fails;
- source runtime and manifest agree but wheel/sdist packaging exposes a different surface -> tagged artifact verifier fails installed stdio check;
- wheel and sdist disagree with each other -> each is independently checked and the differing artifact fails;
- CAL is unavailable -> none of these checks contacts CAL, so normal surface validation remains unaffected.

## Scope decision

No runtime tool, CAL request behavior, public schema, release workflow sequencing, or installed-artifact validation needs to change. The implementation is release-contract consolidation plus offline synchronization coverage.

No CAL live probe is required because this ticket concerns repository/release mechanics only.
