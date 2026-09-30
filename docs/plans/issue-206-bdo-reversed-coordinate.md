# Issue #206 plan — KWIC coordinates written reversed inside `<BDO dir="rtl">`

Date: 2026-09-29. Research: `docs/research/issue-206-bdo-reversed-coordinate.md`, committed before behavior tests.

1. Reduced fixtures without page chrome: `kwic_texts_gml_71002_hebrew_current.html` (BT, 2 hits) and `kwic_texts_mlk_13250_hebrew_current.html` (Tel Dan, 6 hits).
2. RED tests (`tests/test_kwic_hebrew_rtl_coordinate_current.py`):
   - both pages parse, with CAL's `target` coordinates, charset `H`, highlighted tokens and full-context URLs;
   - fail-closed cases: a reversed coordinate outside `<BDO dir="rtl">`, a `BDO` with `dir="ltr"`, a reversed text that is not the exact reverse, and extra link text outside the `BDO`.
3. GREEN: the line parser allows either orientation, and the target-structure parser (which sees the markup) requires the reversed form to be exactly the link's `<BDO dir="rtl">` text.
4. Docs: `docs/tools/concordance.md`, `research.md` R-051, the fixture README, CHANGELOG.
5. Verification: the full suite; live over MCP (BT and Tel Dan with `script="hebrew"`, then full context for one BT hit).
6. Independent adversarial review of the exact candidate SHA.
