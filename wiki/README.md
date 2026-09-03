# CAL-MCP maintainer wiki

This directory is version-controlled maintainer documentation for humans and coding agents. It is deliberately kept in the repository so architecture assumptions, test policy, and backlog state travel with the code.

## Start here

1. [`../research.md`](../research.md) — dated evidence about CAL and prior art.
2. [`../plan.md`](../plan.md) — staged implementation and dependency graph.
3. [`architecture.md`](architecture.md) — system boundaries, components, models, and request flows.
4. [`testing.md`](testing.md) — TDD, fixture, parser-contract, MCP-contract, and live-smoke policy.
5. [`documentation.md`](documentation.md) — user/maintainer documentation architecture and update rules.
6. [`decisions.md`](decisions.md) — durable project decisions.
7. [`backlog.md`](backlog.md) — issue map, dependencies, and release gates.
8. [`agentic-dev-loop.md`](agentic-dev-loop.md) — issue-to-merge automated workflow.

## Source-of-truth boundaries

| Concern | Source of truth |
| --- | --- |
| Current upstream evidence | `research.md` |
| Public project goals/non-goals | `README.md` |
| Delivery ordering | `plan.md` + GitHub issues |
| Durable architecture rules | `wiki/decisions.md` |
| Component design | `wiki/architecture.md` |
| Test requirements | `wiki/testing.md` |
| Documentation structure | `wiki/documentation.md` |
| Current execution state | GitHub issues/PRs |
| Public MCP tool schemas | executable server code/schema once implemented |
| User-facing semantics/examples | `docs/` once corresponding behavior exists |
| Agora marketplace metadata | downstream Agora registry after a CAL-MCP release |

Do not use chat history as project state. If a decision matters for future work, record it in the repository or issue tracker.

## Update discipline

- New CAL evidence: append/update `research.md` and link the exact source.
- Durable architectural choice: add a numbered decision in `decisions.md`.
- Changed component/data flow: update `architecture.md` and its diagrams.
- Changed public capability: update code/schema and the corresponding `docs/` page in the same PR.
- New/changed work item: update the GitHub issue; update `backlog.md` only if sequencing/release scope changes.
- Changed development/review process: update `agentic-dev-loop.md` and `AGENTS.md` together.
