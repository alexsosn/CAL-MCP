# Issue #57 plan — validate remaining request-policy scalar types

**Plan date:** 2026-09-07
**Research:** `docs/research/issue-57-config-scalar-types.md`

Gate order: research → committed plan → behavior-first test-only RED → minimal implementation → full deterministic/latest-compatible GREEN → documentation → exact-head independent adversarial review → merge.

## Contract

`CalClientConfig` must fail at construction for invalid runtime types rather than leaking incidental exceptions or truthiness into request policy.

Numeric scalar fields:

- `connect_timeout_seconds`
- `read_timeout_seconds`
- `total_timeout_seconds`
- `retry_backoff_seconds`
- `cache_ttl_seconds`

accept non-boolean `int`/`float` values only, then retain existing finite/range semantics.

`cache_enabled` accepts only `bool`.

`user_agent` accepts only `str`, then retains the existing non-empty-after-strip rule.

## Gate 1 — test-only RED

Extend the existing table-driven constructor type-validation module, `tests/test_client_config_count_types.py`, with production unchanged. This keeps all `CalClientConfig` runtime-type boundary regressions together and avoids duplicating test scaffolding.

For each numeric scalar, cover:

- `True` and `False`;
- a numeric-looking string;
- an unrelated object value;
- representative valid integer and float values.

Require wrong runtime types to raise:

```text
<field> must be a number
```

Pin existing numeric range messages separately, including non-finite values where applicable, so the implementation cannot collapse type and range errors.

For `cache_enabled`, reject `0`, `1`, and string stand-ins with:

```text
cache_enabled must be a boolean
```

and accept both `True` and `False`.

For `user_agent`, reject representative non-string values with:

```text
user_agent must be a string
```

while retaining the existing `user_agent must not be empty` behavior for whitespace-only strings.

CI RED is valid only if Ruff/format/mypy are green and pytest failures are limited to the new runtime-type expectations.

## Gate 2 — minimal implementation

In `CalClientConfig.__post_init__`:

1. add one shared non-boolean `(int, float)` type guard for the numeric scalar fields before `math.isfinite`/range checks;
2. preserve existing finite/range checks and their existing messages;
3. add an explicit `isinstance(cache_enabled, bool)` guard;
4. add an explicit `isinstance(user_agent, str)` guard before `.strip()`.

Do not coerce values. Do not touch count validation, response-size validation, retry/backoff behavior, transport construction, cache implementation, or MCP schemas.

## Gate 3 — full GREEN

Require both permanent jobs on the exact implementation head:

- deterministic constrained environment + exact dependency verifier + Ruff lint/format + strict mypy + pytest;
- latest-compatible broad-range environment + pip check + Ruff lint/format + strict mypy + pytest.

No CAL traffic.

## Documentation gate

Update `docs/configuration.md` only as needed to state:

- timeout/TTL/backoff settings are numeric and reject booleans/non-numeric values;
- `cache_enabled` is boolean;
- User-Agent is a non-empty string.

If the behavior change makes existing wording materially incomplete, pin the documentation contract with a deterministic test before changing the prose.

## Independent adversarial review

Freeze the exact final SHA and independently try to falsify:

1. bool is rejected for all numeric scalars despite subclassing `int`;
2. valid integers remain accepted for float-valued settings;
3. valid floats and all existing boundaries remain unchanged;
4. strings/objects produce stable `ValueError`, not `TypeError`/`AttributeError`;
5. `cache_enabled` cannot be controlled by generic truthiness;
6. `user_agent` type checking precedes `.strip()` while whitespace-empty behavior remains intact;
7. #55 count validation and #50 backoff cap are unchanged;
8. client/request/cache behavior for valid config is unchanged;
9. normal CI remains offline.

Any blocker enters review-regression RED → minimal fix → full GREEN → fresh exact-head review.

## Merge

Merge only an exact independently reviewed GREEN head with an expected-head SHA guard. `Closes #57` should close the ticket on merge.
