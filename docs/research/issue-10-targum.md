# Issue #10 research — bounded CAL Targum Studies surface

**Rechecked:** 2026-09-05

This note records the bounded live evidence used before implementing issue #10. Normal CI remains offline.

## Current research tasks

CAL's current Targum Studies surface supports four distinguishable researcher tasks:

1. request one biblical verse across MT and available targumic versions, optionally also Peshitta and Samaritan;
2. open one returned Targum source in CAL's existing full text browser;
3. obtain Targum-specific concordance counts for one CAL lemma and follow a selected source to examples;
4. study which CAL Aramaic lemmas translate a selected MT Hebrew lemma in Onqelos or Neofiti.

The second task already composes with the implemented general text tools because the parallel display links source labels directly to `get_a_chapter.php` CAL text pages. Issue #10 therefore should not add a duplicate single-Targum browser.

## Parallel verse comparison

The public form at `searching/targumsearch.html` currently submits:

```text
POST /showtargum.php
bookname=<two-digit CAL biblical-book value>
chapter=<chapter>
verse=<verse>
Peshitta=ON            # optional checkbox
Sam=ON                 # optional checkbox
```

The current book selector exposes these exact display-label/value pairs:

```text
Gen 01; Exod 02; Levit 03; Numb 04; Deut 05; Joshua 06; Judges 07;
1 Sam 08; 2 Sam 09; 1 Kings 10; 2 Kings 11; Isaiah 12; Jeremiah 13;
Ezekiel 14; Hosea 15; Joel 16; Amos 17; Obadiah 18; Jonah 19; Micah 20;
Nahum 21; Hab. 22; Zeph. 23; Haggai 24; Zechariah 25; Malachi 26;
Psalms 27; Job 28; Song of Songs 29; Ruth 30; Qoheleth 31;
Lamentations 32; Proverbs 33; 1 Chronicles 34; 2 Chronicles 35; Esther 36.
```

A bounded Gen 1:1 request with both optional checkboxes returned a page headed `MT and targums for Gen 1:1`. It preserved MT text and ordered source-labelled readings including current CAL labels such as `Onqelos:`, `Pseudo Jonathan:`, `Neofiti:`, `FTP Gn`, `FTV Gn`, and `Peshitta:`. Source names link to CAL text-browser pages where CAL has a browsable source. The page also exposes a separate optional display link for JLA Babylonian pointing; that rendering option is not required for a faithful first task-level MCP contract.

The Samaritan option is conditional on coverage; the representative page states that Samaritan targum J begins with Genesis 12 and is only for the Pentateuch. CAL-MCP must preserve absence rather than manufacture an empty Samaritan reading.

An invalid coordinate such as Gen 1:99 still returns HTTP 200 and the requested-looking heading, but the semantic page ends with CAL's explicit `error in coordinate` marker and contains no valid comparison readings. That is a requested-passage not-found state, not a successful empty comparison and not generic parser drift.

## Targum-specific concordance

The current form at `searching/targum_concordance.html` submits:

```text
POST /showtargumKWIC.php
lemma=<CAL lemma spelling without POS>
pos=<CAL POS/stem suffix>
```

A bounded `klb N` request returned `CAL: Targum KWIC counts for klb N` and an ordered table of named Targum/source groups plus occurrence counts. The current page groups sources under headings such as Torah, Former Prophets, and Writing Prophets and includes exact labels such as `Onqelos`, `Targum Pseudo-Jonathan`, `Targum Neofiti`, `Fragment Targums`, `GT (Genizah Frags, Pal.Tg.)`, `TNeof Marginalia`, `Targum Psalms`, `TgJob`, `TgEsth2 (Tg Sheni)`, and `TgProv`.

For `klb N`, CAL reported `total examples: 59`. Every named source row currently links to `show1dialectKWIC.php` with CAL-owned text IDs/charset values. Those private request parameters should not become MCP parameters; the resulting source label, count, and explicit CAL example URL are useful navigation metadata.

A nonexistent but structurally valid query (`zzzzzz N`) returns the same complete result table with every count equal to zero and `total examples: 0`. This is a successful empty concordance result. It must not be confused with changed markup or network/upstream failure.

## MT Hebrew lemma → Targumic lemma correspondences

`targumicpairsearch.htm` currently describes this task as studying the Aramaic lemmas used to translate MT Hebrew lemmas. It exposes usable selectors for `Neofiti` and `Onqelos`; `Pseudo-Jonathan` is explicitly labelled `(under development)` and is not currently an active selectable workflow.

