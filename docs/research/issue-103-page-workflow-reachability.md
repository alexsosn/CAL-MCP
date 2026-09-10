# Issue #103 research — current CAL page/workflow reachability matrix

**Rechecked:** 2026-09-10  
**Repository baseline:** `1e925b4ba016df7648228d1c8d0d81bfbfcaab89`  
**Issue:** #103

This audit asks a stricter question than the task-level capability matrix: can a researcher actually move through CAL's **current user-facing dynamic pages and meaningful result follow-ups** using explicit CAL-MCP operations and returned typed selectors, without knowing private PHP/form details or executing arbitrary URLs?

The audit is route-family based. It uses current navigation pages and a few representative links only. It does not enumerate corpora, chapters, lemmas, bibliography records, dialect contents, or result sets.

## Classification

1. **Directly reachable** — CAL-MCP invokes the same task faithfully.
2. **Faithfully composed and discoverable** — an existing result gives a selector that another existing tool consumes explicitly.
3. **Implemented but undiscoverable / follow-up gap** — related parsing/tooling exists, but the user-facing route or next selector cannot be consumed through the MCP.
4. **Incorrectly routed or parsed** — a CAL-MCP operation exists but current route/page semantics are wrong.
5. **Missing operation** — CAL exposes a genuine dynamic research task with no faithful MCP operation.
6. **Reference / presentation / deliberately out of scope** — no separate bounded scholarly operation should be exposed, with the reason stated.

## Current top-level navigation

The current CAL search page exposes lexicon browsing, English gloss and citation-text search, citations from texts not in the online database, Text Browse, topic search, Targum Studies, Syriac Studies, dictionary collation, one-text concordance, and multi-text KWIC. The current bibliography module separately exposes author, text/subject, lexical-item, and recent-record workflows.

Current Text Browse still has three root route families that differ from ordinary `showsubtexts.php?subtext=...` navigation: Onkelos/Jonathan, Syriac, and Mandaic. All three are now represented by CAL-MCP after #101/#78/#97/#125.

## Reachability matrix

