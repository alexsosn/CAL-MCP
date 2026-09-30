# Research: CAL-MCP feasibility and upstream interface

**Research snapshot:** 2026-09-03

This document records evidence used to design CAL-MCP. It is intentionally evidence-oriented rather than a product specification. When CAL changes materially, append a dated update instead of silently rewriting historical assumptions.

## R-001 — CAL's scholarly scope and live-data model

CAL describes itself as a text base covering Aramaic dialects from the 9th century BCE through the 13th century CE, with almost four million lexically parsed words, more than 40,000 headwords, more than 100,000 lexical citations, and electronic tools for analysis. CAL explicitly says the lexicon is a work in progress and asks scholarly citations to include the date on which data were retrieved.

Sources:

- https://cal.huc.edu/
- https://cal.huc.edu/info.html
- https://cal.huc.edu/main_index.html

**Implication:** CAL-MCP responses should expose retrieval timestamps and CAL source URLs. A local static mirror would also age differently from CAL's intended live-data model, which is another reason not to build one.

## R-002 — The public CAL surface is much broader than lemma lookup

CAL's current search page exposes:

- lexicon browsing;
- English gloss search;
- searching combinations of English words in citations;
- searching citations from texts not present in the online database;
- text browsing;
- text search by topic;
- Targum studies tools;
- Syriac studies tools;
- dictionary spelling collation;
- basic concordance for a single text;
- multi-text KWIC/concordance tools.

Sources:

- https://cal.huc.edu/searching/CAL_search_page.html
- https://cal.huc.edu/faq.html
- https://cal.huc.edu/cal_new_user_guide.html

**Implication:** a useful first release can focus on lexicon/text/concordance primitives, but “fully functional” should eventually cover the specialist Targum, Syriac, citation, and bibliography surfaces where they can be represented faithfully.

## R-003 — CAL already accepts multiple scholarly input representations

CAL documents access by root, canonical form, or complete inflected form. It also states that searches may use Roman transliteration, Unicode, Hebrew square script, or Syriac keyboards.

Source:

- https://cal.huc.edu/advantages.htm

**Implication:** CAL-MCP should not force agents to know one brittle ASCII syntax. It should expose deterministic input normalization and should preserve the original query alongside the normalized CAL query. The adapter must not invent linguistic normalization not supported by CAL.

## R-004 — Public server-side endpoints are observable, but no stable API contract has been found

Observed public interfaces include, among others:

- `browseSKEYheaders.php` — lexicon browsing;
- `cal_entry_web.php?lemma=...` — lexicon entry rendering;
- `oneentry.php?lemma=...` — full-entry/citation rendering;
- `getlex.php?coord=...&word=...` — lexical analysis from a text coordinate;
- `get_a_chapter.php?file=...` — text browser;
- concordance/KWIC handlers linked from entries and search pages.

Representative live pages:

- https://cal.huc.edu/browseSKEYheaders.php
- https://cal.huc.edu/cal_entry_web.php?lemma=br+N
- https://cal.huc.edu/getlex.php?coord=4400137054005&word=0
- https://cal.huc.edu/get_a_chapter.php?file=71026

The HTML pages expose rich structured relationships, but we have not found a published JSON/REST API specification, versioned schema, or compatibility promise for these endpoints.

**Implication:** endpoint URLs and HTML structure are adapter internals, not the public MCP contract. Each endpoint needs a parser behind typed models and fixture-based contract tests. Material upstream markup/schema changes should fail explicitly rather than produce silently incomplete results.

## R-005 — Automated-access policy is not explicitly documented

As of this snapshot, review of CAL's current project pages, FAQ, search documentation, and public interface did not reveal a CAL-specific API policy, crawler policy, rate-limit policy, or explicit permission/prohibition for automated requests.

CAL does clearly intend broad scholarly use of its online tools and describes them as electronic tools for analyzing/manipulating the data. That does not by itself establish permission for corpus-wide harvesting or redistribution.

Sources reviewed:

- https://cal.huc.edu/
- https://cal.huc.edu/faq.html
- https://cal.huc.edu/info.html
- https://cal.huc.edu/advantages.htm

**Project policy derived from the current uncertainty:**

1. CAL-MCP performs user-initiated, bounded live queries only.
2. No corpus crawl, mirror, background indexing, or bulk extraction.
3. No CAL data is bundled with the package.
4. Caching may only reduce repeated identical/near-identical live requests and must remain bounded.
5. Concurrency and retries remain conservative.
6. If CAL publishes explicit machine-access guidance, update this research record and architecture decision before changing behavior.

This is an engineering policy for CAL-MCP, not a claim about CAL's legal rights or terms.

## R-006 — Provenance must be part of the public data model

CAL's request that scholarly citations include retrieval dates means provenance is user-visible functionality, not merely logging.

Every result type should be able to carry, when applicable:

- `source = "CAL"`;
- canonical/source URL used for the result;
- retrieval timestamp in an unambiguous timezone-aware format;
- CAL lemma key, coordinate, text/file identifier, or other upstream identifier;
- original query and normalized CAL query when normalization occurred;
- optional warnings when an upstream field could not be represented losslessly.

## R-007 — CAL's current UI links lexicon, corpus, and concordance concepts

The text browser lets a user click a word for lexical analysis, and CAL lexical entries link citations/context and concordance operations. This means the domain model should share stable concepts rather than expose each HTML form as an unrelated MCP tool.

Candidate shared models:

- `LemmaRef`
- `LexiconEntry`
- `Sense`
- `Citation`
- `TextRef`
- `Passage`
- `TokenAnalysis`
- `ConcordanceHit`
- `BibliographyRef`
- `Provenance`

These are adapter models only. They must preserve CAL distinctions and must not merge senses, dialect labels, or analyses merely for convenience.

## R-008 — Prior art: PSHAT contains CAL-oriented parsing utilities

The public `nsantacruz/PSHAT` repository contains `cal_tools.py` and code designed around CAL-format material. It is useful as historical prior art for CAL transliteration/record conventions and edge cases.

Repository:

- https://github.com/nsantacruz/PSHAT
- https://github.com/nsantacruz/PSHAT/blob/master/cal_tools.py

**Decision:** use it for research and test-case discovery only unless a later issue verifies license compatibility and identifies specific code worth reusing. Do not couple CAL-MCP to PSHAT or assume its corpus-dump workflow matches CAL's current website.

## R-009 — Prior art: Peshitta MCP demonstrates a nearby MCP interaction pattern

`Jossifresben/peshitta` provides an Aramaic/Syriac research application with MCP-facing operations such as root search, concordance, passage analysis, and citations.

Repository:

- https://github.com/Jossifresben/peshitta

It is useful for studying agent-facing granularity and MCP ergonomics in a nearby scholarly domain. Its data model and linguistic semantics are not CAL's and must not be imported as if they were.

## R-010 — Agora is downstream integration, not an architectural dependency

Agora's current contribution rules define Agora as a thin marketplace responsible for discovery, description, installation, launch/integration, compatibility metadata, and marketplace UX. Third-party domain behavior belongs upstream.

Relevant Agora files:

- https://github.com/alexsosn/Agora/blob/main/CONTRIBUTING.md
- https://github.com/alexsosn/Agora/blob/main/registry/plugins.yaml

Agora already represents remote-data MCP integrations such as Perseus, Sefaria, and SEDRA. The current registry supports local Python servers that query remote scholarly services as well as hosted MCP endpoints.

**Implication:** CAL-MCP should publish a normal standalone package/entry point and its own CAL-specific docs/skills/tests. After a stable release exists, Agora should only register how to discover/install/launch it and perform smoke-level integration verification.

## R-011 — Recommended transport posture

The core server should be transport-agnostic internally. For the first release:

- **stdio** is the required standalone transport because it is simple, local, and directly compatible with agent clients and Agora launch metadata;
- a network transport may be added later only if there is a concrete deployment/client requirement;
- CAL-MCP itself remains a local adapter even though its data source is remote;
- no hosted CAL-MCP service is required for v0.1.

This avoids introducing hosting, authentication, abuse prevention, and shared rate-limit concerns before they are necessary.

## R-012 — Parsing risk is the dominant implementation risk

The MCP protocol layer is conventional. The harder engineering problem is preserving CAL semantics while adapting undocumented, server-rendered pages that can evolve.

