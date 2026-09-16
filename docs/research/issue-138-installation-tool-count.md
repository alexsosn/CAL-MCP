# Issue #138 research — standalone release-surface documentation

Date: 2026-09-16. Base: `8f8aa04efc1ae6826c050b64212139362628e07e`.

`src/cal_mcp/release_surface.py` contains 34 distinct names in `V01_PUBLIC_TOOLS` after #136. `tests/test_release_surface_sync.py` compares the complete set against `mcp.Client(...).list_tools()`, and `scripts/verify_release_artifact.py` imports the same set rather than maintaining a separate count. The release-validation paragraph of `docs/installation.md`, however, still states that installed artifacts expose a frozen `29-tool` surface. This is a documentation contradiction only, not evidence that either artifact verifier or the server enumerates 29 tools.

The docs already make the correct distinction between the future PyPI `cal-mcp==0.1.0` publication and checkout installation. GitHub releases were empty when checked; no release should be inferred. The research found no need for a new tool, live CAL probe, version bump, or release workflow change. Record a scoped regression against the existing manifest, change only the stale sentence, and retain the pre-publication warning.
