# Issue #204 plan — KWIC target lines where CAL highlights nothing

Date: 2026-09-29. Research: `docs/research/issue-204-empty-kwic-highlight.md`, committed before behavior tests.

1. A reduced fixture `kwic_texts_mlk_56000_empty_highlight_current.html`: the four hits on `56000114010`, with the total reduced to 4.
2. RED tests (`tests/test_kwic_empty_highlight_current.py`):
   - the page parses, with `target_text` values `mlK`, `w)rywK`, `)l)sr` and `null` in CAL's order, and the empty-highlight hit keeps its coordinate, context and full-context URL;
   - a target line with no `<b>`, or with two `<b>` elements, fails closed.
3. GREEN: an empty highlight gives `target_text: None`.
4. Docs: `docs/tools/concordance.md`, `research.md` R-050, the fixture README, CHANGELOG.
5. Verification: the full suite; offline on the full 106-hit capture; live over MCP.
6. Independent adversarial review of the exact candidate SHA.