Risk controls:

- isolate each upstream surface in an endpoint adapter/parser;
- parse semantic anchors/relationships instead of relying only on layout position;
- retain small versioned fixtures with source URL and capture date;
- include malformed/missing/changed-element tests;
- fail explicitly on unexpected pages such as maintenance/error/login responses;
- keep normal CI offline;
- run very small opt-in/scheduled live smoke tests after release to detect drift.

## R-013 — Lexicon entries use recursive outline numbering and multi-link citation rows

**Rechecked:** 2026-09-04.

The current `br N` lexicon entry demonstrates two parser-relevant structures that are not safely representable by a one-level parenthetical model or by splitting a rendered citation line independently for each link.

The sense outline includes a top-level sense followed by repeated parenthetical numbering at several nested levels. In the current entry, the sequence under top-level sense 2 includes `(1)` → `(1)` → `(1)`, followed by sibling `(2)` at the deepest active level. The semantic hierarchy therefore has paths equivalent to `2`, `2.1`, `2.1.1`, `2.1.1.1`, then `2.1.1.2`; repeated `(1)` labels cannot be flattened without losing CAL's distinctions.

The same entry also renders more than one linked citation reference on a single semantic row. Citation text must therefore be segmented between the positions of adjacent citation anchors. Taking the entire suffix after each link causes the first citation to absorb later references and their text.

Source:

- https://cal.huc.edu/cal_entry_web.php?lemma=br+N

A deliberately reduced fixture recording these relationships is kept as `tests/fixtures/cal/entry_br_nested.html`; it is not an archived CAL page.

**Implication:** the lexicon parser maintains recursive sense paths from the observed outline sequence, treats inconsistent parenthetical numbering as parser drift rather than guessing, and partitions multi-link citation rows by ordered anchor boundaries.

## R-014 — Current lexicon display shapes are broader than the first fixtures

**Rechecked:** 2026-09-04.

A second review against current CAL pages found several structures that a faithful lexicon adapter cannot reduce to the narrow vocabulary present in the initial `br`/`nmy` fixtures.

CAL's full lexicon browser explicitly accepts CAL code, Unicode transliteration, Unicode Hebrew, and Unicode Syriac. Its character table distinguishes Hebrew shin/sin (`ש` / `שׂ`) and maps Syriac `ܧ` to transliterated `ṗ`; it also documents the space-bar equivalent of CAL `@` in combinations.

CAL's lexical display uses an open set of part-of-speech abbreviations. Current pages/search results include forms such as `interj.`, `adv./conj.`, `nom.ag.`, `v.n.`, and stem-qualified variants rather than only the noun/verb/adverb labels present in the first fixtures. Treating POS as a small closed local enum would reject valid current entries.

CAL publishes dialect codes including subcodes such as `BA-Da`, `BA-Ez`, `OfA-Egypt`, `OfA-Pers`, and `OfA-West`; current entry pages also render human-readable names such as `Common Aramaic`, `Nabatean`, `Palmyrene`, and `Qumran`. Dialect recognition therefore must preserve documented codes/display labels without using capitalization as a generic dialect heuristic.

Finally, current `br N` citation rows can mix plain, unlinked citation fragments with linked citation anchors. The rendered citation-count marker counts both forms. When CAL does not provide a link or a safely separable structured reference for a fragment, the adapter can preserve the rendered fragment as citation text but must not invent a reference or URL. The count marker provides a fail-safe check against silently losing such fragments.

Sources:

- https://cal.huc.edu/searching/fullbrowser.html
- https://cal.huc.edu/Cal_dialect_codes.html
- https://cal.huc.edu/lexical.help.html
- https://cal.huc.edu/cal_entry_web.php?lemma=br+N

**Implication:** the lexicon parser does not use a closed POS whitelist; it recognizes CAL-style abbreviation tokens while preserving their exact text. Dialect matching is based on documented CAL codes/display labels and only after a sense definition has been established. Script comparison preserves the browser's shin/sin and Syriac `ܧ` distinctions. Mixed linked/plain citation rows retain all counted fragments, using nullable adapter `reference`/`url` fields when upstream markup does not supply them.

## R-015 — English gloss and citation-text searches are distinct bounded POST surfaces

**Rechecked:** 2026-09-04.

A bounded form audit confirmed the current request contracts instead of inferring them from result URLs. English gloss search submits `POST /newsearchmngs.php` with the English search string in `English` and CAL's primary/all-glosses radio value in `secondary` (`""` or `"true"`). English citation-text search submits `POST /searchcits.php` with the search string in `English`.

The current gloss result surface renders ordered linked CAL lemma headers followed by gloss text. A bounded `camel#` all-glosses probe produced 10 parsed matches; the production parser identified `bwkty N` / `bactrian camel` as the first result. The current citation-text result surface renders repeated lemma header → lexical context → citation rows, with citation reference, source-language text, and English translation separated in the rendered row. A bounded `camel` probe produced 154 parsed hits; the production parser identified the first as lemma `)w c`, reference `OS MkSin10:25`, with both source text and English translation present.

The same audit established CAL's explicit empty-result messages: `There are no glosses with the word: ...` and `There are no citations with the word: ...`. CAL's citation-search instructions accept one to three English words. They also describe upstream exceptions/behavior for very common short words; that behavior should remain CAL's responsibility rather than becoming an independently maintained CAL-MCP stop-word list.

No page number, next-page link, continuation token, or other stable continuation control was exposed by the representative current gloss or citation result pages inspected in this audit. The citation example was still a single response of roughly 80 KB. Absence from these representative pages is not proof that CAL can never paginate; it is evidence that CAL-MCP must not invent a continuation contract before one is actually observed and tested.

Sources:

- https://cal.huc.edu/searching/englishnew.html
- https://cal.huc.edu/searching/srchcits.html
- https://cal.huc.edu/searching/CAL_search_page.html

The form/result inspection and production-parser smoke were deliberately tiny, branch-only live checks. The temporary workflows were deleted after use; normal CI remains offline and fixture-driven.

**Implication:** CAL-MCP exposes gloss search and citation-text search as two typed tools, each performing exactly one bounded CAL POST per call. It preserves CAL order and distinctions, does not fetch returned lexicon entries automatically, does not rerank/deduplicate citation hits, and does not invent pagination. Response size remains bounded by the shared HTTP safety limit. Endpoint/form names remain adapter internals rather than MCP parameters.

## R-016 — Current text discovery and page navigation are explicit bounded surfaces

**Rechecked:** 2026-09-04.

A bounded live audit of CAL's current text interfaces confirmed three distinct operations rather than one implicit corpus browser.

The topic-search form at `searching/searchtopic.html` submits `POST /newsearchtxts.php` with the query in form field `search`. A `Tel Dan` probe returned a text link to `get_a_chapter.php` carrying CAL file identifier `13250`; the rendered row also supplied the text label/description. CAL currently renders the explicit empty-search message `There are no files associated with the search term ...`, so an intro/result page lacking both a text link and that marker is parser drift rather than a safe empty result.

Text browsing uses CAL file identifiers and, where CAL exposes subdivisions, separate subtext/category navigation identifiers. The root text menu and `showsubtexts.php?subtext=...` surface expose those identifiers in links; CAL-MCP should preserve them as opaque strings, not decode their digits into a locally invented taxonomy.

The current `get_a_chapter.php` text browser uses a zero-based internal `page` parameter even though the page displayed to the researcher is one-based. In a bounded check of file `71026`, upstream `page=0` rendered `Page 1 of 50 (2413 lines total)` and upstream `page=1` rendered Page 2. The page also exposed explicit next-page links plus a `page=all` “show all” link. `show all` is unsuitable for the adapter's bounded-request policy and therefore must not become a public MCP option.

CAL text rows expose lexical-analysis links such as `bablex.php?coord=...&word=...`. These provide a machine line coordinate plus a zero-based word position. Some rows additionally expose a `comment.php?coord=...` anchor whose rendered text is a human-readable manuscript/page/side/line locator. Those relationships can be preserved without calling the lexical-analysis endpoint; token analysis remains a separate explicit operation.

