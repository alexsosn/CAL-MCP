# Issue #83 research — CAL specialized text-route coverage

**Rechecked:** 2026-09-08

This note audits current **navigation route families**, not corpus contents. Live checks were limited to the public CAL search page, text-browser root, Targum/Syriac module landing pages, and one representative link for each distinct route family.

## Question

Mandaic exposed a defect in the assumption that CAL Text Browse is one uniform `showsubtexts.php?subtext=...` hierarchy. The research question for #83 is whether other current CAL navigation pages are similarly absent or misleadingly represented in CAL-MCP.

## Entry-point audit

### CAL search page

`https://cal.huc.edu/searching/CAL_search_page.html` currently exposes these dynamic research workflows:

- lexicon browse;
- English gloss search;
- English words in citations;
- citations from texts outside the online database;
- Text Browse;
- text/topic search;
- Targum Studies;
- Syriac Studies;
- dictionary spelling collation;
- single-text concordance;
- multi-text KWIC.

The existing capability matrix already maps all of these to CAL-MCP operations or an explicit composed workflow. The route problem investigated here is concentrated in **text/source discovery**, where the current browser fans out into several different CAL page families.

## Text Browse route families

Current root: `https://cal.huc.edu/newtextmenu.html`.

The current root contains four materially different navigation shapes.

| Route family | Representative current CAL link | CAL-MCP status before #83 | Finding |
| --- | --- | --- | --- |
| ordinary category | Biblical Aramaic -> `showsubtexts.php?subtext=3` | implemented by `cal_text_catalogue(category_id=...)` | supported |
| ordinary direct text | Tel Dan -> `get_a_chapter.php?cset=H&file=13250` | implemented by `cal_text_page(file_id=...)` and parsed by root catalogue | supported; `cset=H` is also present on already-working ordinary links and is therefore not by itself evidence of a routing defect |
| dedicated Targum collection | Targums Onkelos/Jonathan -> `targum_onkelos_jonathan.html` | silently omitted by generic root parser | **discovery gap** |
| dedicated Syriac collection | Syriac -> `AvailSyr.html` | generic root parser omits it, but dedicated `cal_syriac_texts` exists | **cross-collection discoverability gap**, not a missing Syriac parser |
| dedicated Mandaic collection | Mandaic -> `show_Mandaic.php?R1=74` | generic root parser omits it | **discovery/catalogue gap**, tracked by #78; page-routing follow-up #97 |

Representative ordinary categories were also rechecked across the current sections of the menu (Old/Official, Middle, Palestinian, Jewish Babylonian, and Late Jewish Literary); they continue to use `showsubtexts.php?subtext=...`. No exhaustive per-link traversal was performed.

### Why the current parser misses the specialized branches

`parse_text_catalogue_page()` currently recognizes:

- categories only from links whose path is `showsubtexts.php`;
- texts only from links whose path is `get_a_chapter.php`.

Therefore a valid root page can parse successfully while dropping every link to `targum_onkelos_jonathan.html`, `AvailSyr.html`, and `show_Mandaic.php`. This is a fail-open completeness problem: seeing some ordinary categories/texts is enough for the parser to return success, even when semantically meaningful root branches were ignored.

## Targum route audit

Current module: `https://cal.huc.edu/targumstartpage.html`.

The landing page currently exposes:

1. parallel display of targumic versions of a biblical passage;
2. **Browse a single targum — with lexical analysis**;
3. Targum concordance;
4. MT Hebrew lemma -> Targumic reflex study;
5. static information about CAL Targum texts.

Issue #10 implemented 1, 3, and 4 directly. Its research note treated 2 as composed through general text tools because a parallel-result source link can lead to a text page. That statement is too broad for **source discovery**.

The dedicated browse page `https://cal.huc.edu/targumbrowse.html` groups current sources under Torah, Prophets, and Writings. It includes Onkelos/Jonathan, Palestinian Pentateuchal Targums, Toseftot, and Targums to the Writings. Most Palestinian/later material can be reached through ordinary Text Browse categories such as `54` and `8`, but the current Text Browse root sends Onkelos/Jonathan through `targum_onkelos_jonathan.html`, which the generic parser drops.

The dedicated Onkelos/Jonathan page currently contains:

- subdivided sources such as `51001 TgO Gn` -> `showsubtexts.php?cset=H&subtext=51001`;
- a direct source `51400 MegTan` -> `get_a_chapter.php?cset=H&file=51400`.

`cset=H` appears on already-working ordinary text links such as Tel Dan as well, so this audit does **not** file a routing defect merely because `cset=H` is absent from CAL-MCP requests. Whether a given selector is semantically required must be proven by a focused route test before changing request construction.

### Targum conclusion

There is a confirmed discovery defect: a user starting from CAL-MCP cannot faithfully reproduce CAL's current Targum source-browse entry path because the Onkelos/Jonathan collection disappears at generic Text Browse root discovery.

A focused catalogue-route issue is warranted for the Onkelos/Jonathan collection after collection discovery exposes it. The dedicated `targumbrowse.html` grouping itself should not trigger recursive source fetching.

## Syriac route audit

Current module: `https://cal.huc.edu/SyrStudies.html`.

