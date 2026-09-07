# Issue #55 plan — reject non-integer policy counts

**Plan date:** 2026-09-07

Gate order: research → committed plan → test-only RED → minimal implementation → full deterministic/latest-compatible GREEN → exact-head independent adversarial review → merge.

## Contract

`CalClientConfig` must reject non-boolean non-integer values for:

- `max_concurrency`;
- `max_retries`;
- `cache_max_entries`.

Valid integer ranges remain exactly `1–8`, `0–3`, and `0–4096` respectively.

## Test-only RED

Add table-driven constructor tests covering each field with:

- a fractional float inside the existing numeric range;
- a string representation of a valid number;
- `True` and/or `False` where it would otherwise satisfy the numeric range.

Require a stable `ValueError` naming the field and stating that it must be an integer. Add/retain separate assertions proving existing out-of-range integer errors still use the current bound messages.

Production code remains untouched until CI shows static gates green and failures limited to the new type-validation expectations.

## Minimal implementation

Add one small private validation helper or equivalent direct checks in `CalClientConfig.__post_init__` that:

1. rejects `bool`;
2. rejects any non-`int` value;
3. applies the existing lower/upper bound and existing bound error text.

Use the same policy for all three fields. Do not alter `max_response_bytes` behavior except optional local refactoring if it is exactly semantics-preserving.

## Documentation

Update the configuration table to state `integer` for the three count settings if needed for user-visible precision. No broader config/CLI work belongs here.

## GREEN

Require the repository's deterministic and latest-compatible CI jobs. Locally represented gate commands remain:

```text
ruff check .
ruff format --check .
mypy
pytest
```

No CAL access is needed or permitted.

## Independent adversarial review

Review exact final SHA independently and try to falsify:

- booleans are rejected despite `bool` subclassing `int`;
- in-range floats no longer survive constructor validation;
- strings fail with the intended stable `ValueError`, not incidental comparison `TypeError`;
- valid boundary integers still work (`1/8`, `0/3`, `0/4096`);
- out-of-range integer messages/semantics are unchanged;
- no retry/backoff/concurrency/cache runtime behavior changes for valid config;
- no overlap with #50's backoff implementation;
- normal CI remains offline.

Any blocker receives a test-first review regression, full GREEN, and a fresh exact-head review.
