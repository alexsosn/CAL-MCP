# Errors and upstream drift

CAL-MCP is a thin adapter over live, undocumented CAL web interfaces. A useful failure contract must distinguish “the caller asked for something invalid,” “CAL could not be reached,” “CAL reported no data,” and “CAL returned a page whose semantics can no longer be parsed safely.”

This page describes the current adapter semantics. It does **not** promise a new universal MCP error-envelope schema beyond what the executable server currently returns through the MCP framework.

## Caller validation

Invalid public arguments are rejected before a CAL request where the adapter can decide locally. Depending on the surface this is represented by local `ValueError` validation or, at the shared request boundary, `CalRequestValidationError`.

Examples include malformed page references, unsupported public source selectors, invalid token indexes, unsafe/control-containing identifiers, and CAL request paths that would leave the allowed origin boundary.

A caller-validation failure should not consume a CAL request.

## Network and timeout failures

`CalNetworkError` represents a CAL transport operation that could not complete safely, including configured timeout and network failures after the bounded transient retry policy is exhausted.

CAL-MCP retries only explicitly classified transient conditions and never creates an unbounded retry loop.

## Upstream HTTP failures

`CalUpstreamError` represents a non-successful CAL HTTP response after the bounded retry policy. The object records the status code and URL.

Redirect responses are not followed automatically. A 3xx therefore remains an upstream error rather than silently moving a request outside the already validated CAL boundary.

## Content and size failures

A successful HTTP status is not enough to trust a response.

`CalContentError` covers responses that are unsafe to interpret as the expected CAL content, for example an unexpected media type or recognized maintenance page.

`CalResponseTooLargeError` is a `CalContentError` raised while streaming when decoded response bytes exceed the configured bound. Oversized content is not truncated and passed to a parser.

See [Configuration](../configuration.md) for the shared HTTP policy.

## Parser drift

Each CAL research surface has a small parser with a surface-specific parse-error subclass. Parser drift means CAL returned a successful-looking response but the adapter can no longer recognize the required semantics with enough confidence to return a faithful result.

Examples include:

- missing or contradictory headings/counts;
- unexpected result-container structure;
- malformed or cross-origin navigation links;
- wrong echoed query/source/page identity;
- a returned CAL identifier that does not satisfy the reusable structural contract expected by the next explicit tool;
- a page containing neither recognized data nor CAL's documented explicit empty marker.

The parser fails closed rather than silently dropping material data or reclassifying unknown markup as “no results.”

## Explicit empty results

An empty result is successful only when the relevant CAL surface supplies semantics that the adapter has researched and tested as a genuine empty state.

Examples already modeled by current tools include:

- a gloss/citation search that CAL explicitly reports has no matches;
- a Targum concordance with a complete zero-count table and total zero;
- a dictionary page with CAL's explicit no-data marker;
- an external-citation dialect/source with CAL's explicit no-sources/no-citations marker.

Empty success is not interchangeable with parser drift.

## Not-found states

Some CAL surfaces report a missing coordinate/object inside an HTTP-200 page. Where the upstream marker is stable enough to distinguish it safely, CAL-MCP models a typed not-found/status result rather than calling it a transport error.

For example, current Targum/Syriac verse-comparison pages expose explicit coordinate-error markers. A contradictory page containing both a not-found marker and valid result blocks fails closed instead of choosing one interpretation.

## What to do as a caller

- **Caller validation:** correct the input locally; do not retry the same invalid request.
- **Network/upstream transient failure:** retry only according to the client/application policy; CAL-MCP itself already applies its bounded retry budget.
- **Explicit empty/not-found:** treat the result as CAL's answer for that request at the recorded retrieval time.
- **Parser/content drift:** do not interpret the response as empty or partial CAL data. The adapter needs a researched parser fix and regression test.

## Maintainer response to drift

A CAL markup/semantic change should normally be absorbed behind the existing MCP contract:

1. recheck the exact current CAL source;
2. add a reduced failing fixture/regression test;
3. update the parser minimally;
4. keep the public tool schema stable when the scholarly task has not changed;
5. update provenance/docs if the upstream semantics actually changed.

A breaking public schema change requires its own compatibility decision rather than being hidden inside a parser repair.

See [Limitations](../limitations.md) and the tool-specific pages under [User documentation](../index.md).