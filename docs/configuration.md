# Configuration

CAL-MCP's request layer is deliberately conservative because CAL is a live academic service and the project has not found a published CAL-specific machine-access policy. This page documents the request-policy contract implemented by `CalClientConfig`.

The current MCP server creates one `CalHttpClient` with these defaults for its running server lifespan and reuses it across all CAL-backed tool calls. Starting the client does not itself contact CAL; a request is made only for a CAL-backed tool operation. The shared lifecycle preserves the process/session-local cache and single-flight guarantees described below, and the client is closed when the server shuts down. CLI/environment wiring is not implemented yet; callers cannot widen the safety bounds through the MCP schema. Programmatic use of `CalHttpClient` may supply an explicit `CalClientConfig` within the enforced limits below.

## Default request policy

| Setting | Default | Enforced bound / behavior |
| --- | ---: | --- |
| Connect timeout | 5 s | number (`int`/`float`, not boolean); finite, > 0 |
| Read timeout | 10 s | number (`int`/`float`, not boolean); finite, > 0 |
| Total attempt timeout | 15 s | number (`int`/`float`, not boolean); finite, > 0 |
| Maximum concurrency | 2 | integer; 1–8 |
| Minimum CAL transport interval | 3 s for plain `CalHttpClient()` and the MCP server; 0 s for explicitly supplied `CalClientConfig()` or injected fake transport | number (`int`/`float`, not boolean); finite, 0–5 s |
| Local rolling CAL start ceiling | 8 starts per rolling 60 s for plain real-transport client, MCP server and explicit live-smoke client; disabled for explicit `CalClientConfig()` and injected fake by default | `max_cal_attempts_per_60s`: `None` or actual integer 1–25 |
| Retry count | 1 | integer; 0–3 |
| Initial retry backoff | 0.25 s | number (`int`/`float`, not boolean); finite, 0–1 s; exponential, capped at 1 second per retry sleep |
| Maximum response body | 2 MiB | integer; 1 byte–16 MiB; enforced while streaming decoded response bytes |
| Cache enabled | yes | boolean; completed-result retention can be disabled completely |
| Cache entries | 128 | integer; 0–4096; 0 retains nothing |
| Cache TTL | 900 s (15 min) | number (`int`/`float`, not boolean); > 0 and <= 86400 s |
| User-Agent | `CAL-MCP/<version> (+https://github.com/alexsosn/CAL-MCP)` | non-empty printable-ASCII string (`0x20`–`0x7E`) |

Timeout, TTL, retry-backoff, and minimum-interval settings accept ordinary numeric `int` or `float` values; booleans and non-numeric values are rejected at `CalClientConfig` construction rather than coerced or allowed to fail later inside transport operations. `cache_enabled` must be an actual boolean. User-Agent must be a non-empty string and may contain only printable ASCII characters (`0x20`–`0x7E`); non-string values, whitespace-empty values, non-ASCII Unicode, and control characters are rejected at `CalClientConfig` construction before HTTPX2 transport creation. These runtime checks complement Python type annotations, which do not validate constructor arguments by themselves.

HTTPX2 also receives explicit connection/read timeouts and connection-pool limits. CAL-MCP additionally wraps each transport attempt in the total timeout. The installed MCP server configures **three seconds between CAL transport starts** across all of its tools and retries, even for strictly sequential requests. It enforces the interval at the actual transport boundary, after cache and single-flight checks. Plain `CalHttpClient()` with the real HTTP transport defaults to three-second pacing. This three-second pacing is not a guaranteed CAL-accepted rate: the bounded 2026-10-10 Peshitta smoke received CAL HTTP 429 despite spacing transport attempts more than three seconds apart. An injected/offline fake transport and an explicit `CalClientConfig()` retain a configurable `0` default for existing fast tests/programmatic use; callers overriding the live client configuration must select safe pacing when contacting CAL. This is a per-process, not multi-process/global, limit.

## Response-size limit

The production HTTPX2 transport streams decoded response bytes instead of using an eager `response.content` read. `max_response_bytes` defaults to 2 MiB and cannot be configured above 16 MiB. It must be an actual integer value: booleans, floats, strings, and other non-integer values are rejected by `CalClientConfig` construction before a transport is created.

