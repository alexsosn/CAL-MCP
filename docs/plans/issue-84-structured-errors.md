# Issue #84 plan — structured public MCP tool errors

**Plan date:** 2026-09-11

This ticket follows research → plan → MCP-level RED → minimal implementation → deterministic/full GREEN → docs/architecture update → logically independent adversarial review → review-regression RED/GREEN if needed → fresh exact-head review → guarded merge.

Research is frozen in `docs/research/issue-84-structured-errors.md`.

## Problem and frozen scope

Current `mcp==2.1.1` intentionally sanitizes unexpected tool exceptions to `Error executing tool <name>`. CAL-MCP therefore loses the useful distinction already present in its internal exception taxonomy when a public tool fails.

Issue #84 changes the **public failure representation**, not CAL request semantics and not successful result schemas.

In scope:

- return a consistent machine-readable error object for anticipated CAL-MCP tool failures;
- preserve an accompanying readable text error block;
- classify local invalid input, network, upstream HTTP, response-size, content-policy, and parser-drift failures;
- expose operation, retryability, honest upstream-reachability, safe diagnostic text, and typed source/status metadata when already available;
- migrate intended caller-validation failures from generic `ValueError` to an explicit shared input-error base;
- give all surface parser errors a shared explicit parser-drift base;
- centralize conversion at the MCP server boundary rather than wrapping every tool independently;
- keep unexpected programming errors on the SDK's existing generic crash path.

Out of scope:

- changing successful result models or modeled empty/not-found states;
- changing retries, timeouts, concurrency, caching, or CAL request volume;
- exposing CAL response bodies/HTML;
- accepting arbitrary URLs;
- introducing a generic application exception serializer for every Python exception;
- restructuring all domain modules;
- changing the MCP transport or adding a hosted service.

## Public error shape

Anticipated tool failures return `CallToolResult(is_error=True)` with both one text block and `structuredContent` shaped as:

```json
{
  "error": {
    "kind": "invalid_input",
    "operation": "cal_text_page",
    "upstream_reached": false,
    "retryable": false,
    "message": "file_id must be a CAL decimal identifier",
    "source_url": null,
    "status_code": null
  }
}
```

Frozen fields:

- `kind`: one of `invalid_input`, `network`, `upstream_http`, `response_too_large`, `content`, `parser_drift`;
- `operation`: exact MCP tool name;
- `upstream_reached`: boolean or null;
  - `false` only when CAL-MCP knows transport was not reached;
  - `true` when an HTTP response was received and the failure is response/parser based;
  - `null` for network/timeout failures where CAL receipt cannot be known;
- `retryable`: caller-level retry advice after CAL-MCP's own bounded retry policy;
- `message`: bounded safe diagnostic string produced only from explicitly allowlisted error classes;
- `source_url`: trusted CAL URL when carried by a typed exception, else null;
- `status_code`: HTTP status for `upstream_http`, else null.

Text content is a concise rendering of the same public data. It must not contain more information than `structuredContent`.

No Python class name, traceback, response body, HTML fragment, or arbitrary exception text is part of the public error contract.

## Error taxonomy implementation

Add a small shared error module (prefer `src/cal_mcp/errors.py`) containing:

- `CalInputError(ValueError)` — intentional public caller-validation failure;
- `CalParseError(CalContentError)` — intentional parser-drift base;
- the stable public error-kind enum/model/serializer if keeping it separate from `server.py` improves reviewability.

To avoid an import cycle, `CalParseError` may instead live in `client.py` next to `CalContentError` if necessary; the final shape should keep dependency direction simple and explicit.

### Caller validation migration

Migrate only validation sites deliberately reachable from public tool arguments, including shared validators used by those tools:

- normalization errors (`NormalizationError` and subclasses) should inherit the explicit input-error base;
- structural CAL lemma-key validation;
- text/file/subtext/page/coordinate/search validation;
- token coordinate/index validation;
- English-search/gloss-field validation;
- concordance/KWIC identifier/list/script/charset validation;
- bibliography input validation;
- dictionary-collation source/page validation;
- external-citation selector validation;
- Targum/Syriac selector/book/chapter/verse/opaque-ID validation;
- shared biblical selector validation used by public specialist tools.

Do **not** globally replace every `ValueError`. Configuration validation (`CalClientConfig`), internal invariants, enum/library conversion outside a public validation boundary, and programming failures remain ordinary exceptions unless a focused test proves they are intended caller errors.

### Parser migration

Existing surface parser-error classes should inherit the shared `CalParseError` base rather than `CalContentError` directly. Their public kind becomes `parser_drift` while unrelated shared content-policy errors remain `content`.

This is a type-hierarchy change only; existing parser messages and fail-closed behavior should remain unchanged.

## MCP server boundary

Introduce a CAL-specific subclass of `MCPServer[AppContext]` (or equivalent narrow wrapper) that overrides `call_tool()` with the SDK's current signature.

Algorithm:

1. call `super().call_tool(...)` normally;
2. if it succeeds, return the SDK result unchanged;
3. catch `UnexpectedToolError`;
4. inspect its direct cause;
5. if the cause is one of the explicit CAL-MCP anticipated types, build and return the structured error `CallToolResult`;
6. otherwise re-raise the `UnexpectedToolError` unchanged so the outer SDK keeps its generic crash sanitization/logging;
7. catch SDK `ToolError` separately only where its cause is the SDK's argument/schema validation error and that can be represented safely as `invalid_input`; unknown-tool errors and deliberate non-CAL SDK errors keep normal SDK behavior.

Do not catch all `ToolError` or all `ValueError` and reclassify them.

The global server object becomes this subclass; existing tool decorators and successful output schemas remain unchanged.

## Safe classification

Expected mappings:

