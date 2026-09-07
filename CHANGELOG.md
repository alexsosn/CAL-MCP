# Changelog

## 0.1.0 — 2026-09-06

First standalone release candidate for CAL-MCP, a read-only MCP adapter over the Comprehensive Aramaic Lexicon (CAL).

### Public MCP surface

v0.1.0 freezes **26 public tools** across these research families:

- lexicon lookup;
- English gloss and citation-text search;
- text catalogue/topic discovery and one-page retrieval;
- token-at-coordinate lexical analysis;
- one-text concordance and explicit text/dialect KWIC;
- bibliography author, text/subject-tag, and lemma search;
- dictionary spelling collation;
- citations from sources that CAL cites but does not expose as full online texts;
- Targum parallel verse, Targum concordance, and MT-Hebrew reflex workflows;
- Syriac text-category discovery, CAL's missing-from-*A Syriac Lexicon* lists, and MT/Peshitta verse comparison.

The executable MCP schemas remain the technical source of truth. CAL endpoint names and private form fields are not part of the public contract.

### Request and data policy

- CAL data stay remote and live; no CAL corpus or lexicon is bundled in the package.
- Operations are caller-initiated and bounded. Most public calls perform one CAL request; successful exact lexicon lookup uses a bounded two-request browser + selected-entry flow.
- No background crawl, mirror, cache warming, hidden pagination, link traversal, or automatic source expansion.
- The shared client enforces finite timeouts, low concurrency, bounded transient-only retries, redirect/origin boundaries, response-size limits, single-flight suppression, and a bounded process-local cache.
- Parsers fail closed on material upstream drift rather than returning plausible partial results.

### Standalone runtime

- Python `>=3.11`.
- Primary v0.1 transport: local stdio.
- Installed command: `cal-mcp`.
- Equivalent module entry point: `python -m cal_mcp`.
- Agora is not a runtime dependency; optional Agora registration remains the downstream issue #16 after publication.

### Release and drift validation

- The release pipeline builds wheel and sdist once, validates the built wheel in a fresh virtual environment, launches its installed `cal-mcp` entry point over stdio, and checks version + the frozen 26-tool schema without contacting CAL.
- A separate live drift smoke is opt-in/scheduled and capped at **9 CAL requests**, concurrency 1, retries 0, cache disabled.
- The live smoke covers eight representative parser/service families and distinguishes parser drift from network/upstream and other content/policy failures.

### Known limitations

- CAL is a live scholarly database and its public HTML/form surfaces are not a versioned machine API; upstream drift can temporarily fail a tool closed until the adapter is updated.
- v0.1 does not bundle CAL data or provide an offline research mode.
- v0.1 is stdio-only; there is no hosted CAL-MCP service.
- CAL's recent-five-years bibliography snapshot is intentionally deferred to #39 and is not part of the frozen v0.1 surface.
- Pseudo-Jonathan Hebrew-reflex research is not exposed because CAL currently marks that upstream workflow under development.
- Dependency reproducibility/latest-compatible CI policy remains the separate non-blocking issue #18; v0.1 does not narrow reviewed runtime dependency ranges merely for release packaging.

### Upstream and attribution

CAL remains the authority for the returned lexical, textual, citation, bibliography, Targum, Syriac, and dictionary-collation content. CAL-MCP is not affiliated with or endorsed by the Comprehensive Aramaic Lexicon Project or Hebrew Union College.