Not every valid text is paginated. The current Tel Dan page for file `13250` renders text lines and lexical links without a `Page X of Y` marker. CAL-MCP must therefore leave page-count/total/previous/next metadata nullable instead of fabricating values. Conversely, a nonexistent file/subtext selection currently returns HTTP 200 with the explicit message `NO LINES FOR ... ARE CURRENTLY STORED`; that is a recognizable missing-text state, distinct from network/content failure and from unknown successful markup.

Sources:

- https://cal.huc.edu/newtextmenu.html
- https://cal.huc.edu/searching/searchtopic.html
- https://cal.huc.edu/newsearchtxts.php
- https://cal.huc.edu/showsubtexts.php?subtext=3
- https://cal.huc.edu/get_a_chapter.php?file=71026
- https://cal.huc.edu/get_a_chapter.php?file=13250

The form, pagination, missing-text, and empty-search inspections were deliberately tiny branch-only live probes. The temporary workflows were deleted immediately after the evidence was recorded; normal CI remains offline and uses reduced fixtures.

**Implication:** CAL-MCP exposes three text primitives: one explicit catalogue level, one topic-search request, and one normal text page. Each public call performs exactly one CAL request. Category expansion and page traversal are caller-controlled; no recursive catalogue walk, automatic next-page request, `show all`, token lookup, background indexing, or local corpus mirror is introduced. Public pages are one-based, while CAL's current internal page parameter remains adapter-private. CAL file/subtext/category identifiers and machine/display coordinates are preserved with provenance but are not advertised as permanent CAL-MCP identifiers.

## R-017 — Current Targum Studies surface mixes specialist comparison with existing text/KWIC primitives

**Rechecked:** 2026-09-05.

A bounded live audit of CAL's Targum Studies module established three specialist result families plus one navigation path that already composes with CAL-MCP's general text browser.

The parallel verse form submits one biblical book/chapter/verse to `showtargum.php`, with optional Peshitta and Samaritan checkboxes. The current selector contains 36 exact CAL book labels/values. A Gen 1:1 request returned MT plus ordered CAL-labelled readings including Onqelos, Pseudo Jonathan, Neofiti, Fragment Targum material, and optional Peshitta. Source-name links lead directly to CAL's ordinary `get_a_chapter.php` text pages, so a separate single-Targum MCP browser would duplicate the already implemented text interface. A nonexistent coordinate such as Gen 1:99 returns HTTP 200 with CAL's explicit `error in coordinate` marker; this is a passage-not-found state.

The Targum concordance submits one CAL lemma/POS to `showtargumKWIC.php`. `klb N` returned an ordered source/count table totaling 59 examples across named Targum groups. A nonexistent structurally valid lemma returned the same complete table with every count zero and `total examples: 0`, establishing a valid empty-result shape rather than an error page. Source rows link to the existing CAL KWIC family and should remain explicit navigation metadata rather than trigger hidden follow-up requests.

The Hebrew-reflex module studies which Aramaic lemmas translate a selected MT Hebrew lemma. CAL currently exposes usable Onqelos and Neofiti workflows while Pseudo-Jonathan is explicitly marked `(under development)`. The source-specific letter pages expose vocalized Hebrew lemma labels plus opaque numeric `R1` identifiers. MT ID `1751` (`מַעֲקֶה`) returned Onqelos `תיק #2 N` with frequency 2 and Neofiti `גיפוף N` / `סייג N` with frequency 1 each. A deliberately invalid MT ID returned a broad frequency list under an empty `Onkelos correspondences to` heading, so a faithful adapter must validate the semantic heading instead of trusting apparently well-formed rows.

Sources:

- https://cal.huc.edu/searching/targumsearch.html
- https://cal.huc.edu/searching/targum_concordance.html
- https://cal.huc.edu/targumicpairsearch.htm
- https://cal.huc.edu/Olemmaselect.htm
- https://cal.huc.edu/Omtlemmas/memMTlemma.html
- https://cal.huc.edu/mtlemmas/memMTlemma.html
- bounded branch-only form/result/edge-case probes recorded in `docs/research/issue-10-targum.md`

**Implication:** issue #10 should add specialist one-request operations for parallel verse comparison, Targum-specific concordance counts, MT Hebrew lemma discovery, and Onqelos/Neofiti reflex lookup. Full source browsing and detailed KWIC remain compositions through existing tools. Version labels/order, Unicode text, opaque MT IDs, zero-count results, and explicit coordinate errors must be preserved without harmonization or hidden traversal.

## Open research questions

These should be answered by implementation tickets rather than guessed globally:

1. What is the canonical endpoint and parameter model for basic and advanced KWIC/concordance?
2. Which dialect identifiers are stable machine values versus display labels?
3. Do specialist text/module surfaces use pagination or coordinate shapes that differ materially from the general text browser?
4. Does CAL document any stronger stability guarantee for file/subtext/category identifiers than is observable from the current public links?
5. Which Syriac operations compose cleanly into general tools and which deserve specialist tools?
6. Does the bibliography interface expose stable query parameters suitable for typed search?
7. What minimal cache policy gives useful duplicate-request suppression without retaining a meaningful CAL dataset?
8. Does CAL expose `robots.txt` or future machine-access guidance that should alter request policy?
9. What subset of upstream HTML can be kept as test fixtures while respecting copyright and avoiding unnecessary CAL content retention?

## Research update procedure

When new evidence changes an assumption:

1. add a dated `R-xxx` entry or dated amendment;
2. link the exact upstream page, captured fixture provenance, or upstream communication;
3. state the implementation/architecture consequence;
4. update `wiki/decisions.md` if a durable project decision changes;
5. update affected tickets/acceptance criteria before implementation continues.

## R-052 — Citation search explicitly rejects some single common words

**Rechecked:** 2026-09-29, with four bounded POSTs; issue #207.

`searchcits.php` answers `English=god`, `English=the` and `English=a` with `"<query>" is not a valid search string` and no result container, echoing the query lowercased (`God` → `"god"`). `king god` returns results, and gloss search accepts `god`. Detailed evidence: `docs/research/issue-207-invalid-search-string.md`.

**Implication:** that exact marker naming the submitted query becomes an `invalid_input` error with `upstream_reached: true` and CAL's message. CAL-MCP keeps no local stop-word list.

## R-051 — Text-scoped KWIC writes Hebrew- and Syriac-script coordinates reversed inside `<BDO dir="rtl">`

**Rechecked:** 2026-09-29, with two bounded POSTs; issue #206.

With `charset=H`, `showdialectKWIC.php` renders each target link's coordinate in reverse digit order inside `<BDO dir="rtl">`: `5227701020017` for target `7100201077225` (BT Shabbat), and `3005231` for `1325003` (Tel Dan, both `charset=H` and `charset=S`). The one-dialect endpoint renders its coordinates plainly. Detailed evidence: `docs/research/issue-206-bdo-reversed-coordinate.md`.

**Implication:** a reversed link text is accepted only when it is exactly the reversed `target` and sits entirely inside `<BDO dir="rtl">`. The coordinate returned is always the link's `target`.


## R-050 — CAL's KWIC highlight can mark a neighbouring word or nothing

**Rechecked:** 2026-09-29, with two bounded requests; issue #204.

In `mlk N` KWIC over Samaritan Targum `56000`, 30 of 106 hits have a highlight that is not a form of `mlk` (25 other words, including a two-word highlight, on 16+ lines across chapters 114–529), and 5 of those are empty. In Hebrew-script `mlk N` KWIC over Biblical Aramaic `31000`, 7 of 45 target lines have no highlight at all (2026-09-30). A page with at least two hits and no highlight on any of them still fails closed, because every captured multi-hit page highlights most lines (101/106 and 38/45); the threshold of two is a judgement that keeps a genuine single unhighlighted hit. On line `56000114010`, whose full-context tokens show the lemma at words 3, 6, 9 and 12 and a two-word token at word 8, the four hits are highlighted `mlK`, `w)rywK`, `)l)sr` and nothing. Detailed evidence: `docs/research/issue-204-empty-kwic-highlight.md`.

**Implication:** `target_text` is CAL's highlight as rendered, and is `null` when CAL's highlight is empty or missing. It is documented as unverified; CAL-MCP does not correct it.


## R-049 — Babylonian Talmud full-context rows use `bablex.php` token links

