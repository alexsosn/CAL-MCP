# Issue #258 — research-plan-TDD-test and independent review

1. RED: add one in-process real MCP `Client(server.mcp)` test, parametrized with a foreign URL, non-decimal coordinate, zero, non-ASCII decimals and blank input, using a rejecting fake CAL transport. Assert exact shared structured error `invalid_input`, operation identity, no upstream request and safe message. This test should fail under old built-in ValueError.
2. GREEN: change the exact validation raise in `_validate_full_coordinate` to `CalInputError`, importing the project's defined error type. Do **not** modify global error classification, SDK behavior, or existing coordinate grammar.
3. Full frozen/latest-compatible Ruff, mypy, pytest CI; source-grounded logically independent adversarial review of the final exact SHA.
4. Squash merge only if both jobs pass and no unrelated behavior changes; close #258. No CAL probes, tag, or PyPI publication.
