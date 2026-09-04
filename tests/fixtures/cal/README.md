# CAL parser fixtures

These fixtures are deliberately reduced semantic excerpts, not archived CAL pages. They retain only the minimum current markup/text relationships needed by offline parser tests.

Capture/recheck date: **2026-09-04**.

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

The reduced excerpts are maintained only as test contracts. Normal tests make zero CAL requests. The search/text/token-analysis fixtures were produced from deliberately bounded form/result audits and contain only a few semantic rows, not complete result pages. If current CAL markup materially changes, update the fixture provenance and parser tests rather than silently accepting incomplete output.
