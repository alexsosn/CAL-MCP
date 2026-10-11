# Issue #307 — stop installed smoke on an unclassified MCP call exception

Date: 2026-10-11. Source inspected on merged main `e4f6fe53f70e846c8216b6880e7f1cca0a28dfdc`. This finding requires zero CAL network access.

`src/cal_mcp/stdio_live_smoke.py::evaluate_smoke_cases` iterates a frozen 12-case list with eleven CAL-backed operations. If `client.call_tool` raises an ordinary `Exception`, the handler records `SmokeOutcome(case.name, "harness", "MCP transport or schema error")` but does **not** break: it executes later tests with the same broken or unknown-state stdio `Client`, including up to 60-second waits between CAL-backed cases. An interrupted or failed call may already have issued CAL requests before the exception, so repeated probing of other scholarly operations does not improve release evidence and may consume unknown quota. The outer CLI would fail on even one non-`ok`, regardless of whether future tests succeed, so continued cases cannot rescue publication.

Other fail-closed paths already stop immediately: structured local exhaustion; true CAL HTTP 429; unknown structured MCP error kind, invalid structured envelope, or missing structured content/schema. Ordinary trusted parser drift (e.g. wrong scholarly result/representative rows), however, is intentionally aggregated so maintainers can see independent drift; that behavior must remain. `asyncio.CancelledError` is not swallowed by `except Exception` under supported Python versions. List-tools failures naturally propagate and are CLI harness failures.

Safety invariant: an unclassified MCP `call_tool` exception makes later CAL probes unjustified, even if they would eventually fail harmlessly. A *single* sanitized `harness` outcome should be appended for the failed case, prior successful/drift outcomes must remain, and no new tool invocation or sleep is permitted after failure. No SDK/API or CAL data assumptions changed.

Scope: one control-flow break plus minimal offline fake-client regression tests. No changes to 60s spacing, eight-start rolling cap, hard 25 attempts, independently frozen v0.1 case identities, HTTP client, or live CAL request behavior.
