# Issue #11 research — current CAL Syriac Studies module

**Research date:** 2026-09-05

This note records the current public CAL Syriac Studies surface before implementation. It is evidence for issue #11, not a stability promise for CAL's undocumented HTML endpoints.

## Scope and method

The audit started from CAL's public Syriac Studies page and followed only the links needed to identify current research operations and representative result shapes. Two temporary branch-only GitHub Actions probes then made **eight bounded CAL requests total** (four requests per run, 15-second timeout, at most 300 KB read per response). The temporary workflow was deleted immediately after the evidence was captured. Normal CI remains offline and fixture-driven.

No corpus crawl, alphabet walk, category expansion beyond one representative category, next/previous verse traversal, lexicon-entry follow-up, or citation-source traversal was performed.

## Current public module inventory

`SyrStudies.html` currently exposes four research entry points:

1. **Search available texts by categories** → `AvailSyr.html`.
2. **Review all the Syriac citations from texts not in the CAL database** → the external/non-online-text citation family.
3. **Review the CAL headwords that occur in Syriac but are not listed in A Syriac Lexicon** → `NotInSL.html` and nine curated lists.
4. **Compare the MT with the Peshitta** → `searching/peshsearch.html`.

The smallest faithful issue-#11 surface is therefore three specialist operations: Syriac-category text discovery, CAL's curated "missing from A Syriac Lexicon" lists, and MT/Peshitta verse comparison. The second entry point is the same capability family already tracked by issue #13 and should not be duplicated under a Syriac-specific wrapper.

Sources:

- https://cal.huc.edu/SyrStudies.html
- https://cal.huc.edu/AvailSyr.html
- https://cal.huc.edu/NotInSL.html
- https://cal.huc.edu/searching/peshsearch.html

## MT/Peshitta comparison contract

The current form at `searching/peshsearch.html` submits **POST** to `/showpesh.php` with private fields `bookname`, `chapter`, and `verse`. The book selector has the same 36 biblical books used by CAL's Targum comparison surface, in CAL's current display order and with CAL's current numeric values.

A bounded Gen 1:1 request (`bookname=01`, `chapter=01`, `verse=01`) returned:

- semantic heading `MT and Peshitta for Gen 1:1`;
- MT text rendered in a Hebrew-script span;
- one rendered `Peshitta:` source label/link;
- Syriac text rendered in a Syriac-script span;
- the Peshitta source link targeting CAL's ordinary text browser, currently `get_a_chapter.php?file=62001&sub=01&cset=U`.

A bounded Gen 1:99 request returned HTTP 200 with the matching heading and CAL's explicit `error in coord` marker, plus a previous-verse navigation link. That is a recognizable not-found state; CAL-MCP must not follow the navigation link automatically.

The result page also contains inline `<style>` elements. Parser semantics therefore must ignore `style` and `script` subtrees before collecting headings/markers/content, following the hardening already required by the lexicon and Targum parsers.

**Implication:** one public comparison call should make exactly one POST, require an exact requested-reference heading, preserve MT and Syriac Unicode text, preserve the CAL-owned `Peshitta:` label/link, treat the explicit coordinate marker as typed not-found only when no valid comparison data are present, and fail closed on contradictory or incomplete markup. No previous/next verse traversal is part of the operation.

## Syriac text categories

`AvailSyr.html` currently exposes four Bible-oriented static category pages and sixteen dynamic categories:

- `ot-peshitta` — OT Peshiṭta
- `old-syriac-gospels` — Old Syriac Gospels
- `nt-peshitta` — NT Peshiṭta
- `apocryphal-pseudepigraphal` — Apocryphal/Pseudepigraphal Texts
- `commentaries`
- `metrical-homilies-hymns`
- `dispute-poems`
- `religion`
- `archival`
- `canonical`
- `documents`
- `syro-roman-law-book`
- `canon-law`
- `magic`
- `science-philosophy`
- `history`
- `novels-histories`
- `martyrologies`
- `various`
- `inscriptions`

A review-stage bounded recheck on 2026-09-05 confirmed the exact current static headings `OT Peshiṭta`, `NT Peshiṭta`, and `Apocryphal/Pseudepigraphal Texts`; the reduced fixtures and parser contract use those upstream spellings.

The dynamic categories map to CAL's current numeric category values 5–20. A bounded check of category 6 (`Metrical Homilies and Hymns`) showed two navigation shapes in the same ordered result list:

- direct text pages such as `/get_a_chapter.php?file=60424&cset=S`;
- grouped/subtext navigation such as `/showsubtexts.php?keyword=60420`.

