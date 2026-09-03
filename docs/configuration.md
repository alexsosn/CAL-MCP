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
| Initial retry backoff | 0.25 s | finite, >= 0; exponential per retry |
| Cache enabled | yes | can be disabled completely |
| Cache entries | 128 | 0–4096; 0 retains nothing |
| Cache TTL | 900 s (15 min) | > 0 and <= 86400 s |
| User-Agent | `CAL-MCP/<version> (+https://github.com/alexsosn/CAL-MCP)` | non-empty |

HTTPX2 also receives explicit connection/read timeouts and connection-pool limits. CAL-MCP additionally wraps each transport attempt in the total timeout.

## Retry behavior

Retries are bounded. The current policy retries only:

- network/transport failures;
- timeouts;
- HTTP 500, 502, 503, and 504.

Other HTTP errors are returned as typed upstream errors without blind retry. In particular, CAL-MCP does not automatically retry HTTP 429; a rate/overload response should reduce request pressure rather than create another immediate request.

No retry path creates background work or continues after the caller's operation has ended.

## Cache behavior

The v0.1 cache is **process-local memory only**. It is a bounded LRU cache with TTL expiry.

It is intended only to suppress duplicate requests during a running CAL-MCP process. It is not an offline CAL store.

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
- upstream HTTP errors;
- unexpected content types;
- probable maintenance pages;
- parser exceptions/drift failures.

### Cache identity

A cache key includes:

- parser/cache namespace;
- normalized HTTP method;
- CAL-relative path;
- ordered query parameter pairs;
- ordered form-data pairs.

The namespace prevents two parsers/models from accidentally reusing the same cached representation for an otherwise identical CAL request. Ordered pairs preserve repeated CAL form/query fields rather than collapsing them into a dictionary.

### Provenance on cache hits

A cache hit preserves the original CAL retrieval timestamp and source URL. The hit exposes cache metadata separately; it must not rewrite `retrieved_at` to the time the cached value was reused.

## Request boundary

`CalHttpClient` accepts only relative CAL paths and GET/POST requests. Absolute URLs, external hosts, embedded query strings/fragments, and path traversal are rejected before the transport is invoked. Query/form fields must be represented explicitly by `CalRequest.params` and `CalRequest.data` so request identity remains deterministic.

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
