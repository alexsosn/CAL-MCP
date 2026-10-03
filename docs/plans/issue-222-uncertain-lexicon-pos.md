# Issue #222 plan — preserve trailing POS uncertainty in shared lemma headers

**Date:** 2026-10-03  
**Research:** `docs/research/issue-222-uncertain-lexicon-pos.md`

## Goal

Recognize CAL's current single trailing question-mark uncertainty marker on an otherwise valid
lemma-header POS token, preserve that marker literally in `part_of_speech`, and prevent the exact
entry parser from skipping the real `$lh N` header and accepting later prose as a false lemma
header.

This is a shared lemma-header fix. It must not implement issue #175's cross-reference model.

## Grammar boundary

Keep the existing POS-token grammar unchanged except for one optional terminal uncertainty marker.

A token is POS-like when:

1. it has no `?`; or it ends in exactly one `?`;
2. after removing that one terminal `?` for validation only, the token satisfies the complete
   pre-#222 `_looks_like_pos_token` contract:
   - starts with an ASCII letter;
   - contains at least one period;
   - contains only ASCII alphanumerics plus `.`, `/`, and `-`.

The parser keeps the original source span, so `n.f.?` serializes as `part_of_speech="n.f.?"`.

Do not accept internal, doubled, leading, or alternate punctuation such as `n.?f.`, `n.f.??`,
`?n.f.`, or `n.f.!`.

## TDD gate

### RED — commit before production code

Add focused tests covering the shared helper through public parser behavior.

1. Header-level:
   - `šlh n.f.? watering(?)` parses as:
     - headword `šlh`;
     - POS `n.f.?`;
     - gloss `watering(?)`;
   - nearby invalid punctuation remains unrecognized.

2. Browse-level reduced structural fixture:
   - one ordinary `$lh N` linked header rendered as `šlh n.f.?`;
   - following gloss text remains the gloss rather than part of POS;
   - current parser must fail before GREEN.

3. Exact-entry regression:
   - derive a reduced structural fixture from the existing entry fixture;
   - use the real-header shape `šlh n.f.? watering(?)`;
   - include later synthetic prose containing a word such as `suggestions.` that would satisfy the
     old broad period heuristic;
   - require `parse_lexicon_entry` to select the real first header and return `n.f.?`, not the
     decoy prose.

4. Keep existing ordinary noun/verb/adjective/v.n. tests unchanged.

The RED should fail for the observed uncertainty shape on both browse and exact-entry paths.

### GREEN

Change only the shared POS-token predicate (or an equivalently narrow helper). Do not add
page-specific special cases and do not strip the uncertainty marker before constructing
`LemmaRef`.

## Documentation

Update:

- `docs/tools/lexicon.md` to state that CAL's displayed POS uncertainty marker is preserved;
- `docs/tools/lexicon-browse.md` because the current `$l` example surface contains the marker;
- `CHANGELOG.md`.

No schema field is added; the existing `part_of_speech` string becomes faithful to the current
upstream value.

## Validation

1. full offline CI in both matrices;
2. bounded installed-wheel/stdio live acceptance with at most two explicit calls:
   - `cal_lexicon_browse(prefix="$l", representation="cal_code")`;
   - an exact `cal_lexicon_lookup` workflow selecting `lemma_key="$lh N"` from a caller-supplied
     query if the public lookup contract can select it without hidden extra discovery beyond its
     documented bounded workflow;
3. assert no returned lemma for `$lh N` contains the known false headword
   `See DNWSI 17 for other` or POS `suggestions.`;
4. remove temporary live workflow;
5. rerun workflow-free CI;
6. logically independent adversarial review of the exact final SHA before merge.

The final browse call may still expose #175's pre-existing flattened cross-reference semantics; this
ticket validates header correctness only.