| Current CAL workflow/page family | Representative current route | CAL-MCP path | Class | Finding / child work |
| --- | --- | --- | --- | --- |
| Exact/root/headword/full-form lexicon lookup | bounded browser selection -> `oneentry.php` | `cal_lexicon_lookup` | 1 | Implemented; exact ambiguity remains explicit. |
| **Lexicon prefix discovery** | `searching/fullbrowser.html`, documented 2–3-consonant prefix / one-letter jump | none as a public browse operation | **5** | Exact lookup internally uses the browser but filters to exact/root/full-form matches; it does not expose all prefix candidates. **#112**. |
| English primary/all-gloss search | `searching/englishnew.html` -> current gloss results | `cal_gloss_search` | 1 | Implemented. |
| Search by Specialized Field | field links under `englishnew.html` | `cal_gloss_field` | 1 | Former discoverability gap **#107**, now implemented with readable selectors. |
| English combinations inside citations | citation-text form -> result page | `cal_citation_text_search` | 1 | Implemented. |
| Citations from texts not online | dialect -> source -> citations | `cal_external_citation_dialects` -> `cal_external_citation_sources` -> `cal_external_citations` | 2 | Returned dialect/source selectors are explicit follow-ups. |
| Text Browse ordinary categories | `newtextmenu.html` -> `showsubtexts.php?subtext=...` | `cal_text_catalogue` | 1 | One level per explicit request. |
| Text Browse direct texts | root/category -> `get_a_chapter.php?file=...` | `cal_text_catalogue` -> `cal_text_page` | 2 | Returned file/subtext IDs are consumable. |
| Onkelos/Jonathan dedicated root branch | `targum_onkelos_jonathan.html` | root `cal_text_catalogue()` -> category `51` -> `cal_text_catalogue(category_id="51")` | 2 | Former gap **#101**, now discoverable; no `cset=H` invention required. |
| Mandaic dedicated root branch | `show_Mandaic.php?R1=74` | root `cal_text_catalogue()` -> category `74` -> explicit catalogue/page operations | 2 | Former gaps **#78/#97**, now discoverable and correctly routed. |
| Syriac dedicated root branch | `AvailSyr.html` | root `cal_text_catalogue()` -> `specialized_collections[syriac]` -> `cal_syriac_texts(category=...)` | 2 | Former #83/#125 discoverability gap is now represented without a fake decimal CAL category ID or prefetch. |
| Text/topic search | `searching/searchtopic.html` -> current results | `cal_text_search` | 1 | Implemented; specialized Mandaic search results are supported. |
| Text information | `get_file_info.php?coord=<file/subtext>` | `cal_text_information` | 1 | Former gap **#106**, now implemented. |
| Text page / bounded pagination | `get_a_chapter.php` | `cal_text_page` | 1 | One bounded page; next/previous page numbers are returned for explicit follow-up. |
| Token lexical analysis | `bablex.php` / `getlex.php` from a text token | `cal_text_page` -> `cal_token_analysis` | 2 | Page output exposes coordinate + word index consumed by the token tool. |
| **Line comments / translations** | `comment.php?coord=<machine coordinate>` from red coordinate links | `TextLine.comment_url` only | **3/5** | Current text page still advertises this workflow; no typed consumer. **#108**. |
| CAL `show all` text view | `get_a_chapter.php` presentation link that removes page bounding | deliberately absent | 6 | Deliberately not exposed: it defeats the bounded-page/request-size policy. Explicit page navigation is the supported alternative. |
| Root-catalogue exhaustiveness cue | shallow `newtextmenu.html` result | `cal_text_catalogue()` | usability | Not a route gap: one-level semantics are documented, but **#77** tracks stronger machine-readable clarity. |
| Basic concordance of one text | current basic concordance form/result | `cal_text_concordance` | 1 | Implemented. |
| Multi-text KWIC | current advanced/KWIC form/result | `cal_kwic_texts` | 1 | Implemented for bounded explicit text IDs. |
| Dialect KWIC discovery/follow-up | current dialect chooser/results | `cal_kwic_dialects` -> `cal_kwic_dialect` | 2 | Dialect IDs are read from CAL and then consumed explicitly. |
| **KWIC full-context view** | hit link `get_a_kwicchapter.php?...` | `KwicHit.full_context_url` only | **3/5** | Parent KWIC works, but CAL's target-centered full context is not MCP-followable. **#113**. |
| Dictionary spelling collation | `searchdicts.html` -> one dictionary/page result | `cal_dictionary_collation` | 1 | Implemented for all current displayed dictionary sources and documented page syntax. |
| Dictionary result -> lexicon entry | `oneentry.php?lemma=...` in a collation row | returned canonical lemma key -> `cal_lexicon_lookup` | 2 | The row preserves both display spelling and target CAL lemma identity. |
| Bibliography by author | author prefix -> exact author | `cal_bibliography_authors` -> `cal_bibliography_author` | 2 | Implemented and discoverable. |
| Bibliography by text/subject | bibliography keyword route | `cal_bibliography_keyword` | 1 | Implemented exact CAL tag query. |
| Bibliography by lexical item | `getbiblemma.php?...` family | `cal_bibliography_lemma` | 1 | Implemented exact CAL lemma-key query; also provides the typed follow-up for a lexicon entry's Full Bibliography task. |
| **Five most recent years bibliography snapshot** | `bibliography/index.html` -> `getrecentbib.php` | none | **5** | Existing **#39**. Research/plan exist; implementation is explicitly blocked by the frozen v0.1 contract until #15 publishes or the freeze changes. |
| Bibliography addenda/front matter/archive files | static HTML/PDF links | none | 6 | Reference/archive material, not a task-level dynamic operation. |
| Targum parallel biblical passage | Targum module passage display | `cal_targum_parallel` | 1 | Implemented. |
| Targum single-source browse | `targumbrowse.html` -> ordinary source pages | root/category `cal_text_catalogue` -> `cal_text_page` | 2 | Rechecked beyond Onkelos: Neofiti/Fragment Targums are reachable under root category `54`; Pseudo-Jonathan and Targum Psalms/Job/Proverbs under root category `8`; Onkelos/Jonathan under category `51`. The dedicated page is an alternate navigation view, not a separate unreachable source family. |
| Targum concordance counts | Targum concordance result | `cal_targum_concordance` | 1 | Implemented. |
| **Targum concordance examples** | `show1dialectKWIC.php?...` | `example_url` metadata only | **3/5** | Supporting examples cannot be followed through MCP. **#109**. |
| Hebrew lemma chooser -> Targumic reflexes | chooser -> source-specific result | `cal_targum_hebrew_lemmas` -> `cal_targum_hebrew_reflexes` | 2 | Returned opaque CAL MT identifiers are consumed explicitly. |
| **Targum reflex examples** | `getOMT.php` / `getNMT.php` example links | `example_url` metadata only | **3/5** | Same evidence/follow-up gap tracked in **#109**; focused research decides shared vs split implementation. |
| Syriac top-level text categories | `AvailSyr.html` + category routes | root specialized handoff -> `cal_syriac_texts` | 2 | Twenty current supported category selectors are exposed from the same local config used by the service. |
| Syriac grouped category items | `showsubtexts.php?keyword=<id>` | `cal_syriac_texts` -> `cal_syriac_group` | 2 | Former gap **#105**, now implemented. |
| Syriac citations from non-online texts | Syriac module citation link | generic external-citation workflow | 2 | Faithful composition; no duplicate Syriac-only tool. |
| Syriac missing-from-*A Syriac Lexicon* lists | dedicated missing-word pages | `cal_syriac_missing_words` | 1 | Implemented. |
| MT/Peshitta comparison | Syriac module comparison page | `cal_syriac_peshitta_parallel` | 1 | Implemented. |
| Lexicon entry derivatives/related entries | linked `oneentry.php` rows | returned derivative label/key -> explicit `cal_lexicon_lookup` | 2 | Same typed lexicon operation; no automatic derivative traversal. |
| Lexicon entry Complete KWIC | `dKWIC.php?lemma=...` | canonical entry lemma -> `cal_kwic_dialects` -> `cal_kwic_dialect` | 2 | The task is available as explicit dialect selection rather than arbitrary URL following. |
| Lexicon entry Full Bibliography | `getbiblemma.php?myauthor=<lemma>` | canonical entry lemma -> `cal_bibliography_lemma` | 2 | Explicit composition. |
| **Lexicon linked citation full context** | citation links `showachapter.php?fullcoord=<coordinate>` | citation URL preserved; no typed consumer | **3/5** | Newly confirmed current follow-up gap **#127**. Research must determine overlap with #113 before implementation. |
| CAL help/fonts/about/module prose/classic-display links | presentation/reference pages | none | 6 | No distinct scholarly data operation; classic display is an alternate rendering of the same lexicon entry. |

