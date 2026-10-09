# Issue #224 plan — structural exact-entry header

**Research:** `docs/research/issue-224-entry-header-structure.md` (R-067)

1. Add `lexicon._LemmaHeaderParser`, an `HTMLParser` that finds the single `div.lemma-header` and
   records each child `span`'s class and full text. It also flags stray text or unexpected
   elements directly inside the block.
2. Add `_structural_lemma_header(body, lemma_key)`, which returns a `LemmaRef` built from the spans
   and fails closed as described in R-067 implication 1.
3. `parse_lexicon_entry`:
   - when the page has the block (the #227 count is exactly one), the lemma comes from the
     structural header, and the marked line stays the boundary for senses;
   - otherwise the header must be the first rendered content line, parsed with the existing
     grammar, and anything else fails closed. That line must not be a section marker such as the
     "Form & Usage" heading.
4. Docs: `docs/tools/lexicon.md`: an exact entry's `part_of_speech` is `null` where CAL's header
   has no POS, and older-layout pages need the header first. Also `CHANGELOG.md` and R-067.

## RED tests

- The current `$yp#2 N` header (verbatim) parses: `("šyp", "šypˀ")`, pronunciation `None`,
  `part_of_speech` `None`, gloss "a type of marsh reed".
- The five POS-bearing current headers (verbatim) parse to the pinned values.
- Fail-closed cases on the current block: an unknown span; stray text; a missing gloss; a duplicate
  POS; an empty POS span; an unparenthesized vocalization.
- Older layout: a page whose first line is prose, with a header-looking line later, fails closed.
- The existing entry fixtures still parse unchanged.