**Rechecked:** 2026-09-29 (a capture from #181's research); issue #203.

The full-context page for BT Shabbat (`get_a_kwicchapter.php?file=71002&sub=01051&cset=H&target=7100201051217`) links all 204 tokens through `bablex.php?coord=…&word=…`, with no `hasvariant`, and shows the same terminal empty anchor as other Hebrew-script rows. Detailed evidence: `docs/research/issue-203-bablex-full-context.md`.

**Implication:** full-context rows accept the `bablex.php` family with exactly `{coord, word}`, alongside `getlex.php` with `{coord, word, hasvariant}`; a row mixing them fails closed.


## R-048 — Citation search wraps results in rows; one row can hold a headerless citation

**Rechecked:** 2026-09-29, with two bounded POSTs; issue #178.

`searchcits.php` wraps each result in `<div class="citation-row …">`, holding one `oneentry.php` header with an explicit `<pos>` element, one context and one citation. CAL repeats the header per sense. For `king`, 1067 of 1068 rows have that shape. One row (`brt ym`) carries a second (context, citation) pair with no header, and that pair belongs to another lemma. Eleven headers have POS forms such as `n.(pr.)` that the earlier heuristic header split cannot parse. Detailed evidence: `docs/research/issue-178-headerless-citation.md`.

Source:

- POST https://cal.huc.edu/searchcits.php (`English=king`, `English=camel`)

**Implication:** results are parsed per row container, and the POS is taken from `<pos>`. A headerless pair is returned with `lemma: null`, never attributed to the row's header.

## R-047 — KWIC full-context pages use the text-page file-info coordinate rule

**Rechecked:** 2026-09-29, with four bounded GETs; issue #181.

`get_a_kwicchapter.php` renders its file-information coordinate as the file id plus the submitted `sub` (`56000112` for `56000`/`112`; `310004` for `31000`/`4`) or as the bare file id (`71002` for BT Shabbat `01051`). The label prefix is always the file id. Detailed evidence: `docs/research/issue-181-full-context-subtext.md`.

Source:

- https://cal.huc.edu/get_a_kwicchapter.php?file=56000&sub=112&cset=R&target=56000112010

**Implication:** the full-context parser accepts exactly those two coordinates, with a label naming the file, and fails closed on anything else.


## R-046 — Six-digit Syriac text ids are CAL file plus subtext

**Rechecked:** 2026-09-29, with four bounded GETs; issue #186.

`get_a_chapter.php?file=634081` (listed by the Syriac catalogue) renders file-info `coord=634081` with the label `63408: Tamar and Judah`, and its own links use `file=63408&sub=1`. The group `showsubtexts.php?keyword=63408` lists subtexts `sub=1` and `sub=2` with info coords `634081` and `634082`. Detailed evidence: `docs/research/issue-186-six-digit-syriac-id.md`.

Source:

- https://cal.huc.edu/get_a_chapter.php?file=634081&page=0
- https://cal.huc.edu/showsubtexts.php?keyword=63408

**Implication:** a label prefix that is the requested id minus a trailing sub is accepted only when the page's own links name that file and sub; any other label fails closed.


## R-045 — Text concordances contain CAL's "no data found" rows with non-canonical keys

**Rechecked:** 2026-09-29.

`newconcord.php` for text 41201 has six rows glossed "no data found for …". Their KWIC keys can be invalid, for example `+snqlyTws+N` (a leading space) or `qrb ` (no suffix). Detailed evidence: `docs/research/issue-177-concordance-no-data-rows.md`.

Source:

- https://cal.huc.edu/newconcord.php?text=41201&cset=S

The same page has ordinary proper-noun rows whose keys use undocumented capitals (`bwlbrK PN`, `$lMn) PN`). CAL's own `showKWIC.php` link finds their hit, but the `showdialectKWIC.php` form used by `cal_kwic_texts` drops the capital and reports 0 examples (four bounded requests, 2026-09-29).

**Implication:** "no data found" rows are kept with `cal_reports_no_data: true`, and `lemma_key` is null when CAL's key is invalid. Capital-letter keys are kept verbatim in concordance rows, but the KWIC tools reject them as input and point to the row's `kwic_url`. Other rows keep the strict key check.


## R-044 — Biblical verse headings use CAL's own book labels

**Rechecked:** 2026-09-29.

`showpesh.php` and `showtargum.php` head the verse with CAL's own book abbreviations: Gen, Lev, Num, Sam1, Kings1, Jer, Ezek, Obad, Zech, Mal, Ps, Song, Lam, Prov, Chron1, Chron2 and so on. All 36 were recorded. The adapter's 2-digit coordinates (as in CAL's own links) return the right verse. A 3-digit chapter, which the adapter never sends, shifts CAL's coordinate into another book: `chapter=001` for Genesis returns 1 Kings 1:1. Detailed evidence: `docs/research/issue-173-biblical-headings.md`.

Sources:

- https://cal.huc.edu/showpesh.php (POST `bookname=27`, `chapter=23`, `verse=01`)
- https://cal.huc.edu/showtargum.php (POST `bookname=01`, `chapter=01`, `verse=01`)

**Implication:** the heading must name the requested chapter:verse with CAL's reviewed label for the requested book (or the exact selector label); any other label fails closed. The 2-digit request format is pinned.

## R-043 — Dialect KWIC can omit the requested form and list only other forms

**Rechecked:** 2026-09-25.

`show1dialectKWIC.php` for `n)qh N` in dialect 71 lists `n)qt) N` (1 example) and `nqh N` (0), with no summary for `n)qh N`; in dialects 6, 51, 53 and 3 the requested form is listed. Detailed evidence: `docs/research/issue-176-kwic-omitted-form.md`.

Source:

- https://cal.huc.edu/show1dialectKWIC.php?lemma=n%29qh&pos=N&texts=71

**Implication:** D-014 is amended: an omitted requested form is reported as `requested_form_listed: false` instead of failing.

## R-042 — Current CAL has two-cell plain/unlemmatized text rows

**Rechecked:** 2026-09-28 against current CAL; issue #185.

Bounded structural checks confirmed the same plain-row semantics on Mandaic `74420` and direct
Christian Palestinian Aramaic `55430`: each actual text row has two cells, the first carrying a
rendered display coordinate and the second rendered scholarly text, with no lexical token links.
Mandaic `74501` and Peshitta `62057` were linked controls; no sampled actual text table mixed
linked and plain rows.

Some plain rows still expose a CAL line identity through the first cell's exact
`comment.php?coord=...` link. Current `74420` has 3 such rows among 46; current `55430` has
4 among 50. Other plain rows have no machine/line coordinate at all. This means the original #185
assumption that every plain row has `coordinate: null` was too strong.

The direct CPA audit also found that current `55002` is now an empty `text-display` shell rather
than a plain-text page; its classification is tracked separately by #196.

Detailed request bounds and row evidence:
`docs/research/issue-185-unlemmatized-text.md`.

Sources:

- https://cal.huc.edu/get_a_chapter.php?cset=M&file=74420&page=0
- https://cal.huc.edu/get_a_chapter.php?file=55430&cset=C&page=0
- https://cal.huc.edu/get_a_chapter.php?file=55002&cset=C&page=0

**Implication:** plain rows preserve rendered text and display coordinates with empty token
collections. `TextLine.coordinate` is nullable; a strict comment link supplies a line/comment
coordinate when CAL exposes one. Token analysis remains composable only from returned token
objects, which carry both a token coordinate and word index. Mixed linked/plain tables and empty
text shells fail closed.

## R-041 — Current token analysis can succeed without a linked lemma entry

**Rechecked:** 2026-09-27 against current CAL; issue #193.

A bounded three-request recheck of current Peshitta and Christian Palestinian Aramaic token
analysis confirmed a success shape distinct from R-040's linked `lexlink` table. These pages have
the normal token-analysis result marker, no result table, and zero lemma-entry links.

Observed rendered summary regions:

- Peshitta `620570101`, word 0: one line, `pwlws PN Personal name`;
- Peshitta `620570101`, word 2: two ordered lines,
  `d_ p = d_ p --> dy p` and `y$w( PN Personal name`;
- CPA `5500001001a019001`, word 0: one line, `lwT PN Personal name`.

The two-line example provides no linked key or structural candidate delimiter that would justify
interpreting `=` / `-->` as the same verified redirect relation used by R-040.

Detailed evidence and request bounds:
`docs/research/issue-193-linkless-token-analysis.md`.

Sources:

- https://cal.huc.edu/getlex.php?coord=620570101&word=0
- https://cal.huc.edu/getlex.php?coord=620570101&word=2
- https://cal.huc.edu/getlex.php?coord=5500001001a019001&word=0

**Implication:** CAL-MCP preserves these ordered rendered lines as additive
`unlinked_summaries`, keeps linked `candidates` empty, and reports the operation as `found`.
It does not synthesize `LemmaRef` data or decode free-form relation/POS/gloss text. Explicit
no-data/no-lemma states remain `not_found` with both collections empty.

## R-040 — Current linked Syriac token analysis can redirect to another lemma entry

**Rechecked:** 2026-09-27 against current CAL; issue #179.

Peshitta Philemon 1:1 token `620570101`, word 1 currently renders the analysis label
`)syr noun sg. emphatic= )syr N --> )syr A` and links one malformed-nesting
`a.lexlink` header to `oneentry.php?lemma=)syr A&cits=all`. CAL therefore distinguishes the
analysed/source key `)syr N` from the linked target key `)syr A`.

The same page appends the target entry's sense outline after the one-row result table. The legacy
alternating-line parser correctly read the first candidate, then mistook two following sense lines
for a second candidate and failed because a line containing `s.v.` looked lemma-like but had no
link. The current result-table close is therefore the reliable candidate boundary for this
researched shape.

Bounded research also found valid successful token-analysis pages with no `oneentry.php` link at
all: Peshitta words 0 and 2 on the same line and CPA
`5500001001a019001`, word 0. Their semantics are structurally different and are tracked by #193
instead of being guessed into the linked-candidate model.

Detailed evidence, request counts and parser contract:
`docs/research/issue-179-syriac-token-redirects.md`.

Source:

- https://cal.huc.edu/getlex.php?coord=620570101&word=1

**Implication:** linked current redirects expose additive `analyzed_lemma_key` while
`lemma.lemma_key` remains the validated linked target. The parser bounds the current candidate by
its result table and ignores the following sense outline for token-analysis purposes. Linkless
successful summaries remain explicit parser drift pending #193.

## R-039 — Christian Palestinian Aramaic uses suffix-bearing subtext IDs

**Rechecked:** 2026-09-26 against current CAL; issue #170.

The current Christian Palestinian Aramaic catalogue at
`showsubtexts.php?subtext=55` exposes ordinary text links such as
`get_a_chapter.php?file=55000&sub=01001a&cset=C`. Current observed selectors include
`01001a`, `01001b`, `01001c`, `01002a`, `02003a`, and `03007a`. The first route was
opened successfully, and its Text Information selector is the composed
`get_file_info.php?coord=5500001001a`.

Detailed evidence and the code-impact audit are in
`docs/research/issue-170-cpa-subtext-ids.md`.

Sources:

- https://cal.huc.edu/showsubtexts.php?subtext=55
- https://cal.huc.edu/get_a_chapter.php?file=55000&sub=01001a&cset=C
- https://cal.huc.edu/get_file_info.php?coord=5500001001a

A subsequent installed-stdio acceptance run reached the CPA page but exposed one more related
assumption: CPA token and comment machine coordinates also embed the suffix, for example
`5500001001a019001`. A one-request structural probe confirmed the pattern without retaining
scholarly text.

**Implication:** `subtext_id` is not globally decimal. CAL-MCP preserves the currently observed
grammar of decimal digits plus an optional single lowercase ASCII suffix and shares that grammar
between text and KWIC/full-context workflows. Current text/token machine coordinates are accepted
only as decimal strings or the observed digits + one lowercase ASCII letter + decimal-tail form.
On a suffix-bearing page, returned coordinates must begin with the exact requested
`file_id + subtext_id`. `cal_token_analysis` accepts the same narrow coordinate grammar at the
input boundary, so a returned CPA coordinate reaches CAL rather than being rejected locally.
Current CPA token-analysis response parsing still fails closed and is tracked separately in
release blocker #179. File/category IDs and KWIC target coordinates remain decimal-only.
A complete category-55 route audit accounted for all 555 current CPA text references: 551
subdivided routes (150 suffix-bearing and 401 decimal-subtext) plus four direct routes
(`55002`, `55406`, `55407`, `55430`). Every current route uses `cset=C`. CAL-MCP
therefore keeps separate evidence-backed CPA subdivided/direct file sets rather than inferring
routing from suffix presence or a generic `55` prefix. Malformed near-misses and contradictory
returned routes fail closed. Representative direct file `55002` reaches the exact
`file=55002&cset=C&page=0` route successfully but its current linkless `text-display` content
still fails in the independent unlemmatized/plain-text parser class tracked by release blocker
#185.

## R-038 — Syriac text rows can contain empty lexical word slots

**Rechecked:** 2026-09-26 against current CAL from a bounded GitHub-runner probe.

The original 2026-09-25 E2E observation captured an all-empty row in Ephrem text `60424`:

```html
<tr><td valign="top">1.005:08 </td><td><a href="getlex.php?coord=60424100508&word=0&hasvariant=0"></a> </td></tr>
```

A 2026-09-26 live structural recheck corrected the initial interpretation. The structural probe counted 314 `<tr>` elements in the current text-display region; 10 contain
29 empty `getlex.php` anchors. A later installed-stdio verification returned 313 parsed two-cell
lines while preserving the same 29 slots and nine mixed rows, so raw row count is not treated as
an invariant. Only one affected row is all-empty. The other nine
mix empty word slots with rendered lexical links, and empty slots occur at word indexes 0–11.
All lexical links within each affected row share one machine coordinate. Detailed evidence and
the revised representation are in `docs/research/issue-168-blank-text-lines.md`.

Source:

- https://cal.huc.edu/get_a_chapter.php?file=60424&page=0

**Implication:** rendered tokens remain `tokens`; exact current empty lexical slots are preserved
separately as additive `empty_word_indexes`. Mixed and word>0 empty slots are valid current CAL
data. Altered routes/selectors, coordinate disagreement, duplicate slots, or collisions with
rendered word indexes fail closed.


## R-037 — Dictionary-collation result headings use shorter titles for four sources

**Rechecked:** 2026-09-25.

`searchdicts.php` result headings now read "Dictionary of Jewish Babylonian Aramaic", "Dictionary of Jewish Palestinian Aramaic", "Levy Chaldäisches Wörterbuch" and "Schulthess". The form (`searchdicts.html`) keeps the full titles and codes; the other 11 sources are unchanged. Detailed evidence: `docs/research/issue-174-dictionary-labels.md`.

Sources:

- https://cal.huc.edu/searchdicts.html
- https://cal.huc.edu/searchdicts.php (POST `dict=B`, `page=100`)

**Implication:** each source accepts its form label or its current heading label; any other dictionary label fails closed.


## R-036 — The Mandaic catalogue links texts with the Roman script selector and title-text rows

**Rechecked:** 2026-09-25.

`show_Mandaic.php?R1=74` now renders a Roman/Mandaic-script toggle and grouped list items. Each item is `<a href="/showsubtexts.php?subtext=<file>&cset=R">Title</a>` (or `get_a_chapter.php?file=<file>&cset=R`) followed by an information link. `cset` selects the rendering script only: `R` is CAL code, `M` is Standard Transliteration and `J` is Mandaic script. The `cset=M` page route still works. Detailed evidence: `docs/research/issue-169-mandaic-catalogue.md`.

Sources:

- https://cal.huc.edu/show_Mandaic.php?R1=74
- https://cal.huc.edu/showsubtexts.php?subtext=74410&cset=R

**Implication:** Mandaic catalogue children accept `cset=R` or `M`, and titles come from the link text; page routing is unchanged.

## R-035 — Text pages render each line as a two-cell table row

**Rechecked:** 2026-09-25.

Current `get_a_chapter.php` pages render lines in `<table class="text-display">`, one row per line. The first cell holds the display coordinate, either as a `comment.php` link or as plain text with an optional "[ai]" `ask_ai_prompt.php` link. The second cell holds only lexical token links. The text-page line splitter breaks at every cell, so the coordinate and comment link were silently lost. Detailed evidence: `docs/research/issue-182-text-row-coordinates.md`.

Sources:

- https://cal.huc.edu/get_a_chapter.php?file=56000&sub=112&page=0
- https://cal.huc.edu/get_a_chapter.php?file=62057&page=0

**Implication:** table-layout pages are read per row, with `display_coordinate` and `comment_url` taken from the coordinate cell; any unexpected row shape fails closed.


## R-034 — Paginated text pages share the pagination marker line with navigation links

**Rechecked:** 2026-09-25.

Current paginated `get_a_chapter.php` pages (BT Berakhot `71001`, BT Avodah Zarah `71026`) render `Page N of M (T lines total)` in a `<center>` together with the `previous page` / `next page` / `show all` links, directly after the "Hide manuscript variants" toggle. A second, bottom copy omits the line total. No line consists of the marker alone. Detailed evidence: `docs/research/issue-167-talmud-pagination.md`.

Sources:

- https://cal.huc.edu/get_a_chapter.php?file=71001&page=1
- https://cal.huc.edu/get_a_chapter.php?file=71001&page=49

CAL also clamps a page beyond the last page to its last page (`71001` with `page=50` renders `Page 50 of 50`; a one-page text renders its only page), so a page mismatch is no longer always upstream drift.

- https://cal.huc.edu/get_a_chapter.php?file=71001&page=50

**Implication:** a marker is the leftover text of a non-token line after its link texts are removed, and it must be exactly `Page N of M` with an optional line total; every marker on a page must agree. A clamp to CAL's last page is reported as an `invalid_input` range error.


## R-033 — Subdivided text pages put file plus subtext in the file-info coordinate

**Rechecked:** 2026-09-25.

On pages requested with `sub`, `get_a_chapter.php` now renders the file-information link as `get_file_info.php?coord=<file_id><sub>`, with the submitted `sub` value verbatim (`coord=56000112`, `coord=74410001`). The earlier layout used the bare file identifier. CAL matches an unpadded `sub` as a prefix (`70700` with `sub=1` returns bowls 100–125). Detailed evidence: `docs/research/issue-166-subtext-file-info.md`.

Sources:

- https://cal.huc.edu/get_a_chapter.php?file=56000&sub=112&page=0
- https://cal.huc.edu/get_a_chapter.php?cset=M&file=74410&sub=001
- https://cal.huc.edu/get_a_chapter.php?file=70700&sub=1&page=0

**Implication:** the text-page parser accepts the bare file identifier or the file identifier followed by the exact submitted `sub`; anything else fails closed. Callers must pass `subtext_id` exactly as CAL returned it.


## R-032 — External-citation source lists repeat abbreviations for distinct works

**Rechecked:** 2026-09-24.

The Syriac external-source list (`display.notext.abbrevs.php?dial1=6&dial=6`, 702 rows) lists five abbreviations (`EbPar`, `JS`, `Lag,`, `PO`, `Th`) in two adjacent rows each. The descriptions differ (different editions or works) and the citations link is identical. This is CAL's own data, and abbreviations are not unique keys. Detailed evidence: `docs/research/issue-153-external-sources-repeated-abbreviations.md`.

Source:

- https://cal.huc.edu/display.notext.abbrevs.php?dial1=6&dial=6

**Implication:** source rows are returned exactly as listed, repeats included; the existing link/label check guarantees shared abbreviations share one citation list. Public schema and request counts are unchanged.

## R-031 — Current Targum concordance and Hebrew-reflex pages moved their headings

**Rechecked:** 2026-09-24.

Two bounded POSTs showed that `showtargumKWIC.php` now identifies itself (`CAL: Targum KWIC counts for <key>`) only in the page `<title>`, with an `<h3>` statement in the body, a `<td>` label row (`Torah` plus an `&nbsp;` filler cell), and the total as a single-cell row inside the table. `getOmtlemma.php` moved its `<source> correspondences to <Hebrew lemma>` heading from `<h1>` to `<h3>`, and its header row uses `<td>` cells. Row, link, count and selector semantics are unchanged. Detailed evidence: `docs/research/issue-152-targum-concordance-reflex-drift.md`.

Sources:

- https://cal.huc.edu/showtargumKWIC.php (POST `lemma=klb&pos=N`)
- https://cal.huc.edu/getOmtlemma.php (POST `R1=1751`)

**Implication:** result headings are read from `h1`, `h3` and `title`, and every identifying heading must name the submitted key; the body statement must name the submitted key; the in-table total form is accepted; header rows may be all-`th` or all-`td`. The current page's `Torah` label row (with CAL's literal `&nbsp;` filler) is not applied as a grouping to later rows, because the rows after it include Prophets and Writings. Rows carry `section: null`, and the result gains an additive `section_labels` field (decision D-015). Request counts are unchanged.

## R-030 — Citation context for Babylonian Talmud texts uses the bablex.php token family

**Rechecked:** 2026-09-24.

A lexicon citation `BT Git 48a(50)` (`full_coordinate` `7101801048150`) led to a complete, well-formed `showachapter.php` context page. Its target row is present, bold and comment-linked, but every lexical token uses `bablex.php?coord=…&word=…`, the second token family already recorded for text pages in R-024. The citation-context parser recognized only `getlex.php`, so it found no text rows. This is a long-standing gap for Babylonian Talmud citations, not new drift. Detailed evidence: `docs/research/issue-151-citation-context-bablex.md`.

Source:

- https://cal.huc.edu/showachapter.php?fullcoord=7101801048150

**Implication:** citation-context rows accept both token families with identical validation; a row mixing families fails closed. Public schema and request counts are unchanged.
## R-029 — Current bibliography result pages embed legacy `<p>` records in one card

**Rechecked:** 2026-09-24.

Four bounded requests (lemma `br N`, author `Sokoloff, Michael`, keyword `Vocab`, and one no-data lemma) showed that bibliography result pages now wrap CAL's whole legacy result document, including `<TITLE>CAL BIBLIOGRAPHY SEARCH</TITLE>`, in a single `div.card`, with one `<p>` per bibliographic record. Author and keyword pages include empty placeholder links (`getbiblemma.php?myauthor=` with no label), and the explicit no-data marker now sits inside the card. The one-record-per-card parser merged every work into one record (silent wrong data), rejected the placeholders, and broke empty results.

Detailed evidence: `docs/research/issue-150-bibliography-drift.md`.

Sources:

- https://cal.huc.edu/getbiblemma.php?myauthor=br+N
- https://cal.huc.edu/getbibauthor.php?myauthor=Sokoloff%2C+Michael
- https://cal.huc.edu/getbibsigla.php?myauthor=Vocab

**Implication:** records are parsed per `<p>` within result cards, with fail-closed checks against text outside records; title metadata is ignored; links with both an empty label and an empty target are omitted as CAL placeholders; a marker-only card is the no-data container. The earlier one-card-per-record shape remains a strict fallback. Public schema and request counts are unchanged.

## R-028 — Current concordance/KWIC pages use display labels, BR-line hits, and per-form dialect summaries

**Rechecked:** 2026-09-24.

A user-level MCP end-to-end run found `cal_text_concordance`, `cal_kwic_texts`, and `cal_kwic_dialect` failing live with parser drift, and the fixed `live_smoke` release gate failing at `text_concordance`. Six bounded research requests established three upstream changes:

- `newconcord.php` lemma links now display CAL's label (for example `ˀb, ˀbˀ n.m.`) instead of the lemma key; the key remains in the validated `showKWIC.php` link;
- `showdialectKWIC.php` and `show1dialectKWIC.php` render each hit as BR-delimited before/target/after lines rather than table rows;
- `show1dialectKWIC.php` reports results per lemma form (`N example(s) found for <form> in dialect <id>` / `No examples found for <form> in dialect <id>`, optional `Grand total … across all forms`), may include related-form hits (for example `nqh N` when `n)qh N` was requested), and uses a new `U` hit charset for Syriac.

Detailed evidence: `docs/research/issue-149-concordance-kwic-drift.md`.

Sources:

- https://cal.huc.edu/newconcord.php?text=13250&cset=S
- https://cal.huc.edu/showdialectKWIC.php (POST)
- https://cal.huc.edu/show1dialectKWIC.php?lemma=n%29qh&pos=N&texts=6

**Implication:** concordance rows gain an additive `label`; KWIC hits are parsed from BR lines with the table parser kept as a strict compatibility fallback; KWIC `context` is CAL's rendered target line and additive `target_text` is CAL's highlighted token; dialect KWIC results gain additive `forms` and per-hit `form_lemma_key`, preserving every CAL hit under CAL's own form key; `U` becomes an accepted KWIC charset. Request counts and bounds do not change.

## R-027 — CAL full lexicon entries now inline non-content stylesheet text

**Rechecked:** 2026-09-05.

Bounded live evidence recorded in issue #32 shows that `cal_entry_web.php?lemma=b+s` now emits `fullentry.css` inside a `<style>` element in the page head. CAL-MCP's shared semantic HTML parser previously collected text from every element, so CSS tokens such as `fullentry.css` could satisfy the generic lemma-header grammar before the rendered lexical header and silently replace `entry.lemma` with stylesheet text. The same contamination was observed on unrelated full entries, while existing reduced pre-drift fixtures did not contain head-level style/script content.

Source: https://cal.huc.edu/cal_entry_web.php?lemma=b+s and issue #32, captured 2026-09-05. The reduced regression fixture `tests/fixtures/cal/entry_b_s_inline_style.html` preserves only the semantic shape needed to reproduce this drift.

**Implication:** semantic HTML extraction excludes non-rendered `style` and `script` subtrees before lexicon parsing. Public lexicon models, request behavior, and lemma-header heuristics remain unchanged.

## R-018 — CAL entries may begin with parenthetical senses at depth 1

**Rechecked:** 2026-09-05.

Issue #31 records a bounded live check of `oneentry.php?lemma=)lh N`: the current CAL entry begins its sense outline `(1) (2) (3) (4)` without a preceding plain-numbered enclosing sense. The same parser failure class was observed for `)r( N`. CAL-MCP previously excluded path index 0 when placing parenthetical siblings, so the first `(1)` produced `(1,)` but `(2)` then raised instead of becoming sibling path `(2,)`.

Source: https://cal.huc.edu/oneentry.php?lemma=)lh%20N and issue #31, captured 2026-09-05. Offline regression coverage uses a reduced semantic fixture rather than an archived full CAL page.

**Implication:** parenthetical numbering is placed using the deepest matching predecessor across every existing path depth, including depth 1. Non-consecutive/unplaceable jumps still fail closed; no enclosing level is invented when CAL omits one. Trailing plain-number tokens observed on the live page remain a separate unresolved parsing question and are outside this correction.

## R-019 — Current Syriac Studies module composes specialist and general CAL surfaces

**Rechecked:** 2026-09-05.

A bounded live audit of CAL's current Syriac Studies module found four public entry points: available Syriac texts by category, citations from texts absent from the online CAL database, CAL headwords occurring in Syriac but absent from *A Syriac Lexicon*, and MT/Peshitta verse comparison.

The Peshitta comparison form currently submits one biblical `bookname`/chapter/verse POST to `showpesh.php`. Gen 1:1 returned the exact heading `MT and Peshitta for Gen 1:1`, Hebrew MT text, a CAL-owned `Peshitta:` link to the ordinary text browser, and Syriac Peshitta text. Gen 1:99 returned HTTP 200 with the matching heading plus CAL's explicit `error in coord` marker. Result HTML contains inline styles, so non-rendered `style`/`script` subtrees cannot participate in semantic marker detection.

`AvailSyr.html` currently exposes four Bible-oriented static lists plus dynamic Syriac categories. A representative dynamic category returned both direct `get_a_chapter.php` text links and grouped `showsubtexts.php?keyword=...` navigation, together with file-information links. These are one-level discovery results; group expansion and text browsing remain explicit caller actions.

`NotInSL.html` currently exposes nine CAL-curated lists (adjectives, adverbs, miscellaneous, nomina agentis, abstracts, verbal nouns, verbs, masculine nouns, feminine nouns) for Syriac headwords not listed in the Brockelmann/Sokoloff *A Syriac Lexicon*. Individual list pages expose ordered CAL lexicon links plus rendered notes/glosses. This is CAL's own research comparison surface and must not be represented as a SEDRA query or as adapter-inferred dictionary equivalence.

The module's “citations from texts not in the CAL database” link is the Syriac-filtered entry to the same external/non-online-text citation family tracked by issue #13, so issue #11 should not duplicate that public operation. General Syriac-script lexical lookup likewise remains the existing CAL-MCP lexicon surface.

Sources and bounded probe details are recorded in `docs/research/issue-11-syriac.md`. Two temporary branch-only probes made eight CAL requests total and were removed before planning; normal CI remains offline.

**Implication:** issue #11 should expose three bounded task-level specialist operations: Syriac text-category discovery, CAL's curated missing-from-*A Syriac Lexicon* lists, and MT/Peshitta verse comparison. Each public operation performs exactly one CAL request and returns CAL provenance. External citations, direct text reading, grouped text expansion, lexicon-entry fetching, and verse traversal remain separate caller-controlled operations.

## R-020 — Current external-text citation finder is an explicit dialect → source → citation workflow

**Rechecked:** 2026-09-05.

CAL's current search page exposes citations from texts not present in the online database as a separate Citation Finder. The live UI is an explicit three-stage workflow: `citfinder.html` lists 19 ordered CAL dialect IDs/labels; choosing one dialect opens a source-abbreviation list headed as texts with citations but no full text yet; choosing one exact source abbreviation opens that source's ordered lexical citations. A bounded Syriac probe returned 703 source rows in one approximately 317 KB response, and `1CorH` returned three citation rows. No pagination/continuation control was observed on these representative pages.

Current source rows preserve a CAL source abbreviation plus rendered bibliographic/source description. Current citation rows expose a same-origin CAL lexical-entry link with canonical lemma key, rendered lemma/POS, external-source citation string, lexical gloss, source-language citation text when present, and optional English translation. The lexical link is an explicit follow-up into entry context; the absent source is not thereby available through CAL's ordinary online text browser. A source abbreviation such as `1CorH` must therefore not be represented as a CAL online `file_id` or guessed passage coordinate.

CAL currently returns explicit HTTP-200 empty markers for both stages: `No extra citations for that dialect are currently found.` and `No citations for "…" are currently stored.` A successful-looking page with neither recognized semantic rows nor the corresponding marker is parser drift rather than an empty result.

Branch-only research made seven fixed, bounded CAL GETs across three runs (three structural pages, two negative pages, and one repeat of those same two negative pages after correcting a local visible-text extractor). All requests had hard time/size caps; no dialect/source/citation enumeration or lexical-entry traversal occurred. Detailed evidence and raw semantic shapes are recorded in `docs/research/issue-13-external-citations.md`.

**Implication:** expose caller-controlled dialect discovery, one-dialect source discovery, and one-source citation retrieval as separate bounded operations. Keep private endpoint/form fields hidden, do not invent pagination, never auto-follow lexical-entry links, and keep this result model distinct from both English citation-text search and online-corpus passage retrieval.


## R-021 — Current full-entry citations expose structural item/separator semantics

**Rechecked:** 2026-09-06.

Issue #41's focused `br N` probe shows that current `cal_entry_web.php` citation groups wrap each citation in `span.cit-item` and wrap the punctuation *between* citations in `span.cit-sep`. Citation content itself may contain semicolons: the current `BT Yev 76a(40)` citation includes one inside its transliteration and another clause semicolon in the rendered translation. Current entries also pre-render hidden alternate `span.cit-script` representations and distinguish unlinked references with `span.cit-ref-plain`.

The old semantic parser flattened those boundaries and then treated whitespace-adjacent semicolons as citation separators. That can inflate a rendered three-citation group to four or more parsed citations and trigger the otherwise-correct citation-count drift guard. It can also mix hidden alternate script text into the visible citation representation.

Source: https://cal.huc.edu/cal_entry_web.php?lemma=br+N and `docs/research/issue-41-lexicon-citation-count-drift.md`, rechecked 2026-09-06 with three fixed requests to that single entry (final structural probe run `34024100169` used the production CAL-MCP User-Agent). No neighboring entries were enumerated.

**Implication:** current structural `cit-sep` boundaries must take precedence over punctuation splitting; hidden alternate `cit-script` variants must not contaminate visible citation text; safely delimited `cit-ref-plain` references may be preserved with a null URL. Legacy/reduced markup without structural separators may retain the existing semicolon fallback. Rendered citation-count equality remains a strict fail-closed invariant.


## R-022 — Current one-text concordance rows are inline BR-delimited streams

**Rechecked:** 2026-09-06.

A release-blocking live check of `newconcord.php?text=13250&cset=S` found that CAL still returns HTTP 200, the expected `Frequencies of lemmas in text 13250` marker, and 41 `showKWIC.php` lemma links with the same `lemma`, `charset`, and `texts` semantics. The row layout has changed from the reduced table-row shape captured on 2026-09-05: current rows are rendered in an inline `span` stream and separated by `<br>`, for example an integer frequency and dotted filler followed by the lemma link, `:`, and the gloss.

One fixed branch-only probe made one CAL GET with a 20-second timeout and 256 KiB cap; it returned 7,071 bytes. No text enumeration, pagination, KWIC follow-up, or retry occurred. Detailed evidence and the reduced structural fixture are recorded in `docs/research/issue-42-text-concordance-parser-drift.md`.

Source:

- https://cal.huc.edu/newconcord.php?text=13250&cset=S

**Implication:** the single-text concordance parser recognizes the current BR-delimited semantic rows while retaining the earlier table parser as a strict compatibility fallback. Required frequency/link/gloss semantics and link/request consistency checks remain fail-closed. The public MCP schema, request contract, provenance, and one-request bound do not change.

## R-023 — v0.1 release validation separates built-artifact proof from capped live drift smoke

**Rechecked:** 2026-09-06.

Issue #15 release research established two distinct validation boundaries. The existing `tests/test_bootstrap.py` proves the editable development install can launch `cal-mcp` over stdio and expose the frozen 26-tool schema without CAL traffic, but current CI does not yet build a wheel/sdist and install that wheel into a fresh environment. Release evidence therefore requires a built-artifact clean-install/stdio check rather than reusing editable-install success as proof of publishability.

A previous branch-only release probe (workflow run `33995822616`) exercised eight representative released service families under concurrency 1, retries disabled, cache disabled, and a hard **9 CAL-request** budget. It exposed genuine current-CAL parser drift in lexicon and one-text concordance (#41/#42), both now fixed through their own research/TDD/review loops. The same probe showed that the MCP client may return a tool result with `is_error=true` for server-side parser failure, so a returned result object cannot be treated as smoke success without inspecting that flag.

Current shared-client exceptions distinguish network/upstream failures from `CalContentError`, while each domain exposes a dedicated parser-error subclass. Permanent live smoke can therefore diagnose domain parser exceptions as drift and network/upstream exceptions as availability/HTTP failures without changing the public MCP error contract. The researched smoke set remains nine requests total: one two-request exact lexicon success plus one request each for text search, text concordance, bibliography, dictionary collation, external citations, Targum comparison, and Syriac Peshitta comparison. No result links or pagination are followed.

PyPI's current official Trusted Publishing documentation recommends GitHub Actions OIDC with job-level `id-token: write` and the PyPA publishing action. PyPI must separately trust the repository/workflow (and optionally a GitHub `pypi` environment); repository code cannot infer or create that account-side trust. A pending publisher can create a new project on first upload but does not reserve its name before publication.

Sources and full evidence: `docs/research/issue-15-v0.1-release.md`; https://docs.pypi.org/trusted-publishers/; release research workflow run `33995822616`.

**Implication:** v0.1 ships an offline built-wheel/stdio gate and a separate opt-in/scheduled nine-request drift smoke. Publishing automation is compatible with PyPI Trusted Publishing, but documentation must not claim a successful PyPI release until the external trust prerequisite and actual upload have succeeded.


## R-024 — Current CAL text pages use more than one lexical-token link family

**Rechecked:** 2026-09-08.

Issue #79's bounded Tel Dan probe established that current `get_a_chapter.php?file=13250` rows link lexical tokens through `getlex.php?coord=...&word=...&hasvariant=0`, while the current paginated `BT AZ` text (`file=71026`) still exposes `bablex.php?coord=...&word=...` token links. Tel Dan with and without upstream `page=0` returned the same 9,002-byte HTML, so page-number mapping is not the regression. The file-info link, unpaginated line text, decimal token coordinates/word indexes, and comment links remain semantically intact.

Detailed evidence and probe load are recorded in `docs/research/issue-79-tel-dan-text-page.md`. The branch-only probe made four fixed Tel Dan GETs total and was removed before planning; no linked token analysis or neighboring text/page traversal occurred.

**Implication:** text-page parsing must recognize both current CAL lexical-token endpoint families while preserving the exact returned URL and existing coordinate/index validation. Do not infer tokens from unlinked text, replace one endpoint globally with the other, or expose CAL-private link parameters in the MCP schema.


## R-025 — Mandaic collection 74 mixes subdivided and direct text routes

**Rechecked:** 2026-09-08.

Issue #97 corrects the route assumption introduced by #95. Current CAL does not expose every `74...` Mandaic file through the same `showsubtexts.php` / `get_a_chapter.php?...&sub=NNN` workflow. A bounded live menu audit found both route kinds inside the same collection and even inside the same numeric subfamilies.

The current live menu snapshot exposes these files through `showsubtexts.php`: `74401`, `74402`, `74410`, `74411`, `74421`, `74422`, `74423`, `74428`, `74430`, `74432`, `74701`, and `74923`. It exposes `74420`, `74424`, `74425`, `74426`, `74427`, `74429`, `74431`, and `74501` directly through `get_a_chapter.php`. Independent browser/index evidence also shows direct `74716`/`74717` and subdivided `74700`. Therefore neither `74`, `744`, nor `747` is a valid route discriminator.

A post-review bounded direct-page probe of `74717` confirmed HTTP 200 with the expected file heading, ordinary line/token coordinates, the first `getlex.php` token link, and no previous/next-page navigation. The reduced `tests/fixtures/cal/text_page_mandaic_direct_74717.html` fixture preserves only those parser-relevant semantics.

Five fixed branch-only CAL GETs were made in total: four menu/rendering requests while resolving route classification and one direct-page request for `74717`. Each had a 15-second timeout and 512 KiB cap. No token, comment, next-page, catalogue-child, or other returned navigation link was followed. Detailed evidence is in `docs/research/issue-97-mandaic-route-scope.md`.

**Implication:** `cal_text_page` keeps one public schema and one-request behavior, but private Mandaic route selection must be per-file. A current allowlist selects only CAL files explicitly observed as subdivided; all other `74...` files use the direct Mandaic page-1 route rather than inventing `sub=NNN`. Explicit public `subtext_id` and non-Mandaic routing remain unchanged. New subdivided files require researched allowlist updates rather than prefix inference or runtime discovery.

### 2026-09-09 exact-head review amendment

A fresh independent check of the same current Mandaic menu found three subdivided `747xx` rows omitted by the first partial observation: `74702`, `74711`, and `74714`. The current `747xx` subdivided set is therefore `74700`, `74701`, `74702`, `74711`, and `74714`; neighboring rows `74703`–`74710`, `74712`–`74713`, and `74715`–`74723` are direct links. This confirms again that `747` is a mixed route family and cannot be handled by a prefix rule.

The review did not traverse those texts. It classified the menu's own destination hrefs and recorded the complete current `747xx` mapping in `docs/research/issue-97-review-747xx-route-addendum.md`.

**Amended implication:** the private subdivided-file allowlist must include `74702`, `74711`, and `74714` in addition to the previously researched entries. Any future route change still requires explicit current-menu evidence rather than arithmetic inference or runtime probing.

## R-026 — Current Syriac Peshitta book rows use shallow catalogue navigation

**Rechecked:** 2026-09-09.

Current CAL OT and NT Peshitta category pages no longer expose their biblical book rows as direct text-page links. Representative current rows such as `62001 P Gn` and `62040 P Mt` link to `showsubtexts.php` with a decimal book selector; the immediate destination is a shallow chapter catalogue whose chapter rows then use ordinary `file` + `sub` text-page navigation. This route is distinct from Syriac grouped navigation selected by CAL's `keyword` field.

Focused evidence and bounded request details are recorded in `docs/research/issue-110-syriac-peshitta-subtext-routing.md`.

**Implication:** Syriac category parsing preserves three navigation kinds: direct `text`, grouped `group`, and shallow `catalogue`. Peshitta book rows use `catalogue` and compose explicitly through `cal_text_catalogue(category_id=<returned upstream_id>)`; CAL-MCP does not prefetch chapters or expose private selector/form controls.