## Focused live checks added on 2026-09-10

### Targum single-source reachability

The current dedicated Targum browser was checked against the generic Text Browse hierarchy rather than assumed composable:

- Pseudo-Jonathan points to `showsubtexts.php?subtext=81001`; the same TgPsJon family is present under root category `8` (Late Jewish Literary).
- Neofiti points to `showsubtexts.php?subtext=54001`; Neofiti and Fragment Targums are present under root category `54` (Yerushalmi Targum).
- Targum Psalms, Job, Proverbs and other Writings are present under root category `8`.
- Onkelos/Jonathan are the exceptional dedicated root branch already corrected by #101.

This is enough to establish route-family reachability without enumerating every Targum source or chapter.

### Lexicon result follow-ups

A current `mlkw N` entry still exposes:

- Complete KWIC;
- Full Bibliography;
- related/derivative lexicon entries;
- linked citation references.

The first three have typed CAL-MCP paths using the returned canonical lemma identity. The linked citations use the distinct `showachapter.php?fullcoord=...` family. Repository search found no consumer for that route, so #127 was filed rather than treating the preserved citation URL as supported navigation.

### Text comments / translations

A current text page for file `71026` still tells users to click a red coordinate for comments and/or translations and renders `comment.php?coord=...` links. `cal_text_page` preserves such links but does not consume them; #108 remains current.

