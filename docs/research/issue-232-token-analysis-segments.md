# Issue #232 research — current token-analysis pages list several `<hr>`-separated lexemes

**Date:** 2026-10-09  
**Base:** `main` at `f0e9d84`

## Bounded current CAL evidence

Three live GETs were made with the production client. No links were followed.

| Label | Request | Status | Bytes |
| --- | --- | --- | --- |
| `tok` | `GET getlex.php?coord=56000112010&word=1` (`yhwh`) | 200 | 3248 |
| `tok0` | `GET getlex.php?coord=56000112010&word=0` (`w)mr`) | 200 | 8102 |
| `tok2` | `GET getlex.php?coord=56000112010&word=2` (`l)brM`) | 200 | 2802 |

## Findings

After the H2 marker "Click on a headword to see a complete lexicon entry", CAL renders one
segment per lexeme of the token, with `<hr>` between segments:

- **A linked segment:** an analysis label (`w_ c`, `)mr verb G`), then a one-cell table whose
  `a.lexlink` holds the headword, an optional `span.rom` pronunciation, `<pos>` and the gloss.
  A verb is followed by its sense outline (`<p><span class="bin">G</span>…`).
- **An unlinked segment:** text only, for example `)brM PN Personal name`.

`w)mr` renders `w_ c` (`<pos>conj.</pos>`, "and, also") and then `)mr V`
(`<pos>vb. a/a</pos>`, "to say"). `l)brM` renders `l_ p` (`<pos>prep.</pos>`, "to, for") and then
the unlinked `)brM PN Personal name`.

The current parser, `_CurrentLinkedRedirectParser`, reads only the first table after the marker.
For `w)mr`, `cal_token_analysis` therefore returns only `w_ c`: the verb and its vowel class are
silently dropped. For `l)brM` it returns only `l_ p`, dropping the summary. Single-lexeme tokens
such as `yhwh` are unaffected.

For candidates that do survive, the flattened header grammar stops at `vb.`, so a verb's vowel class
would land at the start of `gloss` (`a/a to say`). This is the defect #232 originally reported;
CAL marks the whole POS in `<pos>`.

## Implication

Parse every segment after the marker, in order:

- a segment with a table becomes a candidate, under the existing one-row, one-cell, single-lexlink
  contract and the existing redirect notation;
- a segment without a table but with text becomes an `unlinked_summaries` entry;
- empty segments are skipped.

A candidate's `part_of_speech` is CAL's `<pos>` text. The grammar's POS token must be its prefix,
the extra marked text must open the remainder, and the gloss is what follows it. Any disagreement
fails closed. Text after a candidate's table (its sense outline) stays outside the public result,
as before.
