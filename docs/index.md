# CAL-MCP user documentation

CAL-MCP is a read-only MCP adapter for the [Comprehensive Aramaic Lexicon](https://cal.huc.edu/). It sends bounded, user-initiated requests to CAL and returns structured CAL results with adapter provenance. It does not bundle, mirror, or reinterpret the CAL database.

> **Status:** [v0.1.0 is published](https://github.com/alexsosn/CAL-MCP/releases/tag/v0.1.0) with 36 tools. The **v0.2.0 release candidate (not yet published)** includes 37 tools and has passed a nonpublishing all-37 same-wheel smoke. It is not yet a PyPI release; `cal_bibliography_recent()` still requires the candidate source. Agora registration has merged, but its candidate v1.1 marketplace release is not published; see [Agora handoff](integrations/agora.md).

Start with [Getting started](getting-started.md). For local setup, see [Installation](installation.md) and [Standalone MCP](integrations/standalone-mcp.md).

## Public capability matrix

**Audited against CAL's current public research surfaces: 2026-09-12.**

| CAL research area | Status | CAL-MCP surface |
| --- | --- | --- |
| Deterministic supported-script / Unicode input conversion to CAL code | **Implemented as adapter-owned deterministic preprocessing** | [`cal_convert_to_code`](concepts/input-and-transliteration.md); performs no CAL request |
| Lexicon/root/headword/full-form lookup, bounded lexicon prefix browsing, and explicit linked-citation full context | **Implemented** | [`cal_lexicon_lookup`, `cal_lexicon_citation_context`](tools/lexicon.md) plus [`cal_lexicon_browse`](tools/lexicon-browse.md); browse returns one CAL page and an explicit validated continuation instead of traversing automatically |
| English gloss, specialized indexed gloss-field, and citation-text search | **Implemented** | [`cal_gloss_search`, `cal_gloss_field`, `cal_citation_text_search`](tools/search.md) |
| Online text discovery, including dedicated Onkelos/Jonathan and Mandaic routes plus operation-aware Syriac root handoff, topic search, explicit text-information metadata, bounded page reading, and explicit line comments/translations | **Implemented** | [`cal_text_catalogue`, `cal_text_search`, `cal_text_information`, `cal_text_page`, `cal_text_line_comments`](tools/texts.md); root Syriac discovery returns explicit `cal_syriac_texts` follow-up metadata rather than a synthetic CAL category ID |
| Lexical analysis of one token from a returned text coordinate | **Implemented as explicit composition** | [`cal_token_analysis`](tools/token-analysis.md) after a caller-selected text page/token |
| Text concordance, text/dialect KWIC, and explicit target-centered KWIC full context | **Implemented** | [`cal_text_concordance`, `cal_kwic_texts`, `cal_kwic_dialects`, `cal_kwic_dialect`, `cal_kwic_full_context`](tools/concordance.md); parent KWIC calls return selectors but never prefetch full context |
| Bibliography by author, text/subject tag, or lemma | **Implemented** | [`cal_bibliography_authors`, `cal_bibliography_author`, `cal_bibliography_keyword`, `cal_bibliography_lemma`](tools/bibliography.md) |
| Dictionary spelling collation | **Implemented** | [`cal_dictionary_collation`](tools/dictionary-collation.md) |
| Citations from sources not available as full online CAL texts | **Implemented** | [`cal_external_citation_dialects`, `cal_external_citation_sources`, `cal_external_citations`](tools/external-citations.md) |
| Targum parallel verse, Targum concordance, and MT-Hebrew reflex study | **Implemented** | [`cal_targum_parallel`, `cal_targum_concordance`, `cal_targum_concordance_examples`, `cal_targum_hebrew_lemmas`, `cal_targum_hebrew_reflexes`, `cal_targum_reflex_examples`](tools/targum.md) |
| Browse one Targum source and inspect words | **Intentionally composed** | Use the ordinary [text tools](tools/texts.md), then [token analysis](tools/token-analysis.md); CAL itself links Targum sources into the general text browser. |
| Syriac text-category discovery, grouped-text follow-up, missing-from-*A Syriac Lexicon* lists, MT/Peshitta comparison | **Implemented** | [`cal_syriac_texts`, `cal_syriac_group`, `cal_syriac_missing_words`, `cal_syriac_peshitta_parallel`](tools/syriac.md) |
| Syriac citations from texts not online | **Intentionally composed** | Use the generic [external-citation workflow](tools/external-citations.md) with the Syriac dialect rather than a duplicate Syriac-only tool. |
| Bibliography: CAL's “five most recent years” snapshot | **Deferred from v0.1.0; unpublished v0.2.0 release candidate** | [`cal_bibliography_recent()`](tools/bibliography.md) retrieves one CAL-ordered complete snapshot with no year selector, deduplication, or archive traversal. |
| Legacy/static bibliography addenda and archive documents | **Reference material, not an MCP operation** | CAL-MCP does not wrap static documents merely to increase tool count. |

## Release boundaries and deliberate limitations

The Targum concordance and Hebrew-reflex example follow-ups are already implemented and included in **published v0.1.0**, using `cal_targum_concordance_examples` and `cal_targum_reflex_examples`. Their selectors must come from a previous explicit CAL-backed call; examples are never prefetched.

Completed [#39](https://github.com/alexsosn/CAL-MCP/issues/39) added `cal_bibliography_recent()` to **unpublished v0.2.0 release candidate** source. The reviewed implementation does **not** make the tool available in pinned v0.1.0 installs. A future tag still requires a complete installed-wheel live release gate and actual PyPI/GitHub publication. Other CAL URLs are not automatically MCP-followable merely because they are preserved as provenance.

CAL's text-browser **show all** presentation is deliberately **not exposed** as a separate MCP operation because it removes the page bound. Use bounded `cal_text_page(..., page=...)` calls and explicit returned page navigation instead.

## Choose documentation by task

- [Getting started](getting-started.md) — common research workflows and how to compose tools explicitly.
- [Installation](installation.md) — pinned released package installation, source development setup and entry points.
- [Configuration](configuration.md) — conservative request, retry, response-size, and cache policy.
- [CAL identifiers](concepts/cal-identifiers.md) — file/subtext/category IDs, coordinates, and stability boundaries.
- [Input and transliteration](concepts/input-and-transliteration.md) — deterministic CAL/Unicode/Hebrew/Syriac and researched dedicated-script input conversion.
- [Provenance and citation](concepts/provenance-and-citation.md) — source URLs, retrieval dates, and reproducibility.
- [Errors and upstream drift](concepts/errors-and-upstream-drift.md) — caller errors, network/upstream failures, empty states, and parser drift.
- [Lexical research guide](guides/lexical-research.md) — lemma/search/concordance/bibliography workflows.
- [Corpus-context guide](guides/corpus-context.md) — text discovery, pages, coordinates, line comments, and token analysis.
- [Reproducible citations guide](guides/reproducible-citations.md) — recording CAL data and retrieval provenance.
- [Standalone MCP](integrations/standalone-mcp.md) — stdio process/launch contract independent of Agora.
- [Agora integration handoff](integrations/agora.md) — authoritative v0.1.0 upstream release identity and bounded downstream smoke.
- [Limitations](limitations.md) — upstream dependency, boundedness, deferred surfaces, and non-capabilities.

## Tool reference

- [Input conversion and transliteration](concepts/input-and-transliteration.md) — `cal_convert_to_code` and lexicon input-conversion semantics.
- [Lexicon lookup and citation context](tools/lexicon.md) — `cal_lexicon_lookup` and `cal_lexicon_citation_context`.
- [Lexicon prefix browsing](tools/lexicon-browse.md) — `cal_lexicon_browse` and explicit continuation semantics.
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

A second research step is explicit: returned lemma keys, text identifiers, source abbreviations, coordinates, continuation selectors, or selector IDs can be passed to a suitable follow-up tool, but CAL-MCP does not automatically traverse result links, next pages, books, dialects, sources, text-information metadata, line comments/translations, specialized gloss fields, Syriac groups, lexicon citation-context pages, KWIC full-context pages, or bibliography archives. Lexicon browse pagination is available only when the caller explicitly passes the returned `next_continuation` back to `cal_lexicon_browse`; linked lexicon citation context is available only when the caller explicitly passes a returned citation's typed `full_coordinate` to `cal_lexicon_citation_context`; line comments/translations are available only when the caller explicitly passes a returned line coordinate to `cal_text_line_comments`; KWIC full context is available only when the caller explicitly passes a returned hit's typed selectors to `cal_kwic_full_context`.

Successful CAL-backed results preserve an actual CAL source URL and retrieval timestamp. See [Provenance and citation](concepts/provenance-and-citation.md) and [Errors and upstream drift](concepts/errors-and-upstream-drift.md) for the cross-cutting result contract.