For a production response with status 300 or higher, CAL-MCP keeps the status, URL, content type, and retrieval timestamp but does not iterate the application response body. The surrounding HTTPX2 streaming context closes that response, and the shared request layer then applies its existing redirect/4xx/5xx retry or error policy. Bodies are streamed only for responses below 300 that continue toward normal content validation and parsing; this optimization therefore does not weaken the successful-response byte limit.

CAL-MCP accumulates only chunks that keep the retained response body at or below the configured limit. The decoded streaming iterator is requested in bounded chunks of at most 64 KiB (or `max_response_bytes + 1` for smaller limits), so the transport needs only one bounded look-ahead chunk to detect an over-limit response. An exactly-at-limit body is accepted; the first chunk that would make the retained body exceed the limit raises `CalResponseTooLargeError`, a `CalContentError` subclass, and the response stream is closed.

An oversized response:

- is not retried as a transient network failure;
- never reaches an endpoint parser;
- is never inserted into the completed-result cache;
- does not cause later chunks to be consumed after the over-limit condition is known.

The limit applies to decoded bytes delivered by HTTPX2 to CAL-MCP. This is the representation that would otherwise become the HTML parser input. Normal tests use HTTPX2 `MockTransport` and synthetic streams; no live CAL request is needed to verify exact-limit and over-limit behavior.

## Retry behavior

Retries are explicitly whitelisted rather than applied to every transport exception. The current policy retries only:

- CAL-MCP's finite per-attempt timeout (`TimeoutError`);
- HTTPX2 timeout exceptions (`httpx2.TimeoutException`);
- HTTPX2 network exceptions (`httpx2.NetworkError`);
- HTTP 500, 502, 503, and 504.

Other HTTPX2 errors, including local/protocol-type errors, are surfaced after one attempt as typed CAL-MCP transport failures. A bare `OSError` from an injected/custom transport is also treated as non-retryable rather than being assumed transient. This keeps retries tied to the explicit production HTTPX2 transient categories instead of a broad base exception class.

Other HTTP statuses are returned as typed upstream errors without blind retry. For HTTP 429, `upstream_http` reports `retryable: true` to indicate that a caller may try *later*, not immediately. A short, syntactically valid positive `Retry-After` (maximum 2 seconds) may trigger **at most one** retry within the existing retry budget, provided the hinted delay leaves time under the total-attempt policy; a missing, malformed, zero, negative, or longer server hint does not cause an automatic retry. CAL-MCP does not retry **before** the server's requested delay. Valid Retry-After values may be surfaced as a safe delay in the error message. The HTTP transport retains only this rate-limit header, not an arbitrary collection of response headers.

Production HTTP responses that are going to be retried or rejected on status are closed without consuming their application body. For a transient 500/502/503/504, each failed attempt is therefore status-classified before the retry sleep rather than downloading an error page that CAL-MCP will never parse. This does not alter the retry count or status-code whitelist.

The initial backoff is capped at 1 second and the retry count at 3. Each retry sleep uses `min(base * 2**attempt, 1.0)`, preserving exponential growth until the absolute 1-second per-sleep ceiling is reached. The configured retry sleep budget is therefore finite and cannot be made arbitrarily large by configuration.

HTTP redirects are not followed automatically. A 3xx response is returned as a typed upstream error before parsing or caching. If a later CAL endpoint demonstrably requires redirects, support should be added explicitly with a same-origin, bounded redirect policy rather than enabling arbitrary automatic redirect following.

No retry path creates background work or continues after the caller's operation has ended.

## Duplicate-request suppression and cache behavior

The v0.1 completed-result cache is **process-local memory only**. It is a bounded LRU cache with TTL expiry. In the MCP server, the cache belongs to the lifespan-managed `CalHttpClient`, so successive tool calls in the same running server share it; restarting the server discards it.

In addition, simultaneous requests with the same normalized request identity and parser/cache namespace are coalesced into one in-flight operation. One caller performs the request directly; matching callers await that same operation. Because the MCP server shares one client, identical overlapping tool calls participate in the same single-flight map rather than creating separate CAL requests. This is single-flight coordination only: it creates no background task and retains no extra CAL content. If completed-result caching is disabled, a later request after the in-flight operation has finished performs a new request normally.

