# Configuration

CAL-MCP's request layer is deliberately conservative because CAL is a live academic service and the project has not found a published CAL-specific machine-access policy. This page documents the request-policy contract implemented by `CalClientConfig`.

The MCP server does not expose CAL-backed tools yet, so these settings are currently programmatic configuration for the adapter layer. CLI/environment wiring should be added only when a later tool ticket needs it; the defaults and safety bounds below remain the baseline.

## Default request policy

| Setting | Default | Enforced bound / behavior |
| --- | ---: | --- |
| Connect timeout | 5 s | finite, > 0 |
| Read timeout | 10 s | finite, > 0 |
| Total attempt timeout | 15 s | finite, > 0 |
| Maximum concurrency | 2 | 1–8 |
| Retry count | 1 | 0–3 |
| Initial retry backoff | 0.25 s | finite, 0–1 s; exponential per retry |
| Cache enabled | yes | completed-result retention can be disabled completely |
| Cache entries | 128 | 0–4096; 0 retains nothing |
| Cache TTL | 900 s (15 min) | > 0 and <= 86400 s |
| User-Agent | `CAL-MCP/<version> (+https://github.com/alexsosn/CAL-MCP)` | non-empty |

HTTPX2 also receives explicit connection/read timeouts and connection-pool limits. CAL-MCP additionally wraps each transport attempt in the total timeout.

## Retry behavior

Retries are explicitly whitelisted rather than applied to every transport exception. The current policy retries only:

- CAL-MCP's finite per-attempt timeout (`TimeoutError`);
- HTTPX2 timeout exceptions (`httpx2.TimeoutException`);
- HTTPX2 network exceptions (`httpx2.NetworkError`);
- HTTP 500, 502, 503, and 504.

Other HTTPX2 errors, including local/protocol-type errors, are surfaced after one attempt as typed CAL-MCP transport failures. A bare `OSError` from an injected/custom transport is also treated as non-retryable rather than being assumed transient. This keeps retries tied to the explicit production HTTPX2 transient categories instead of a broad base exception class.

Other HTTP statuses are returned as typed upstream errors without blind retry. In particular, CAL-MCP does not automatically retry HTTP 429; a rate/overload response should reduce request pressure rather than create another immediate request.

The initial backoff is capped at 1 second and the retry count at 3. Backoff is exponential (`base * 2**attempt`), so the configured retry sleep budget is finite and cannot be made arbitrarily large by configuration.

HTTP redirects are not followed automatically. A 3xx response is returned as a typed upstream error before parsing or caching. If a later CAL endpoint demonstrably requires redirects, support should be added explicitly with a same-origin, bounded redirect policy rather than enabling arbitrary automatic redirect following.

No retry path creates background work or continues after the caller's operation has ended.

## Duplicate-request suppression and cache behavior

The v0.1 completed-result cache is **process-local memory only**. It is a bounded LRU cache with TTL expiry.

In addition, simultaneous requests with the same normalized request identity and parser/cache namespace are coalesced into one in-flight operation. One caller performs the request directly; matching callers await that same operation. This is single-flight coordination only: it creates no background task and retains no extra CAL content. If completed-result caching is disabled, a later request after the in-flight operation has finished performs a new request normally.

The completed-result cache is intended only to suppress duplicate requests during a running CAL-MCP process. It is not an offline CAL store.

CAL-MCP does not provide:

- disk/database persistence;
- cache warming;
- prefetching;
- background refresh;
- corpus-building behavior.

### What is cached

Only a response that has passed all of the following steps is eligible:

1. request validation;
2. successful bounded HTTP request;
3. successful HTTP status validation;
4. expected CAL HTML content validation;
5. successful endpoint parser callback.

The cache stores the **successfully parsed typed value and provenance**, not a durable archive of CAL HTML.

The following are never cached:

- network failures or timeouts;
- redirects or upstream HTTP errors;
- unexpected content types;
- probable maintenance pages;
- parser exceptions/drift failures.

### Cache and single-flight identity

The identity key includes:

- parser/cache namespace;
- normalized HTTP method;
- CAL-relative path;
- ordered query parameter pairs;
- ordered form-data pairs.

The namespace prevents two parsers/models from accidentally reusing the same representation for an otherwise identical CAL request. Ordered pairs preserve repeated CAL form/query fields rather than collapsing them into a dictionary.

### Provenance on cache hits

A cache hit preserves the original CAL retrieval timestamp and source URL. The hit exposes cache metadata separately; it must not rewrite `retrieved_at` to the time the cached value was reused.

An in-flight follower receives the result of the active request rather than a fabricated fresh retrieval. It does not cause a second CAL request.

## Request boundary

`CalHttpClient` accepts only relative CAL paths and GET/POST requests. Absolute URLs, external hosts, embedded query strings/fragments, and path traversal are rejected before the transport is invoked. Query/form fields must be represented explicitly by `CalRequest.params` and `CalRequest.data` so request identity remains deterministic.

The production transport does not follow redirects. This keeps the validated `cal.huc.edu` origin as the actual network boundary rather than validating only the first URL and allowing a redirect to move the request elsewhere.

Deterministic transport-level tests exercise the actual HTTPX2 request construction with `MockTransport`: repeated query parameters, repeated POST form fields, the CAL-MCP User-Agent, and an external redirect target are checked at the HTTP boundary rather than only against an injected `CalRequest` object.

Response-size bounding is intentionally tracked separately in issue #20 and must be completed before public CAL-backed scholarly tools go live.

## Example

```python
from cal_mcp.client import CalClientConfig, CalHttpClient

config = CalClientConfig(
    max_concurrency=1,
    max_retries=0,
    cache_enabled=False,
)

async with CalHttpClient(config=config) as client:
    ...
```

Endpoint-specific CAL parsers and scholarly tools are introduced in later tickets; this configuration layer deliberately contains none of them.
