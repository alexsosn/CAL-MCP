# Issue #84 research — typed structured public tool errors

**Research date:** 2026-09-11

## Problem rechecked

Current public CAL-MCP tools return ordinary typed dictionaries on success, but service/parser/request exceptions are raised through `MCPServer`. The pinned deterministic environment uses `mcp==2.1.1`. Under that SDK, an exception not intentionally represented as an MCP tool error becomes an `UnexpectedToolError`; the caller receives `isError=true` with only a generic `Error executing tool <name>` message. This matches the user-visible failures reported in #84.

The existing user documentation already distinguishes local caller validation, network/timeouts, upstream HTTP errors, content/size failures, parser drift, explicit empty results, and modeled not-found states, but explicitly says there is no universal structured MCP error envelope yet.

## MCP SDK behavior

Current MCP Python SDK v2 documentation and source establish three relevant behaviors:

1. `ToolError` is an anticipated tool failure. The client receives `isError=true` plus readable text, but `structured_content` is `None`.
2. Unexpected exceptions are intentionally sanitized to a generic `Error executing tool <name>` result, while the original exception remains available server-side as the cause of `UnexpectedToolError`.
3. A tool may return `CallToolResult` directly. When `is_error` is true, `MCPServer` does not validate `structured_content` against the successful tool output model. The MCP protocol permits `CallToolResult` to contain both `isError=true` and structured content.

Sources rechecked 2026-09-11:

- https://py.sdk.modelcontextprotocol.io/servers/handling-errors/
- https://py.sdk.modelcontextprotocol.io/api/mcp/server/mcpserver/server/
- https://py.sdk.modelcontextprotocol.io/api/mcp/server/mcpserver/tools/base/
- https://py.sdk.modelcontextprotocol.io/api/mcp/server/mcpserver/utilities/func_metadata/
- https://github.com/modelcontextprotocol/python-sdk/blob/main/schema/2026-07-28.json

## Repository exception taxonomy

The shared request layer already has stable explicit exception classes:

- `CalRequestValidationError` — rejected before transport;
- `CalNetworkError` — transport/timeout failure;
- `CalUpstreamError` — non-successful HTTP response, with `status_code` and `url`;
- `CalContentError` — successful HTTP response unsafe to interpret;
- `CalResponseTooLargeError` — bounded response exceeded, with `url` and configured limit.

Deterministic input conversion has `NormalizationError` and its subclasses, all inheriting `ValueError`.

Surface parsers use dedicated parse-error subclasses that currently inherit `CalContentError` (for example `LexiconParseError`). This is semantically useful but does not provide a shared type that distinguishes parser drift from other content-policy failures.

Generic `ValueError` must **not** be treated as an anticipated public error globally: doing so would risk converting a programming bug into an `invalid_input` result and exposing arbitrary internal exception text. Expected caller-validation errors need an explicit shared public-validation type or deliberate wrapping at the validation boundary.

## Error-result contract candidate

A failed **known CAL-MCP operation** should remain a normal MCP tool result with `isError=true`, so the model/client can inspect it. The structured content should be a small stable object:

```json
{
  "error": {
    "kind": "invalid_input | network | upstream_http | response_too_large | content | parser_drift",
    "operation": "cal_text_page",
    "upstream_reached": false,
    "retryable": false,
    "message": "safe diagnostic text",
    "source_url": null,
    "status_code": null
  }
}
```

`upstream_reached` is tri-state: `false` when local validation definitely rejected the request, `true` when an HTTP response was received / parsed, and `null` for transport failures where the client cannot know whether CAL received the request.

`source_url` is present only when the exception already carries a trusted CAL URL. Do not parse URLs back out of arbitrary exception messages. `status_code` is present only for upstream HTTP failures.

The textual `content` should contain the same safe kind + diagnostic in human/model-readable form. Structured content is for programmatic clients; text remains useful to clients/models that display only content blocks.

## Retryability policy

- local invalid input: `false`;
- parser drift/content policy/oversize: `false` for the same call;
- network failure after the adapter's bounded retry budget: `true` at a later caller-selected time;
- upstream HTTP: `true` only for the same transient status set already used by the shared request layer (`500`, `502`, `503`, `504`), otherwise `false`.

This does not add retries or change request volume.

## Successful empty/not-found results are not errors

Existing typed empty/not-found states remain successful result objects. Examples include modeled no-match searches, text/Targum/Syriac not-found states, and zero-result concordances. #84 must not reclassify these into `isError=true` merely to make all absence look uniform.

## Centralization boundary

The cleanest integration point is a small CAL-specific `MCPServer` subclass or equivalent server-boundary wrapper around `MCPServer.call_tool()`:

- call the normal SDK implementation first;
- catch `UnexpectedToolError` before the outer SDK handler sanitizes it;
- inspect only the original exception type/cause;
- convert **allowlisted CAL-MCP exception classes** into a direct structured `CallToolResult`;
- re-raise all unknown exceptions unchanged so SDK crash sanitization/logging remains intact.

This avoids copying try/except logic into 32 public tools and automatically applies to future tools that use the same typed error classes.

## Shared type gaps to resolve in the plan

Two explicit types are needed for safe classification:

1. a shared parser-drift base (for example `CalParseError(CalContentError)`) with existing surface parse errors migrated mechanically to inherit it;
2. a shared caller-validation base (for example `CalInputError(ValueError)`) used by public service/input validators that are intended to reach the tool boundary.

The migration must be test-driven. It should not catch arbitrary `ValueError`, `AssertionError`, `TypeError`, or other programming exceptions.

## Security / privacy boundary

- unexpected exceptions stay generic and must not expose `str(exc)`;
- no response body or CAL HTML is included in public errors;
- only already-validated CAL URLs carried by typed request exceptions may be exposed;
- caller values should not be copied wholesale into diagnostics unless the existing validation error is already deliberately safe;
- source URLs may contain query parameters that represent the explicit user request; they are acceptable scholarly/request provenance but must stay on the validated CAL origin.

## TDD implications

The first RED should prove the current user-visible defect through the in-memory MCP client, not by unit-testing a helper in isolation. Representative cases should include:

- local invalid input -> structured `invalid_input`, `upstream_reached=false`, no CAL request;
- parser drift -> structured `parser_drift`, `upstream_reached=true`;
- transient upstream HTTP -> structured `upstream_http`, status/source URL, retryable true;
- response-too-large/content failure classification;
- unexpected programming exception remains generic and has no structured CAL-MCP error payload;
- successful explicit not-found/empty remains `isError=false`;
- success output schemas/results are unchanged.

Normal tests remain offline with mock transports/monkeypatching. No CAL request is required for issue #84 research or implementation.

## Architecture consequence

This changes a durable public MCP boundary: tool execution failures that CAL-MCP recognizes become structured error results rather than opaque SDK crash strings. `wiki/architecture.md`, `wiki/decisions.md`, `wiki/testing.md`, and `docs/concepts/errors-and-upstream-drift.md` should be updated in the same PR after GREEN.
