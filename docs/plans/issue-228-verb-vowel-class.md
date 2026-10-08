# Issue #228 plan — take row POS from CAL's `<pos>` element

**Research:** `docs/research/issue-228-verb-vowel-class.md` (R-063)

1. `_SemanticHTMLParser` records, for each link, the text of any `<pos>` element inside it and
   how many there are (`_Link.marked_pos`, `_Link.marked_pos_count`). Line text is unchanged.
2. A new helper, `lexicon._apply_marked_pos(parsed, link)`, does the following:
   - no `<pos>`: returns `parsed` unchanged;
   - exactly one non-empty `<pos>` whose text starts with the grammar's POS token, where the
     link's remaining text after it is that extra POS text and then optionally `#N`: returns
     `part_of_speech` = the `<pos>` text, whitespace-collapsed;
   - anything else (several `<pos>`, an empty one, disagreement): returns `None`, so the caller
     fails closed.
3. It is applied in `lexicon.parse_browse_page`, `lexicon_browse.parse_lexicon_browse_page`
   (entry rows) and `search.parse_gloss_search_page`.
4. Docs: `docs/tools/search.md` (the citation-search note about "shorter `vb.`"),
   `lexicon-browse.md`, `lexicon.md` (the exact entry keeps the vowel class as `pronunciation`),
   `CHANGELOG.md`, and R-063.

## RED tests

- A verbatim browse fixture for `(hr`: `part_of_speech == "vb. a/u"` through both
  `parse_lexicon_browse_page` and `parse_browse_page`.
- A verbatim gloss-field fixture: `vb. a(i)/u` followed by `#2`, and `vb. a/u, e/a`.
- Fail-closed cases: two `<pos>` in a link; `<pos>` text that disagrees with the rendered header;
  unexpected text after `<pos>` other than `#N`.
- Legacy rows without `<pos>` are unchanged (the existing fixtures).
