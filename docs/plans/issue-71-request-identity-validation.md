# Issue #71 plan — validate low-level request identity structure before transport

Date: 2026-09-08
Research prerequisite: `docs/research/issue-71-request-identity-validation.md`

## Goal

Make `CalHttpClient.fetch()` reject runtime-invalid or mutable request-identity shapes before cache-key construction, single-flight participation, transport, or parser execution, while preserving every valid request/cache behavior.

## Gate 1 — test-only behavioral RED

Add a focused test module, preferably `tests/test_request_identity_validation.py`. Modify tests only.

Use an injected recording transport returning a minimal valid HTML `CalResponse`, so tests can prove invalid inputs never reach transport. No CAL access.

### Scalar/type boundary

Add tests proving stable `CalRequestValidationError` for:

1. a non-`CalRequest` request object → `CAL request must be a CalRequest`;
2. non-string `CalRequest.method` → `CAL request method must be a string`;
3. non-string `CalRequest.path` → `CAL request path must be a string`;
4. non-string `cache_namespace` → `cache_namespace must be a string`.

Preserve current precedence: request normalization/validation happens before cache-namespace validation.

### Params/data immutable shape

Table-drive both `params` and `data` through representative invalid shapes:

- outer list instead of tuple;
- tuple containing a list pair;
- tuple containing a one-item tuple;
- tuple containing a three-item tuple;
- tuple containing a non-string key;
- tuple containing a non-string value.

All must raise:

- `CAL request params must be a tuple of string pairs`, or
- `CAL request data must be a tuple of string pairs`.

The transport must record zero calls for every invalid shape.

### Valid regressions

Prove:

- empty `params=()` / `data=()` remain valid;
- method/path normalization is unchanged (e.g. `" get "`, `"/entry.php"` → normalized `GET`, `entry.php`);
- ordered duplicate pairs remain byte-for-byte/equality identical in the normalized request received by the injected transport;
- a normal non-empty namespace remains accepted;
- existing whitespace-empty namespace error remains `cache_namespace must not be empty`.

Do not change existing production-boundary repeated-field tests.

### RED acceptance

Accept the RED only when both deterministic and latest-compatible CI jobs show:

- install/environment verification GREEN;
- Ruff lint GREEN;
- Ruff format GREEN;
- strict mypy GREEN;
- pytest failures confined to the newly added runtime-identity expectations.

Do not touch production before this RED is demonstrated.

## Gate 2 — minimal implementation

Change only `src/cal_mcp/client.py` initially.

### Request object/scalars

At the start of `_validate_and_normalize_request()`:

```python
if not isinstance(request, CalRequest):
    raise CalRequestValidationError("CAL request must be a CalRequest")
if not isinstance(request.method, str):
    raise CalRequestValidationError("CAL request method must be a string")
if not isinstance(request.path, str):
    raise CalRequestValidationError("CAL request path must be a string")
```

Then retain the existing method/path normalization and security checks unchanged.

### Pair helper

Add a small helper that validates, without coercion, that a field is:

- an actual tuple;
- every element is an actual tuple;
- every element length is exactly two;
- both pair members are actual strings.

Return the original typed tuple (or simply validate it in place). Do not rebuild/list-normalize valid values.

Run it for `params` and `data` before constructing the normalized `CalRequest` and before `_cache_key()` can run.

### Cache namespace

After request normalization and before `.strip()`:

```python
if not isinstance(cache_namespace, str):
    raise CalRequestValidationError("cache_namespace must be a string")
```

Keep the existing whitespace-empty error unchanged.

## Gate 3 — focused/full GREEN

Run normal CI in both environments. Required:

- dependency/install checks GREEN;
- Ruff lint/format GREEN;
- strict mypy GREEN;
- all pytest GREEN.

Specifically recheck existing tests for:

- repeated HTTP query/form fields;
- redirect boundary;
- cache-key namespace separation;
- single-flight coalescing/cancellation;
- cache disabled/enabled behavior;
- request path security.

No CAL traffic.

## Gate 4 — documentation

Update `docs/configuration.md` Request boundary / cache identity text only if needed to state that low-level programmatic requests enforce the declared immutable tuple-of-string-pairs runtime shape and typed namespace before transport.

Preserve existing wording about ordered repeated fields and relative CAL paths.

If an existing docs-contract test pins affected wording, treat any failure as a review-regression gate rather than weakening the test silently.

## Gate 5 — logically independent adversarial review

Review the exact final SHA against issue #71, research, plan, current `main`, whole diff, and exact-head CI.

Challenge at least:

- request-vs-namespace validation precedence;
- bool/int/object values leaking through string checks;
- list outer containers being rejected rather than coerced;
- nested list pairs being rejected;
- malformed tuple lengths rejected cleanly rather than via unpacking errors;
- non-string keys/values rejected;
- empty immutable tuples accepted;
- valid ordered repeated pairs unchanged;
- method uppercase/whitespace normalization unchanged;
- leading slash path normalization unchanged;
- absolute URL/query/fragment/traversal security checks unchanged;
- cache key and single-flight identity unchanged for valid requests;
- zero transport/parser activity for invalid requests;
- no `client.py` overlap with active PR #53 at review time;
- no CAL access.

Any blocker requires a review-regression test-only RED, minimal fix, full GREEN, and a fresh exact-head review.

## Merge gate

Immediately before ready/merge:

1. refetch PR head and `main`;
2. refetch PR #53 changed files/status for overlap;
3. if `main` advanced, synchronize non-destructively and rerun exact-head CI/review as appropriate;
4. mark ready only after clean exact-head review;
5. merge using `expected_head_sha` equal to the reviewed head;
6. verify #71 closes and the merge commit is current on `main`.
