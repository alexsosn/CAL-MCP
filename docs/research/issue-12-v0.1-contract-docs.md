# Issue #12 research — v0.1 public contract and documentation audit

**Rechecked:** 2026-09-06

This audit freezes the evidence used for the v0.1 contract/documentation pass. It compares CAL's current public research surface, the current executable MCP schema, and the repository's documentation architecture. It does not add a new CAL research operation.

## Scope and sources

Primary current CAL sources rechecked for this audit:

- https://cal.huc.edu/searching/CAL_search_page.html
- https://cal.huc.edu/cal_new_user_guide.html
- https://cal.huc.edu/targumstartpage.html
- https://cal.huc.edu/SyrStudies.html
- https://cal.huc.edu/bibliography/index.html
- https://cal.huc.edu/searching/fullbrowser.html
- https://cal.huc.edu/info.html

Repository sources of truth:

- executable MCP registration and schemas in `src/cal_mcp/server.py` / `tests/test_bootstrap.py`;
- implemented tool semantics under `docs/tools/`;
- documentation architecture in `wiki/documentation.md`;
- architecture/ownership rules in `wiki/architecture.md` and `wiki/decisions.md`.

No new CAL result crawling was used for this audit. The capability inventory relies on current public module/index pages plus the bounded research already committed by the feature tickets that implemented those surfaces.

## Current executable MCP surface

`tests/test_bootstrap.py` currently freezes 26 public tools:

1. `cal_lexicon_lookup`
2. `cal_gloss_search`
3. `cal_citation_text_search`
4. `cal_text_catalogue`
5. `cal_text_search`
6. `cal_text_page`
7. `cal_token_analysis`
8. `cal_text_concordance`
9. `cal_kwic_texts`
10. `cal_kwic_dialects`
11. `cal_kwic_dialect`
12. `cal_bibliography_authors`
13. `cal_bibliography_author`
14. `cal_bibliography_keyword`
15. `cal_bibliography_lemma`
16. `cal_dictionary_collation`
17. `cal_targum_parallel`
18. `cal_targum_concordance`
19. `cal_targum_hebrew_lemmas`
20. `cal_targum_hebrew_reflexes`
21. `cal_external_citation_dialects`
22. `cal_external_citation_sources`
23. `cal_external_citations`
24. `cal_syriac_texts`
25. `cal_syriac_missing_words`
26. `cal_syriac_peshitta_parallel`

The current public schemas expose research concepts and adapter-owned identifiers rather than raw CAL form controls. `tests/test_bootstrap.py` already guards against leakage of private parameters such as `lemma`, `pos`, `texts`, `charset`, `R1`, `bookname`, `Peshitta`, `Sam`, and `dict`.

## CAL capability matrix

