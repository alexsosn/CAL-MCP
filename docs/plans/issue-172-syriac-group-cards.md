# Issue #172 plan — `cal_syriac_group` and CAL's current card layout

Date: 2026-09-30. Research: `docs/research/issue-172-syriac-group-cards.md`, committed before behavior tests.

1. Reduced fixtures: `syriac_group_60420_cards_current.html` and `syriac_group_61000_cards_current.html`, each with 3 cards.
2. RED tests (`tests/test_syriac_group_cards_current.py`):
   - both groups give ordered text children with `upstream_id`, `subtext_id`, label, navigation URL and info URL;
   - `subtext_id` is serialized;
   - fail-closed cases: an unknown link class in a card, a card with two book-links, a book-link for another file than its info link, a toggle naming another group, a summary info link naming another group, and a repeated card.
3. GREEN: the card-layout parser, and `SyriacTextItem.subtext_id`.
4. Docs: `docs/tools/syriac.md`, `research.md` R-055, the fixture README, CHANGELOG.
5. Verification: the full suite; live over MCP (both groups, then one child with `cal_text_page`).
6. Independent adversarial review of the exact candidate SHA.
