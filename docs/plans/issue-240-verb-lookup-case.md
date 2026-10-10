# Issue #240 plan — match verbs despite CAL's uppercase root display

**Research:** `docs/research/issue-240-verb-lookup-case.md` (R-069)

1. In `lexicon._query_matches`, for a lemma whose key ends in ` V`, add the lowercase form of each
   all-uppercase headword to the compared surfaces. Every other headword and alias is unchanged.
2. Output is unchanged: `matches` keep CAL's displayed headwords (`KTB`).
3. Docs: `docs/tools/lexicon.md` (verbs are matched by their lowercase root), `CHANGELOG.md`, R-069.

## RED tests (offline, with the verbatim `browse_verb_vowel_class.html` fixture)

- `cal_lexicon_lookup("(hr")` is ambiguous between `(hr V` and `(hr A`. Before the fix it found
  only `(hr A`.
- `cal_lexicon_lookup("(hr", lemma_key="(hr V")` is accepted.
- A non-verb row with a case-significant uppercase letter is not folded.
