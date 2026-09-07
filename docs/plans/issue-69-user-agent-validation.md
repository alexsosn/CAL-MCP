# Issue #69 plan — reject unsafe User-Agent configuration before HTTPX2 construction

Date: 2026-09-07
Research prerequisite: `docs/research/issue-69-user-agent-validation.md`

## Goal

Make `CalClientConfig.user_agent` fail deterministically at configuration construction when the value cannot safely travel through CAL-MCP's HTTPX2 string-header path, without changing the default User-Agent or any request behavior for valid configurations.

## Gate 1 — test-only behavioral RED

Modify tests only.

Prefer a focused new regression module, e.g. `tests/test_client_config_user_agent.py`, so the configuration contract is isolated from endpoint behavior.

Add table-driven invalid cases proving that `CalClientConfig(user_agent=...)` raises a field-specific `ValueError` for:

- non-ASCII Unicode;
- LF;
- CR;
- tab;
- NUL;
- DEL.

Pin the expected message to `user_agent must contain only printable ASCII characters`.

Preserve/verify accepted values:

- `CalClientConfig().user_agent` remains accepted and unchanged;
- a compact custom printable-ASCII value is accepted;
- ordinary internal ASCII spaces are accepted.

Also pin existing behavior:

- non-string values raise `user_agent must be a string`;
- whitespace-only strings continue to raise `user_agent must not be empty`.

RED acceptance:

- dependency/install checks GREEN;
- Ruff lint GREEN;
- Ruff format GREEN;
- strict mypy GREEN;
- pytest failure limited to the new unsafe-character cases because current production accepts them.

Do not touch production code until this gate is demonstrated.

## Gate 2 — minimal implementation

Change only `src/cal_mcp/client.py`.

In `CalClientConfig.__post_init__()`, after the existing `str` type check and whitespace-empty check, reject any character outside inclusive code-point range `0x20`–`0x7E`.

A minimal expression is sufficient, for example:

```python
if any(not 0x20 <= ord(char) <= 0x7E for char in self.user_agent):
    raise ValueError("user_agent must contain only printable ASCII characters")
```

Do not:

- add a User-Agent length cap;
- parse RFC product/comment grammar;
- change the default;
- accept bytes;
- modify `_Httpx2Transport`;
- alter retries, cache, single-flight, endpoint services, public tools, or schema.

## Gate 3 — full GREEN

Run the repository's full normal CI in both deterministic/frozen and latest-compatible jobs:

- dependency/install verification;
- Ruff lint;
- Ruff format;
- strict mypy;
- full pytest.

No CAL access.

## Gate 4 — documentation

Update `docs/configuration.md` only as needed to state:

- User-Agent must be a non-empty printable-ASCII string;
- invalid values fail at `CalClientConfig` construction before HTTPX2 transport creation.

Do not broaden CLI/environment configuration scope.

## Gate 5 — logically independent adversarial review

Review the exact final SHA against issue #69, research, plan, current `main`, whole diff, and CI.

Challenge at least:

- off-by-one acceptance of space (`0x20`) and tilde (`0x7E`);
- accidental acceptance of DEL (`0x7F`);
- accidental rejection of the existing default punctuation/URL/comment syntax;
- CR/LF/tab/NUL rejection;
- non-ASCII rejection;
- preservation of non-string and whitespace-empty error precedence;
- no hidden User-Agent length policy;
- no change to actual outgoing valid User-Agent behavior;
- no overlap with active PR #53 conversion/lexicon work;
- no CAL access.

Any blocking finding requires a review-regression test-only RED, minimal fix, fresh full GREEN, and a new exact-head review.

## Merge gate

Immediately before ready/merge:

1. refetch PR head and current `main`;
2. if `main` advanced, synchronize/reassess and rerun exact-head CI/review as needed;
3. mark ready only after a clean exact-head adversarial review;
4. merge with `expected_head_sha` equal to the reviewed SHA;
5. verify issue #69 closes and the merge is present on `main`.
