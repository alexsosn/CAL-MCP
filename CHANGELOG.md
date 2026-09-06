# Changelog

## 0.1.0 — 2026-09-06

First standalone CAL-MCP release.

### Released interface

- 26 public tools over local MCP stdio via the installed `cal-mcp` command;
- bounded CAL lexicon lookup, English gloss/citation search, text discovery/retrieval, token analysis, concordance/KWIC, bibliography, dictionary spelling collation, Targum Studies, Syriac Studies, and external/non-online-text citations;
- typed CAL provenance with source URL and retrieval timestamp on CAL-backed results;
- deterministic input normalization and explicit CAL identifiers rather than exposing CAL form/DOM internals;
- conservative CAL HTTP policy with finite timeouts, bounded transient retries, same-origin request enforcement, response-size limits, low concurrency, process-local bounded caching, and duplicate-request suppression.

### Release/runtime contract

- package: `cal-mcp==0.1.0`;
- Python: 3.11 or newer;
- required transport: stdio;
- executable: `cal-mcp` with no required arguments;
- module equivalent: `python -m cal_mcp`;
- CAL-MCP runs independently of Agora.

### Verification

Normal CI is offline with respect to CAL and uses reduced fixtures/mocked transports. Release verification additionally builds an sdist and wheel, installs the built wheel into a clean environment, and launches the installed stdio command. A separate opt-in/scheduled live drift smoke uses eight fixed public-tool calls, sequential execution, retries disabled, cache disabled, concurrency 1, and a hard maximum of nine CAL requests.

### Known limitations

- CAL-backed operations require live network access to `https://cal.huc.edu/`; CAL-MCP is not an offline CAL mirror.
- No CAL corpus, lexicon, text, bibliography, or dictionary data is bundled in the package.
- CAL's undocumented HTML/PHP interfaces can change; parser drift is reported explicitly rather than silently converted to empty data.
- Some CAL workflows require caller-controlled follow-up calls; CAL-MCP does not crawl discovered texts, lemmas, dialects, sources, or pagination automatically.
- v0.1 requires stdio; no hosted CAL-MCP service is provided.
- Agora registration is a separate downstream step after this release.
- This release does not claim PyPI publication unless a separately reviewed authenticated package-index publication path is established.
