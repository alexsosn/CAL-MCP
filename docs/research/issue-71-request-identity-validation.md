# Issue #71 research — validate low-level request identity structure before transport

Date: 2026-09-08
Baseline: `main` at `6c0389beaa79dd13349e14ff453c3656d31d0a3e`

## Question

Does the low-level `CalHttpClient.fetch()` boundary enforce the runtime shape promised by `CalRequest` and `cache_namespace`, or can malformed/mutable programmatic values leak incidental exceptions or break the deterministic request/cache identity?

## Current contract

`CalRequest` is declared as a frozen, slotted dataclass:

```python
@dataclass(frozen=True, slots=True)
class CalRequest:
    method: str
    path: str
    params: tuple[tuple[str, str], ...] = ()
    data: tuple[tuple[str, str], ...] = ()
```

`fetch()` accepts a `CalRequest`, parser callback, and string `cache_namespace`. The configuration documentation states that the cache/single-flight identity includes:

- parser/cache namespace;
- normalized HTTP method;
- CAL-relative path;
- ordered query parameter pairs;
- ordered form-data pairs.

It also states that query/form fields must be represented explicitly by `CalRequest.params` and `CalRequest.data` so request identity remains deterministic, and that invalid request boundaries are rejected before transport.

## Current runtime behavior

Python annotations and `frozen=True` do not enforce nested runtime types.

### Method/path

`_validate_and_normalize_request()` begins with:

```python
method = request.method.upper().strip()
...
if not request.path.strip():
    ...
```

A programmatic caller can construct `CalRequest(method=1, ...)` or `CalRequest(path=None, ...)` at runtime (ignoring static typing), and the request layer leaks incidental `AttributeError`/`TypeError` before it can raise the intended `CalRequestValidationError`.

### Cache namespace

After request normalization, `fetch()` calls:

```python
if not cache_namespace.strip():
    raise CalRequestValidationError("cache_namespace must not be empty")
```

A non-string namespace likewise leaks an incidental attribute error rather than a stable request-validation error.

### Params/data structure

The production transport later consumes:

```python
params = list(request.params)
form_content = urlencode(request.data).encode("utf-8") if request.data else None
```

but there is no runtime validation that `params`/`data` are actual immutable tuples of two-string tuples.

This is more than an exception-shape issue. `CalRequest` is only shallowly frozen: callers can supply a mutable list despite the annotation, and the frozen dataclass keeps that list by reference.

`fetch()` performs these steps in order:

1. `_validate_and_normalize_request(request)` constructs a new `CalRequest` but currently copies `request.params` and `request.data` by reference;
2. `_cache_key(...)` immediately computes a string from `repr((namespace, method, path, params, data))`;
3. later, after async single-flight/semaphore scheduling, the transport consumes the same `params`/`data` objects.

Therefore a mutable list can be changed after the cache key is computed but before transport consumption. The response can then be parsed and stored under a key describing different query/form fields than were actually sent. The same mismatch can affect single-flight coalescing.

Nested mutable list pairs create the same class of problem even if the outer container is a tuple.

## Narrow safe rule

The runtime request identity should match the declared immutable representation exactly, without coercion:

- `request` is an actual `CalRequest`;
- `method` is an actual `str` before normalization;
- `path` is an actual `str` before path validation;
- `params` is an actual `tuple`;
- every `params` element is an actual two-item `tuple` of two `str` values;
- `data` has the same rule;
- `cache_namespace` is an actual `str` before the existing whitespace-empty check.

Violations should raise `CalRequestValidationError` before transport or parser execution.

This rule deliberately does **not** coerce lists to tuples. Silent coercion would hide caller contract violations and would create an additional normalization policy not required by the defect.

## Existing behavior that must stay unchanged

- Method normalization remains uppercase + surrounding-whitespace trimming for valid strings.
- Only GET/POST are accepted.
- Empty/absolute/external/query-bearing/fragment-bearing/traversal paths retain their existing rejection semantics.
- Empty `params` and `data` tuples remain valid.
- Ordered repeated query/form pairs remain valid and preserve duplicates/order.
- Ordinary string values are not character-whitelisted here; existing URL/form encoding remains responsible for representation.
- Cache namespace whitespace-empty validation keeps its existing error after the new type guard.
- Cache/single-flight key content for valid requests must not change.
- No endpoint, retry, timeout, response-size, redirect, cache-retention, or public MCP behavior changes.

## TDD strategy

Use a focused new offline test module around `CalHttpClient.fetch()` with an injected transport that records whether it was called.

### Invalid scalar cases

Pin stable `CalRequestValidationError` for:

- non-`CalRequest` request object;
- non-string `method`;
- non-string `path`;
- non-string `cache_namespace`.

The RED should show current incidental exceptions rather than the expected typed errors.

### Invalid pair-container cases

Cover both `params` and `data` with representative malformed values:

- outer list instead of tuple;
- tuple containing a list pair;
- tuple containing a one-item or three-item tuple;
- tuple containing non-string key or value.

Current production should fail some of these later/incidental paths and silently accept others, so the test-only commit should be a behavioral RED.

### Valid regressions

Pin:

- empty tuple fields;
- repeated ordered pairs;
- valid method/path normalization;
- unchanged cache namespace behavior;
- transport receives the normalized request with exactly the original immutable ordered pair tuples.

Reuse the existing production HTTPX2 `MockTransport` regression as coverage that repeated query/form fields remain encoded in order at the actual HTTP boundary.

## Implementation boundary

Keep the implementation in `src/cal_mcp/client.py`, preferably in `_validate_and_normalize_request()` plus a small pair-shape helper and a `cache_namespace` type guard in `fetch()`.

Validation must occur before `_cache_key()` and before any transport/parser call.

Do not move endpoint validation into service modules and do not change `CalRequest` construction semantics globally via `__post_init__`; existing design intentionally validates CAL-specific method/path safety at the client boundary.

## Interaction with active PR #53

PR #53 modifies conversion/lexicon/server/docs/test surfaces but not `src/cal_mcp/client.py` in its current changed-file set. Issue #71 can therefore proceed independently. Recheck overlap and `main` immediately before merge.

## Conclusion

Issue #71 is a request-identity correctness and fail-fast stability defect. Runtime-invalid scalar fields currently leak dependency/Python exceptions, while runtime-accepted mutable pair containers can make the cache/single-flight identity diverge from the request eventually consumed by the transport. Enforcing the already-declared immutable tuple-of-string-pairs structure before key construction is the smallest fix that restores the documented deterministic boundary.
