# Issue #152 plan — Targum concordance and Hebrew-reflex drift

Date: 2026-09-24. Research: `docs/research/issue-152-targum-concordance-reflex-drift.md`, committed before behavior tests.

1. Reduced current fixtures:
   - `targum_concordance_klb_current.html`: title heading, `<h3>` statement, header, `Torah` `<td>` section, a few rows including a multi-text selector, and the in-table total adjusted to the retained rows;
   - `targum_reflex_onqelos_1751_current.html`: `<h3>` heading and `<td>` header.
2. RED tests: both parse with the same semantics as the earlier fixtures. Fail-closed cases: a title for another lemma, a body statement naming another lemma, a total row contradicting the row sum, two totals, a section row with a link, a reflex heading for the wrong source.
3. GREEN: the smallest changes in `src/cal_mcp/targum.py`.
4. Docs: `docs/tools/targum.md` if user-visible semantics change (none expected), `research.md` R-031, fixture README.
5. Verification: full offline suite; live over MCP (about 3 requests: concordance, chooser and reflex); `live_smoke`; independent review.
