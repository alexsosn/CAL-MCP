# Issue #321 — oversized integers bypass CAL client configuration validation

Source inspection: `src/cal_mcp/client.py` from main commit `41d4468f317b61d674db3259484354ad5cac6086`, 2026-10-11. No CAL network I/O.

## Root cause and boundaries
- `CalClientConfig.__post_init__` type-allows `int`/`float` excluding bool, but then directly invokes `math.isfinite(value)` for positive timeout/TTL fields (connect, read, per-attempt total, cache TTL), optional retry backoff, and pacing interval. A huge integer such as `10**1000` raises `OverflowError` during int→float conversion inside `math.isfinite`, contrary to the constructor's explicit field-specific `ValueError` contract.
- The public configuration documentation promises numeric bad values are rejected at construction, and existing runtime tests verify booleans/NaN/infinity and normal bounds; they do not explicitly cover unrepresentable integer magnitude.
- `MemoryResponseCache` constructor's separate issue #317 is now fixed; no changes to its constructor are needed. The current GitHub open PR #319 is documentation/release validation only and does not overlap.

## Requirements
Apply field-specific invalid-input `ValueError` for all six scalar fields, regardless of giant `int` magnitude. Preserve existing valid `float`/`int` semantics, finite checks, and documented 0–5 pacing / 0–1 backoff / positive timeout limits. This should be an offline pure configuration change with no new CAL requests, no public MCP schema change, no retry/cooldown modification, no publication. The empirical #262 upstream rate-limit acceptance stays open.
