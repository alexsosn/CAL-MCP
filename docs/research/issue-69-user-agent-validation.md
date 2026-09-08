# Issue #69 research — reject unsafe User-Agent configuration before HTTPX2 construction

Date: 2026-09-07
Baseline: `main` at `8c8e3268b67cf2f56c701f0ff6ee9efb4f7ba007`

## Question

Does `CalClientConfig.user_agent` enforce the same fail-fast configuration boundary as the other request-policy settings, or can values pass CAL-MCP validation and fail later inside HTTPX2 header handling?

## Current CAL-MCP behavior

`src/cal_mcp/client.py` currently validates `user_agent` only in two steps:

1. value must be a `str`;
2. `user_agent.strip()` must be non-empty.

`_Httpx2Transport.__init__()` later constructs:

```python
httpx2.AsyncClient(
    ...,
    headers={"User-Agent": config.user_agent},
    ...,
)
```

Therefore the config boundary currently accepts arbitrary non-empty Unicode and control-bearing strings and delegates header encodability/legality to HTTPX2.

`docs/configuration.md` explicitly says programmatic callers may supply an explicit `CalClientConfig` within enforced bounds, and repeatedly states that invalid caller-supplied request-policy values should be rejected at `CalClientConfig` construction rather than leaking dependency-specific failures later.

Existing tests cover the default User-Agent being present at the production HTTPX2 boundary, plus non-string/empty config behavior indirectly through the general config tests, but there is no character-safety regression for `user_agent`.

## HTTPX2 header contract

Current HTTPX2 documentation states that string header keys/values may contain only ASCII characters. Its current issue tracker also preserves the inherited behavior where a non-ASCII string header value raises `UnicodeEncodeError` while normalizing the header value.

Sources rechecked 2026-09-07:

- https://httpx2.pydantic.dev/ (project/docs)
- https://pydantic.dev/docs/httpx2/httpcore2/quickstart/ — string header keys/values are ASCII-range only
- https://github.com/pydantic/httpx2/issues/864 — current non-ASCII header-value failure example (`UnicodeEncodeError`)

This is enough to establish a CAL-MCP boundary defect: `CalClientConfig` can claim success for a value that the configured production transport cannot represent through HTTPX2's string-header API.

## Safe local rule

The narrowest dependency-independent rule that keeps the current default and avoids lower-layer header failures is:

- `user_agent` must remain a non-empty `str`;
- every character must be printable ASCII, code points `0x20` through `0x7E` inclusive.

This intentionally rejects:

- non-ASCII Unicode;
- CR and LF;
- tab;
- NUL and other C0 controls;
- DEL (`0x7F`).

The existing default

`CAL-MCP/<version> (+https://github.com/alexsosn/CAL-MCP)`

is entirely within this range.

The rule is deliberately not a complete RFC User-Agent grammar validator. CAL-MCP only needs to guarantee that a configured string is a conservative HTTP-header-safe value before dependency construction. A stricter product-token/comment parser would add policy not required by the observed defect.

## Why not accept arbitrary bytes or obs-text

HTTPX2 allows explicit bytes for callers that want to manage non-ASCII header encodings themselves, but `CalClientConfig.user_agent` is typed/documented as `str` and is passed through the string-header API. Expanding CAL-MCP to bytes would widen the configuration contract and is outside this maintenance fix.

## Why not add a length limit here

There is no current project requirement or evidence selecting a defensible maximum User-Agent length. A length cap may be useful later, but coupling an invented size policy to this proven character-safety defect would violate the minimal-change rule.

## Test strategy

Use configuration-only tests; no CAL access and no HTTP client construction is required for the RED.

Representative invalid values should include:

- non-ASCII: `CAL-MCP/0.1 λ`;
- newline injection: `CAL-MCP/0.1\nX-Test: value`;
- carriage return: `CAL-MCP/0.1\rX`;
- tab: `CAL-MCP/0.1\tX`;
- NUL: `CAL-MCP/0.1\x00X`;
- DEL: `CAL-MCP/0.1\x7fX`.

All currently pass the existing non-empty-string check, so a test-only commit should fail because construction does not raise.

Valid regressions should include:

- the exact default config;
- a compact custom printable-ASCII value such as `CAL-MCP-test/1.0 (+https://example.org)`;
- ordinary internal spaces.

Existing non-string and whitespace-empty behavior must remain unchanged.

## Implementation boundary

The minimal implementation belongs in `CalClientConfig.__post_init__()` immediately after the existing string/non-empty checks. It should raise a stable field-specific `ValueError`, e.g. `user_agent must contain only printable ASCII characters`.

No changes are needed to `_Httpx2Transport`, request construction, retries, cache/single-flight, endpoint services, MCP schema, or dependency versions.

## Research conclusion

Issue #69 is a real configuration-boundary stability defect. CAL-MCP currently accepts `user_agent` values that cannot be represented safely by the production HTTPX2 string-header path. Enforcing non-empty printable ASCII at `CalClientConfig` construction is a narrow, deterministic fix that preserves the default and keeps dependency-specific header failures out of runtime transport setup.
