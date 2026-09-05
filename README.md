# CAL-MCP

An independent, read-only Model Context Protocol (MCP) adapter for the [Comprehensive Aramaic Lexicon (CAL)](https://cal.huc.edu/).

> **Status:** active pre-release development. The repository includes CAL-backed lexicon lookup, bounded English gloss/citation-text search, bounded text catalogue/search/page retrieval, bounded token-at-coordinate lexical analysis, bounded concordance/KWIC research operations, bounded bibliography search, and bounded dictionary spelling collation; no versioned release has been published yet.

CAL-MCP makes CAL's existing scholarly interfaces easier to use from agents and MCP clients without copying, mirroring, or redistributing the CAL database. Queries remain live, user-initiated requests to CAL; CAL remains the authority for lexical data, texts, citations, bibliography, dictionary collation, and scholarly interpretation.

This project is not affiliated with or endorsed by the Comprehensive Aramaic Lexicon Project or Hebrew Union College.

## Goals

- Provide a small, stable, typed MCP interface over CAL's existing public research functions.
- Preserve CAL semantics rather than reinterpret or repair CAL data.
- Accept practical Aramaic inputs (CAL transliteration, Unicode transliteration, Hebrew square script, and Syriac where CAL supports them) and handle them deterministically for CAL queries.
- Return source URLs, retrieval timestamps, CAL identifiers/coordinates when available, and enough provenance for reproducible scholarly use.
- Work as a standalone MCP server with no dependency on Agora.
- Be easy for [Agora](https://github.com/alexsosn/Agora) to discover, install, launch, and describe as a thin third-party plugin.
- Keep automated access conservative: bounded concurrency, no corpus-wide crawl, no background extraction, and no bundled CAL data.

## Non-goals

- Reconstructing or mirroring the CAL database.
- Bulk harvesting CAL content.
- Correcting CAL lexical analyses, morphology, citations, or textual data.
- Adding AI-generated linguistic analyses and presenting them as CAL results.
- Making Agora responsible for CAL-specific behavior.
- Depending on Agora at runtime.

## MCP surface

The public surface is introduced incrementally and stabilized by tests before release.

| Area | Status | Capability |
| --- | --- | --- |
| Lexicon | **Implemented** | `cal_lexicon_lookup`: root/headword/form lookup, explicit homograph disambiguation, complete entry parsing with provenance |
| Input handling | **Implemented** | deterministic CAL/Unicode/Hebrew/Syriac normalization and query encoding |
| English search | **Implemented** | `cal_gloss_search` and `cal_citation_text_search`: bounded live CAL search with typed ordered results and provenance |
| Concordance | **Implemented** | `cal_text_concordance`, `cal_kwic_texts`, `cal_kwic_dialects`, and `cal_kwic_dialect`: explicit one-request frequency/KWIC operations with text/dialect bounds, ordered duplicate-preserving hits, and provenance |
| Texts | **Implemented** | `cal_text_catalogue`, `cal_text_search`, and `cal_text_page`: explicit one-request discovery/navigation and line/token coordinate preservation |
| Token analysis | **Implemented** | `cal_token_analysis`: every CAL lexical analysis for one explicit machine coordinate + zero-based token index, with ambiguity preserved |
| Bibliography | **Implemented** | `cal_bibliography_authors`, `cal_bibliography_author`, `cal_bibliography_keyword`, and `cal_bibliography_lemma`: one-request author discovery/exact-author, exact CAL text/subject-tag, and exact lemma bibliography operations with record links and provenance |
| Dictionary collation | **Implemented** | `cal_dictionary_collation`: one explicit dictionary/page lookup with readable source identifiers, ordered CAL lemma correspondences, and provenance |
| Citations | Planned | citation lookup, source links, retrieval metadata beyond English citation-text search |
| Targum | Planned | CAL Targum comparison/research operations |
| Syriac | Planned | CAL Syriac research operations |

The server distinguishes between **CAL data returned by the upstream service** and **adapter metadata produced by CAL-MCP**.

See [`docs/tools/lexicon.md`](docs/tools/lexicon.md) for lexicon lookup, [`docs/tools/search.md`](docs/tools/search.md) for English gloss/citation-text search, [`docs/tools/texts.md`](docs/tools/texts.md) for bounded CAL text discovery/page retrieval, [`docs/tools/token-analysis.md`](docs/tools/token-analysis.md) for token-at-coordinate lexical analysis, [`docs/tools/concordance.md`](docs/tools/concordance.md) for bounded frequency/KWIC operations, [`docs/tools/bibliography.md`](docs/tools/bibliography.md) for bounded CAL bibliography search, and [`docs/tools/dictionary-collation.md`](docs/tools/dictionary-collation.md) for bounded dictionary-page collation. CAL-owned identifier semantics are documented in [`docs/concepts/cal-identifiers.md`](docs/concepts/cal-identifiers.md).

## System boundary

```mermaid
flowchart LR
    U[Researcher / agent] --> C[MCP client]
    C --> M[CAL-MCP]
    M -->|bounded live queries| CAL[cal.huc.edu]
    CAL -->|HTML / upstream responses| M
    M -->|typed results + provenance| C

    A[Agora] -. optional discovery / install / launch .-> M

    M -. no corpus mirror .-> X[(No local CAL database)]
```

CAL-MCP is independently runnable. Agora integration is downstream packaging and marketplace metadata, not part of the server's domain logic.

## Internal architecture

```mermaid
flowchart TB
    MCP[MCP tool layer]
    SVC[Application services]
    NORM[Input normalization]
    MODEL[Typed domain models]
    CLIENT[CAL HTTP client]
    POLICY[Request policy\nrate limits / timeouts / cache]
    PARSERS[Endpoint parsers]
    UP[CAL public web interfaces]

    MCP --> SVC
    SVC --> NORM
    SVC --> CLIENT
    CLIENT --> POLICY
    CLIENT --> UP
    UP --> PARSERS
    PARSERS --> MODEL
    MODEL --> SVC
    SVC --> MCP
```

The MCP tool layer does not parse CAL HTML directly. Endpoint-specific parsing stays behind typed services so CAL markup changes can be handled without changing public MCP contracts unnecessarily.

## Documentation map

The repository uses documentation as executable project state for humans and coding agents:

- [`research.md`](research.md) — dated evidence about CAL, its public interfaces, access assumptions, and prior art.
- [`plan.md`](plan.md) — staged implementation plan and ticket dependency graph.
- [`AGENTS.md`](AGENTS.md) — mandatory entry point and invariants for coding agents.
- [`wiki/README.md`](wiki/README.md) — maintainer documentation index.
- [`wiki/architecture.md`](wiki/architecture.md) — system/component/data-flow architecture and boundaries.
- [`wiki/documentation.md`](wiki/documentation.md) — documentation information architecture, ownership, generation, and validation plan.
- [`wiki/testing.md`](wiki/testing.md) — TDD, fixtures, parser contracts, live-smoke policy, and MCP contract tests.
- [`wiki/decisions.md`](wiki/decisions.md) — durable architecture decisions.
- [`wiki/backlog.md`](wiki/backlog.md) — issue map and release gates.
- [`wiki/agentic-dev-loop.md`](wiki/agentic-dev-loop.md) — exact issue → implementation → review → merge loop.
- [`docs/configuration.md`](docs/configuration.md) — implemented CAL HTTP/request/cache policy and conservative defaults.
- [`docs/concepts/input-and-transliteration.md`](docs/concepts/input-and-transliteration.md) — deterministic input detection, limited CAL-code mapping, and query/form encoding.
- [`docs/concepts/cal-identifiers.md`](docs/concepts/cal-identifiers.md) — CAL-owned file/subtext/category identifiers, line coordinates, token positions, and stability boundaries.
- [`docs/tools/lexicon.md`](docs/tools/lexicon.md) — `cal_lexicon_lookup` semantics, examples, limits, failures, and CAL provenance.
- [`docs/tools/search.md`](docs/tools/search.md) — English gloss/citation-text search semantics, request bounds, empty results, and provenance.
- [`docs/tools/texts.md`](docs/tools/texts.md) — bounded text catalogue/topic search/page retrieval, navigation, line/token coordinates, failures, and provenance.
- [`docs/tools/token-analysis.md`](docs/tools/token-analysis.md) — explicit token coordinates/indexes, ordered ambiguity, no-data/drift semantics, and one-request bounds.
- [`docs/tools/concordance.md`](docs/tools/concordance.md) — one-text frequency indexes, explicit text/dialect KWIC, duplicate-hit preservation, bounds, failures, and provenance.
- [`docs/tools/bibliography.md`](docs/tools/bibliography.md) — author discovery/exact-author retrieval, exact text/subject-tag and lemma bibliography search, result links, bounds, failures, and provenance.
- [`docs/tools/dictionary-collation.md`](docs/tools/dictionary-collation.md) — supported dictionaries/page syntax, ordered CAL lemma correspondences, alias-target preservation, bounds, failures, and provenance.

Additional user-facing reference documentation under `docs/` is introduced alongside the corresponding implemented behavior so it cannot get ahead of the executable interface. Its target structure is specified in `wiki/documentation.md`.

## Current development state

The repository currently has:

- a standalone stdio MCP server;
- a bounded CAL HTTP/request-policy layer with strict origin, redirect, retry, concurrency, cache, and response-size controls;
- deterministic input normalization/query encoding;
- the live `cal_lexicon_lookup` tool with typed lexicon parsing and provenance;
- live `cal_gloss_search` and `cal_citation_text_search` tools with one-request bounded CAL search semantics;
- live `cal_text_catalogue`, `cal_text_search`, and `cal_text_page` tools with explicit bounded navigation, CAL line/token coordinates, and missing-vs-drift semantics;
- live `cal_token_analysis` with one-request token-at-coordinate analysis, ordered CAL ambiguity, shared lexicon references, and no hidden entry expansion;
- live `cal_text_concordance`, `cal_kwic_texts`, `cal_kwic_dialects`, and `cal_kwic_dialect` tools with explicit text/dialect scope, one-request bounds, duplicate-hit preservation, and no hidden full-context traversal;
- live `cal_bibliography_authors`, `cal_bibliography_author`, `cal_bibliography_keyword`, and `cal_bibliography_lemma` tools with explicit two-step author selection, exact CAL tag/lemma semantics, ordered records/links, and no hidden archive traversal;
- live `cal_dictionary_collation` with one-request dictionary/page lookup, readable source selection, ordered CAL lemma correspondences, and no hidden lemma expansion;
- offline parser fixtures and deterministic MCP/request-policy tests.

Requirements: Python 3.11+.

```bash
python -m pip install -e ".[dev]"
```

Run the local stdio server:

```bash
cal-mcp
```

The equivalent module entry point is:

```bash
python -m cal_mcp
```

Run the deterministic development checks:

```bash
ruff check .
ruff format --check .
mypy
pytest
```

Importing `cal_mcp.server` remains network-free. When the MCP server starts, its lifespan creates one bounded CAL client for that running server without issuing a CAL request; live traffic begins only when a CAL-backed tool is called. Reusing that client preserves the request layer's process/session-local cache and single-flight behavior across tool calls, and the client is closed at server shutdown. The installed stdio entry point is tested separately. Normal HTTP, normalization, lexicon/search/text/token-analysis/concordance/bibliography/dictionary-collation parser/service, and MCP contract tests make no live CAL requests.

## Development model

Development is issue-driven and test-driven:

1. Pick one unblocked GitHub issue with explicit acceptance criteria.
2. Check that no active PR already implements it.
3. Add or update a failing test/fixture that captures the required behavior.
4. Implement the smallest correct change.
5. Run deterministic tests with normal CI network access disabled.
6. Update interface/architecture/research documentation when required.
7. Open a focused PR linked to the issue.
8. Review independently against the issue, repository invariants, and upstream CAL evidence.
9. Merge only when acceptance criteria, tests, and documentation are complete.

See [`AGENTS.md`](AGENTS.md) and [`wiki/agentic-dev-loop.md`](wiki/agentic-dev-loop.md).

## Upstream and access policy

CAL describes itself as a live work in progress and asks scholarly users to cite the retrieval date. CAL exposes public research forms and server-side query endpoints, but as of the research snapshot documented in this repository we have not found a published CAL API contract or a CAL-specific automated-access policy.

CAL-MCP therefore uses a deliberately narrow operational rule: perform only bounded requests required to answer the user's current MCP call; do not crawl, mirror, prefetch the corpus, or redistribute CAL content. If CAL publishes a machine API or explicit automation policy, `research.md` and the relevant architecture decision must be updated before changing behavior.

## License

CAL-MCP software and repository documentation are licensed under the MIT License. This license does **not** grant rights to CAL data, CAL website content, underlying text editions, or third-party dictionaries. Those remain governed by their respective owners and upstream terms.
