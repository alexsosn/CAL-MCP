# Issue #232 plan — every lexeme segment of a current token-analysis page, with CAL's marked POS

**Research:** `docs/research/issue-232-token-analysis-segments.md` (R-066)

1. `_CurrentLinkedRedirectParser` collects ordered segments after the H2 marker. A new segment
   starts at each `<hr>` outside a table. Collection stops at `div.cal-footer`. Each segment
   records its label text, the table state used by the existing checks, its links (with `<pos>`
   text and count), loose table text, and whether a second table appeared.
2. The current-layout path returns a `TokenAnalysisPage` with ordered `candidates` (one per
   linked segment) and ordered `unlinked_summaries` (one per text-only segment). Each candidate
   goes through the existing per-table validation and redirect logic, unchanged. A second table
   in one segment, or a linked segment without a label, fails closed. Pages with no table keep
   the existing linkless path.
3. A candidate's POS comes from its `<pos>` (`vb. a/a`), with the gloss after it (`to say`).
   Several `<pos>` elements, an empty one, or a disagreement fail closed.
4. Docs: `docs/tools/token-analysis.md`, `docs/tools/search.md` (remove the caveat that token
   analysis may give the shorter `vb.`), `CHANGELOG.md`, R-066.

## RED tests

- `w)mr` (verbatim fixture): two candidates, `w_ c` conj. and `)mr V`, `vb. a/a`, "to say".
- `l)brM` (verbatim fixture): one candidate `l_ p`, plus `unlinked_summaries == (")brM PN Personal name",)`.
- Fail-closed cases: two tables in one segment; a linked segment with no label; `<pos>` that
  disagrees with the rendered header.
- The existing token-analysis fixtures and tests stay unchanged.
