# Issue #171 plan — non-Mandaic `showsubtexts.php` links in text search results

Date: 2026-09-30. Research: `docs/research/issue-171-text-search-subtext-links.md`, committed before behavior tests.

1. Reduced fixtures: `text_search_neofiti_subtexts_current.html` and `text_search_onkelos_subtexts_current.html`.
2. RED tests (first design, superseded by the revision below) (`tests/test_text_search_subtext_links_current.py`):
   - Neofiti gives `54001`, label `TN (Targum Neofiti)`, a description, and `follow_with: cal_text_catalogue`;
   - Onkelos gives `70703012`, followed with the catalogue;
   - the existing Ginza (Mandaic) and ordinary results give `follow_with: cal_text_page`;
   - an unknown `cset`, a missing `cset`, or a non-decimal `subtext` fails closed;
   - the MCP result serializes `follow_with`.
3. GREEN: `TextSearchMatch` (the `TextRef` fields plus `follow_with`), with the classification in `_search_text_ref_from_link`.
4. Docs: `docs/tools/texts.md` (which tool follows each match), the tool docstring, `research.md` R-053, the fixture README, CHANGELOG.
5. Verification: the full suite; live over MCP (`Neofiti` → catalogue → page, `Ginza`, `Onkelos`).
6. Independent adversarial review of the exact candidate SHA.

## Revision after review (2026-09-30)

`follow_with` became `follow_up_tool`. Catalogue nodes report `category_id` with `file_id: null`. Routing is decided by the Mandaic collection prefix and the `cset`, and a Peshitta (`cset=U`) fixture was added.
