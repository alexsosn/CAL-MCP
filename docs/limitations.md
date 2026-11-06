# Limitations

CAL-MCP is a thin live adapter, not a local replacement for the Comprehensive Aramaic Lexicon. These boundaries are part of the v0.1 contract.

## CAL is a live upstream dependency

CAL-backed tools require CAL to be reachable over the network. CAL-MCP does not bundle an offline lexicon/corpus/bibliography copy and does not promise that a result retrieved on one date will remain unchanged after CAL is corrected or extended.

Keep the returned source URL and retrieval timestamp with research results. See [Provenance and citation](concepts/provenance-and-citation.md).

## CAL web interfaces are not a versioned machine API

The current adapter is built against public CAL web forms/result pages for which no published versioned JSON/REST compatibility contract has been found.

Parsers therefore fail closed when required semantics change unexpectedly. A successful HTTP response with unrecognized markup is not silently treated as an empty result.

See [Errors and upstream drift](concepts/errors-and-upstream-drift.md).

## Bounded requests, not corpus traversal

CAL-MCP intentionally does not provide:

- corpus-wide crawling or mirroring;
- background indexing/prefetch/cache warming;
- automatic traversal of all pages, books, dialects, sources, authors, lemmas, or bibliography years;
- an unbounded “show all” text operation;
- hidden following of returned entry/context links;
- a persistent CAL cache/database.

Most public operations map to exactly one explicit CAL request. The documented bounded exception is `cal_lexicon_lookup`: a successful exact lookup normally uses two CAL requests (browser discovery followed by the selected entry fetch). Multi-stage workflows otherwise expose each stage as a separate caller-controlled tool.

The shared HTTP client also applies finite timeouts, conservative concurrency/retries, same-origin/redirect boundaries, and a decoded-response size limit. See [Configuration](configuration.md).

## Pagination is surface-specific

CAL does not expose one universal pagination contract. CAL-MCP only exposes page/navigation controls that have been researched for the specific surface.

It does not invent generic `offset`, `limit`, continuation-token, or page parameters merely because a result could be large. Where current CAL shows no stable continuation mechanism, one bounded response is the operation boundary.

## CAL identifiers are upstream-owned

Lemma keys are structurally validated for reuse, but many file/subtext/category/source/selector IDs remain CAL-owned navigation identifiers. CAL-MCP preserves them rather than assigning undocumented local meaning or permanence.

See [CAL identifiers](concepts/cal-identifiers.md).

## Input normalization is deliberately limited

CAL-MCP performs deterministic, documented representation handling. It does not use an LLM to infer roots, reconstruct spellings, resolve linguistic ambiguity, or choose among CAL analyses.

See [Input and transliteration](concepts/input-and-transliteration.md).

## No scholarly correction/enrichment layer

CAL remains the authority for the lexical/textual data returned from CAL. CAL-MCP does not silently fix CAL analyses, merge senses, harmonize version labels, generate missing translations, infer etymology, or rerank results as scholarly truth.

Any downstream interpretation should be identified as the researcher's/agent's work rather than CAL data.

## Specialist upstream limitations remain visible

CAL-MCP only exposes specialist workflows that current CAL supports faithfully. For example, CAL's Targum Hebrew-reflex interface currently supports the adapter's Onqelos/Neofiti path while the corresponding Pseudo-Jonathan path is marked under development by CAL; CAL-MCP does not advertise that unfinished path as implemented.

See [Targum Studies](tools/targum.md) and [Syriac Studies](tools/syriac.md) for current specialist boundaries.

## Recent bibliography on development source

The immutable v0.1.0 release implements targeted author/text-subject/lemma bibliography queries, but not the recent-years snapshot. Unreleased 0.2.0 development source adds [`cal_bibliography_recent()`](tools/bibliography.md) for one CAL-owned ordered snapshot, with no selectable years and no computed recency boundary. CAL showed 2021–2025 in 2026. Unknown pagination or missing entries fail closed as parser drift; there is no local archive traversal.

## Static/legacy CAL documents are not wrapped automatically

A public CAL link does not automatically justify an MCP tool. Static bibliography addenda, front matter, help pages, and historical documents remain ordinary references unless a focused issue demonstrates a research operation that benefits from a bounded typed adapter.

This avoids tool proliferation and accidental content redistribution.

## Published and development installation status

The standalone [v0.1.0 release](https://github.com/alexsosn/CAL-MCP/releases/tag/v0.1.0) is published and can be installed as `cal-mcp==0.1.0`. The current development checkout identifies as `0.2.0.dev0`; unreleased features are not available through the v0.1.0 package pin. Future releases require their own bounded validation and publishing gates.

See [Installation](installation.md).

## Agora is not part of the runtime

CAL-MCP currently runs standalone over stdio. Agora registration is deferred to issue #16 and, when added, should only provide downstream discovery/install/launch metadata around the released standalone package.

See [Standalone MCP](integrations/standalone-mcp.md).

## Rights boundary

The CAL-MCP MIT license applies to CAL-MCP software and repository documentation. It does not grant rights to CAL data, CAL website content, source editions, or third-party dictionaries. CAL-MCP does not redistribute a local copy of those materials.