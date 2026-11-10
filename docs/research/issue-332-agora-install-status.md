# Issue #332 — Agora installation status audit (2026-11-10)

## Contradiction and ground truth

The published [v0.1.0 CAL-MCP release](https://github.com/alexsosn/CAL-MCP/releases/tag/v0.1.0) remains independently installable as `cal-mcp==0.1.0` over local MCP stdio, without CAL data redistribution. However, `docs/installation.md` currently says that Agora registration **remains downstream work** and its manifest is an **unverified proposal**. These statements were true before but are now outdated.

The upstream [CAL-MCP PR #327](https://github.com/alexsosn/CAL-MCP/pull/327) merged and closed issue #16 after checking [Agora PR #268](https://github.com/alexsosn/Agora/pull/268), which merged on 4 November 2026 and closed downstream Agora issue #222. The canonical `docs/integrations/agora.md` already records the distinctions:

- Agora's canonical registry includes CAL-MCP in **candidate** v1.1 (not yet a **published marketplace release**).
- Its Claude and Codex manifests are generated from the downstream registry, use a version-pinned local `uvx`/stdio launch, and do not embed CAL data or adapters.
- A bounded real CAL lookup through the generated **Codex** path succeeded (Agora workflow runs 38234918961 and 38235243021), with all 36 published tools discoverable. The generated **Claude** path has deterministic manifest coverage only and is still community/unverified live.
- This does not assert public ChatGPT/mobile Plugin Directory availability or certify CAL uptime, and preserves the independent upstream install.

Evidence sources: the 11/10/2026 current mainline contents of `docs/installation.md`, `docs/integrations/agora.md`, upstream PR #327 / issue #16 and downstream PR #268 / issue #222. No new CAL request is required for this documentation discrepancy.
