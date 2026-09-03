# Architecture decisions

This file records durable project decisions. New evidence belongs first in `research.md`; a decision belongs here when it constrains future implementation.

## D-001 — CAL-MCP is a thin live adapter

**Status:** accepted — 2026-09-03

CAL-MCP will issue bounded live requests to CAL for explicit user/MCP operations. It will not reconstruct, mirror, pre-index, or bulk-download the CAL database.

Consequences:

- package contains software, not CAL data;
- no background corpus crawl or cache warming;
- result limits/pagination must remain bounded;
- caching exists only to suppress duplicate requests and is size/TTL bounded;
- offline functionality is not a goal for CAL-backed queries.

## D-002 — CAL is the scholarly authority

**Status:** accepted — 2026-09-03

CAL-MCP preserves CAL's analyses, labels, senses, citations, and text data. It does not silently fix or enrich CAL results.

Consequences:

- no LLM-generated morphology/lexicography is presented as CAL;
- potential CAL scholarly errors are reported upstream or documented as upstream limitations;
- adapter tests check fidelity, not linguistic truth.

## D-003 — Standalone operation is primary; Agora is optional downstream integration

**Status:** accepted — 2026-09-03

A released CAL-MCP package must install and run without Agora. Agora may discover, install, launch, and describe a released version but does not own CAL-specific behavior.

Consequences:

- CAL-specific parsers, tools, docs, examples, and skills remain in CAL-MCP;
- a stable package/entry point is published before Agora registration;
- Agora integration pins a release and performs smoke-level verification only;
- CAL-MCP source must not import Agora runtime code.

## D-004 — Public MCP schemas are separated from upstream HTML/forms

**Status:** accepted — 2026-09-03

CAL's current PHP handlers and HTML layout are undocumented implementation details. Public MCP models expose scholarly concepts instead of DOM/form structure.

Consequences:

- endpoint-specific parsers live behind services;
- markup-only changes should normally be absorbed without MCP schema changes;
- material semantic fields cannot be silently discarded;
- parser drift produces explicit errors when fidelity is uncertain.

## D-005 — Input normalization is deterministic

**Status:** accepted — 2026-09-03

Normalization/query encoding uses explicit deterministic rules and CAL-supported representations. It does not use an LLM to infer spellings, roots, or analyses.

Consequences:

- preserve original input;
- expose normalized query/strategy when useful for reproducibility;
- ambiguous/lossy conversions are explicit;
- prefer sending a script/representation directly when CAL supports it faithfully.

## D-006 — Provenance is part of the public result contract

**Status:** accepted — 2026-09-03

Successful CAL-backed results expose at least a CAL source URL and retrieval timestamp. CAL identifiers/coordinates and original/normalized query metadata are preserved when available/applicable.

Rationale: CAL is a live work in progress and explicitly asks scholarly users to cite retrieval dates.

## D-007 — Normal CI is offline; live tests only detect drift

**Status:** accepted — 2026-09-03

Deterministic tests use minimal fixtures and mocked HTTP. Live CAL tests are opt-in/scheduled/release smoke checks with strict request caps.

Consequences:

- CI is not coupled to CAL uptime;
- tests cannot accidentally create sustained automated load;
- live tests prove integration compatibility, not scholarly correctness.

## D-008 — Conservative request behavior until CAL publishes explicit machine guidance

**Status:** accepted — 2026-09-03

No CAL-specific automated-access/API policy was found in the initial research snapshot. CAL-MCP therefore defaults to low concurrency, bounded retries, finite timeouts, bounded caching, and no prefetching.

This decision is operational caution, not a legal interpretation of CAL's terms.

Any material increase in automated request volume requires a new/updated decision citing current CAL guidance or concrete operational evidence.

## D-009 — stdio is the required v0.1 transport

**Status:** accepted — 2026-09-03

The first release will be a local MCP process with stdio support. A hosted/network transport is not required for v0.1.

Consequences:

- CAL-MCP avoids hosting/auth/abuse/rate-sharing complexity;
- clients and Agora can launch the same local package;
- application/core layers remain transport-agnostic so another MCP transport can be added later without rewriting CAL services.

## D-010 — Documentation is split by audience and ships with behavior

**Status:** accepted — 2026-09-03

- root docs provide project state and entry points;
- `wiki/` stores maintainer/agent architecture, testing, decisions, and process;
- `docs/` stores versioned user-facing documentation and is added incrementally with implemented capabilities;
- executable tool schemas remain the technical source of truth.

Consequences:

- feature PRs update user docs in the same change;
- no empty aspirational tool pages;
- diagrams use Mermaid in Markdown and change with architecture;
- examples should be test-backed.

## D-011 — Do not prematurely choose a static documentation generator

**Status:** accepted — 2026-09-03

The bootstrap uses repository Markdown and GitHub Mermaid rendering. A static documentation generator will be selected only when enough `docs/` content exists to justify it, using criteria in `documentation.md`.

Rationale: this avoids creating framework maintenance work before there is a stable public API to document.

## D-012 — Related CAL/Aramaic projects are prior art, not compatibility targets

**Status:** accepted — 2026-09-03

Projects such as PSHAT and Peshitta MCP may inform edge cases and agent-facing ergonomics, but CAL-MCP will not inherit their data models/interfaces by default.

Any copied/reused code requires an issue that verifies license compatibility and demonstrates that reuse is preferable to a small native implementation.
