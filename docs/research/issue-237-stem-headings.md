# Issue #237 research — current verb entries mark each stem heading in `div.stem-header`

**Date:** 2026-10-09  
**Base:** `main` at `4ce3903` (after #224)

## Bounded current CAL evidence

The pages used are the #224 capture of `cal_entry_web.php?lemma=)mr V` (2026-10-09), the #228
capture of `(hr V` (2026-10-08), and one new GET of `ktb V` (2026-10-09, 103306 bytes). No links
were followed.

Each stem of a verb entry opens with:

```html
<div class="stem-header" onclick="toggleStem('04')"><span class="stem-label">Gt</span><span class="stem-name">ˀeṯpəˁel</span><span class="stem-gloss">to be said</span><span class="stem-count">2 senses</span><span class="stem-chevron" id="chev-04">&#x25B6;</span></div>
```

Observations:

- The spans have no whitespace between them, so the flattened line is `Gtˀeṯpəˁelto be said2 senses▶`.
- `stem-gloss` can contain markup, for example `ktb V` D: `to enroll, register : <small>see s.v. <i>kwtb</i></small>`.
- `stem-count` is `N sense` / `N senses`, the number of top-level senses in that stem. Within each
  stem the senses are numbered from 1. A one-sense stem may render its sense unnumbered (`ktb V` D).
- Stems: `)mr V` has G (4 senses) and Gt (2 senses); `ktb V` has G 2, D 1, C 3 and Gt 2;
  `(hr V` has G 2.

## Current CAL-MCP behaviour (`main`)

`_STEM_HEADING_RE` (`^(?P<heading>.+?)\s+\d+\s+senses?▶$`) is written for the older layout, where
the heading is `D paˁˁel to make a son 1 sense▶`. It never matches the unspaced current line, so:

- the line becomes the definition of a fabricated unnumbered first sense
  (`(hr V`: `"Gpəˁal(animals) to be sexually aroused. lustful2 senses▶"`);
- every sense has `heading: null`;
- from the second stem on, the heading line is taken as an extra citation of the previous sense,
  so the citation count check fails closed. `cal_lexicon_lookup` fails on `)mr V` and `ktb V`.

The leading `G` / `D Dt` line is CAL's stem summary and is correctly returned as `grammar`, the
same as in the older layout.

## Implication

Read `div.stem-header` structurally:

- the heading is the label, name and gloss joined with single spaces, which matches the older
  layout's `heading` (`D paˁˁel to make a son`);
- every sense under that stem carries the heading;
- the declared count must equal the number of top-level senses parsed for the stem (numbered
  senses, or the single unnumbered one);
- an unknown span, a missing label or count, or a malformed count fails closed.

The older-layout regular expression stays for the historical fixtures.
