# Issue #160 — proxy environment for stdio MCP clients

**Date:** 2026-10-10. **Base:** `main` at `cf99b098`.
**Type:** documentation / process ergonomics; no CAL network requests.

## Research gate

- The 2026-09-24 user-level installed-stdio reproduction in #160 returned HTTP 200 with
  the correct egress proxy environment and gateway HTTP 403 ("Host not in allowlist")
  when `HTTPS_PROXY` was absent. This is an observation from that environment, **not**
  a universal diagnostic for all HTTP 403 responses.
- `src/cal_mcp/client.py` constructs `httpx2.AsyncClient` without overriding
  `trust_env`, so it honors the process's supported proxy / CA variables.
- MCP stdio clients may pass a restricted child environment: the Python SDK's
  `StdioServerParameters` does not implicitly guarantee preservation of a host's
  `HTTPS_PROXY`. The caller must supply `env=` where proxy access is required.
- No new CAL request or independent upstream HTML interpretation is needed.

## Plan

1. **RED**: add an offline docs-contract test that requires both user-facing guides
   to explain child-process environment inheritance, the possible 403 symptom,
   and the precise proxy/CA variables; require an executable-looking Python SDK
   `StdioServerParameters(..., env=...) ` example in the standalone guide.
   This test is document-only and has no CAL dependency.
2. **GREEN**: add concise troubleshooting text in `docs/installation.md` and
   `docs/integrations/standalone-mcp.md`. Use an explicit environment copied from
   `os.environ` and document the relevant proxy/CA variables; show an
   MCP connection snippet. Preserve existing release pin and process contract.
3. Validate the new contract and existing Markdown links offline, then full
   deterministic CI and latest-compatible CI when available.
4. Perform a logically independent review of the exact PR head before merge.

## Non-goals and boundaries

No HTTP configuration switches, transport behavior changes, MCP schema changes,
public version changes, CAL queries, workflow changes, or new permissions.
Do not claim that every 403 is a proxy problem or that the SDK always drops
all environment variables.
