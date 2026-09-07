# Issue #60 research — skip unused non-success response bodies

Date: 2026-09-07

## Question

Can CAL-MCP stop consuming response bodies for HTTP statuses that the shared request layer will reject or retry, without changing public semantics or weakening the successful-response size bound?

## Repository baseline

Current `main` is `1aa9dd9cd7fe9e4592e586b5b117e271a47c03c8`.

`src/cal_mcp/client.py` currently splits production response handling across two layers:

1. `_Httpx2Transport.__call__` opens `AsyncClient.stream(...)` and **unconditionally iterates `response.aiter_bytes(...)`**, accumulating the full decoded body up to `max_response_bytes` before returning `CalResponse`.
2. `CalHttpClient._request_with_retries` receives that completed `CalResponse` and only then applies status policy:
   - retry 500/502/503/504 within the existing retry cap;
   - reject every other status >= 300 with `CalUpstreamError`;
   - return only <300 responses to content validation/parsing/cache.

Therefore bodies from redirects, semantic 4xx/429 responses, and transient/final 5xx responses are never used by an endpoint parser or cache entry. The typed upstream error contains only `status_code` and `url`.

Existing `tests/test_response_size_policy.py` already provides `CountingStream` plus an HTTPX2 `MockTransport` factory. It proves successful-response streams close and that over-limit 2xx streaming stops after the first over-limit chunk, but it does not assert that non-success bodies remain unread.

## HTTP streaming semantics

HTTP response status and fields precede content. RFC 9110 describes messages as streams in which control data and header fields are available before content; response control data includes the status code. This makes a status decision before application-level body consumption a normal HTTP processing boundary.

Source: RFC 9110, HTTP Semantics, especially sections 5.5, 6, and 15: <https://www.rfc-editor.org/rfc/rfc9110.html>

HTTPX documents streaming responses specifically so callers can inspect response metadata and conditionally decide whether to read the body. Its quickstart shows `with httpx.stream(...) as r:` followed by a header check before `r.read()`. Exiting the streaming context closes the response when content is not consumed.

Source: HTTPX QuickStart, Streaming Responses: <https://www.python-httpx.org/quickstart/#streaming-responses>

The repository uses `httpx2`, whose streaming API is intentionally compatible with this HTTPX model and is already exercised by the existing `MockTransport`/`AsyncByteStream` tests.

## Contract boundary

The optimization is safe only at the production transport boundary for `status_code >= 300`:

- Preserve `status_code`, final request URL, content type, and retrieval timestamp in the returned `CalResponse`.
- Set `body=b""` because downstream status handling never exposes or parses it.
- Let the existing `async with self._client.stream(...)` exit close the unread response stream.
- Do **not** move retry/status classification into `_Httpx2Transport`; `_request_with_retries` remains the sole policy owner.
- Do **not** alter injected/custom transports. They may still return bodies, but the shared client rejects status >=300 before content validation/parsing.
- Do **not** change successful 2xx behavior: decoded-byte streaming, exact-limit acceptance, over-limit failure, parser/cache gates, and provenance remain unchanged.

## Why not optimize via `Content-Length`

A separate idea was to reject a body early when `Content-Length > max_response_bytes`. That is not adopted here. CAL-MCP's documented limit applies to **decoded bytes delivered by HTTPX2**, while `Content-Length` participates in HTTP message framing and can differ from the decoded representation when content codings are present. Treating it as the decoded-size authority would change the existing contract or require extra encoding-specific rules for little benefit. Streaming remains the authoritative 2xx size check.

## Failure/retry semantics to preserve

The maintenance change must prove all of these at the production HTTP boundary:

- 302/other 3xx: no redirect following, one request, body stream not iterated, `CalUpstreamError`.
- 404 and 429: no retry, body stream not iterated, `CalUpstreamError`.
- 503 (representative transient status): existing configured retry count remains exact; each failed attempt closes without iterating its body; final failure remains `CalUpstreamError` if retries are exhausted.
- 200: stream is still consumed normally; existing response-size tests remain authoritative.

## Load and safety impact

This change can only reduce bytes consumed on failed CAL responses. It creates no new request, retry, traversal, background work, cache behavior, or public MCP surface. No live CAL request is needed to validate it.

## Smallest implementation

Inside `_Httpx2Transport.__call__`, immediately after entering the response stream and before constructing/iterating the body buffer:

- if `response.status_code >= 300`, return a `CalResponse` with an empty body and the existing metadata;
- otherwise execute the existing bounded 2xx streaming loop unchanged.

The surrounding response context manager closes the stream on return.
