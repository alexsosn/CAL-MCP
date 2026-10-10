# v0.1 pre-release user-facing E2E smoke — 2026-10-10

**Base:** `main` @ `86dc6e7` (synced 2026-10-10)
**Artifact:** `cal_mcp-0.1.0-py3-none-any.whl` built from that revision and installed into a fresh
virtual environment (Python 3.13); every call below went through the installed `cal-mcp`
executable over stdio using the MCP Python client, sequentially, one session per stage.
**Related:** #15 (release), D-022 / #157 (bounded installed-stdio smoke)

## Summary

| Check | Result |
| --- | --- |
| Offline gates (`ruff check`, `ruff format --check`, `mypy src`, `pytest`) | pass — 1956 tests |
| Built-in bounded smoke `python -m cal_mcp.stdio_live_smoke` | **passed**, 12 cases, 13/25 CAL transport attempts |
| `tools/list` | 36 tools, matches README / capability matrix |
| Broad user-facing matrix (≈140 calls, 4 stages) | **9 defects**, of which 6 are upstream-shape drift that turns ordinary inputs into `parser_drift` |

The fixed smoke set passes, but a wider range of texts, scripts and dialects shows that
several common user journeys fail closed with `parser_drift`. The four rated release-blocking
below affect basic lexicon lookup, KWIC by dialect, and the Peshitta / Ginza text surfaces.

Request load: the run was manual and sequential, and every request is attributable to one
explicit tool call. Diagnosing the drift took 8 extra single-page fetches through the
project's own `CalHttpClient` (project User-Agent). Plain `curl` without the project
User-Agent gets CAL's "Please do not try to scrape our site" page instead of data, so curl
was not used further. No CAL page content is committed; the quotes below are the shortest
fragments that identify the drift.

## Defects

Severity: **B** = release-blocking (a common user input fails), **M** = should fix before
release, **m** = minor/UX.

### B1 — explicit CAL "no headwords" page reported as `parser_drift` (lexicon lookup + browse)

- `cal_lexicon_lookup("qqqqzz")` and `cal_lexicon_browse("qqq")` → `parser_drift: CAL lexicon
  browse page contains neither entries nor explicit no-match`.
- **Every Hebrew-script word beginning with bare `ש`** is affected: `ש` expands to the `$` and `&`
  candidates, and for most words the `&` prefix has no headwords, so the whole lookup fails.
  Reproduced with `cal_lexicon_lookup("שלמא")` → failing URL
  `browseSKEYheaders.php?first3="&lm"`. (The Syriac `ܫܠܡܐ` resolves fine because it has only one candidate.)
- CAL's current wording is `There are no headwords beginning with: qqq`. That phrase is
  not in `_NOT_FOUND_PHRASES` (`src/cal_mcp/lexicon.py`), which `lexicon_browse.py` shares.
- Fix: recognize the explicit phrase (tied to the requested prefix), and add a reduced
  fixture with a regression test for both tools plus a ש-initial Hebrew lookup.

### B2 — `cal_kwic_dialect` rejects CAL's alphanumeric target coordinates

- `cal_kwic_dialect("mlk N", "2")` (Imperial) and `("mlk N", "71")` (Babylonian Talmudic) →
  `parser_drift: CAL returned a non-decimal target_coordinate`.
- CAL hit links now include targets such as `213011R5`, `2235212A1`, `22554133b01`,
  `23203005A08` (`get_a_kwicchapter.php?...&target=…`). The same letter-bearing coordinate
  shape also appears in lexicon citations (`showachapter.php?fullcoord=13200202a16`), where
  CAL-MCP already preserves the link but returns `full_coordinate: null`.
- The selector contract for `cal_kwic_full_context` (decimal `target_coordinate`) needs a
  research/decision step first: accept CAL's opaque alphanumeric coordinate and verify that the
  full-context route accepts it, or else return the hit with a null selector instead of failing
  the whole page.

### B3 — unknown CAL charset `T` (Old Aramaic KWIC, Palmyrene text search)

