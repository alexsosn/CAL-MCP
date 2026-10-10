# Issue #240 research — CAL shows verb roots in uppercase on result rows

**Date:** 2026-10-09  
**Base:** `main` at `c092f89`

## Evidence

One new bounded GET was made: `browseSKEYheaders.php?first3="ktb"` (10619 bytes). The earlier
captures were re-read offline: browse `(hr` (#228) and `$yp` (#227), and the gloss-field and
gloss-search pages (R-062), 1587 rows in total.

- Every verb row (lemma key ending ` V`) has an entirely uppercase headword: `KTB` (`ktb V`),
  `ˁHR, ˀHR` (`(hr V`), and `ḤŠL`, `ŠḤL`, `ˀRYN`, `ŠGNY`, … in the gloss fields (9 of 9).
- No other row has an all-uppercase headword. Two non-verb rows contain one uppercase letter
  (`qmPy, qmPytˀ`, `Pksynˀ`), so case is significant outside the verb convention.
- The exact verb entry renders the headword in lowercase (`ˁhr, ˀhr`).

`cal_lexicon_lookup` compares the query with browse-row headwords case-sensitively, so a verb is never a
match: `)mr` finds only the `)mr` nouns, `ktb` / `כתב` only `ktb N`, and an explicit
`lemma_key=")mr V"` is rejected.

## Implication

When comparing a query with a browse row, use the lowercase form of a headword only when the row is
a verb (lemma key ending ` V`) and the headword is entirely uppercase. Other headwords keep their
case-significant comparison, and output keeps CAL's display form.
