# Issue #154 plan — repair gloss-field POS drift; expose CAL gloss-search redirects

**Research:** `docs/research/issue-154-gloss-field-drift.md` (R-062)

## Changes

1. `lexicon._looks_like_pos_token` accepts one trailing secondary-gender group:
   an existing POS token, optionally followed by `/`, then `(` + lowercase letters + `.)`, optionally followed by the #222 `?`. The literal token is
   preserved in `part_of_speech`. This shared fix also repairs lexicon browse and lookup headers.
2. `search.parse_gloss_search_page` gets its own row parser in place of `parse_browse_page`:
   - exactly one lemma link per result row;
   - rendered text before the link must be empty, or `<source> ⟹` (the gloss-search redirect),
     or the legacy `→` alias form;
   - anything else fails closed;
   - the gloss stays the next non-link line, as before.
3. Gloss matches become `GlossSearchMatch(lemma, cross_reference_from)`. JSON stays flat: the
   existing lemma keys plus `cross_reference_from`. This is an additive public field.
4. Docs: `docs/tools/search.md`, `CHANGELOG.md`, `research.md` R-062, and fixture README rows.

## RED tests

- A reduced current field fixture with ordinary, `n.m.(f.)`, `n.m.(f.) #3`, and `n.f./(m.)` rows
  parses, with literal POS values.
- A reduced current `camel#` fixture: two `n)qh N` rows, the second with
  `cross_reference_from == "nqh N"` and the first `null`.
- Fail-closed cases: unexplained text before the link; two arrows; an empty redirect source.
- Unit checks on the POS grammar: `n.m.(f.)`, `n.f./(m.)` and `n.m.(f.)?` are accepted;
  `n.m.(f.`, `n.m.()`, `n.m.(f.)(m.)`, `(f.)` and `n.m.(ḥ.)` are rejected.

## Out of scope (follow-up issues)

- Empty `<pos>` rows, which need a nullable `part_of_speech` (#227).
- `vb.` vowel class dropped in gloss/browse rows (#228).
