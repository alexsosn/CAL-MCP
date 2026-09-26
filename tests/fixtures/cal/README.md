# CAL parser fixtures

These fixtures are deliberately reduced semantic excerpts, not archived CAL pages. They retain only the minimum current markup/text relationships needed by offline parser tests.

Capture/recheck dates: **2026-09-04–2026-09-11**.

| Fixture | CAL source | Purpose |
| --- | --- | --- |
| `browse_b.html` | `https://cal.huc.edu/browseSKEYheaders.php?first3=%22b%22` | direct headwords, homographs, alias-arrow resolution |
| `entry_br_n.html` | `https://cal.huc.edu/cal_entry_web.php?lemma=br+N` | numbered/nested senses, dialects, Unicode citation text, form/usage, derivative depth, notes |
| `entry_br_nested.html` | `https://cal.huc.edu/cal_entry_web.php?lemma=br+N` | repeated parenthetical sense levels plus mixed linked/plain citations sharing rendered rows |
| `entry_bysh_n.html` | `https://cal.huc.edu/cal_entry_web.php?lemma=by%24h+N` | full-form alias resolution and optional-section absence |
| `entry_nmy_x.html` | `https://cal.huc.edu/oneentry.php?cits=all&lemma=nmy+X` | unnumbered primary sense, nested sense, notes |
| `entry_abr_v.html` | `https://cal.huc.edu/oneentry.php?cits=all&lemma=%29br+V` | root cross-reference and stem-specific verb senses |
| `lexicon_citation_context_ezra_4_24.html` | `https://cal.huc.edu/showachapter.php?fullcoord=31000424` | reduced Biblical Aramaic context around Ezra 4:24 with source info, preceding/target lines, comments, and lexical-token anchors |
| `lexicon_citation_context_tgj_ez_31_6.html` | `https://cal.huc.edu/showachapter.php?fullcoord=5101431061` | reduced Targum context around TgJ Ez31:6 with variable-length source identity and ignored navigation links |
| `lexicon_citation_context_bt_git_48a50.html` | `https://cal.huc.edu/showachapter.php?fullcoord=7101801048150` (2026-09-24) | Babylonian Talmud context whose tokens use `bablex.php`, with manuscript-style line labels, separator rows, and a red comment-linked target row |
| `lexicon_citation_context_not_found.html` | `https://cal.huc.edu/showachapter.php?fullcoord=999999999999` | exact no-citations marker and selector-binding semantics for the explicit context follow-up |
| `not_found.html` | CAL lexicon surface | explicit no-match semantic page |
| `search_gloss_camel.html` | `POST https://cal.huc.edu/newsearchmngs.php` (`English=camel#`, `secondary=true`) | ordered lemma-link + gloss result shape |
| `search_gloss_empty.html` | `POST https://cal.huc.edu/newsearchmngs.php` (`English=qzxvjk#`, `secondary=true`) | exact current empty-gloss marker |
| `search_citations_camel.html` | `POST https://cal.huc.edu/searchcits.php` (`English=camel`) | repeated lemma/context/citation rows with Hebrew and Syriac source text |
| `search_citations_empty.html` | `POST https://cal.huc.edu/searchcits.php` (`English=qzxvjk`) | exact current empty-citation marker |
| `text_catalogue_root.html` | `https://cal.huc.edu/newtextmenu.html` | root category links plus a directly linked text |
| `text_catalogue_biblical.html` | `https://cal.huc.edu/showsubtexts.php?subtext=3` | explicit subtext/file navigation identifiers |
| `text_catalogue_mandaic_current.html` | `https://cal.huc.edu/show_Mandaic.php?R1=74` (2026-09-25) | current Mandaic catalogue: script toggle, grouped `cset=R` title rows with information links (6 of 20 texts), not-available notes |
| `text_search_tel_dan.html` | `POST https://cal.huc.edu/newsearchtxts.php` (`search=Tel Dan`) | topic-search text reference, label, and rendered description |
| `text_page_bt_az.html` | `https://cal.huc.edu/get_a_chapter.php?file=71026&page=0` | paginated text metadata, line/display coordinates, token links, comments, and next-page navigation |
| `text_page_bt_ber_p2_current.html` | `https://cal.huc.edu/get_a_chapter.php?file=71001&page=1` (2026-09-25) | current paginated page: both pagination markers share lines with previous/next/show-all links; first 2 of 45 rows |
| `text_page_bt_ber_last_current.html` | `https://cal.huc.edu/get_a_chapter.php?file=71001&page=49` (2026-09-25) | current last page: markers with previous/show-all links only; first 2 of 16 rows |
| `text_page_tel_dan.html` | `https://cal.huc.edu/get_a_chapter.php?file=13250&page=0` | valid short text with line/token coordinates but no page-count marker |
| `text_page_missing.html` | `https://cal.huc.edu/get_a_chapter.php?file=13250&sub=999` | current explicit `NO LINES FOR ... ARE CURRENTLY STORED` missing-text marker |
| `text_page_samaritan_56000_112_current.html` | `https://cal.huc.edu/get_a_chapter.php?file=56000&sub=112&page=0` (2026-09-25) | current subdivided page: file-info `coord` is the file id followed by the submitted `sub`; first 2 of 20 rows |
| `text_page_ginza_right_001_current.html` | `https://cal.huc.edu/get_a_chapter.php?cset=M&file=74410&sub=001` (2026-09-25) | current Mandaic subdivided page: file-info `coord` carries the private `sub` page selector; first 2 of 24 rows plus the next-page link |
| `text_page_samaritan_56000_prefix_11_current.html` | `https://cal.huc.edu/get_a_chapter.php?file=56000&sub=11&page=0` (2026-09-25) | CAL's prefix match of `sub=11`: one row each from subtexts 112 and 113 of 197 rows across 112–119, under the chapter-12 label |
| `text_page_blank_word0_60424_current.html` | exact blank row retained from `https://cal.huc.edu/get_a_chapter.php?file=60424&page=0` (2026-09-25), inside a clearly marked synthetic file-info shell | current Ephrem all-empty row: one empty `getlex.php` lexical slot at `word=0&hasvariant=0` |
| `text_page_empty_slots_mixed_60424_structural.html` | structural fixture based on the 2026-09-26 live recheck of `60424`; coordinate and empty-slot position are observed, rendered token text is explicitly synthetic | mixed current shape: rendered word 0 plus an empty word-1 lexical slot, used only to test slot semantics |
| `text_page_philemon_62057_current.html` | `https://cal.huc.edu/get_a_chapter.php?file=62057&page=0` (2026-09-25) | current table row whose coordinate cell carries CAL's "[ai]" Ask-AI link after the display coordinate; first 2 of 25 rows |
| `text_page_samaritan_raw_lt_current.html` | `https://cal.huc.edu/get_a_chapter.php?file=56000&sub=112&page=0` (2026-09-25) | rows Gen12:04–05; CAL renders the first token `<w)th` with a raw, unescaped `<` |
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
| `bibliography_empty.html` | bounded nonexistent queries against CAL bibliography result endpoints | earlier layout: explicit shared bibliography no-data marker |
| `bibliography_lemma_br_n_current.html` | `https://cal.huc.edu/getbiblemma.php?myauthor=br+N` (2026-09-24) | current layout: legacy `<TITLE>` plus three `<p>` records inside one result card; link lists shortened |
| `bibliography_author_sokoloff_current.html` | `https://cal.huc.edu/getbibauthor.php?myauthor=Sokoloff%2C+Michael` (2026-09-24) | current layout: two `<p>` records in CAL order, the first ending in CAL's empty placeholder link |
| `bibliography_empty_current.html` | `https://cal.huc.edu/getbiblemma.php?myauthor=qqqqzz+N` (2026-09-24) | current no-data marker alone inside the result card |
| `concordance_text_13250.html` | `https://cal.huc.edu/newconcord.php?text=13250&cset=S` | earlier table-row layout: one-text lemma-frequency rows whose link text was the CAL lemma key, glosses, and explicit KWIC links |
| `concordance_text_13250_label_current.html` | `https://cal.huc.edu/newconcord.php?text=13250&cset=S` (2026-09-24) | current BR rows whose link text is CAL's display label (`ˀb, ˀbˀ n.m.`) or, for proper nouns, the key |
| `kwic_texts_mlk.html` | `POST https://cal.huc.edu/showdialectKWIC.php` (`mlk N`, texts `12250 13250`, charset `R`) | multi-text result with one empty scope and ordered duplicate target coordinates |
| `kwic_texts_empty.html` | `POST https://cal.huc.edu/showdialectKWIC.php` (bounded no-hit text scope) | explicit per-text no-example marker plus `total examples: 0` |
| `kwic_dialects_aryk2_a.html` | `https://cal.huc.edu/dKWIC.php?lemma=%29ryk%232+A` | ordered CAL-owned dialect IDs/labels plus hidden lemma/POS contract |
| `kwic_dialect_aryk2_a_biblical.html` | `https://cal.huc.edu/show1dialectKWIC.php?lemma=%29ryk%232&pos=A&texts=3` | earlier table-row layout: one Biblical-Aramaic target hit with file/subtext/charset/coordinate and Hebrew context |
| `kwic_texts_mlk_br_current.html` | `POST https://cal.huc.edu/showdialectKWIC.php` (`mlk N`, texts `12250 13250`, charset `R`; 2026-09-24) | current BR-line hits under per-text `<b>NNNN:</b>` sections, one empty scope, a duplicated target coordinate distinguished only by the highlighted token; total reduced to retained hits |
| `kwic_dialect_aryk2_a_br_current.html` | `https://cal.huc.edu/show1dialectKWIC.php?lemma=%29ryk%232&pos=A&texts=3` (2026-09-24) | current single-form dialect page: BR-line Hebrew hit and one per-form summary |
| `kwic_dialect_nqh_n_forms_current.html` | `https://cal.huc.edu/show1dialectKWIC.php?lemma=n%29qh&pos=N&texts=6` (2026-09-24) | requested form with no examples, related form `nqh N` owning one Unicode Syriac (`cset=U`) hit, and a grand total |
| `kwic_dialect_nqh_n_zero_current.html` | `https://cal.huc.edu/show1dialectKWIC.php?lemma=n%29qh&pos=N&texts=51` (2026-09-24) | two per-form "No examples found" summaries and no total |
| `kwic_full_context_syr_romlaw_unicode.html` | `https://cal.huc.edu/get_a_kwicchapter.php?file=60301&sub=53&cset=U&target=603015323` (2026-09-24) | three Unicode Syriac full-context rows around a `U` KWIC target |
| `targum_parallel_gen_1_1.html` | `POST https://cal.huc.edu/showtargum.php` (`bookname=01`, `chapter=01`, `verse=01`, optional Peshitta/Samaritan requested) | MT plus ordered current CAL Targum/source readings, Hebrew/Aramaic/Syriac Unicode, source chapter links, optional Peshitta, and absent Samaritan output |
| `targum_parallel_not_found.html` | `POST https://cal.huc.edu/showtargum.php` (`bookname=01`, `chapter=01`, `verse=99`) | current explicit `error in coordinate` not-found semantics |
| `targum_concordance_klb.html` | `POST https://cal.huc.edu/showtargumKWIC.php` (`lemma=klb`, `pos=N`) | ordered Targum section/source counts, same-origin example links, and reported total 59 |
| `targum_concordance_zero.html` | bounded structurally valid no-hit Targum concordance query | complete all-zero source table plus `total examples: 0` |
| `targum_hebrew_lemmas_mem_onqelos.html` | `https://cal.huc.edu/Omtlemmas/memMTlemma.html` | Onqelos MT-Hebrew lemma chooser with ordered opaque `R1` IDs, vocalized labels, and displayed POS |
| `targum_hebrew_lemmas_mem_neofiti.html` | `https://cal.huc.edu/mtlemmas/memMTlemma.html` | Neofiti source-specific MT-Hebrew lemma chooser form/action semantics |
| `targum_reflex_onqelos_1751.html` | `POST https://cal.huc.edu/getOmtlemma.php` (`R1=1751`) | selected MT Hebrew lemma plus Onqelos CAL lemma correspondence, frequency, and example URL |
| `targum_reflex_neofiti_1751.html` | `POST https://cal.huc.edu/getNmtlemma.php` (`R1=1751`) | selected MT Hebrew lemma plus multiple ordered Neofiti CAL lemma correspondences |
| `targum_concordance_klb_current.html` | `POST https://cal.huc.edu/showtargumKWIC.php` (`lemma=klb`, `pos=N`; 2026-09-24) | current layout: title-only identifying heading, `<h3>` statement, `<td>` section row, `<div>`-wrapped cells, CAL's truncated `texts=… 5102` selector, and an in-table total adjusted to the four retained rows |
| `targum_reflex_onqelos_1751_current.html` | `POST https://cal.huc.edu/getOmtlemma.php` (`R1=1751`; 2026-09-24) | current `<h3>` source/result heading and `<td>` header row |
| `targum_reflex_invalid_id.html` | bounded invalid Onqelos selector probe (`R1=999999`) | current broad invalid-ID fallback with missing selected Hebrew lemma, which must fail closed |
| `syriac_category_metrical.html` | `https://cal.huc.edu/show_Syriac_categories.php?category=6` | dynamic Syriac category with ordered direct/group navigation and file-information links |
| `syriac_category_ot_peshitta.html` | `https://cal.huc.edu/ot_peshitta.html` | static OT Peshitta category using the same typed text-item contract |
| `syriac_missing_verbs.html` | `https://cal.huc.edu/display_missing_verbs.php` | CAL-curated verbs absent from *A Syriac Lexicon*, with canonical lemma links and notes |
| `syriac_peshitta_gen_1_1.html` | `POST https://cal.huc.edu/showpesh.php` (`bookname=01`, `chapter=01`, `verse=01`) | Gen 1:1 MT/Peshitta Unicode text and Peshitta chapter navigation |
| `syriac_peshitta_not_found.html` | bounded invalid-coordinate `showpesh.php` probe | current explicit `error in coord` not-found semantics |
| `external_citation_sources_syriac_current.html` | `https://cal.huc.edu/display.notext.abbrevs.php?dial1=6&dial=6` (2026-09-24) | current card layout: five of 702 rows in CAL order, including the `EbPar` and `JS` pairs that share an abbreviation across distinct works |
| `dictionary_collation_djba_100_current.html` | `POST https://cal.huc.edu/searchdicts.php` (`dict=B`, `page=100`, 2026-09-25) | current shorter heading label "Dictionary of Jewish Babylonian Aramaic"; both entries |
| `dictionary_collation_schulthess_100_current.html` | `POST https://cal.huc.edu/searchdicts.php` (`dict=S`, `page=100`, 2026-09-25) | current shorter heading label "Schulthess"; first 2 of 9 entries |

The reduced excerpts are maintained only as test contracts. Normal tests make zero CAL requests. The lexicon citation-context/search/text/token-analysis/concordance/bibliography/Targum/Syriac fixtures were produced from deliberately bounded form/result audits and contain only a few semantic rows, not complete result pages. If current CAL markup materially changes, update the fixture provenance and parser tests rather than silently accepting incomplete output.
