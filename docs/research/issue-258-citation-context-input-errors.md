# Issue #258 — research: citation-context invalid selector escapes MCP error boundary

Date: 2026-10-10. Source: release candidate installed-wheel user-facing E2E evidence in issue #258, and inspection of actual main source `src/cal_mcp/lexicon_citation_context.py`, `src/cal_mcp/errors.py`, and `src/cal_mcp/server.py`.

A caller passing `https://cal.huc.edu/x` instead of a `Citation.full_coordinate` to `cal_lexicon_citation_context` obtains only an untyped MCP error, not the repository's standard structured `invalid_input` envelope. The local `_validate_full_coordinate` checks ASCII decimal/positive integer correctly **before** calling the HTTP client, but raises built-in `ValueError`. Shared `classify_public_tool_error` intentionally maps only allowlisted `CalInputError` and other known classes; it does not classify arbitrary `ValueError` (correct as a policy). Hence the narrow safe fix is raising `CalInputError` at the validation source, *not* teaching the generic MCP boundary to serialize unrelated Python ValueErrors.

Shared structured error envelope contract: `error.kind="invalid_input"`, `error.operation="cal_lexicon_citation_context"`, `upstream_reached=false`, `retryable=false`, `source_url=null`, `status_code=null`, with the current selector message. Existing service callers that expect ValueError remain compatible because `CalInputError(ValueError)`.

No upstream CAL request necessary or justified, since input rejection happens before transport. No public tool schema, URL acceptance, or release count change.
