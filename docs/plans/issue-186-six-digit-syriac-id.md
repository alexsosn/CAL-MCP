# Issue #186 plan — Syriac text ids whose file-info label shows 5 digits

Date: 2026-09-29. Research: `docs/research/issue-186-six-digit-syriac-id.md`, committed before behavior tests.

1. A reduced current fixture from `get_a_chapter.php?file=634081&page=0`, with a provenance comment.
2. RED tests (`tests/test_text_page_six_digit_syriac_id_current.py`):
   - `cal_text_page("634081")` parses with `file_id` `634081` and label `Tamar and Judah`;
   - a label naming an unrelated file (`63409:`) fails closed;
   - the matching prefix without corroborating `file=63408&sub=1` links fails closed;
   - a prefix whose remainder is not the linked sub (links name `sub=2`) fails closed.
3. GREEN: `_page_text_ref` accepts the split label only with the navigation corroboration.
4. Docs: `docs/tools/texts.md`, `research.md` R-046, the fixture README, CHANGELOG if a bullet fits.
5. Verification: the full suite; offline on the four captures; live over MCP (`cal_syriac_texts` → `cal_text_page` for 634081 and 634082, page 2).
6. Independent adversarial review of the exact candidate SHA.
