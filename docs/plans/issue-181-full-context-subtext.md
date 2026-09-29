# Issue #181 plan — full-context file-info coordinate for subdivided texts

Date: 2026-09-29. Research: `docs/research/issue-181-full-context-subtext.md`, committed before behavior tests.

1. Reduced current fixtures with provenance comments: `kwic_full_context_samaritan_56000_112_current.html` (composed coordinate) and `kwic_full_context_bt_71002_01051_current.html` (bare coordinate, Hebrew script).
2. RED tests (`tests/test_kwic_full_context_subtext_current.py`):
   - both pages are found, with the target row;
   - a coordinate naming another subtext (`56000113`) or another file (`56001112`) fails closed;
   - a label naming another file fails closed;
   - a composed coordinate on a request without a sub fails closed.
3. GREEN: `_validate_full_context_file_identity` takes the submitted sub and applies the #166 rule.
4. Docs: `docs/tools/concordance.md` (full context), `research.md` R-047, fixture README.
5. Verification: the full suite; offline on the three captures; live over MCP (KWIC hit → full context for 56000 and 71002).
6. Independent adversarial review of the exact candidate SHA.