The MT lemma chooser is letter-indexed. Current Onqelos pages use paths such as `Omtlemmas/memMTlemma.html` and post the selected opaque MT lemma identifier in field `R1` to `/getOmtlemma.php`. Neofiti uses the parallel `mtlemmas/...` pages and `/getNmtlemma.php`. The numeric IDs are CAL-owned selector identifiers and must be treated as opaque rather than decoded.

Representative chooser evidence for the letter `mem` included Hebrew Unicode labels such as `מַעֲקֶה n` with `R1=1751`. The chooser preserves Hebrew vocalization and displayed POS.

A bounded `R1=1751` request produced:

- Onqelos heading: `Onkelos correspondences to מַעֲקֶה`;
- one CAL lemma correspondence, `תיק #2 N`, frequency `2`;
- Neofiti heading: `Neofiti correspondences to מַעֲקֶה`;
- two CAL lemma correspondences, `גיפוף N` and `סייג N`, each frequency `1`.

Each correspondence links to a CAL examples page and the URL repeats the selected MT ID plus CAL lemma key.

A deliberately invalid MT ID (`999999`) exposed an upstream hazard: CAL returned a broad Onqelos frequency list headed only `Onkelos correspondences to` with no Hebrew lemma after `to`, rather than a clean no-result page. The adapter therefore must require a nonempty selected MT lemma in the result heading before accepting a correspondence page. Merely seeing well-formed CAL lemma rows is insufficient.

## Public-surface implications

The smallest faithful specialist surface is four operations:

```text
cal_targum_parallel(book, chapter, verse, include_peshitta=False, include_samaritan=False)
cal_targum_concordance(lemma_key)
cal_targum_hebrew_lemmas(initial, targum)
cal_targum_hebrew_reflexes(targum, mt_lemma_id)
```

- `book` should use CAL's exact current display label and be mapped internally to the current two-digit selector value. Private `bookname` must not leak into MCP.
- `lemma_key` should reuse the existing CAL lemma-key structural validation and split into CAL's private `lemma`/`pos` fields internally.
- `targum` is currently restricted to `onqelos` or `neofiti` for Hebrew-reflex research. Pseudo-Jonathan is not advertised as implemented while CAL marks the workflow under development.
- `initial` should be a bounded selector slug from CAL's current Hebrew-letter chooser (`alef` … `taw`, with separate `shin` and `sin`) and map internally to the selected source's current letter page.
- `mt_lemma_id` is an opaque positive decimal selector ID returned by `cal_targum_hebrew_lemmas`; callers should not infer it.

Every public operation performs exactly one CAL request. Choosing a Hebrew lemma and then retrieving reflexes remains two explicit caller actions. Following a Targum concordance source into example KWIC or a parallel-reading source into a full chapter also remains a separate explicit call.

## Result fidelity and drift rules

- Preserve CAL source/version labels and order rather than normalize them into locally invented canonical names.
- Preserve Unicode Hebrew, Aramaic, and Syriac text exactly as rendered after ordinary HTML text extraction.
- Preserve current CAL source/example URLs as absolute same-origin navigation metadata.
- Parallel comparison: explicit `error in coordinate` is a not-found passage; unknown nonempty markup is parser drift.
- Concordance: an all-zero complete table with `total examples: 0` is a valid empty result; missing table/heading/total semantics is parser drift.
- Hebrew chooser: preserve ordered opaque IDs, vocalized labels, and displayed POS. An expected chooser page with no options and no explicit empty semantics is drift.
- Hebrew reflexes: require a nonempty MT Hebrew lemma in the source-specific `correspondences to ...` heading and require correspondence links to be same-origin and semantically consistent with the submitted MT ID.

## Sources

- https://cal.huc.edu/searching/targumsearch.html
- https://cal.huc.edu/showtargum.php
- https://cal.huc.edu/searching/targum_concordance.html
- https://cal.huc.edu/showtargumKWIC.php
- https://cal.huc.edu/targumicpairsearch.htm
- https://cal.huc.edu/Olemmaselect.htm
- https://cal.huc.edu/Omtlemmas/memMTlemma.html
- https://cal.huc.edu/mtlemmas/memMTlemma.html
- https://cal.huc.edu/getOmtlemma.php
- https://cal.huc.edu/getNmtlemma.php
- four temporary branch-only bounded research runs described above

## Research load

Four temporary branch-only research runs made 15 bounded CAL requests total. They inspected four public entry pages, two representative comparison/concordance results, two MT-lemma chooser pages, valid Onqelos/Neofiti correspondence results, one deliberate invalid-MT-ID response, and final missing-coordinate/zero-concordance edge cases. No biblical book, Targum source, lemma alphabet, KWIC example set, text chapter, or corpus was traversed automatically. The temporary workflow is removed before test implementation.