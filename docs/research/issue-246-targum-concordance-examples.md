# Issue #246: CAL Targum concordance example follow-up — source and architecture research

Date: 2026-10-10. Grounded in the current checked-in code, `targum_concordance_klb_current.html`, and the exact bounded CAL live inspections [38059457264](https://github.com/alexsosn/CAL-MCP/actions/runs/38059457264) and [38059641146](https://github.com/alexsosn/CAL-MCP/actions/runs/38059641146). No new CAL requests for this ticket.

## Source semantics

Parent `cal_targum_concordance("klb N")` posts to `showtargumKWIC.php` and returns ordered rows with validated same-origin example URLs. One row contains an exact group of five text IDs, another six, and one **nine**, which rules out reusing generic `cal_kwic_texts` (caps IDs at eight, uses POST `showdialectKWIC.php`). The generic `cal_kwic_dialect` does use GET `show1dialectKWIC.php` but accepts one dialect, not a Targum text group, and omits the `charset=H` selector.

A current source URL has exact `lemma=klb&pos=N&texts=51001%2051002%2051003%2051004%2051005&charset=H` and returns HTTP 200. The page is **BR-line**, not table-based. Header `Looking for klb N in 51001 51002 51003 51004 51005` identifies the caller's group. Three linked targets point to `get_a_kwicchapter.php` with `file,sub,target,cset`; rendered target lines include `span.red` under `b`, with one line before/after. A source total reads `3 examples found for klb N in dialect 51001 51002 51003 51004 51005`. It is NOT generic KWIC's `total examples` heading. The generic parser's `_parse_kwic_hit_lines` and `_apply_kwic_target_structure` already validate target links, coordinates, highlight, and full-context selectors; they should be reused *only* where the observed markup supports it. CAL's generic `KwicHit` and `_hit_to_dict` are appropriate to reuse.

## Implementation boundary

Introduce one caller-controlled `cal_targum_concordance_examples(lemma_key, text_ids)` and one service GET to the fixed `show1dialectKWIC.php` route, with precisely ordered `lemma, pos, texts, charset=H`; never accept arbitrary upstream URLs. Expose `text_ids` as a derived, backward-compatible array on parent rows to make the exact group followable without manual URL parsing. Validate 1..32 distinct ASCII-decimal IDs, preserving source order and leading zeroes, with total selector bytes bounded; this exceeds the observed nine IDs but prevents unbounded queries. Do not prefetch anything.

The new page parser must validate the source URL selectors, single identifying heading, single **Targum-specific** result summary, exact count of target lines, only requested text files, CAL `get_a_kwicchapter` links with the existing safe URL validation, optional explicit CAL empty marker only when fixture-backed. Unrecognized/contradictory content should fail as parser drift, not silently become zero examples. Return ordered `hits` with actual CAL context and target highlight, `total`, and provenance, without invented scripture coordinates. Keep follow-up `get_a_kwicchapter` as a distinct optional caller action via existing `cal_kwic_full_context` where selectors fit.

## Research risk

A header, summary, link or group mismatch must not be hidden by generic KWIC fallback. The source parser is intentionally route-specific; use generic *internal* hit parsing only if fixture-backed. No new browsing or CAL web requests are needed before local RED/GREEN tests; the limited current-source shape above is already recorded.
