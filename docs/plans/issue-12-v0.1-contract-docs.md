# Issue #12 plan — stabilize v0.1 public contract and user documentation

**Plan date:** 2026-09-06

This ticket follows research → plan → test-only RED → minimal implementation → full GREEN → documentation/architecture verification → logically independent adversarial review → review-regression RED/GREEN if needed → fresh exact-head review → guarded merge.

## Frozen scope

The v0.1 public MCP surface is the 26 tools already frozen by `tests/test_bootstrap.py`. This issue does **not** add a new CAL research operation unless a failing regression proves a release-blocking defect in an existing contract.

The capability audit in `docs/research/issue-12-v0.1-contract-docs.md` classifies every current CAL search/module workflow as:

- directly implemented;
- intentionally composed from existing bounded tools;
- explicitly deferred/reference-only.

The newly identified recent-bibliography snapshot is tracked separately as issue #39 and is non-blocking for v0.1.

## Contract policy to freeze

After this issue:

- the 26 public tool names and current argument schemas are frozen for v0.1 except release-blocking regression fixes;
- raw CAL endpoint/form names remain private adapter details;
- successful CAL-backed results preserve source URL and actual retrieval timestamp plus task-specific provenance fields;
- caller errors, network/upstream failures, response-size/content failures, parser drift, explicit empty results, and not-found states remain semantically distinct where the upstream surface supports them;
- pagination/bounds remain surface-specific: no invented generic `page`, `offset`, `limit`, continuation, `show all`, or hidden traversal;
- composition is preferred over duplicate specialist wrappers when CAL itself reuses the same underlying text/citation/KWIC surface.

No common-model rewrite is planned merely for aesthetic uniformity.

## TDD RED gate

Before adding missing docs or changing architecture prose, add an offline `tests/test_docs_contract.py` that establishes executable documentation invariants.

The initial RED should assert at least:

1. required v0.1 user entry points exist:
   - `docs/index.md`
   - `docs/getting-started.md`
   - `docs/installation.md`
   - `docs/concepts/provenance-and-citation.md`
   - `docs/concepts/errors-and-upstream-drift.md`
   - `docs/guides/lexical-research.md`
   - `docs/guides/corpus-context.md`
   - `docs/guides/reproducible-citations.md`
   - `docs/integrations/standalone-mcp.md`
   - `docs/limitations.md`;
2. every executable public MCP tool name appears in at least one `docs/tools/*.md` page;
3. every current `docs/tools/*.md` page is linked from the user documentation index;
4. relative Markdown links in `README.md` and `docs/**/*.md` resolve to repository files/directories (ignore external URLs and intra-page fragments);
5. the user docs do not claim an Agora integration exists before issue #16 (no required `docs/integrations/agora.md` in v0.1 contract);
6. a dated capability matrix exists in the user docs and explicitly references deferred issue #39.

A valid RED requires install, Ruff lint, Ruff format check, and strict mypy to remain green while pytest fails only because these issue-12 documentation artifacts/invariants are not yet satisfied.

Do not make production/schema changes to manufacture the RED.

## Minimal implementation / GREEN

### 1. User entry point and capability matrix

Add `docs/index.md` as the versioned user navigation root. It should contain a concise dated capability matrix derived from the research audit, with clear implemented/composed/deferred statuses and links to the relevant tool/concept pages.

It must not duplicate generated schemas or raw CAL form details.

### 2. Getting started

Add `docs/getting-started.md` with task-first guidance:

- Aramaic form → lexicon entry;
- English concept → candidate lemma → entry/attestations;
- text discovery → page → explicit token analysis;
- lemma → concordance/KWIC;
- lemma/text/subject → bibliography;
- external/non-online citations;
- Targum and Syriac specialist workflows;
- dictionary-page collation.

Examples must be drawn from existing fixture-backed tool documentation/tests. Do not invent live answers.

### 3. Installation and standalone integration

Add:

- `docs/installation.md` — current source/development installation, Python requirement, `cal-mcp` and `python -m cal_mcp` entry points, explicit statement that no versioned release has yet been published;
- `docs/integrations/standalone-mcp.md` — stdio launch/configuration concepts and client-agnostic process contract.

Release-from-package/PyPI instructions remain issue #15. Agora registration remains issue #16.

### 4. Cross-cutting concepts

Add:

- `docs/concepts/provenance-and-citation.md` — common provenance guarantees, cache timestamp semantics, CAL's retrieval-date requirement, task-specific fields;
- `docs/concepts/errors-and-upstream-drift.md` — caller validation vs network vs upstream HTTP vs content/size vs parser drift vs explicit empty/not-found states.

Do not claim MCP clients receive a richer structured error envelope unless executable code actually provides one; document adapter semantics and current exception taxonomy faithfully.

### 5. Research workflows

