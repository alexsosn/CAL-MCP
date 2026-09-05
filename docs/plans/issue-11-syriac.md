# Issue #11 plan — bounded CAL Syriac Studies tools

**Plan date:** 2026-09-05

This plan follows the repository loop: research → plan → test-only RED → minimal implementation → GREEN → documentation → independent skeptical review → review-regression RED/GREEN if needed → fresh exact-SHA re-review → merge.

## Public contract

Expose three task-level operations:

```text
cal_syriac_texts(category)
cal_syriac_missing_words(category)
cal_syriac_peshitta_parallel(book, chapter, verse)
```

Do **not** expose a duplicate Syriac external-citation wrapper. The corresponding Syriac Studies link is the dialect-filtered form of the generic non-online-text citation capability owned by issue #13. Do not add a second generic Syriac lexicon lookup or text reader; existing `cal_lexicon_lookup` and `cal_text_page` own those operations.

## Input contract and bounds

### Syriac text category

`category` is one exact public slug from this adapter-owned finite set:

- `ot-peshitta`
- `old-syriac-gospels`
- `nt-peshitta`
- `apocryphal-pseudepigraphal`
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

Map these internally to CAL's current four static category pages or dynamic category values 5–20. Submit exactly one GET. CAL filenames and the private numeric `category` parameter must not appear in the public MCP schema.

### Missing-from-*A Syriac Lexicon* category

`category` is one exact public slug:

- `adjectives`
- `adverbs`
- `miscellaneous`
- `nomina-agentis`
- `abstracts`
- `verbal-nouns`
- `verbs`
- `masculine-nouns`
- `feminine-nouns`

Map each slug internally to CAL's current curated list page. Submit exactly one GET. The result describes CAL's comparison against Brockelmann/Sokoloff *A Syriac Lexicon*; it is not a SEDRA query and must not imply adapter-generated dictionary equivalence.

### MT/Peshitta verse

- `book`: one exact current CAL biblical display label from the same 36-book selector used by the Targum module.
- `chapter`: positive integer, maximum 999.
- `verse`: positive integer, maximum 999.
- Submit one POST to CAL's current comparison endpoint with the private book/chapter/verse form fields.

The public result preserves requested reference, MT text, Peshitta text, CAL's rendered Peshitta label/link, typed status, and provenance.

## Typed models

Add `src/cal_mcp/syriac.py` with specialist models rather than overloading unrelated result types:

- `SyriacTextNavigationKind` — `text` or `group`;
- `SyriacTextItem` — CAL upstream identifier, rendered label, navigation kind, same-origin navigation URL, optional same-origin file-information URL;
- `SyriacTextCategoryPage` / result — public category slug, CAL category label, ordered items, provenance;
- `SyriacMissingWord` — CAL lemma key, rendered linked label, rendered note/gloss text if present, same-origin entry URL;
- `SyriacMissingWordsPage` / result — public category slug, CAL list heading/description, ordered entries, upstream dictionary attribution, provenance;
- `SyriacPeshittaStatus` — `found` / `not_found`;
- `SyriacPeshittaPage` / result — requested biblical reference, MT text, Peshitta label/text/chapter URL, provenance;
- `SyriacProvenance` — source, source URL, retrieval time, operation, plus operation-specific public/upstream identifiers.

Do not infer textual relationships, dictionary equivalence, normalized version names, or source taxonomy beyond CAL's rendered semantics.

## Parser contracts

All new HTML parsers must ignore `style` and `script` subtrees **before** semantic state transitions or data collection and must fail closed on an unclosed ignored subtree. This is required by current CAL pages and follows the hardened lexicon/Targum parser pattern.

### Text-category page

Require one expected category title/heading matching the selected public category's current CAL display label.

Parse ordered result rows. Each accepted item must expose exactly one supported navigation target:

- direct text: same-origin `get_a_chapter.php` with one decimal `file` identifier; or
- grouped navigation: same-origin `showsubtexts.php` with one decimal `keyword` identifier.

If a file-information link is present, require same-origin `get_file_info.php` with one decimal `coord` equal to the item's upstream identifier. Preserve its URL but do not follow it.

Reject cross-origin links, repeated/blank identifiers, conflicting navigation kinds, detached information links, or a successful-looking page with no recognized items. Do not recursively expand groups.

For the four static Bible category pages, accept the same direct/group item model; do not special-case them into automatic text traversal.

### Missing-word list

Require CAL's current semantic list heading/intro for the selected missing-word category, including the relationship to *A Syriac Lexicon*. Parse only linked CAL lexicon-entry rows in document order.

For each row:

- require a same-origin CAL lexicon entry target from the recognized lexicon family;
- extract exactly one canonical CAL lemma key from the link query;
- preserve the rendered linked label without normalization;
- preserve the rendered trailing note/gloss as text when present;
- do not fetch the full entry.

Reject duplicate/contradictory lemma-link semantics, cross-origin entry links, or pages lacking the expected heading and at least one valid list row. No empty marker was established by live research, so do not manufacture an empty success state.

### MT/Peshitta comparison

Require the exact semantic heading `MT and Peshitta for <book> <chapter>:<verse>` to match the submitted public reference.

A found page must expose exactly:

- nonempty rendered MT Hebrew text;
- one rendered `Peshitta:` source label/link;
- nonempty rendered Syriac Peshitta text;
- a same-origin Peshitta chapter link targeting `get_a_chapter.php`.

