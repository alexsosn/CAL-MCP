# Issue #117 research — cache-aware request-volume wording for core text tools

**Research date:** 2026-09-09  
**Baseline:** `main` at `f3e84cd2032773a9b96c5145e5baa63c8a76889a`  
**Related follow-up:** #120 covers non-`TextService` tool families discovered during this audit.

## Question

What request-volume contract is actually true for the four core text operations when they run through CAL-MCP's shared lifespan-managed HTTP client, and which current user/runtime descriptions contradict it?

## Runtime architecture

`src/cal_mcp/server.py` creates one `CalHttpClient` in the MCP lifespan and reuses that client for every CAL-backed tool call until server shutdown. The client therefore owns one shared completed-result cache and one shared single-flight map across successive/overlapping MCP calls.

The four core text operations all call the same shared `CalHttpClient.fetch()` path with stable namespaces in `src/cal_mcp/texts.py`:

| Operation | Namespace | Upstream request identity on a cache miss |
| --- | --- | --- |
| `cal_text_catalogue` | `text-catalogue-v1` | one catalogue request for the explicitly selected level |
| `cal_text_search` | `text-search-v1` | one topic-search request |
| `cal_text_information` | `text-information-v1` | one `get_file_info.php` request for the deterministic coordinate |
| `cal_text_page` | `text-page-v1` | one explicit page request on the researched route |

No operation performs a route-discovery preflight or follows returned links automatically.

## Completed cache semantics

`docs/configuration.md` and `tests/test_http_client.py::test_identical_request_reuses_parsed_cache_and_preserves_retrieved_at` already establish the shared contract:

1. only successfully validated and parsed results enter the bounded process-local cache;
2. the first cache miss performs the logical request and records the actual CAL retrieval timestamp;
3. an identical later call through the same client can be served from the completed cache with **zero new upstream I/O**;
4. the cache hit preserves the original source URL/retrieval timestamp rather than pretending that CAL was contacted again;
5. disabling caching causes a later identical call to perform a new request normally.

Therefore “every invocation performs exactly one CAL request” is false for a running MCP process with default caching.

## Single-flight semantics

`docs/configuration.md` also establishes that simultaneous requests with the same normalized request identity and parser/cache namespace are coalesced. One live caller owns the active generation; matching callers await that result and do not create a duplicate upstream request while the generation remains active.

This coordination is caller-owned and creates no background request, prefetch, cache warming, or recursive work.

## Retry semantics and terminology

The shared client may retry specifically whitelisted transient failures according to its bounded retry policy. A cache miss therefore should not be documented as “exactly one HTTP transport attempt”. The useful public contract has three layers:

- **explicit MCP operation** — the caller's one requested scholarly action;
- **logical CAL request identity/workflow** — at most one new request identity submitted by each core text operation to the shared client;
- **transport attempts** — zero on a completed cache hit or in-flight follower; normally one on an ordinary cache miss; potentially more within the finite retry budget after retryable failures.

This ticket should use “at most one new logical CAL request” / “zero new upstream I/O on a completed cache hit” and defer transport-attempt details to the shared configuration/retry documentation.

## Current stale wording

### Runtime MCP descriptions

Current `src/cal_mcp/server.py` says:

- `cal_text_catalogue`: “Each call performs exactly one bounded CAL request.”
- `cal_text_search`: “Each call performs exactly one bounded CAL search request.”
- `cal_text_information`: “One call performs exactly one bounded CAL request and follows no metadata links.”

`cal_text_page` does not currently make the same exact-count claim in its executable description, but it shares the identical cache/single-flight request layer and should use the same bounded terminology when request behavior is described.

### User text documentation

Current `docs/tools/texts.md` contains several unconditional one-request statements, including:

- catalogue calls perform one CAL request;
- text search performs the original single CAL request;
- text-information calls perform exactly one `get_file_info.php` request;
- supported text-page calls make exactly one CAL request;
- the Request bounds section says every public text tool performs exactly one user-initiated CAL request.

These statements correctly intend to prohibit hidden traversal/prefetch, but they conflate that bounded workflow property with actual new upstream I/O after cache/single-flight suppression.

## Existing behavior tests

`tests/test_text_information.py` already proves that a direct uncached text-information service call constructs exactly one deterministic `CalRequest` identity with no metadata-link follow-up.

`tests/test_http_client.py` proves generic completed-cache behavior, but there is not yet a focused endpoint-level invariant showing two identical `TextService.information()` calls through one shared client result in one transport call total. Adding that GREEN invariant is useful because #117 was triggered specifically by `cal_text_information`.

No runtime defect was found. The production service already behaves according to the cache-aware contract.

## Scope decision

#117 will change only core `TextService` request-volume descriptions/tests:

- relevant `src/cal_mcp/server.py` executable descriptions;
- `docs/tools/texts.md`;
- focused documentation/runtime-contract tests;
- one endpoint-specific cache reuse invariant for `cal_text_information`.

No `CalHttpClient`, `TextService`, request construction, cache, retry, single-flight, parser, schema, or provenance implementation will change.

The audit also found the same unconditional exact-count wording in other domains, notably `docs/tools/concordance.md`, `docs/tools/search.md`, and corresponding server descriptions. Those are tracked separately in #120 so this correction remains independently reviewable.

## Frozen wording contract

For the core text family, documentation should communicate all of the following:

1. one explicit operation never recursively traverses/prefetches related CAL resources;
2. each operation submits at most one new logical CAL request to the shared client;
3. on an ordinary cache miss the relevant upstream request is performed, subject to the shared bounded retry policy;
4. a completed shared-client cache hit performs zero new upstream I/O;
5. an identical overlapping single-flight follower does not duplicate the active upstream request;
6. validation failures may also stop before transport;
7. cache/single-flight suppression is not background work and preserves the existing provenance contract.

## CAL load impact

Zero. This research is grounded in repository implementation/tests and the already documented request layer; no live CAL probe is needed.