Cancellation is caller-local where possible. Cancelling a follower does not cancel the active leader or the shared in-flight result. If the active leader itself is cancelled, that request stops promptly and its shared generation is cancelled and removed; independent matching followers do not inherit that cancellation. Surviving followers re-enter the same guarded single-flight election, coalesce onto at most one replacement generation, and only that replacement leader performs new CAL I/O. The replacement is still owned by a live caller—CAL-MCP does not spawn a background retry task—and cancellation of the replacement leader follows the same bounded handoff behavior.

The completed-result cache is intended only to suppress duplicate requests during a running CAL-MCP process. It is not an offline CAL store.

For programmatic/offline use, the optional `CalHttpClient(clock=...)` monotonic clock injection governs **both** the transport pacing/cooldown/rolling budget **and** the completed-result cache TTL. Entries expire when the injected clock reaches their retention boundary; a still-valid cached result can be returned during a CAL rate-limit cooldown, but an expired entry must go through admission again. The normal production client uses the same default `time.monotonic` source for these policies. This is a deterministic local clock contract, not a mechanism for relaxing CAL's request budget.

CAL-MCP does not provide:

- disk/database persistence;
- cache warming;
- prefetching;
- background refresh;
- corpus-building behavior.

### What is cached

Only a response that has passed all of the following steps is eligible:

1. request validation;
2. successful bounded HTTP request and response-size check;
3. successful HTTP status validation;
4. expected CAL HTML content validation;
5. successful endpoint parser callback.

The cache stores the **successfully parsed typed value and provenance**, not a durable archive of CAL HTML.

The following are never cached:

- network failures or timeouts;
- oversized responses;
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

An in-flight follower receives the result of the active request rather than a fabricated fresh retrieval. It does not cause a second CAL request while that generation remains active. If the active leader is cancelled, surviving followers may cause exactly one replacement generation as described above.

## Request boundary

`CalHttpClient` accepts only relative CAL paths and GET/POST requests. Absolute URLs, external hosts, embedded query strings/fragments, and path traversal are rejected before the transport is invoked. Low-level programmatic requests must use an actual `CalRequest` with string method/path fields; `params` and `data` must be immutable tuples of two-string tuples, and the cache/parser namespace must be a non-empty string. Invalid runtime shapes are rejected with `CalRequestValidationError` before cache-key construction or transport rather than being coerced. Ordered repeated query/form pairs remain intact, so request, cache, and single-flight identity use the same immutable representation.

Request **endpoint paths** must be unambiguous before URL resolution. A bare script name such as `entry.php`, a single-leading-slash name such as `/entry.php`, or a multi-component script path such as `cgi-bin/getlex.php` is accepted; redundant slash components, `.`/`..` segments (including a trailing dot segment), raw whitespace or controls, backslashes, percent-escaped *path components*, and literal `?`/`#` delimiters (including empty query/fragment suffixes) are refused locally with `CalRequestValidationError` and zero CAL traffic. Put CAL identifiers, Syriac/Hebrew transliteration, percent signs and other arbitrary values in `CalRequest.params` or `data`; those fields remain URL/form encoded by the transport and support repeated ordered keys. The validator protects the endpoint identity used by the cache and request policy; it is not evidence that a previously accepted path could escape the CAL hostname.

The production transport does not follow redirects. This keeps the validated `cal.huc.edu` origin as the actual network boundary rather than validating only the first URL and allowing a redirect to move the request elsewhere.

Deterministic transport-level tests exercise the actual HTTPX2 request construction with `MockTransport`: repeated query parameters, repeated POST form fields, the CAL-MCP User-Agent, redirect non-following, and response streaming/size limits are checked at the HTTP boundary rather than only against an injected `CalRequest` object.

## Example

```python
from cal_mcp.client import CalClientConfig, CalHttpClient

config = CalClientConfig(
    max_concurrency=1,
    max_retries=0,
    min_request_interval_seconds=3.0,
    max_cal_attempts_per_60s=8,
    max_response_bytes=1024 * 1024,
    cache_enabled=False,
)

async with CalHttpClient(config=config) as client:
    ...
```