| Current CAL public function | v0.1 disposition | CAL-MCP surface / rationale |
| --- | --- | --- |
| Browse the lexicon; root/headword/full-form access | **Implemented** | `cal_lexicon_lookup`; query normalization preserves CAL-supported representations and explicit lemma-key disambiguation. |
| Search English glosses | **Implemented** | `cal_gloss_search`. |
| Search combinations of English words in citations | **Implemented** | `cal_citation_text_search`. |
| Find citations from texts not in the online database | **Implemented** | `cal_external_citation_dialects` → `cal_external_citation_sources` → `cal_external_citations`; the staged workflow prevents hidden enumeration. |
| Text Browse | **Implemented / composed** | `cal_text_catalogue` for one discovery level and `cal_text_page` for one explicit file/subtext/page. |
| Search texts by topic | **Implemented** | `cal_text_search`. |
| Click a token for lexical analysis while reading text | **Implemented as explicit composition** | `cal_text_page` preserves machine coordinates/token positions; caller invokes `cal_token_analysis` explicitly. No hidden token expansion. |
| Basic concordance of one text | **Implemented** | `cal_text_concordance`. |
| KWIC of multiple text numbers | **Implemented** | `cal_kwic_texts`; explicit text IDs and one request. |
| Dialect-level KWIC discovery/drilldown exposed by current concordance pages | **Implemented** | `cal_kwic_dialects` and `cal_kwic_dialect`. |
| Dictionary Spelling Collation | **Implemented** | `cal_dictionary_collation`. |
| Targum: display all targumic versions of a Biblical passage | **Implemented** | `cal_targum_parallel`. |
| Targum: browse a single targum with lexical analysis | **Intentionally composed** | CAL links into its ordinary text browser; use `cal_text_catalogue` / `cal_text_page`, then `cal_token_analysis` explicitly. A separate Targum browser would duplicate the same research primitive. |
| Targum: create a concordance | **Implemented** | `cal_targum_concordance` for the specialist source-count result; detailed KWIC remains explicit follow-up through generic concordance tools where applicable. |
| Targum: study reflexes of Biblical Hebrew lemmas | **Implemented** | `cal_targum_hebrew_lemmas` then `cal_targum_hebrew_reflexes`; only currently supported Onqelos/Neofiti workflow is exposed. |
| Syriac: search available texts by categories | **Implemented** | `cal_syriac_texts`; grouped/direct text navigation remains explicit. |
| Syriac: review citations from texts not in the CAL database | **Intentionally composed** | Same Citation Finder family as the general external-citation workflow; use the external citation tools with Syriac dialect selection rather than duplicate Syriac-only tools. |
| Syriac: headwords occurring in Syriac but absent from *A Syriac Lexicon* | **Implemented** | `cal_syriac_missing_words`. |
| Syriac: compare MT with Peshitta | **Implemented** | `cal_syriac_peshitta_parallel`. |
| Bibliography: search by author | **Implemented** | `cal_bibliography_authors` + `cal_bibliography_author`. |
| Bibliography: search by text or subject | **Implemented** | `cal_bibliography_keyword`. |
| Bibliography: search by lexical item | **Implemented** | `cal_bibliography_lemma`. |
| Bibliography: view five most recent years | **Explicitly deferred from v0.1** | Separate issue #39. It is a convenience snapshot rather than a prerequisite for targeted bibliography research; its aggregate request/size/year semantics need their own research/TDD boundary. |
| Bibliography legacy addenda/front matter/publication archives | **Linked reference material, not an MCP research operation in v0.1** | Static/historical documents are better reached as CAL references; CAL-MCP does not mirror or wrap static archives merely to increase tool count. |

## New User Guide / workflow audit

CAL's current new-user guide emphasizes workflows rather than isolated forms:

- English → lemma → attestations;
- text collection → passage → lexical analysis;
- bibliography around a lemma or text;
- Peshitta/Targum browsing;
- citation dates because CAL is continually updated.

The 26-tool surface already supports those workflows, but the repository currently documents them mostly on individual tool pages. The missing v0.1 work is therefore cross-tool guidance and contract documentation, not another set of endpoint wrappers.

## Documentation tree audit

`wiki/documentation.md` defines the v0.1 user tree. Current branch state already has:

- `docs/configuration.md`;
- `docs/concepts/cal-identifiers.md`;
- `docs/concepts/input-and-transliteration.md`;
- all implemented tool-reference pages: bibliography, concordance, dictionary collation, external citations, lexicon, search, Syriac, Targum, texts, token analysis.

Missing user-facing v0.1 pages are:

- `docs/index.md`;
- `docs/getting-started.md`;
- `docs/installation.md`;
- `docs/concepts/provenance-and-citation.md`;
- `docs/concepts/errors-and-upstream-drift.md`;
- `docs/guides/lexical-research.md`;
- `docs/guides/corpus-context.md`;
- `docs/guides/reproducible-citations.md`;
- `docs/integrations/standalone-mcp.md`;
- `docs/limitations.md`.

`docs/integrations/agora.md` should remain deferred to issue #16, because no released package is yet registered in Agora and the page must not claim an integration that does not exist.

The release-specific exact install-from-PyPI/version instructions belong to issue #15. Issue #12 can document the current source/development install and stable stdio entry points without claiming a published release.

## Provenance audit

The architecture decision D-006 requires successful CAL-backed results to expose at least source URL and retrieval time. Current feature implementations return typed per-surface provenance objects and serialize them into public results. The exact auxiliary fields differ appropriately by task (for example original/submitted query, selected source, file/page identity, or operation name).

A single universal provenance dataclass is not required for v0.1 and forcing one now would create contract churn without evidence that CAL surfaces share all fields. The stable common convention to document/freeze is:

