# Issue #16 — released CAL-MCP identity for downstream Agora

Source-grounded research (2026-10-11 UTC). No CAL HTTP requests in this ticket.

## Verified upstream release
- Annotated signed-by-GitHub tag `v0.1.0` targets commit `d8aa7fe269198ee37b4da8d71f5ed2f7eb5fe1fb` (not current `main`).
- GitHub [release](https://github.com/alexsosn/CAL-MCP/releases/tag/v0.1.0) published 2026-10-11T22:07:07 UTC, with `cal_mcp-0.1.0-py3-none-any.whl` and `cal_mcp-0.1.0.tar.gz`.
- [Release workflow run 38178217487](https://github.com/alexsosn/CAL-MCP/actions/runs/38178217487) completed SUCCESS: build-and-test, tagged wheel/sdist clean installation and 36-tool stdio checks, real fixed 12-case installed-wheel/25-attempt CAL smoke, PyPI trusted publication, GitHub release creation. Thus registry can pin `cal-mcp==0.1.0`; do not call it a prerelease.
- Release `pyproject.toml`: Python >=3.11, MIT software license, package `cal-mcp`, executable `cal-mcp` mapped to `cal_mcp.server:main`; `mcp>=2,<3`, `httpx2>=2.12,<3`, `jsonschema>=4.26,<5`. Stdout/stdin transport `stdio` with no args.
- The [36 published tool families](../index.md) include lexicon, gloss, texts, token analysis, concordance, bibliography, Targum, Syriac etc. Direct programmatic clients and source checkout remain independent of Agora. CAL is remote `cal.huc.edu` with upstream-dependent content/terms; neither corpus data nor a hosted server ships.

## Downstream Agora contract
- `alexsosn/Agora` 1.0 release is already published; issue [Agora#222](https://github.com/alexsosn/Agora/issues/222) is the post-1.0 task for CAL integration, replacing closed-not-planned Agora#57. Its existing issue text predates this release and needs revalidation.
- Agora `AGENTS.md`, `CONTRIBUTING.md` and `wiki/architecture/ref-plugin-boundary.md` prohibit semantic wrappers and require canonical registry metadata plus generated client manifests. `registry/plugins.yaml` and `registry/providers.yaml` currently enumerate Context-Fabric, Perseus, Sefaria, SEDRA; CAL is absent. The generator uses `registry/v0.1.yaml` to select four required plugin IDs, so downstream addition needs explicit post-1.0 scope decision/versioning before truthful generated manifests.
- `src/cal_mcp/stdio_live_smoke.py` fixes one representative read: `cal_lexicon_lookup(query="br", lemma_key="br N")`, expected status `found`. Select this **one** user-triggered downstream CAL call, no crawl, no entire 12-case matrix. Validate launch/tool enumeration without CAL I/O first, and respect CAL backpressure (normal 3s pacing, 8 starts/60s local cap, 60s cooldown). A successful upstream smoke in the release workflow does not prove any not-yet-created Agora client launch path.
- Avoid asserting ChatGPT plugin store integration or hosted capability; Agora targets local Claude/Codex MCP launches.

## Scope
Create upstream authoritative `docs/integrations/agora.md` and offline contracts grounded in the released package, and correct stale user-doc pre-release status. The actual Agora canonical-registry and generated-artifact PR remains downstream, tracked separately in Agora#222 and not falsely attributed to this CAL repository.
