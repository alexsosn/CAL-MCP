# Issue #237 plan — structural current stem headings

**Research:** `docs/research/issue-237-stem-headings.md` (R-068)

1. `_SemanticHTMLParser` records the field spans of a `div.stem-header` on the line it renders
   (`_Line.stem_fields`: an ordered tuple of `(class, text)`, with nested markup flattened into
   the text). Lines outside a stem header have `None`.
2. `parse_lexicon_entry` handles that line first:
   - validate the fields: exactly one `stem-label` and one `stem-count` (`N sense(s)`); at most one
     `stem-name`, `stem-gloss` and `stem-chevron` (`▶`); no other class;
   - finish the current sense and check the previous stem's declared count;
   - start a new stem with `heading = "label name gloss"`;
   - every numbered or unnumbered sense built until the next stem carries that heading, and
     sense numbering restarts.
3. When the entry ends, the last stem's count is checked. A mismatch fails closed.
4. Docs: `docs/tools/lexicon.md` (stem headings and counts) and `CHANGELOG.md`.

## RED tests

The verbatim stem headers live in `tests/fixtures/cal/entry_stem_headers_current.txt`, with
minimal synthetic senses.

- `ktb V`-shaped: G with two numbered senses, D with one unnumbered sense, C with three, Gt with two.
  Headings are `G pəˁal to write`, `D paˁˁel to enroll, register : see s.v. kwtb`, and so on, and
  there is no fabricated sense.
- `(hr V` G: the senses carry `G pəˁal (animals) to be sexually aroused. lustful`.
- Fail-closed cases: a count that disagrees with the senses; an unknown stem span; a missing label;
  a malformed count.
- The older-layout `entry_abr_v.html` is unchanged.