- `cal_kwic_dialect("mlk N", "1")` → `parser_drift: CAL KWIC target link has an unknown charset`
  (92 links carry `cset=T`, for example `get_a_kwicchapter.php?file=11200&sub=2&cset=T&target=11200206`).
- `cal_text_search("Palmyr")` → `parser_drift: CAL text search subtext result has an invalid cset`
  (`showsubtexts.php?subtext=41201&cset=T`).
- `_KWIC_CHARSETS` and `_SCRIPT_CSETS` allow only `R/H/S/U`. `T` is new upstream evidence:
  record it in `research.md` and confirm what it renders before adding it.

### B4 — `cal_text_concordance` rejects CAL's returned key `prC PN`

- `cal_text_concordance("62040")` (Peshitta Matthew) → `parser_drift: CAL concordance row
  contains an invalid lemma key`. Exactly one of 1375 rows fails: the proper noun `prC PN`
  (Perez), whose key has the capital `C`. Returned keys only allow the observed capitals
  `K`/`M` (R-045). One proper noun fails a whole core Syriac text.
- *Correction:* the first version of this report blamed the trailing-underscore keys `b_ p`,
  `dyl_ P` and `l_ p`. That came from a faulty ad-hoc regex. Those keys already validate (R-072).
- Fix: add `C` to the observed returned-key capitals, with a fixture.

### M1 — Mandaic Ginza catalogue: subtext info links name the parent text

- `cal_text_catalogue("74410")` (Ginza Rabba, Right) → `parser_drift: CAL Mandaic subtext
  information coordinate names another text`. All 396 info links are `get_file_info.php?coord=74410`,
  while the parser (`texts.py`, Mandaic subtext rows) requires `file_id + subtext_id`.
- Likely fix: accept the parent-file coordinate as an explicit, tested variant, without inventing a
  per-subtext info coordinate.

### M2 — `cal_bibliography_lemma` fails for keys containing `$`

- `cal_bibliography_lemma("$lm N")` → `parser_drift: … heading does not match the submitted query`.
  CAL echoes the key backslash-escaped (`CAL Bibliography for \$lm N … NO data FOR \$lm N`). In
  this case the correct result is an empty record list. `$` (shin) is one of the most common
  initial letters.

### M3 — `cal_lexicon_citation_context` returns an unstructured error for invalid input

- `cal_lexicon_citation_context("https://cal.huc.edu/x")` → `isError` with only the text
  `Error executing tool cal_lexicon_citation_context` and no `structuredContent.error`.
  Every other tool returns a typed `invalid_input` error here.
- Cause: `_validate_full_coordinate` in `src/cal_mcp/lexicon_citation_context.py` raises a bare
  `ValueError` instead of `CalInputError`. It is the only tool-reachable input validator that does.

### M4 — `cal_text_search` with non-ASCII input reports `parser_drift`

- `cal_text_search("מלכא")` → `parser_drift: CAL text search page is missing its result marker`.
  CAL actually answers `"" is not a valid search string`. `cal_citation_text_search` already
  maps this response to a CAL-rejected-input error (`_CITATION_REJECTED_RE` in `search.py`);
  text search should do the same (or reject non-ASCII input locally if research shows CAL
  never accepts it).

### m1 — biblical book labels are hard to discover

- `cal_targum_parallel(book="Genesis", …)` and `cal_syriac_peshitta_parallel(book="Matthew", …)`
  → `book must be one exact current CAL biblical book label`. The accepted labels (`Gen`, `Exod`,
  `Levit`, …, `Psalms`) are in `docs/tools/targum.md`, but neither the input schema (plain
  `string`) nor the error lists them, so an agent has to guess. Adding them as a schema `enum`, or
  quoting them in the error (about 330 characters, which fits the 500-character message limit),
  would make the tool usable without reading the docs. The Peshitta parallel covers OT books only.
  That is correct for CAL, but is worth saying in the tool description.

## Working as documented (spot-checked content)