The public MCP tools do not expose these low-level settings as arguments. Endpoint-specific services consume the server's shared request layer and inherit its bounded defaults. See [Lexicon lookup](tools/lexicon.md) and [Concordance and KWIC](tools/concordance.md) for representative CAL-backed tool behavior.

## Shared terminal 429 cooldown

After one terminal CAL HTTP 429, the client suppresses subsequent uncached calls for at least 60 seconds, or the longer validated Retry-After. The *first* typed upstream HTTP 429 error reports the effective **local cooldown** separately from CAL's original `Retry-After` hint (when present); an upstream hint of one second does not override the longer local safety minimum. Suppressed later calls are typed rate-limit errors with `upstream_reached=false` and zero transport attempts. Cached results remain available.

If an allowed short `Retry-After` triggers a one-time retry, but the caller **cancels while waiting** (during the hint delay, a queued paced retry, or subsequent bounded retry backoff), that operation leaves at least the same 60-second protective cooldown. It propagates cancellation to the caller, and later uncached operations are rejected without another CAL request. When the permitted retry actually succeeds, it does not retain this terminal cooldown. The shared protection applies to one CAL-MCP server process, not across separately running instances.

If a permitted short-hint retry **fails without succeeding** (for example with a subsequent HTTP 503, redirect rejection, or terminal transport failure, or an oversized-response rejection), the original tool call reports that actual later failure; the earlier CAL 429 still activates at least 60 seconds of local suppression for **later** uncached calls. A later retry success does not activate this terminal cooldown. This distinction also applies to an interrupted retry as described above.

## Local rolling transport budget (protective precaution)

The ordinary real-transport `CalHttpClient()`, the MCP server, and the deliberately scoped installed-wheel live-smoke client enforce **at most eight actual CAL transport starts in any rolling 60-second period**, in addition to the minimum three seconds between starts. This deliberately stops a repeated burst *before* the tenth transport attempt where CAL returned HTTP 429 in the measured 2026-10-10 Peshitta smoke. **Eight per 60 seconds is an adapter precaution, not a demonstrated or published CAL quota.** CAL may reject even earlier requests or requests after the local window expires. The [37-token installed-wheel acceptance](research/issue-262-slow-acceptance.md) completed once with zero 429s using caller-controlled waits of at least 60 seconds after every completed operation, concurrency one and zero retries; this does not establish safe completion at the default three-second pace.

The rolling admission check is atomic per client, even when the minimum interval is set to zero. Each actual transport start counts, including retries, GETs and POSTs. A bounded 60-second timestamp deque is pruned on admission. Cached results, already-coalesced in-flight waiters, invalid requests, and a transport hook that denies the attempt **do not consume a rolling slot**. No hidden retries or background CAL requests are initiated when the window fills.

On exhaustion, the attempted new CAL request is **not sent**. The tool returns `local_rate_limit`, with `upstream_reached=false` when no earlier HTTP response was received within that same fetch (or `true` if an earlier retry attempt already returned a real CAL HTTP response), `source_url=null`, `status_code=null`, and a conservative number of seconds before the oldest recorded attempt expires. This differs from genuine CAL HTTP 429 (`upstream_http`) and its separate fail-closed 60-second circuit breaker. If a permitted short-hint CAL 429 retry is blocked by the local budget, that operation instead reports its **actual original CAL HTTP 429** with the truthful >=60-second local cooldown; later uncached calls remain suppressed.

Direct programmatic clients supplying an explicit `CalClientConfig()` do **not** automatically inherit the rolling cap; `max_cal_attempts_per_60s=None` disables it for backward compatibility with offline/injected test transports. Real CAL clients with explicit configurations must opt into conservative spacing and a rolling cap, as shown in the example above. Do not interpret the absence of this local guard as upstream CAL permission. The limit is process-local, not shared across separate CAL-MCP instances.

The installed-wheel smoke runner now spaces completed CAL-backed tool cases by a full 60 seconds (issue #299), so its fixed matrix no longer blindly emits a cross-case burst against the rolling limit. A single tool can still exceed eight starts or receive an upstream 429. The separate 37-token acceptance passed under the documented caller waits; the fixed 12-case release smoke remains a separate publication gate and must pass on the selected installed artifact.