| Exception | kind | upstream_reached | retryable | metadata |
| --- | --- | --- | --- | --- |
| `CalInputError` / explicit request validation | `invalid_input` | false | false | no URL/status unless already safe and local |
| `CalNetworkError` | `network` | null | true | no inferred URL |
| `CalUpstreamError` | `upstream_http` | true | status in {500,502,503,504} | trusted `url`, `status_code` |
| `CalResponseTooLargeError` | `response_too_large` | true | false | trusted `url` |
| `CalParseError` | `parser_drift` | true | false | source URL only if the typed error explicitly carries one; do not scrape messages |
| other `CalContentError` | `content` | true | false | source URL only when explicitly carried |

If a type does not carry a trustworthy URL, `source_url` stays null even if its human message happens to contain one.

Messages are bounded to a conservative maximum length (plan target: 500 code points) and normalized to one line before serialization. The known exception classes currently emit short adapter-authored messages; the bound protects future additions.

## TDD RED gate

Before production changes, add MCP-level tests using the in-memory `mcp.Client` and mocked CAL transport/service behavior.

Required RED cases:

1. **Caller input** — malformed `cal_text_page` or `cal_token_analysis` input returns `is_error=true`, `kind=invalid_input`, `upstream_reached=false`, `retryable=false`, and consumes zero CAL requests.
2. **SDK argument/schema validation** — wrong JSON type/missing required field receives a structured `invalid_input` only if the SDK exposes a safely identifiable validation cause; otherwise document and preserve SDK behavior rather than guessing.
3. **Parser drift** — a mocked successful HTTP response with malformed semantic markup returns `parser_drift`, `upstream_reached=true`, no HTML leakage.
4. **Upstream transient HTTP** — mocked 503 after the bounded retry budget returns `upstream_http`, trusted URL/status, `retryable=true`.
5. **Non-transient HTTP** — representative 404/4xx returns `retryable=false`.
6. **Network failure** — exhausted timeout/network failure returns `network`, `upstream_reached=null`, `retryable=true`.
7. **Response too large/content policy** — typed size/content error maps distinctly and is not retryable.
8. **Unexpected crash** — monkeypatched service/tool raises a `RuntimeError` containing a secret sentinel; client still receives the SDK's generic `Error executing tool ...`, no CAL-MCP structured error payload, and the sentinel is absent.
9. **Successful absence** — one existing `not_found`/empty result remains `is_error=false` and unchanged.
10. **Successful output schema** — representative success still has the same structured success content/schema.

A valid RED requires deterministic install/Ruff lint/Ruff format/mypy green and pytest failures only for the missing structured-error behavior. Normal CI remains fully offline.

## Implementation / GREEN gate

Implement the minimum common types, validation-base migration, parser-base migration, classifier, and MCP-server boundary needed to satisfy the RED.

After focused tests pass, run the repository's full two-matrix CI:

- deterministic constrained Python 3.11 job;
- latest-compatible dependency job;
- existing offline pytest suite;
- no live CAL request.

Because this relies on MCP SDK extension behavior, latest-compatible CI is a required compatibility signal rather than optional evidence.

## Documentation and architecture updates

After initial GREEN, update:

- `docs/concepts/errors-and-upstream-drift.md` — replace “no universal envelope” with the exact structured-error contract, retry/upstream-reached semantics, and successful empty/not-found distinction;
- `docs/integrations/standalone-mcp.md` / getting-started only if callers need one concise example;
- `wiki/architecture.md` — show the server-boundary error classifier without making it a CAL-domain parser;
- `wiki/testing.md` — MCP contract tests require structured anticipated errors plus generic unknown-crash non-leakage;
- `wiki/decisions.md` — add a durable decision that known CAL-MCP failures are structured `isError` results while unexpected crashes remain SDK-sanitized;
- README/tool docs only where a cross-link is needed; do not repeat the entire schema on every tool page.

No CAL research record update is required beyond the focused issue research because this ticket changes the adapter/MCP boundary, not CAL behavior.

## Adversarial review gate

Freeze an exact final SHA and conduct a logically independent whole-PR review from the security/client boundary.

Challenge specifically:

1. Does any generic `ValueError`, `RuntimeError`, assertion, output-conversion failure, or unexpected SDK exception get misclassified as anticipated?
2. Can any traceback, arbitrary exception text, CAL response body, HTML, or secret sentinel reach public error content?
3. Is `upstream_reached` honest rather than guessed for network failures?
4. Are retryability flags consistent with the existing request policy and status allowlist?
5. Is `source_url` exposed only from trusted typed fields, never message parsing?
6. Do parser errors distinguish from generic content-policy failures?
7. Do invalid caller values fail before CAL transport where they did previously?
8. Are successful empty/not-found states still success results?
9. Are success output schemas/tool names unchanged?
10. Does `mcp>=2,<3` latest-compatible CI still pass with the subclass/return shape?
11. Does the central boundary cover all current public tools without duplicating wrappers?
12. Are unknown-tool and SDK protocol errors preserved rather than converted into a misleading CAL error?

Any blocker requires review-regression RED → minimal fix → full GREEN → fresh exact-head review.

## Merge gate

Merge only when:

1. this research and plan are committed before tests/implementation;
2. MCP-level RED is valid;
3. full deterministic and latest-compatible CI are green;
4. docs/architecture/decision updates match the executable contract;
5. exact final SHA has a clean logically independent adversarial review;
6. no unresolved review threads/helper workflows remain;
7. guarded merge pins the reviewed SHA;
8. issue #84 closes.

## CAL load impact

Zero CAL requests are required for implementation/review. Tests use mocked transports or in-process tool failures. This ticket does not change the number, concurrency, retry count, or traversal behavior of CAL requests.