Rows also expose `/get_file_info.php?coord=...` information links. These identifiers and URLs should be preserved, not decoded into a locally invented corpus taxonomy. Grouped navigation must not be followed automatically; a single category operation remains one CAL request.

The Bible-oriented category pages likewise lead to CAL text-browser material. Existing `cal_text_page` remains the specialist's explicit follow-up for direct text identifiers rather than issue #11 introducing another text reader.

**Implication:** the public result needs an ordered category-item model capable of representing both direct-text and grouped-navigation entries, preserving CAL's rendered label, upstream identifier, navigation kind/URL, and optional information URL. A public category slug is preferable to leaking CAL's static filenames or numeric `category` parameter.

## CAL-curated headwords absent from *A Syriac Lexicon*

`NotInSL.html` currently describes more than 4,100 Syriac words in CAL that are not listed in the Brockelmann/Sokoloff *A Syriac Lexicon* and exposes nine explicit lists:

- `adjectives`
- `adverbs`
- `miscellaneous`
- `nomina-agentis`
- `abstracts`
- `verbal-nouns`
- `verbs`
- `masculine-nouns`
- `feminine-nouns`

The corresponding current CAL pages are, respectively, `display_missing_adj.php`, `display_missingSL.php`, `display_missing_misc.php`, `display_missing_nomag.php`, `display_missingU.php`, `display_missing_vn.php`, `display_missing_verbs.php`, `display_missing.mascnouns.php`, and `display_missing.femnouns.php`.

A bounded inspection of `display_missing_verbs.php` showed a semantic introduction stating that the listed verbs are not found in *A Syriac Lexicon* but have citations in CAL, followed by ordered linked CAL headwords and short rendered notes/glosses. The links lead to CAL full lexicon entries. The adapter should preserve those links and rendered text but must not fetch the entries automatically or infer a stronger lexical equivalence from CAL's curated list membership.

This CAL research surface is about CAL's comparison against *A Syriac Lexicon*; it is **not a SEDRA lookup**. CAL-MCP must keep CAL provenance and the upstream dictionary attribution explicit.

**Implication:** one public missing-word call should map a stable descriptive category slug to exactly one current CAL list page, return ordered CAL-owned entries with lemma key/rendered label/note/entry URL where exposed, and perform no follow-up lexicon requests. The shared HTTP response-size bound is the hard load ceiling; no invented pagination is exposed because none was observed in these pages.

## External citations are issue #13, not a duplicate Syriac tool

The Syriac Studies page links a `dial=6` view listing citations from texts not present in CAL's online text database. A bounded public-page inspection showed this is the same external/non-online-text citation capability family already represented by issue #13, merely entered with a Syriac filter.

Issue #11 therefore should document the composition boundary rather than add another endpoint-shaped tool. Issue #13 remains responsible for the general typed model and bounded search/lookup semantics; its eventual public contract can include CAL's dialect/source distinctions where upstream exposes them.

## Existing general tools already cover other Syriac work

CAL documents Syriac-script input for general lexical access. CAL-MCP's existing lexicon normalization/lookup surface already owns that behavior. Issue #11 should not add a second generic Syriac lexical-search wrapper just because the Syriac Studies landing page exists.

Likewise, direct category results that lead to ordinary CAL text pages compose with `cal_text_page`; source links are navigation metadata, not an instruction for hidden retrieval.

## Empty/error/drift distinctions

For the comparison operation, the explicit `error in coord` marker is a typed not-found state only when the requested heading matches and no successful MT/Peshitta pair is present. A successful-looking heading without either valid comparison data or the explicit error marker is parser drift.

For category and missing-word lists, the live audit did not establish a dedicated empty marker. An otherwise successful response lacking the expected semantic heading/list structure should therefore fail closed rather than be silently returned as an empty list. If a future bounded check finds an explicit upstream empty state, add it through a focused regression.

Network/HTTP policy errors continue to come from the shared `CalHttpClient` and remain distinct from local validation, typed not-found, and parser drift.

## Provenance and request bounds

Every issue-#11 result should preserve:

- `source = "CAL"`;
- exact CAL source URL;
- timezone-aware retrieval timestamp;
- operation name;
- caller's public category or biblical reference;
- relevant CAL upstream identifiers returned by the page.

Production request budget: **exactly one CAL request per public operation**. Category grouping, text browsing, lexicon-entry lookup, external-citation retrieval, and verse navigation remain separate caller-controlled actions.

Normal CI is offline and uses deliberately reduced semantic fixtures, not archived CAL pages.
