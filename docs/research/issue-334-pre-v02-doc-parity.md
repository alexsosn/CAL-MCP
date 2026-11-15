# Issue #334 — pre-v0.2 public-documentation audit (2026-11-15)

## Frozen evidence and source hierarchy

- The latest GitHub release collection currently contains **v0.1.0** (published 2026-10-11 UTC), built from tagged commit `d8aa7fe269198ee37b4da8d71f5ed2f7eb5fe1fb`. There is no published v0.2.0 release. The published package pin is `cal-mcp==0.1.0`.
- `main` at audit start: `2d759841913daca2a3bdd5aa0aa7e0076027fded`. `pyproject.toml` identifies current development source as `0.2.0.dev0`, *not* a published candidate or final artifact.
- `src/cal_mcp/release_surface.py` freezes 36 `V01_PUBLIC_TOOLS`; `CURRENT_PUBLIC_TOOLS` adds only `cal_bibliography_recent` (37). The 36 include both `cal_targum_concordance_examples` and `cal_targum_reflex_examples`. `docs/tools/targum.md` documents the six Targum operations.
- Issue [#109](https://github.com/alexsosn/CAL-MCP/issues/109) is closed/completed as of 2026-10-10; its Targum example-follow-up work is in the **published** 36-tool surface. However `docs/index.md` still labels it a current *unfollowable* gap and omits the two example tools in the capability matrix.
- Issue [#39](https://github.com/alexsosn/CAL-MCP/issues/39) is closed/completed as of 2026-11-06. Its new bibliography operation exists **only on current development source**; `docs/getting-started.md` incorrectly says it is still deferred to #39. `docs/tools/bibliography.md` correctly documents a no-argument bounded snapshot and its unreleased status.
- Issue [#16](https://github.com/alexsosn/CAL-MCP/issues/16) and Agora [#222](https://github.com/alexsosn/Agora/issues/222) are completed after merged [Agora PR #268](https://github.com/alexsosn/Agora/pull/268). `docs/installation.md` and `docs/integrations/agora.md` already say the registry entry is in an **unpublished** Agora v1.1 candidate; bounded Codex real-CAL verification is recorded, Claude remains community/deterministic-only. `docs/limitations.md` and `docs/integrations/standalone-mcp.md` still call integration a future task; README diagram likewise says optional future. Merging Agora registration must not be represented as marketplace publication.
- `README.md` v0.1 tool table omits `cal_targum_reflex_examples`, though code and detailed tool docs include it.
- `.github/workflows/release.yml` uses tagged `v*` push, frozen build/test, wheel+sdist validation, exact installed wheel's live smoke, PyPI trusted publisher, then GitHub release. `docs/plans/issue-330-current-release-smoke.md` requires a current 13-case matrix, 12 CAL-backed cases and >=12 actual CAL starts, <=25 total, no retries. A PR merge is **not** a publication.

## Scope and risks

Fix documentation truthfulness and researcher navigation; preserve the old published v0.1.0 surface and its actual release URLs and pins. Do **not** revise executable schemas, bundled CAL data, HTTP budgets, old release assets, dependencies, tags, or Agora registry. Avoid misleading users into treating `0.2.0.dev0` or a merged marketplace candidate as installed public releases. Add only bounded deterministic documentation tests and a release-maintainer checklist; no live CAL calls.

Source links: [v0.1.0 GitHub Release](https://github.com/alexsosn/CAL-MCP/releases/tag/v0.1.0), [release workflow](https://github.com/alexsosn/CAL-MCP/blob/main/.github/workflows/release.yml), [issue #330](https://github.com/alexsosn/CAL-MCP/issues/330), [issue #334](https://github.com/alexsosn/CAL-MCP/issues/334).
