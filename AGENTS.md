# AGENTS.md

This repository is designed for an automated, issue-driven development loop. This file is the mandatory entry point for coding agents.

## Read first

Before changing code, read in order:

1. `README.md`
2. `research.md`
3. `plan.md`
4. `wiki/README.md`
5. `wiki/architecture.md`
6. `wiki/testing.md`
7. `wiki/documentation.md`
8. `wiki/decisions.md`
9. `wiki/agentic-dev-loop.md`
10. the GitHub issue being implemented and any linked PR/discussion

If the issue depends on a CAL page or behavior, re-check the relevant live upstream page before changing an assumption. Record materially changed evidence in `research.md`.

## Non-negotiable rules

- Work from a GitHub issue with explicit acceptance criteria.
- Before starting, search for an open PR or active issue implementing the same scope. Do not create concurrent duplicate implementations.
- Use TDD for behavior changes: first establish a failing deterministic test or fixture, then implement the smallest correct change, then refactor.
- CAL is the authority for CAL data. Do not silently correct, enrich, infer, rank, or reinterpret upstream linguistic results.
- Do not crawl, mirror, bulk-download, or prefetch the CAL corpus. A request to CAL must be directly attributable to the current user/MCP operation, except for narrowly bounded cache revalidation or explicit opt-in live smoke tests.
- Do not vendor CAL lexicon entries, text corpora, dictionary content, or large captured pages. Test fixtures must be minimal and contain only the fragment needed to exercise parser behavior.
- Preserve provenance: public tool results must include the CAL source URL and retrieval timestamp; preserve CAL coordinates/identifiers when available.
- Input normalization must be deterministic. Never use an LLM to invent CAL query syntax or to choose a linguistic analysis while presenting the result as CAL.
- Treat CAL HTML and query endpoints as undocumented upstream interfaces unless CAL publishes a machine contract. Parsers must fail explicitly on material schema changes instead of silently dropping fields.
- Keep the public MCP contract independent of CAL HTML structure and independent of Agora.
- Agora integration is optional downstream discovery/install/launch metadata. CAL-specific behavior, documentation, skills, parsers, and tests belong here, not in Agora.
- Keep unrelated cleanup out of implementation PRs.

## Request-policy rules

Until superseded by an explicit, documented CAL policy decision:

- default to low concurrency;
- use finite connect/read/total timeouts;
- identify the client honestly with a project User-Agent when practical;
- retry only transient failures, with bounded backoff;
- do not retry semantic/application errors;
- cache only to reduce duplicate live requests, with conservative TTLs and bounded storage;
- provide a way to disable caching for reproducibility/debugging;
- never use cache behavior to build a local corpus mirror.

Any change that materially increases request volume, concurrency, prefetching, or cache persistence requires an explicit architecture decision update.

## Definition of done

An implementation PR is complete only when:

- all issue acceptance criteria are met;
- changed behavior has deterministic tests;
- malformed/upstream-change/error cases have tests where relevant;
- normal CI does not require CAL network access;
- public MCP schemas and examples are updated when the interface changes;
- `research.md` is updated when new upstream evidence changes an assumption;
- `wiki/decisions.md` is updated for durable architecture changes;
- user-facing docs are updated in the same PR as the capability they describe;
- provenance, request-load, and data-rights implications are stated in the PR;
- the repository state is sufficient for a different agent to resume the work without chat history.

## Preferred issue decomposition

Keep issues independently reviewable. Separate:

- transport/server scaffolding from CAL domain behavior;
- HTTP request policy from HTML parsing;
- input normalization from lexical lookup;
- each CAL research surface (lexicon, concordance, texts, citations, bibliography, Targum, Syriac) from the others where practical;
- standalone packaging from Agora registration;
- documentation infrastructure from individual tool reference pages.

Do not implement multiple unrelated CAL forms in one PR merely because they share HTML parsing utilities.

## Repository map

- `src/cal_mcp/` — server, client, normalization, models, parsers, and application services once implementation begins.
- `tests/` — unit, parser-contract, MCP-contract, and opt-in live-smoke tests.
- `tests/fixtures/` — minimal upstream HTML/response fragments with provenance metadata.
- `docs/` — versioned user-facing documentation introduced with implemented capabilities.
- `research.md` — dated upstream evidence and prior-art notes.
- `plan.md` — staged delivery plan and issue dependency graph.
- `wiki/architecture.md` — intended component/data-flow architecture.
- `wiki/documentation.md` — documentation architecture and maintenance rules.
- `wiki/decisions.md` — durable architecture decisions.
- `wiki/backlog.md` — staged issue map and release gates.
- `wiki/testing.md` — TDD and validation requirements.
- `wiki/agentic-dev-loop.md` — exact automated development/review loop.

## Review posture

Review independently and skeptically. A passing happy-path fixture is insufficient evidence for a parser. Check ambiguous/missing elements, Unicode/script handling, upstream error pages, pagination where relevant, provenance, and whether the tool contract accidentally promises semantics CAL does not provide.