- `source` identifies CAL;
- `source_url` is the actual upstream result URL;
- `retrieved_at` is timezone-aware and represents actual CAL retrieval;
- task-specific submitted/original identifiers are preserved where useful;
- cache hits preserve the original upstream retrieval timestamp rather than pretending to be a new CAL retrieval.

## Error / empty-state audit

The shared HTTP layer already distinguishes:

- local request-boundary failure: `CalRequestValidationError`;
- transport/timeout failure: `CalNetworkError`;
- non-success upstream HTTP: `CalUpstreamError`;
- successful HTTP with unsafe/unexpected content: `CalContentError` and surface-specific parse subclasses;
- configured response-size violation: `CalResponseTooLargeError`.

Feature services additionally use local `ValueError` for invalid caller parameters and surface-specific typed empty/not-found semantics where CAL provides them. Current parser policy is fail-closed: successful but unrecognized markup is not silently converted to an empty result.

The main v0.1 gap is documentation of this taxonomy and user-visible expectations. A cross-cutting rewrite of all error classes is not justified by current evidence and would create release-risking contract churn.

## Pagination / boundedness convention audit

There is no single CAL pagination contract across surfaces. Current adapter policy is therefore intentionally semantic rather than syntactic:

- expose pagination only where CAL provides a researched stable bounded control;
- public operations use the smallest researched bounded request sequence for the task; most use one CAL request, while a successful `cal_lexicon_lookup` normally uses two CAL requests (browser discovery, then the selected entry fetch);
- never invent `page`, `offset`, `limit`, continuation, or `show all` semantics that CAL does not expose;
- never automatically follow result links, next pages, source lists, lexical entries, or corpus navigation;
- the shared decoded-response byte limit remains the ultimate response-size bound.

This convention should be documented centrally while individual tool pages retain surface-specific details.

## Architecture/documentation drift found

`wiki/architecture.md` is conceptually correct but its detailed service/component and target-layout diagrams predate several implemented surfaces. In particular:

- external citation and dictionary-collation services are absent from the service diagram;
- token analysis is not represented as a first-class implemented application surface;
- the planned `models/`, `parsers/`, and `services/` package tree no longer matches the current intentionally small flat `src/cal_mcp/*.py` layout.

Issue #12 should update those diagrams to describe current implementation rather than preserving an obsolete target map.

`README.md` accurately lists the current implemented tools, but its documentation map is now long and still lacks the cross-cutting user entry point that `docs/index.md` should provide. After #12, README should become a shorter landing path into the versioned user docs rather than duplicating their full navigation.

## Docs/schema consistency automation opportunity

The repository currently freezes the exact tool set and argument names in `tests/test_bootstrap.py`, but there is no automated check that:

- every public tool is named in user-facing tool documentation;
- the required v0.1 documentation entry points exist;
- relative Markdown links in README/docs resolve.

A small offline test can enforce those invariants without adding a documentation framework or generated schema copy. That is preferable to selecting a static-site generator in this ticket (D-011).

## Contract-freeze recommendation

The current 26-tool schema is coherent enough to freeze for v0.1. No accidental raw HTML/form abstraction was found that warrants a breaking rename/removal in #12. The specialist duplication decisions above are deliberate compositions rather than missing tools.

Freeze rule after #12:

- no public tool/argument/result breaking change before v0.1 except a release-blocking bug proven by a regression test;
- newly discovered CAL capabilities become focused issues and default to post-v0.1 unless they reveal a serious coverage or correctness defect;
- markup-only CAL drift remains an adapter/parser fix and should not change public schemas when avoidable.

## Research conclusions for implementation

Issue #12 should remain primarily offline and documentation/contract oriented:

1. commit an executable docs/schema consistency contract before adding missing pages;
2. add the missing cross-cutting user docs and a dated public capability matrix;
3. update stale architecture/documentation diagrams to current code boundaries;
4. centralize provenance/error/boundedness guidance without forcing unnecessary model rewrites;
5. keep issue #39 explicitly deferred and linked;
6. declare the 26-tool public surface frozen for v0.1 except release-blocking fixes;
7. perform a logically independent adversarial review focused on redundancy, naming, agent selection ergonomics, documentation truthfulness, and any hidden public-contract drift.

## CAL access / load impact

This audit added no new automated CAL result traversal. It used current public index/module/documentation pages and existing bounded feature research. Normal CI remains offline.