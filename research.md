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

## Open research questions

These should be answered by implementation tickets rather than guessed globally:

1. What is the canonical endpoint and parameter model for basic and advanced KWIC/concordance?
2. Which dialect identifiers are stable machine values versus display labels?
3. Do specialist text/module surfaces use pagination or coordinate shapes that differ materially from the general text browser?
4. Does CAL document any stronger stability guarantee for file/subtext/category identifiers than is observable from the current public links?
5. Which Targum and Syriac operations compose cleanly into general tools and which deserve specialist tools?
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

## R-017 — CAL full lexicon entries now inline non-content stylesheet text

**Rechecked:** 2026-09-05.

Bounded live evidence recorded in issue #32 shows that `cal_entry_web.php?lemma=b+s` now emits `fullentry.css` inside a `<style>` element in the page head. CAL-MCP's shared semantic HTML parser previously collected text from every element, so CSS tokens such as `fullentry.css` could satisfy the generic lemma-header grammar before the rendered lexical header and silently replace `entry.lemma` with stylesheet text. The same contamination was observed on unrelated full entries, while existing reduced pre-drift fixtures did not contain head-level style/script content.

Source: https://cal.huc.edu/cal_entry_web.php?lemma=b+s and issue #32, captured 2026-09-05. The reduced regression fixture `tests/fixtures/cal/entry_b_s_inline_style.html` preserves only the semantic shape needed to reproduce this drift.

**Implication:** semantic HTML extraction excludes non-rendered `style` and `script` subtrees before lexicon parsing. Public lexicon models, request behavior, and lemma-header heuristics remain unchanged.

## R-018 — CAL entries may begin with parenthetical senses at depth 1

**Rechecked:** 2026-09-05.

Issue #31 records a bounded live check of `oneentry.php?lemma=)lh N`: the current CAL entry begins its sense outline `(1) (2) (3) (4)` without a preceding plain-numbered enclosing sense. The same parser failure class was observed for `)r( N`. CAL-MCP previously excluded path index 0 when placing parenthetical siblings, so the first `(1)` produced `(1,)` but `(2)` then raised instead of becoming sibling path `(2,)`.

Source: https://cal.huc.edu/oneentry.php?lemma=)lh%20N and issue #31, captured 2026-09-05. Offline regression coverage uses a reduced semantic fixture rather than an archived full CAL page.

**Implication:** parenthetical numbering is placed using the deepest matching predecessor across every existing path depth, including depth 1. Non-consecutive/unplaceable jumps still fail closed; no enclosing level is invented when CAL omits one. Trailing plain-number tokens observed on the live page remain a separate unresolved parsing question and are outside this correction.
