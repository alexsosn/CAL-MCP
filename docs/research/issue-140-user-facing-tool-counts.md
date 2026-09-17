# Issue #140 research — user-facing v0.1 tool-count drift

Date: 2026-09-17. Base: `6b48dd2d0ef04ec86ac06c3fcb528c07341d4c48`.

The authoritative frozen v0.1 public-tool manifest is `src/cal_mcp/release_surface.py::V01_PUBLIC_TOOLS`, currently 34 distinct names. `tests/test_release_surface_sync.py` already checks exact equality between that manifest and the executable MCP registry, and the release artifact verifier consumes the same manifest.

Current user-facing count claims were rechecked after #139:

- `README.md`: 34 public tools / 34-tool surface — current.
- `docs/index.md`: 34 tools — current.
- `docs/installation.md`: frozen 34-tool MCP surface — current after #139.
- `CHANGELOG.md`: 34 public tools / frozen 34-tool schema — current.
- `docs/integrations/standalone-mcp.md`: **29 public tools** — stale.

The existing docs contract protects README and docs-index counts with literal `34` assertions, while #139 added a separate installation-guide regression deriving its expected value from `V01_PUBLIC_TOOLS`. The standalone guide is not covered by either mechanism. Literal expected counts in tests can drift together with prose and are a second source of truth.

The safe correction is documentation/test-only: derive the expected count from `V01_PUBLIC_TOOLS`, require each intentional user-facing release-count claim to match it, and change only the stale standalone count. Historical research/plans and old PR evidence may legitimately mention earlier surface sizes and must not be rewritten.

No CAL access, package/version change, runtime behavior, release publication, or public MCP schema change is required.