# CAL parser fixtures

These fixtures are deliberately reduced semantic excerpts, not archived CAL pages. They retain only the minimum current markup/text relationships needed by offline parser tests.

Capture/recheck dates: **2026-09-04–2026-09-05**.

| Fixture | CAL source | Purpose |
| --- | --- | --- |
| `browse_b.html` | `https://cal.huc.edu/browseSKEYheaders.php?first3=%22b%22` | direct headwords, homographs, alias-arrow resolution |
| `entry_br_n.html` | `https://cal.huc.edu/cal_entry_web.php?lemma=br+N` | numbered/nested senses, dialects, Unicode citation text, form/usage, derivative depth, notes |
| `entry_br_nested.html` | `https://cal.huc.edu/cal_entry_web.php?lemma=br+N` | repeated parenthetical sense levels plus mixed linked/plain citations sharing rendered rows |
| `entry_bysh_n.html` | `https://cal.huc.edu/cal_entry_web.php?lemma=by%24h+N` | full-form alias resolution and optional-section absence |
| `entry_nmy_x.html` | `https://cal.huc.edu/oneentry.php?cits=all&lemma=nmy+X` | unnumbered primary sense, nested sense, notes |
| `entry_abr_v.html` | `https://cal.huc.edu/oneentry.php?cits=all&lemma=%29br+V` | root cross-reference and stem-specific verb senses |
| `not_found.html` | CAL lexicon surface | explicit no-match semantic page |
| `search_gloss_camel.html` | `POST https://cal.huc.edu/newsearchmngs.php` (`English=camel#`, `secondary=true`) | ordered lemma-link + gloss result shape |
| `search_gloss_empty.html` | `POST https://cal.huc.edu/newsearchmngs.php` (`English=qzxvjk#`, `secondary=true`) | exact current empty-gloss marker |
| `search_citations_camel.html` | `POST https://cal.huc.edu/searchcits.php` (`English=camel`) | repeated lemma/context/citation rows with Hebrew and Syriac source text |
| `search_citations_empty.html` | `POST https://cal.huc.edu/searchcits.php` (`English=qzxvjk`) | exact current empty-citation marker |
| `text_catalogue_root.html` | `https://cal.huc.edu/newtextmenu.html` | root category links plus a directly linked text |
| `text_catalogue_biblical.html` | `https://cal.huc.edu/showsubtexts.php?subtext=3` | explicit subtext/file navigation identifiers |
| `text_search_tel_dan.html` | `POST https://cal.huc.edu/newsearchtxts.php` (`search=Tel Dan`) | topic-search text reference, label, and rendered description |
| `text_page_bt_az.html` | `https://cal.huc.edu/get_a_chapter.php?file=71026&page=0` | paginated text metadata, line/display coordinates, token links, comments, and next-page navigation |
| `text_page_tel_dan.html` | `https://cal.huc.edu/get_a_chapter.php?file=13250&page=0` | valid short text with line/token coordinates but no page-count marker |
| `text_page_missing.html` | `https://cal.huc.edu/get_a_chapter.php?file=13250&sub=999` | current explicit `NO LINES FOR ... ARE CURRENTLY STORED` missing-text marker |
| `token_analysis_single.html` | `https://cal.huc.edu/getlex.php?coord=4400137054005&word=0` | one compact CAL analysis label paired with one linked lemma header |
| `token_analysis_multiple.html` | `https://cal.huc.edu/getlex.php?coord=7102601002203&word=0` | current ordered two-analysis token (`w_ c`, `my c`) plus following non-candidate sense text |
| `token_analysis_not_found.html` | bounded `getlex.php` probes | current explicit no-data marker shared by nonexistent decimal coordinates and out-of-range word indexes |
| `token_analysis_unicode.html` | reduced current token-analysis shape | Syriac rendered headword preservation |
| `token_analysis_hebrew.html` | reduced current token-analysis shape | Hebrew rendered headword preservation |
| `token_analysis_marker_only.html` | synthetic drift from current token-analysis marker | analysis shell with no candidate must fail closed |
| `token_analysis_missing_lemma.html` | synthetic drift from current token-analysis shape | rendered lemma-like header without the required CAL lemma link must fail closed |
| `bibliography_authors_kau.html` | `POST https://cal.huc.edu/browsenames.php` (`first3=Kau`) | ordered exact-author selector values and labels |
| `bibliography_authors_empty.html` | `POST https://cal.huc.edu/browsenames.php` (`first3=Qqqqqq`) | current explicit no-author marker |
| `bibliography_author_kaufman.html` | `https://cal.huc.edu/getbibauthor.php?myauthor=Kaufman%2C+Stephen+A.` | ordered author records, Unicode title text, subject and lemma links |
| `bibliography_keyword_tada.html` | `https://cal.huc.edu/getbibsigla.php?myauthor=TADA` | exact CAL text/subject tag results with ordered record links |
| `bibliography_lemma_cly_v.html` | `https://cal.huc.edu/getbiblemma.php?myauthor=cly+V` | exact CAL lemma bibliography and linked lemma keys |
| `bibliography_empty.html` | bounded nonexistent queries against CAL bibliography result endpoints | current explicit shared bibliography no-data marker |
| `concordance_text_13250.html` | `https://cal.huc.edu/newconcord.php?text=13250&cset=S` | one-text lemma-frequency rows with CAL lemma keys, glosses, and explicit KWIC links |
| `kwic_texts_mlk.html` | `POST https://cal.huc.edu/showdialectKWIC.php` (`mlk N`, texts `12250 13250`, charset `R`) | multi-text result with one empty scope and ordered duplicate target coordinates |
| `kwic_texts_empty.html` | `POST https://cal.huc.edu/showdialectKWIC.php` (bounded no-hit text scope) | explicit per-text no-example marker plus `total examples: 0` |
| `kwic_dialects_aryk2_a.html` | `https://cal.huc.edu/dKWIC.php?lemma=%29ryk%232+A` | ordered CAL-owned dialect IDs/labels plus hidden lemma/POS contract |
| `kwic_dialect_aryk2_a_biblical.html` | `https://cal.huc.edu/show1dialectKWIC.php?lemma=%29ryk%232&pos=A&texts=3` | one Biblical-Aramaic target hit with file/subtext/charset/coordinate and Hebrew context |
| `targum_parallel_gen_1_1.html` | `POST https://cal.huc.edu/showtargum.php` (`bookname=01`, `chapter=01`, `verse=01`, optional Peshitta/Samaritan requested) | MT plus ordered current CAL Targum/source readings, Hebrew/Aramaic/Syriac Unicode, source chapter links, optional Peshitta, and absent Samaritan output |
| `targum_parallel_not_found.html` | `POST https://cal.huc.edu/showtargum.php` (`bookname=01`, `chapter=01`, `verse=99`) | current explicit `error in coordinate` not-found semantics |
| `targum_concordance_klb.html` | `POST https://cal.huc.edu/showtargumKWIC.php` (`lemma=klb`, `pos=N`) | ordered Targum section/source counts, same-origin example links, and reported total 59 |
| `targum_concordance_zero.html` | bounded structurally valid no-hit Targum concordance query | complete all-zero source table plus `total examples: 0` |
| `targum_hebrew_lemmas_mem_onqelos.html` | `https://cal.huc.edu/Omtlemmas/memMTlemma.html` | Onqelos MT-Hebrew lemma chooser with ordered opaque `R1` IDs, vocalized labels, and displayed POS |
| `targum_hebrew_lemmas_mem_neofiti.html` | `https://cal.huc.edu/mtlemmas/memMTlemma.html` | Neofiti source-specific MT-Hebrew lemma chooser form/action semantics |
| `targum_reflex_onqelos_1751.html` | `POST https://cal.huc.edu/getOmtlemma.php` (`R1=1751`) | selected MT Hebrew lemma plus Onqelos CAL lemma correspondence, frequency, and example URL |
| `targum_reflex_neofiti_1751.html` | `POST https://cal.huc.edu/getNmtlemma.php` (`R1=1751`) | selected MT Hebrew lemma plus multiple ordered Neofiti CAL lemma correspondences |
| `targum_reflex_invalid_id.html` | bounded invalid Onqelos selector probe (`R1=999999`) | current broad invalid-ID fallback with missing selected Hebrew lemma, which must fail closed |

The reduced excerpts are maintained only as test contracts. Normal tests make zero CAL requests. The search/text/token-analysis/concordance/bibliography/Targum fixtures were produced from deliberately bounded form/result audits and contain only a few semantic rows, not complete result pages. If current CAL markup materially changes, update the fixture provenance and parser tests rather than silently accepting incomplete output.
