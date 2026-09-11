# CAL-MCP user documentation

CAL-MCP is a read-only MCP adapter for the [Comprehensive Aramaic Lexicon](https://cal.huc.edu/). It sends bounded, user-initiated requests to CAL and returns structured CAL results with adapter provenance. It does not bundle, mirror, or reinterpret the CAL database.

> **Status:** pre-release. The current public contract contains 32 tools, including adapter-owned deterministic input conversion and the current CAL-backed research operations documented below. A versioned package release and Agora registration are separate follow-up work.

Start with [Getting started](getting-started.md). For local setup, see [Installation](installation.md) and [Standalone MCP](integrations/standalone-mcp.md).

## Public capability matrix

**Audited against CAL's current public research surfaces: 2026-09-11.**

| CAL research area | v0.1 status | CAL-MCP surface |
| --- | --- | --- |
| Deterministic supported-script / Unicode input conversion to CAL code | **Implemented as adapter-owned deterministic preprocessing** | [`cal_convert_to_code`](concepts/input-and-transliteration.md); performs no CAL request |
| Lexicon/root/headword/full-form lookup | **Implemented** | [`cal_lexicon_lookup`](tools/lexicon.md) |
| English gloss, specialized indexed gloss-field, and citation-text search | **Implemented** | [`cal_gloss_search`, `cal_gloss_field`, `cal_citation_text_search`](tools/search.md) |
| Online text discovery, including dedicated Onkelos/Jonathan and Mandaic routes plus operation-aware Syriac root handoff, topic search, explicit text-information metadata, bounded page reading, and explicit line comments/translations | **Implemented** | [`cal_text_catalogue`, `cal_text_search`, `cal_text_information`, `cal_text_page`, `cal_text_line_comments`](tools/texts.md); root Syriac discovery returns explicit `cal_syriac_texts` follow-up metadata rather than a synthetic CAL category ID |
| Lexical analysis of one token from a returned text coordinate | **Implemented as explicit composition** | [`cal_token_analysis`](tools/token-analysis.md) after a caller-selected text page/token |
| Text concordance, text/dialect KWIC, and explicit target-centered KWIC full context | **Implemented** | [`cal_text_concordance`, `cal_kwic_texts`, `cal_kwic_dialects`, `cal_kwic_dialect`, `cal_kwic_full_context`](tools/concordance.md); parent KWIC calls return selectors but never prefetch full context |
| Bibliography by author, text/subject tag, or lemma | **Implemented** | [`cal_bibliography_authors`, `cal_bibliography_author`, `cal_bibliography_keyword`, `cal_bibliography_lemma`](tools/bibliography.md) |
| Dictionary spelling collation | **Implemented** | [`cal_dictionary_collation`](tools/dictionary-collation.md) |
| Citations from sources not available as full online CAL texts | **Implemented** | [`cal_external_citation_dialects`, `cal_external_citation_sources`, `cal_external_citations`](tools/external-citations.md) |
| Targum parallel verse, Targum concordance, and MT-Hebrew reflex study | **Implemented** | [`cal_targum_parallel`, `cal_targum_concordance`, `cal_targum_hebrew_lemmas`, `cal_targum_hebrew_reflexes`](tools/targum.md) |
| Browse one Targum source and inspect words | **Intentionally composed** | Use the ordinary [text tools](tools/texts.md), then [token analysis](tools/token-analysis.md); CAL itself links Targum sources into the general text browser. |
| Syriac text-category discovery, grouped-text follow-up, missing-from-*A Syriac Lexicon* lists, MT/Peshitta comparison | **Implemented** | [`cal_syriac_texts`, `cal_syriac_group`, `cal_syriac_missing_words`, `cal_syriac_peshitta_parallel`](tools/syriac.md) |
| Syriac citations from texts not online | **Intentionally composed** | Use the generic [external-citation workflow](tools/external-citations.md) with the Syriac dialect rather than a duplicate Syriac-only tool. |
| Bibliography: CAL's “five most recent years” snapshot | **Deferred from v0.1** | Tracked separately in [issue #39](https://github.com/alexsosn/CAL-MCP/issues/39); its aggregate window/size semantics require a focused research/TDD ticket. |
| Legacy/static bibliography addenda and archive documents | **Reference material, not an MCP operation** | CAL-MCP does not wrap static documents merely to increase tool count. |

## Known current reachability gaps

An **Implemented** capability above means the named research task is supported; it does not mean every follow-up link rendered by CAL is MCP-followable. The 2026-09-11 route-level audit keeps the remaining gaps explicit rather than treating a preserved URL as a supported operation:

- [#112](https://github.com/alexsosn/CAL-MCP/issues/112) — CAL's lexicon **prefix browse** remains a separate discovery task from exact/root/full-form lookup.
- [#109](https://github.com/alexsosn/CAL-MCP/issues/109) — Targum concordance/reflex **supporting examples** are returned as validated links but are not yet MCP-followable.
- [#127](https://github.com/alexsosn/CAL-MCP/issues/127) — linked lexicon **citation full context** uses CAL's distinct `showachapter.php?fullcoord=...` route and requires focused research before it can be composed safely with text/KWIC tools.
- [#39](https://github.com/alexsosn/CAL-MCP/issues/39) — the bibliography **recent five-years snapshot** is still missing; its implementation is intentionally blocked until the standalone v0.1 release in [#15](https://github.com/alexsosn/CAL-MCP/issues/15) is published or the frozen public-contract decision changes.

CAL's text-browser **show all** presentation is deliberately **not exposed** as a separate MCP operation because it removes the page bound. Use bounded `cal_text_page(..., page=...)` calls and explicit returned page navigation instead.

## Choose documentation by task

- [Getting started](getting-started.md) — common research workflows and how to compose tools explicitly.
- [Installation](installation.md) — current pre-release source installation and entry points.
- [Configuration](configuration.md) — conservative request, retry, response-size, and cache policy.
- [CAL identifiers](concepts/cal-identifiers.md) — file/subtext/category IDs, coordinates, and stability boundaries.
- [Input and transliteration](concepts/input-and-transliteration.md) — deterministic CAL/Unicode/Hebrew/Syriac and researched dedicated-script input conversion.
- [Provenance and citation](concepts/provenance-and-citation.md) — source URLs, retrieval dates, and reproducibility.
- [Errors and upstream drift](concepts/errors-and-upstream-drift.md) — caller errors, network/upstream failures, empty states, and parser drift.
- [Lexical research guide](guides/lexical-research.md) — lemma/search/concordance/bibliography workflows.
- [Corpus-context guide](guides/corpus-context.md) — text discovery, pages, coordinates, line comments, and token analysis.
- [Reproducible citations guide](guides/reproducible-citations.md) — recording CAL data and retrieval provenance.
- [Standalone MCP](integrations/standalone-mcp.md) — stdio process/launch contract independent of Agora.
- [Limitations](limitations.md) — upstream dependency, boundedness, deferred surfaces, and non-capabilities.

## Tool reference

- [Input conversion and transliteration](concepts/input-and-transliteration.md) — `cal_convert_to_code` and lexicon input-conversion semantics.
- [Lexicon](tools/lexicon.md)
- [English search](tools/search.md)
- [Texts](tools/texts.md)
- [Token analysis](tools/token-analysis.md)
- [Concordance and KWIC](tools/concordance.md)
- [Bibliography](tools/bibliography.md)
- [Dictionary spelling collation](tools/dictionary-collation.md)
- [External citations](tools/external-citations.md)
- [Targum Studies](tools/targum.md)
- [Syriac Studies](tools/syriac.md)

## Contract principles

The v0.1 surface is task-oriented rather than a mirror of CAL's PHP forms. Endpoint names, form controls, and HTML structure are private adapter details. Returned CAL identifiers are preserved where useful, but CAL-MCP does not decode opaque IDs into invented semantics. The local `cal_convert_to_code` tool is adapter-owned deterministic preprocessing and does not claim to be a CAL research endpoint.

A second research step is explicit: returned lemma keys, text identifiers, source abbreviations, coordinates, or selector IDs can be passed to a suitable follow-up tool, but CAL-MCP does not automatically traverse result links, next pages, books, dialects, sources, text-information metadata, line comments/translations, specialized gloss fields, Syriac groups, KWIC full-context pages, or bibliography archives. Line comments/translations are available only when the caller explicitly passes a returned line coordinate to `cal_text_line_comments`; KWIC full context is available only when the caller explicitly passes a returned hit's typed selectors to `cal_kwic_full_context`.

Successful CAL-backed results preserve an actual CAL source URL and retrieval timestamp. See [Provenance and citation](concepts/provenance-and-citation.md) and [Errors and upstream drift](concepts/errors-and-upstream-drift.md) for the cross-cutting result contract.
