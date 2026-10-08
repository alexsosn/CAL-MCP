# Issue #227 plan — empty CAL `<pos>` on result rows; guard the exact-entry header

**Research:** `docs/research/issue-227-empty-pos.md` (R-064)

1. `LemmaRef.part_of_speech: str | None`.
2. `lexicon._parse_row_lemma_header(link, lemma_key)` becomes the single entry point for row
   headers in gloss search, `cal_lexicon_browse` and lookup's browse step:
   - exactly one empty `<pos>`: the header must contain no POS-looking token. Headwords and
     pronunciation come from the rendered label, with a trailing `#N` homograph marker removed,
     and `part_of_speech` is `None`;
   - otherwise: the existing grammar plus `_apply_marked_pos` (#228).
3. `_SemanticHTMLParser` marks a line produced by a `div.lemma-header` block.
   `parse_lexicon_entry` uses only that line when one exists, and fails closed when it does not
   parse. Pages without that block keep the existing scan, which is #224's scope.
4. Docs: `search.md`, `lexicon-browse.md`, `lexicon.md`, `CHANGELOG.md`, R-064.

## RED tests

- Verbatim botany gloss row and browse row for `$yp#2 N`: `part_of_speech is None` with the
  correct headwords and gloss.
- An empty `<pos>` combined with a POS-looking token in the header fails closed.
- Two `<pos>` elements, one of them empty, fail closed.
- The verbatim current entry header without a POS raises `LexiconParseError` instead of
  returning `Page / refs.`.
- The verbatim current entry header for `(hr V` still parses (`vb.`, `a/u`).