Add:

- `docs/guides/lexical-research.md`;
- `docs/guides/corpus-context.md`;
- `docs/guides/reproducible-citations.md`.

These pages should teach explicit composition and prevent hidden broad traversal. They should choose the narrowest relevant tool and show when a second explicit call is required.

### 6. Limitations

Add `docs/limitations.md` covering at least:

- live upstream dependency and CAL work-in-progress status;
- no bundled CAL data/offline research mode;
- undocumented upstream HTML/form contract and parser-drift risk;
- bounded response/request policy;
- no automatic corpus traversal or invented pagination;
- v0.1 deferred recent bibliography #39;
- no static archive wrapping merely for completeness;
- current specialist source limitations (for example CAL's under-development Pseudo-Jonathan reflex path as already documented);
- pre-release installation status until #15.

### 7. README simplification

Keep README a landing page. Add a prominent `docs/index.md` path and reduce duplicated navigation where safe, but do not remove maintainer entry points or current status information needed before release.

### 8. Architecture/documentation correction

Update `wiki/architecture.md` so detailed diagrams describe current code rather than the old target layout:

- include token analysis, external citations, and dictionary collation in implemented application surfaces;
- describe the current flat `src/cal_mcp/*.py` modules rather than a nonexistent `models/`, `parsers/`, `services/` hierarchy;
- keep CAL/Agora/runtime ownership boundaries unchanged.

Update `wiki/documentation.md` target tree to include tool pages that actually landed after the original architecture note (`dictionary-collation.md`, `external-citations.md`) and clarify that `docs/integrations/agora.md` arrives with #16 rather than #12.

No architecture decision change is required unless implementation reveals a new durable boundary.

## Test/GREEN gate

After implementation, require the normal deterministic CI suite:

```text
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy
pytest
```

Normal tests perform zero CAL requests.

The docs-contract tests must demonstrate that:

- all required user pages exist;
- every public tool is covered by tool docs;
- tool pages are navigable from the user index;
- relative documentation links resolve;
- deferred capability #39 is visible rather than silently omitted.

## Public-contract audit gate

Before independent review, perform a deliberate non-editing audit of the current executable MCP schema against the docs:

- 26 tool names exactly;
- current required/optional arguments from `tests/test_bootstrap.py`;
- no raw CAL form controls exposed in docs as caller parameters;
- no user page claims a tool or integration that is not executable now;
- all top-level CAL-backed result families described as carrying source URL/retrieval time;
- boundedness/pagination language matches each tool page rather than implying one generic CAL pagination model.

If this audit finds an actual public behavior defect, stop and create a focused regression test (and separate issue if it is a newly discovered functional gap) before changing code.

## Adversarial review gate

Freeze an exact final SHA and conduct a logically independent whole-PR review from the user/release boundary rather than from implementation history.

Challenge specifically:

1. **Coverage:** does the matrix omit a current CAL search/module function or falsely mark one implemented?
2. **Redundancy:** are any specialist tools duplicating a generic workflow without CAL-specific semantics?
3. **Naming/ergonomics:** can an agent choose the narrowest tool from names/descriptions/docs without knowing CAL PHP/forms?
4. **Schema truth:** do docs state the current arguments rather than planned ones?
5. **Provenance:** is CAL source URL + retrieval timestamp consistently described without pretending task-specific fields are globally identical?
6. **Errors:** do docs distinguish empty/not-found from parser/upstream failure without promising an MCP error envelope the server does not implement?
7. **Bounds:** do docs accidentally encourage `show all`, archive enumeration, automatic next-page traversal, or hidden follow-ups?
8. **Install/release truth:** do pages clearly distinguish current source install from future published v0.1 and future Agora registration?
9. **Links/examples:** are examples fixture/test-backed and all local links valid?
10. **Architecture:** do diagrams match current modules and boundaries?
11. **Contract freeze:** is the 26-tool v0.1 freeze stated clearly and is issue #39 explicitly non-blocking/deferred?

Any blocker found after the first candidate must enter a review-regression RED → minimal fix → full GREEN → fresh exact-head adversarial review loop.

## Merge gate

Merge only when:

1. research and plan are committed before implementation;
2. docs-contract RED is valid;
3. missing documentation/architecture changes reach full deterministic GREEN;
4. no hidden feature implementation was introduced;
5. exact final SHA has green CI;
6. exact final SHA receives a clean logically independent adversarial review;
7. no unresolved review threads remain;
8. guarded merge pins the reviewed head SHA;
9. issue #12 closes.

## CAL access / load impact

Implementation and CI are offline. No new live CAL result probes are planned for the documentation work. If a review discovers a current-source ambiguity that cannot be resolved from public index/module pages and existing focused research, use at most a tiny fixed probe and record it explicitly; never enumerate a result family.