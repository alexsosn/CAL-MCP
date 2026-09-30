# Issue #204 research — KWIC target lines where CAL highlights nothing

Date: 2026-09-29. Base: `c9892c7`.

## Trigger

While smoke-testing #181, `cal_kwic_texts("mlk N", ["56000"])` (Samaritan Targum) failed with `parser_drift` "CAL KWIC target line lacks one highlighted target token". The whole 106-hit result was lost.

## Live-current evidence

Two bounded requests through the production client on 2026-09-29:

1. `POST showdialectKWIC.php` with `lemma=mlk`, `pos=N`, `texts=56000`, `charset=R`: 106 target lines. CAL's highlight counts: `mlK` 53, `mlkh` 5, **empty 5**, `lmlK` 3, `mlkyh` 3, `(wg` 3, `mlky` 3, and others (`w)rywK`, `)l)sr`, `sdM`, `)dmh`, …).
2. `GET get_a_kwicchapter.php?file=56000&sub=114&cset=R&target=56000114010`: CAL's own tokens for that line are

   `whwh(0) bywmy(1) )mrpl(2) mlK(3) $n(r(4) w)rywK(5) mlK(6) )l)sr(7) "kdr l(mr"(8) mlK(9) (ylM(10) wtd(l(11) mlK(12) gwyM(13)`

   Word 8 is one token made of two words.

The four `mlk N` hits on line `56000114010` (the lemma occurs at words 3, 6, 9 and 12) are highlighted as `mlK`, `w)rywK`, `)l)sr` and **nothing** (`<b>&nbsp;&nbsp; </b>` between `mlK` and `(ylM`). The highlight drifts by one word per hit on this line. The same pattern appears on `56000114080` (`mlK`, `sdM`, empty, `wmlK`, `)dmh`).

## Findings

- On some Samaritan lines, CAL's KWIC highlight does not mark the lemma occurrence it reports. It can mark a neighbouring word, or nothing at all. This is CAL's rendering. CAL-MCP cannot tell from the page which word CAL meant, and must not correct it.
- The hit itself, meaning its coordinate, context and full-context link, is still CAL's hit for the requested lemma.

## Consequences

- A target line whose single `<b>` highlight is empty (whitespace or no-break spaces only) is returned with `target_text: null`. A missing `<b>`, or two of them, still fails closed.
- `docs/tools/concordance.md` states that `target_text` is CAL's highlight as rendered, which on some lines marks a neighbouring word or nothing. Use `cal_kwic_full_context` to see the line's own tokens.
- Production requests are unchanged.
