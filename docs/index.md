# CAL-MCP user documentation

CAL-MCP is a read-only MCP adapter for the [Comprehensive Aramaic Lexicon](https://cal.huc.edu/). It sends bounded, user-initiated requests to CAL and returns structured CAL results with adapter provenance. It does not bundle, mirror, or reinterpret the CAL database.

> **Status:** pre-release. The v0.1 public tool contract is frozen at the 26 tools documented here except for release-blocking regression fixes. A versioned package release and Agora registration are separate follow-up work.

Start with [Getting started](getting-started.md). For local setup, see [Installation](installation.md) and [Standalone MCP](integrations/standalone-mcp.md).

## Public capability matrix

**Audited against CAL's current public research surfaces: 2026-09-06.**

| CAL research area | v0.1 status | CAL-MCP surface |
| --- | --- | --- |
| Lexicon/root/headword/full-form lookup | **Implemented** | [`cal_lexicon_lookup`](tools/lexicon.md) |
| English gloss and citation-text search | **Implemented** | [`cal_gloss_search`, `cal_citation_text_search`](tools/search.md) |
| Online text discovery, topic search, and bounded page reading | **Implemented** | [`cal_text_catalogue`, `cal_text_search`, `cal_text_page`](tools/texts.md) |
| Lexical analysis of one token from a returned text coordinate | **Implemented as explicit composition** | [`cal_token_analysis`](tools/token-analysis.md) after a caller-selected text page/token |
| Basic text concordance and text/dialect KWIC | **Implemented** | [`cal_text_concordance`, `cal_kwic_texts`, `cal_kwic_dialects`, `cal_kwic_dialect`](tools/concordance.md) |
| Bibliography by author, text/subject tag, or lemma | **Implemented** | [`cal_bibliography_authors`, `cal_bibliography_author`, `cal_bibliography_keyword`, `cal_bibliography_lemma`](tools/bibliography.md) |
| Dictionary spelling collation | **Implemented** | [`cal_dictionary_collation`](tools/dictionary-collation.md) |
| Citations from sources not available as full online CAL texts | **Implemented** | [`cal_external_citation_dialects`, `cal_external_citation_sources`, `cal_external_citations`](tools/external-citations.md) |
| Targum parallel verse, Targum concordance, and MT-Hebrew reflex study | **Implemented** | [`cal_targum_parallel`, `cal_targum_concordance`, `cal_targum_hebrew_lemmas`, `cal_targum_hebrew_reflexes`](tools/targum.md) |
| Browse one Targum source and inspect words | **Intentionally composed** | Use the ordinary [text tools](tools/texts.md), then [token analysis](tools/token-analysis.md); CAL itself links Targum sources into the general text browser. |
| Syriac text-category discovery, missing-from-*A Syriac Lexicon* lists, MT/Peshitta comparison | **Implemented** | [`cal_syriac_texts`, `cal_syriac_missing_words`, `cal_syriac_peshitta_parallel`](tools/syriac.md) |
| Syriac citations from texts not online | **Intentionally composed** | Use the generic [external-citation workflow](tools/external-citations.md) with the Syriac dialect rather than a duplicate Syriac-only tool. |
| Bibliography: CAL's “five most recent years” snapshot | **Deferred from v0.1** | Tracked separately in [issue #39](https://github.com/alexsosn/CAL-MCP/issues/39); its aggregate window/size semantics require a focused research/TDD ticket. |
| Legacy/static bibliography addenda and archive documents | **Reference material, not an MCP operation** | CAL-MCP does not wrap static documents merely to increase tool count. |

## Choose documentation by task

- [Getting started](getting-started.md) — common research workflows and how to compose tools explicitly.
- [Installation](installation.md) — current pre-release source installation and entry points.
- [Configuration](configuration.md) — conservative request, retry, response-size, and cache policy.
- [CAL identifiers](concepts/cal-identifiers.md) — file/subtext/category IDs, coordinates, and stability boundaries.
- [Input and transliteration](concepts/input-and-transliteration.md) — deterministic CAL/Unicode/Hebrew/Syriac input handling.
- [Provenance and citation](concepts/provenance-and-citation.md) — source URLs, retrieval dates, and reproducibility.
- [Errors and upstream drift](concepts/errors-and-upstream-drift.md) — caller errors, network/upstream failures, empty states, and parser drift.
- [Lexical research guide](guides/lexical-research.md) — lemma/search/concordance/bibliography workflows.
- [Corpus-context guide](guides/corpus-context.md) — text discovery, pages, coordinates, and token analysis.
- [Reproducible citations guide](guides/reproducible-citations.md) — recording CAL data and retrieval provenance.
- [Standalone MCP](integrations/standalone-mcp.md) — stdio process/launch contract independent of Agora.
- [Limitations](limitations.md) — upstream dependency, boundedness, deferred surfaces, and non-capabilities.

## Tool reference

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

The v0.1 surface is task-oriented rather than a mirror of CAL's PHP forms. Endpoint names, form controls, and HTML structure are private adapter details. Returned CAL identifiers are preserved where useful, but CAL-MCP does not decode opaque IDs into invented semantics.

A second research step is explicit: returned lemma keys, text identifiers, source abbreviations, coordinates, or selector IDs can be passed to a suitable follow-up tool, but CAL-MCP does not automatically traverse result links, next pages, books, dialects, sources, or bibliography archives.

Successful CAL-backed results preserve an actual CAL source URL and retrieval timestamp. See [Provenance and citation](concepts/provenance-and-citation.md) and [Errors and upstream drift](concepts/errors-and-upstream-drift.md) for the cross-cutting result contract.