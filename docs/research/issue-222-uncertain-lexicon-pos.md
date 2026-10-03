# Issue #222 research — CAL marks uncertain lemma POS with a trailing question mark

**Date:** 2026-10-03  
**Base:** `main` after #208 (`112e9fb`)  
**Discovered from:** issue #175 research

## Trigger

The current `$l` lexicon browse page fails because lemma key `$lh N` is rendered as
`šlh n.f.?`. The shared lemma-header parser does not recognize `n.f.?` as a part-of-speech
token.

The defect is shared by browse and exact-entry parsing. On the exact entry, the current parser does
not fail closed: after skipping the real header, it can accept later prose as a false lemma header.
That makes this a data-integrity defect rather than only a browse availability defect.

## Bounded current CAL evidence

No returned link was followed automatically. The exact entry request below was chosen explicitly
from the already-observed `$lh N` lemma key.

### Run 37082310142 — browse + exact entry

Two GETs:

1. `browseSKEYheaders.php?first3="$l"`;
2. `oneentry.php?lemma=$lh N&cits=all`.

Current browse evidence:

- CAL renders two `$lh N` linked headers as `šlh n.f.?`;
- both fail `_parse_lemma_header(..., require_gloss=False)`;
- the browse page therefore fails with
  `CAL lexicon browse candidate is missing a recognizable lemma header`;
- direct DOM inspection of the browse HTML found two uncertain POS values, both exactly
  `n.f.?`, inside CAL's POS markup.

Current exact-entry evidence:

- `_parse_lines` exposes the real header as `šlh n.f.? watering(?)`;
- that real header fails `_parse_lemma_header(..., require_gloss=True)`;
- nevertheless `parse_lexicon_entry` returns success by finding a later prose line that happens
  to contain a token ending in a period.

The first probe showed the resulting public POS as `suggestions.`, which required a dedicated
follow-up to establish exactly which prose was being misclassified.

### Run 37082399451 — exact-entry DOM and false-header identification

One GET of the same exact `$lh N` entry.

CAL's current DOM places the uncertainty marker inside the semantic lemma-header POS element:

`div.lemma-header > span.lemma-pos` → `n.f.?`.

This establishes that the question mark belongs to the displayed part-of-speech value. It is not
gloss punctuation and must not be dropped or moved.

The real semantic header line is:

`šlh n.f.? watering(?)`

and currently produces no parsed lemma header.

The current parser then accepts this later prose as a false header:

`See DNWSI 17 for other suggestions. Compare CPA šlyh, Syr. šltˀ "drop".`

That produces the corrupted lemma:

- headwords: `("See DNWSI 17 for other",)`;
- part of speech: `suggestions.`;
- gloss: `Compare CPA šlyh, Syr. šltˀ "drop".`.

Another later prose line beginning `Page refs. ...` also satisfies the current generic
period-containing POS heuristic, demonstrating why recognizing the real header early is necessary.

Total issue-#222 research load: **3 explicit GETs** across the two runs. No browse continuation,
citation traversal, or entry crawl was performed.

## Parser cause

`_parse_lemma_header` tokenizes on non-whitespace and calls `_looks_like_pos_token`.
The current predicate accepts ASCII letters/digits plus `.`, `/`, and `-`, and requires at
least one period. Therefore `n.f.?` fails only because of its final `?`.

The current observed uncertainty form is a **single trailing question mark after an otherwise valid
POS token**. The safe grammar extension is correspondingly narrow:

1. if a token ends in exactly one `?`, remove that final marker only for validation;
2. require the remaining token to satisfy the complete existing POS-token predicate;
3. preserve the original token, including `?`, in `part_of_speech`;
4. do not allow `?` elsewhere in a token and do not admit other punctuation.

For the observed `n.f.?`, the returned public value is therefore literally
`part_of_speech="n.f.?"`.

## Scope across parser surfaces

The change belongs in the shared lemma-header predicate because both current surfaces use the same
header grammar:

- lexicon browse candidate parsing;
- exact lexicon entry header parsing.

The parser must not add browse-specific cleanup or exact-entry fallback behavior to hide the
problem.

A correct shared fix makes the real exact-entry header parse before later prose can be considered.
The existing exact-entry algorithm remains structurally weak in that it scans lines for a
header-looking shape, but this ticket does not redesign entry-page boundary detection. A separate
adversarial test must ensure the current `$lh N` page selects the real uncertain header and never
the known `suggestions.` false positive.

## Compatibility boundary

The research observed only `n.f.?` in the fixed current surfaces. The implementation should not
hard-code that exact noun label; the evidence-backed semantic unit is an optional **single trailing
uncertainty marker** on a token whose unmarked form already satisfies the existing POS grammar.

Nearby forms such as `n.?f.`, `n.f.??`, `n.f.!`, `?n.f.`, or punctuation-only tokens remain
invalid.

Issue #175 remains responsible for modeling arrow cross-reference rows separately. This ticket must
not change cross-reference semantics or `LemmaRef.aliases`.