Its current dynamic tasks are:

1. search/browse available Syriac texts by categories -> `AvailSyr.html`;
2. review Syriac citations from texts outside the online CAL database;
3. review CAL headwords occurring in Syriac but absent from *A Syriac Lexicon*;
4. compare MT with Peshitta.

Existing CAL-MCP coverage:

- `cal_syriac_texts` implements the current top-level `AvailSyr.html` category surface;
- generic external-citation tools cover task 2 with explicit dialect/source discovery;
- `cal_syriac_missing_words` covers task 3;
- `cal_syriac_peshitta_parallel` covers task 4.

`src/cal_mcp/syriac.py` currently has explicit configs for the 20 linked `AvailSyr.html` categories (OT Peshitta, Old Syriac Gospels, NT Peshitta, Apocryphal/Pseudepigraphal, Commentaries, Metrical Homilies/Hymns, Dispute Poems, Religion, Archival, Canonical, Documents, Syro-Roman Law Book, Canon Law, Magic, Science/Philosophy, History, Novels/Histories, Martyrologies, Various, Inscriptions).

### Syriac conclusion

No missing Syriac dynamic route family was found in this bounded recheck. The defect is that the generic text root silently drops the Syriac branch instead of telling a caller that this branch is served by the dedicated Syriac tool family.

## Mandaic route audit

Current route: `https://cal.huc.edu/show_Mandaic.php?R1=74`.

The dedicated page remains a genuine specialized collection. Its root discoverability/catalogue problem is #78. Current collection `74` also mixes subdivided and direct text shapes; the over-generalized page-routing correction is #97. Those issues remain separate because their request semantics differ from collection discovery.

## Other current specialized/alternate pages

Search indexing exposes `newshow_browsedialects.php?R1=...` aggregate dialect pages, including `R1=51` for Jewish Literary Aramaic. They are not current first-hop links from `newtextmenu.html`, and this issue does not turn legacy/alternate indexed URLs into a second public contract. The authoritative scope is current user-facing navigation starting from CAL's public entry pages.

Static reference pages (for example the Targum text-information page) are documentation/reference content, not dynamic research operations, and remain outside the MCP operation count unless a future issue demonstrates a task that needs structured access.

## Coverage classification after research

| Current user-facing route family | Classification | Work |
| --- | --- | --- |
| ordinary Text Browse category/direct text | directly implemented | preserve behavior |
| Targum parallel/concordance/Hebrew-reflex workflows | directly implemented | preserve |
| Targum single-source discovery | implemented only partially/composition not discoverable | fix collection discovery in #83; focused Onkelos/Jonathan catalogue route follow-up |
| Syriac Studies dynamic tasks | directly implemented | expose Syriac as specialized collection in cross-collection discovery |
| Mandaic collection | inaccessible/incompletely routed | expose in #83; #78/#97 own actual catalogue/page fixes |
| static reference/info pages | intentionally not operationalized | document only |

## Design implication

The generic text catalogue cannot truthfully model every root link as a numeric `category_id`. Specialized routes must be represented explicitly rather than guessed into `showsubtexts.php` requests.

The smallest correction is a bounded **collection-discovery operation** sourced from the current `newtextmenu.html` root. It should recognize the current dedicated collection links and return stable adapter-level collection IDs plus the supported CAL-MCP follow-up operation. It must not fetch child pages automatically.

The initial specialized collections proven by current navigation are:

- `targum-onkelos-jonathan` -> focused generic-text catalogue route (follow-up issue);
- `syriac` -> existing `cal_syriac_texts` family;
- `mandaic` -> generic-text catalogue/page work tracked by #78/#97.

Ordinary Text Browse remains `cal_text_catalogue` and is not reimplemented.

## Test implications

Deterministic fixtures need only minimal fragments containing:

- one ordinary `showsubtexts.php` link;
- one ordinary `get_a_chapter.php` link;
- the three current dedicated root links;
- an unknown dedicated-looking CAL navigation link to prove fail-closed drift handling where completeness would otherwise be silently overstated.

No full live page fixture is required.

## Sources

Rechecked 2026-09-08:

- https://cal.huc.edu/searching/CAL_search_page.html
- https://cal.huc.edu/newtextmenu.html
- https://cal.huc.edu/targumstartpage.html
- https://cal.huc.edu/targumbrowse.html
- https://cal.huc.edu/targum_onkelos_jonathan.html
- https://cal.huc.edu/SyrStudies.html
- https://cal.huc.edu/AvailSyr.html
- https://cal.huc.edu/show_Mandaic.php?R1=74
- representative `showsubtexts.php?subtext=3`, `?subtext=54`, `?subtext=71`, `?subtext=8`
- representative direct `get_a_chapter.php?cset=H&file=13250`
- representative Targum child `showsubtexts.php?cset=H&subtext=51001`
- representative Targum direct `get_a_chapter.php?cset=H&file=51400`
- CAL manual dialect-code appendix (for interpretation only; current navigation remains authority)

## Research load

The audit inspected navigation pages and a small fixed set of representative links. It did not enumerate texts, chapters, Syriac categories recursively, Targum sources recursively, Mandaic texts recursively, dialect contents, or lexicon rows. Normal tests remain offline.
