# CAL-MCP

An independent, read-only Model Context Protocol (MCP) adapter for the [Comprehensive Aramaic Lexicon (CAL)](https://cal.huc.edu/).

> **Status:** architecture and implementation planning. No production MCP server has been released yet.

CAL-MCP is intended to make CAL's existing scholarly interfaces easier to use from agents and MCP clients without copying, mirroring, or redistributing the CAL database. Queries remain live, user-initiated requests to CAL; CAL remains the authority for lexical data, texts, citations, bibliography, and scholarly interpretation.

This project is not affiliated with or endorsed by the Comprehensive Aramaic Lexicon Project or Hebrew Union College.

## Goals

- Provide a small, stable, typed MCP interface over CAL's existing public research functions.
- Preserve CAL semantics rather than reinterpret or repair CAL data.
- Accept practical Aramaic inputs (CAL transliteration, Unicode transliteration, Hebrew square script, and Syriac where CAL supports them) and convert them deterministically for CAL queries.
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

## Planned MCP surface

The exact tool schemas will be stabilized by tests before the first release. The target research surface is:

| Area | Planned capability |
| --- | --- |
| Lexicon | lemma/root/form lookup; complete entry retrieval; lexicon browse |
| English search | gloss search; citation-text search |
| Concordance | KWIC/concordance queries with text/dialect constraints supported by CAL |
| Texts | text catalogue/search; passage/context retrieval |
| Token analysis | CAL lexical analysis for a token at a CAL text coordinate |
| Citations | citation lookup, source links, retrieval metadata |
| Bibliography | bibliographic search where the public CAL interface supports it |
| Targum | CAL Targum comparison/research operations |
| Syriac | CAL Syriac research operations |
| Input handling | deterministic CAL/Unicode/Hebrew/Syriac normalization and query encoding |

The server must distinguish between **CAL data returned by the upstream service** and **adapter metadata produced by CAL-MCP**.

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

The MCP tool layer must not parse CAL HTML directly. Endpoint-specific parsing stays behind typed services so CAL markup changes can be handled without changing public MCP contracts unnecessarily.

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

User-facing reference documentation under `docs/` will be introduced alongside the corresponding implemented tools so it cannot get ahead of the executable interface. Its planned structure is specified in `wiki/documentation.md`.

## Bootstrap development state

The repository currently has a minimal MCP server shell only; no CAL-backed scholarly tools are implemented yet.

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

Bootstrap tests guard the import of `cal_mcp.server` itself and subsequent MCP introspection against outbound socket connections, so import-time client initialization cannot silently contact CAL. The installed stdio entry point is tested separately. Network-backed CAL behavior will be introduced only in the issues that implement the HTTP client and scholarly tools.

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

CAL-MCP therefore starts from a deliberately narrow operational rule: perform only bounded requests required to answer the user's current MCP call; do not crawl, mirror, prefetch the corpus, or redistribute CAL content. If CAL publishes a machine API or explicit automation policy, `research.md` and the relevant architecture decision must be updated before changing behavior.

## License

CAL-MCP software and repository documentation are licensed under the MIT License. This license does **not** grant rights to CAL data, CAL website content, underlying text editions, or third-party dictionaries. Those remain governed by their respective owners and upstream terms.
