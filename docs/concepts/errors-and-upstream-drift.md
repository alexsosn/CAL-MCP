# Errors and upstream drift

CAL-MCP is a thin adapter over live, undocumented CAL web interfaces. Public tool failures distinguish invalid caller input, transport failures, upstream HTTP failures, bounded-response/content failures, and parser drift without exposing tracebacks or CAL response bodies.

## Public MCP error contract

Anticipated CAL-MCP failures return an MCP tool result with `isError=true`, one concise text block, and matching structured content:

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

`kind` is one of `invalid_input`, `network`, `upstream_http`, `response_too_large`, `content`, or `parser_drift`.

`upstream_reached` is deliberately three-valued:

- `false` only when CAL-MCP knows the request was rejected locally before transport;
- `true` when a CAL HTTP response was received and the failure is response/content/parser based;
- `null` for network or timeout failures where CAL receipt cannot be known.

`retryable` is caller-level advice after CAL-MCP's own bounded retry policy. Upstream HTTP errors are marked retryable only for the currently allowed transient statuses `500`, `502`, `503`, and `504`. Invalid input, parser drift, content-policy failures, oversized responses, and ordinary non-transient HTTP failures are not marked retryable.

`source_url` and `status_code` are populated only from typed failure metadata already carried by the adapter. CAL-MCP does not scrape URLs or status values from exception messages.

Public diagnostic messages are adapter-authored or derived from explicitly allowlisted CAL-MCP exception classes, normalized to one line, and capped at 500 characters. Python class names, tracebacks, response bodies, HTML fragments, and arbitrary unexpected exception text are not part of the structured contract.

Unexpected programming failures remain on the MCP SDK's generic sanitized error path and do not receive a CAL-MCP structured error payload.

## Caller validation

Invalid public arguments are rejected before a CAL request where the adapter can decide locally. Public caller-validation failures use the shared `CalInputError` family; request-boundary validation uses `CalRequestValidationError`. Both serialize as `invalid_input` with `upstream_reached=false` and `retryable=false`.

Examples include malformed page references, unsupported public source selectors, invalid token indexes, unsafe/control-containing identifiers, and CAL request paths that would leave the allowed origin boundary.

A caller-validation failure should not consume a CAL request.

## Network and timeout failures

`CalNetworkError` represents a CAL transport operation that could not complete safely, including configured timeout and network failures after the bounded transient retry policy is exhausted. Public results use `kind=network`, `upstream_reached=null`, and `retryable=true`.

CAL-MCP retries only explicitly classified transient conditions and never creates an unbounded retry loop.

## Upstream HTTP failures

`CalUpstreamError` represents a non-successful CAL HTTP response after the bounded retry policy. The typed object records the status code and URL, which are carried into the structured public error.

Redirect responses are not followed automatically. A 3xx therefore remains an upstream error rather than silently moving a request outside the already validated CAL boundary.

## Content and size failures

A successful HTTP status is not enough to trust a response.

`CalContentError` covers responses that are unsafe to interpret as the expected CAL content, for example an unexpected media type or recognized maintenance page. These return `kind=content` unless a more specific typed subclass applies.

`CalResponseTooLargeError` is raised while streaming when decoded response bytes exceed the configured bound. Oversized content is not truncated and passed to a parser; it returns `kind=response_too_large` and is not marked retryable.

See [Configuration](../configuration.md) for the shared HTTP policy.

## Parser drift

Each CAL research surface has a small parser with a surface-specific parse-error subclass under the shared `CalParseError` base. Parser drift means CAL returned a successful-looking response but the adapter can no longer recognize the required semantics with enough confidence to return a faithful result. Public results use `kind=parser_drift`, `upstream_reached=true`, and `retryable=false`.

Examples include:

- missing or contradictory headings/counts;
- unexpected result-container structure;
- malformed or cross-origin navigation links;
- wrong echoed query/source/page identity;
- a returned CAL identifier that does not satisfy the reusable structural contract expected by the next explicit tool;
- a page containing neither recognized data nor CAL's documented explicit empty marker.

The parser fails closed rather than silently dropping material data or reclassifying unknown markup as “no results.”

## Explicit empty and not-found results

Empty and not-found results are successful tool results, not structured errors, when the relevant CAL surface supplies semantics that the adapter has researched and tested as genuine absence.

Examples include:

- a gloss/citation search that CAL explicitly reports has no matches;
- a Targum concordance with a complete zero-count table and total zero;
- a dictionary page with CAL's explicit no-data marker;
- an external-citation dialect/source with CAL's explicit no-sources/no-citations marker;
- supported coordinate/object surfaces with an explicit stable not-found marker.

A contradictory page containing both a not-found marker and valid result blocks fails closed instead of choosing one interpretation. Empty success is not interchangeable with parser drift.

## What to do as a caller

- **`invalid_input`:** correct the input locally; do not retry the same invalid request.
- **`network` or retryable `upstream_http`:** retry only according to the client/application policy; CAL-MCP itself already applies its bounded retry budget.
- **non-retryable `upstream_http`:** inspect the status and request semantics before deciding on another action.
- **`response_too_large`, `content`, or `parser_drift`:** do not interpret the failure as empty or partial CAL data. The adapter needs a configuration/research/parser decision rather than blind retry.
- **successful empty/not-found:** treat it as CAL's answer for that request at the recorded retrieval time.
- **generic SDK execution error without structured content:** treat it as an unexpected server/programming failure, not as a classified CAL response.

## Maintainer response to drift

A CAL markup/semantic change should normally be absorbed behind the existing MCP contract:

1. recheck the exact current CAL source;
2. add a reduced failing fixture/regression test;
3. update the parser minimally;
4. keep the public tool schema stable when the scholarly task has not changed;
5. update provenance/docs if the upstream semantics actually changed.

A breaking public schema change requires its own compatibility decision rather than being hidden inside a parser repair.

See [Limitations](../limitations.md) and the tool-specific pages under [User documentation](../index.md).