Validate the Peshitta source link's `file` and optional `sub` values as CAL decimal identifiers, but preserve the full same-origin URL as returned/resolved. Do not expose or interpret the private `cset` query parameter as public schema.

If CAL's explicit `error in coord` marker is present, return typed `not_found` only when no successful MT/Peshitta pair is present. A contradictory page containing both the error marker and valid comparison data is parser drift. A matching heading with neither valid data nor explicit error is parser drift.

Ignore previous/next verse links for result semantics and never follow them automatically.

## Service/request contracts

`SyriacService` uses the shared `CalHttpClient` only.

- `texts(category)` → one GET to the mapped static/dynamic category surface;
- `missing_words(category)` → one GET to the mapped curated list page;
- `peshitta_parallel(book, chapter, verse)` → one POST to the current comparison surface.

Use operation-specific cache namespaces. All input validation occurs before transport. No operation issues a second request from its parser or service.

## Public MCP schema

Register exactly:

```text
cal_syriac_texts(category)
cal_syriac_missing_words(category)
cal_syriac_peshitta_parallel(book, chapter, verse)
```

The MCP schemas must not expose CAL-private names/values such as `bookname`, numeric `category`, `dial`, `cset`, static source filenames, or endpoint paths. Tool descriptions should explain caller-controlled composition with `cal_text_page`, `cal_lexicon_lookup`, and future issue-#13 external citations.

## Test-first RED sequence

Before production code, add reduced semantic fixtures/tests covering at minimum:

1. a dynamic Syriac text category with ordered grouped and direct text items plus matching info links;
2. a static Bible category page with direct CAL text items;
3. same-origin link resolution and exact upstream identifiers;
4. cross-origin, repeated-ID, mismatched-info-ID, conflicting-navigation, and unrecognized-empty category pages fail closed;
5. a reduced missing-verbs list preserving ordered CAL lemma keys, Unicode/transliteration labels, notes/glosses, and entry URLs;
6. malformed/cross-origin/duplicate-identifier missing-word rows fail closed;
7. a missing-word page with no recognized semantic list rows fails closed rather than becoming empty success;
8. Gen 1:1 MT/Peshitta comparison preserves exact Hebrew/Syriac Unicode, label, and chapter URL;
9. Gen 1:99 explicit `error in coord` → typed `not_found`;
10. heading/request mismatch, error+data contradiction, missing MT/Peshitta data, wrong endpoint family, or cross-origin source link → parser drift;
11. `style`/`script` semantic-marker contamination is ignored for all parser families;
12. unclosed ignored subtrees fail closed for all parser families;
13. invalid public category, missing-word category, book, chapter, and verse fail before transport;
14. exact one-request request mapping/provenance for all three service operations;
15. no automatic group, text, lexicon, verse-navigation, or citation follow-up occurs;
16. MCP introspection exposes exactly the three public task-level tools and excludes private CAL parameters.

The valid primary RED must have install, Ruff lint/format, and strict mypy green while pytest fails only on the intended missing `cal_mcp.syriac` module/public tools.

## Minimal GREEN implementation

Implement only the models, finite mappings, validators, small fail-closed parsers, service methods, and MCP registration needed by the RED suite. Reuse established shared concepts/helpers only where doing so does not couple one specialist module to another module's private implementation details. If the 36-book mapping needs reuse, extract a small neutral shared biblical-coordinate helper rather than importing a private Targum constant.

Do not add another HTTP stack, generic crawler, automatic `showsubtexts` expansion, automatic text/lexicon fetch, external-citation implementation, SEDRA fallback, dictionary matching, pagination invented from response size, or a local Syriac corpus/index.

## Documentation gate

Before independent review:

- add `docs/tools/syriac.md`;
- update README implemented-surface summary and documentation map;
- document all public category slugs and missing-word category slugs;
- document the MT/Peshitta not-found semantics and one-request bound;
- state explicitly that the missing-word lists are CAL's comparison against *A Syriac Lexicon*, not SEDRA;
- state that external/non-online-text citations are owned by issue #13 and are not duplicated here;
- explain caller-controlled composition with text and lexicon tools;
- update fixture provenance.

## Independent review gate

Review the exact final SHA skeptically for:

- duplicate endpoint-shaped tools that should compose with existing text/lexicon/#13 capabilities;
- leaking CAL private filenames/form fields/category numbers into public schemas;
- normalizing or inventing CAL source/category/dictionary semantics;
- accepting `style`/`script` text as semantic content;
- silently returning empty results for incomplete category/list markup;
- accepting cross-origin or wrong-endpoint navigation/entry links;
- identifier mismatches between navigation and file-info links;
- treating grouped navigation as a direct text or automatically following it;
- accepting Peshitta heading/reference contradictions or `error in coord` plus data;
- more than one CAL request per operation or any hidden follow-up traversal;
- loss of Syriac/Hebrew Unicode or CAL-rendered labels;
- provenance inconsistent with the request/result page;
- test fixtures that are cleaner than the live semantic shapes they claim to model.

Any blocker gets a test-only review-regression RED before its fix, followed by full GREEN and a fresh whole-PR exact-SHA review.

## CAL load bound

Production: exactly one CAL request per public operation. Group expansion, text reading, lexicon lookup, external citations, and verse navigation remain separate caller actions. No category crawl, Bible walk, missing-word category sweep, lexicon-entry expansion, or corpus mirror.

Tests: offline reduced fixtures only. Live research for this plan used eight deliberately bounded requests total across two temporary runs; the research workflow was removed before planning.