- **Conversion, local, no CAL request:** Hebrew `מלכא`, Syriac `ܡܠܟܐ`, Imperial `𐡌𐡋𐡊𐡀` → `mlk)`;
  Mandaic `ࡌࡀࡋࡊࡀ` → `malka`; Palmyrene, Nabataean, Samaritan, Hatran letters map correctly;
  `בר אנש` → `br` + `)n$|)n&`. Clear `invalid_input` for pointed Hebrew (with an unpointed
  suggestion), vocalized Syriac, mixed scripts, empty input, emoji, and undocumented transliteration
  (`malkāʾ`).
- **Lexicon:** `מלכא`/`ܡܠܟܐ`/`mlk)` → `ambiguous` (`mlk N` king, counsel) and then `found` with
  `lemma_key`; `)zl V` (29 senses, 75 citations), `br N`, Syriac `ܫܠܡܐ`, JBA `הכי`, Syriac `ܐܙܠ`,
  Imperial-script input all OK; a mismatched `lemma_key` is rejected; browse `ml` plus one
  `next_continuation` hop OK; ambiguous Hebrew browse prefix `ש` is rejected with guidance.
- **Citation context** for decimal `full_coordinate`s (Idumaean ostraca, Bavli) OK.
- **English search:** gloss (`king`, `water` all-glosses, `son of man`, `naïve`), gloss field
  `astronomy` (an invalid field is rejected), citation search `bread` (Syriac and JLA citations
  with translations).
- **Texts:** root catalogue (with the Syriac specialized collection), Biblical Aramaic category,
  Peshitta Matthew chapters; text search `Tel Dan`, `Ahiqar`, `Genesis`, `Ginza`, `Berakhot`, plus
  an empty no-match; pages for Tel Dan, Ahiqar (pages 1–2; page 999 rejected with "last page (5)"),
  P Mt ch. 5, and Midrash Haggadol; text information; line comments with and without records;
  token analysis (Ahiqar `)lh R`).
- **Concordance/KWIC:** Tel Dan concordance (41 lemmas), `cal_kwic_dialects("mlk N")`,
  `cal_kwic_texts` for Tel Dan/Ahiqar, KWIC in Biblical Aramaic, KWIC full context; 9 text IDs
  rejected. Syriac `mlk N` exceeds the documented 2 MiB response ceiling (documented behavior).
- **Bibliography:** author prefix `Sok`, author `Sokoloff, Michael`, keyword `TDanStel`, lemma
  `mlk N`; unknown keyword and author prefix return empty results.
- **Dictionary collation:** Jastrow 100, DJBA 500, Payne Smith 200, Mandaic Dictionary 10,
  Thesaurus Syriacus `2:4000`; a non-numeric page is rejected.
- **External citations:** dialects; Syriac (702 sources) and Mandaic sources; citations for `DC`
  and `1KgdHex`.
- **Targum:** parallel Gen 1:1 with Onqelos, Ps-J, Neofiti, FTP, FTV, Peshitta; Ps 23:1;
  Esther 1:1 (TgEsth2); Gen 99:1 returns `not_found`; concordance `mlk N` (4233), then
  Onqelos examples (116); MT Hebrew lemmas (Onqelos `mem`, Neofiti `shin`), then reflexes;
  `pseudo-jonathan` rejected.
- **Syriac:** NT Peshitta, Old Syriac Gospels, inscriptions, group `61000`, missing words
  (verbs, feminine nouns), Peshitta parallel Gen 1:1 and Isa 53:5.
- Every successful CAL-backed result carried `provenance.source_url` and `retrieved_at`.

## Recommendation for #15

Do not tag v0.1 until B1–B4 are fixed. B1 and M3 are small, well-understood parser/validation
fixes. B2–B4, M1 and M2 are upstream-shape changes. Under `AGENTS.md`, each needs its own issue
with a reduced fixture, a `research.md` entry, and (for B2) a selector-contract decision. Consider
adding one ש-initial Hebrew lookup and one Imperial-Aramaic KWIC case to the D-022 smoke matrix,
within the 25-attempt budget, so these regressions show up in the weekly drift run.
