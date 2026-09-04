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

## Open research questions

These should be answered by implementation tickets rather than guessed globally:

1. What exact request parameters do the current English gloss/citation search forms submit?
2. What is the canonical endpoint and parameter model for basic and advanced KWIC/concordance?
3. Which dialect identifiers are stable machine values versus display labels?
4. How is text pagination represented and how should passage boundaries be modeled?
5. Which CAL identifiers are stable enough to expose as public adapter identifiers?
6. Which Targum and Syriac operations compose cleanly into general tools and which deserve specialist tools?
7. Does the bibliography interface expose stable query parameters suitable for typed search?
8. What minimal cache policy gives useful duplicate-request suppression without retaining a meaningful CAL dataset?
9. Does CAL expose `robots.txt` or future machine-access guidance that should alter request policy?
10. What subset of upstream HTML can be kept as test fixtures while respecting copyright and avoiding unnecessary CAL content retention?

## Research update procedure

When new evidence changes an assumption:

1. add a dated `R-xxx` entry or dated amendment;
2. link the exact upstream page, captured fixture provenance, or upstream communication;
3. state the implementation/architecture consequence;
4. update `wiki/decisions.md` if a durable project decision changes;
5. update affected tickets/acceptance criteria before implementation continues.