### Dictionary collation

The current dictionary-collation page still exposes the 15 dictionary sources represented by `cal_dictionary_collation`, and still documents decimal plus volume-qualified page syntax. No additional current collation route family was found.

### Bibliography

The current bibliography landing still exposes exactly the three targeted search families implemented by CAL-MCP plus the separate recent-five-years snapshot tracked by #39. Static addenda/front-matter links remain reference material.

## Current class 3/4/5 work

Open focused route gaps after today's reclassification:

- **#39** — recent-five-years bibliography snapshot; class 5, intentionally blocked by #15 / v0.1 freeze.
- **#108** — line comments/translations; class 3/5.
- **#109** — Targum concordance/reflex supporting examples; class 3/5.
- **#112** — lexicon prefix browsing; class 5.
- **#113** — KWIC full-context pages; class 3/5.
- **#127** — lexicon citation full-context pages; class 3/5, newly filed by this audit.

Resolved route gaps that the old 2026-09-08 matrix must no longer present as open:

- #78 Mandaic catalogue discovery;
- #97 Mandaic mixed direct/subdivided page routing;
- #101 Onkelos/Jonathan catalogue discovery;
- #105 grouped Syriac follow-up;
- #106 text-information metadata;
- #107 specialized gloss fields;
- #125 Syriac root discovery.

Cross-cutting or ergonomic tickets are not substitutes for route fixes:

- #77 shallow root-catalogue clarity;
- #82 bounded interlinear convenience;
- #84 typed public error payloads.

## Specialized text-route umbrella (#83)

The specific specialized-root question that motivated #83 is now resolved:

- Onkelos/Jonathan: category `51` dedicated catalogue path;
- Mandaic: category `74` dedicated catalogue plus corrected mixed page routing;
- Syriac: operation-aware root specialized reference pointing to the existing `cal_syriac_texts` selector vocabulary;
- ordinary root categories remain normal `showsubtexts.php` navigation.

The recheck of Targum's alternate single-source browser did not reveal another specialized source family absent from the generic hierarchy. Therefore #83 can be closed once this updated matrix/documentation PR is reviewed and merged; the remaining open issues above are distinct result-follow-up or non-text-root operations.

## Capability-document implications

The public capability matrix should remain truthful at both levels:

- keep implemented rows for exact lexicon lookup, ordinary/specialized gloss search, text discovery, bibliography targeted search, dictionary collation, Targum parent operations, Syriac operations, and concordance/KWIC;
- add an explicit current-gaps section so users do not infer that **every link/follow-up on those pages** is MCP-followable;
- distinguish lexicon exact lookup from the missing prefix-browse task (#112);
- distinguish implemented KWIC parent results from unfollowable target-centered full context (#113);
- distinguish Targum count/reflex results from their supporting example pages (#109);
- expose text line comments/translations (#108), lexicon citation context (#127), and the recent bibliography snapshot (#39) as known gaps rather than silent omissions;
- retain the deliberate boundedness decision against CAL's `show all` text view.

## No new production behavior in #103

Issue #103 is research/decomposition and capability-documentation work. Child route behavior remains independently reviewable in its focused tickets. This branch must not add parsers, tools, request routes, or public schemas.

## CAL load impact

Low and bounded. The update used current navigation/index pages and one or a few representative links for each uncertain route family. It did not enumerate all Targum sources, text chapters, lexicon candidates, bibliography records, Syriac groups, KWIC hits, or corpora.