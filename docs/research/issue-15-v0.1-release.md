# Issue #15 research — v0.1 standalone release and live drift smoke

**Rechecked:** 2026-09-06

## Release baseline

Current `main` at `5d4d57414adcf87607bc23e57d17b283102f6ea8` has the v0.1 public contract frozen by #12 and the release-blocking live parser fixes #41/#42 merged. There are no open pull requests.

Packaging is already standard Python packaging through Hatchling:

- project name: `cal-mcp`;
- current development version: `0.1.0.dev0`;
- Python: `>=3.11`;
- runtime dependencies: `httpx2>=2.12,<3`, `mcp>=2,<3`;
- installed console entry point: `cal-mcp = cal_mcp.server:main`;
- equivalent module launch: `python -m cal_mcp`;
- required v0.1 transport: local stdio.

The existing deterministic suite already proves that the installed editable `cal-mcp` entry point starts over stdio and exposes the frozen 26-tool schema without contacting CAL. It does not yet prove that a built wheel/sdist installs cleanly in a fresh environment.

No GitHub releases currently exist and the repository has no PyPI publication workflow or package-index credential/configuration. For #15, the bounded publishable artifact is therefore a GitHub `v0.1.0` release containing the source distribution and universal wheel built from the reviewed release commit. PyPI publication is not claimed by this ticket unless a separate authenticated/reviewed publication path is introduced.

## Existing live-smoke evidence

Issue #15 already performed one temporary bounded research probe in Actions run `33995822616` on 2026-09-05. The workflow self-removed after the run.

The probe used one shared `CalHttpClient` configured with:

- `max_concurrency=1`;
- `max_retries=0`;
- `cache_enabled=False`;
- explicit hard budget `MAX_REQUESTS=9`.

It called eight public MCP tools sequentially:

1. `cal_lexicon_lookup(query="br", lemma_key="br N")`;
2. `cal_text_search(query="Tel Dan")`;
3. `cal_text_concordance(text_id="13250")`;
4. `cal_bibliography_lemma(lemma_key="cly V")`;
5. `cal_dictionary_collation(source="jastrow", page="705")`;
6. `cal_external_citation_dialects()`;
7. `cal_targum_parallel(book="Gen", chapter=1, verse=1)`;
8. `cal_syriac_peshitta_parallel(book="Gen", chapter=1, verse=1)`.

The run made exactly nine CAL requests because the selected lexicon operation performs candidate discovery plus one selected-entry fetch; each other operation made one request. The probe exposed two real release blockers: the lexicon citation parser (#41) and current single-text concordance parser (#42). Both are now fixed and merged.

A second important finding was in the probe harness itself: MCP tool failures were returned as `CallToolResult` values with `result.is_error == True`; merely receiving a result object did not mean success. The research script printed the two failed tools as `OK` because it inspected only `structured_content` and did not check `is_error`. Permanent smoke must therefore fail immediately on `is_error`.

## Permanent smoke boundary

Normal CI must remain CAL-independent. Permanent live smoke belongs in a separate workflow invoked manually and on a low-frequency schedule/release gate.

The v0.1 smoke should preserve the researched eight-operation coverage and hard nine-request ceiling because it spans the major released surface families without enumeration. Requirements:

- sequential execution only;
- one shared client;
- concurrency fixed at 1;
- retries disabled;
- cache disabled;
- exactly the fixed eight tool calls above; no discovered-result traversal;
- a hard request counter that raises before request 10;
- fail on MCP `result.is_error`;
- require structured output and CAL provenance on successful CAL-backed results;
- classify infrastructure/network/upstream HTTP failures separately from adapter/parser/tool failures as far as the MCP error payload permits;
- always report observed request count;
- no corpus, text, dialect, bibliography, dictionary, citation, or lemma iteration.

A fake-result unit test must establish the `is_error` failure behavior before the live workflow is enabled.

## Release artifact/clean-install boundary

The release candidate must be built from the reviewed tree as both sdist and wheel. Deterministic CI should:

1. build both artifacts;
2. create a fresh virtual environment;
3. install the built wheel rather than the source tree/editable checkout;
4. assert installed metadata version `0.1.0`;
5. launch the installed `cal-mcp` command over stdio and perform MCP initialization/tool discovery without CAL network access.

The package contains software only; no CAL pages/data are bundled.

## Publication ordering

Tag/release publication is a post-merge action, not a way to test the branch. The safe order is:

research → committed plan → test-only RED → implementation → full offline GREEN → bounded live GREEN → exact-head independent adversarial review → merge → verify merged main → create `v0.1.0` release/tag from that exact merge commit and attach built artifacts.

If the bounded live smoke discovers new drift, publication stops and the defect gets its own focused research/plan/TDD/review loop before #15 resumes.
