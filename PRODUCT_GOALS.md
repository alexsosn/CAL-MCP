# Product goals — CAL-MCP

## Users and purpose

Researchers of Aramaic, Syriac and Targum traditions should be able to use the existing Comprehensive Aramaic Lexicon (CAL) through a stable, conservative, read-only MCP interface, retrieve original CAL evidence and understand where results or interpretations remain uncertain.

## Representative research journeys

1. Look up an Aramaic or Syriac lemma from a practical input form, inspect CAL lexical senses and follow a citation to its original source.
2. Search texts or concordances by CAL-supported selectors, inspect KWIC contexts and trace examples to stable CAL text identities.
3. Investigate a Syriac textual or lexical question using the specific CAL search/group tools without silently changing dialect or fabricated grouping.
4. Compare a Hebrew lemma with a Targum reflex or parallel where CAL directly supplies the relevant evidence.
5. Find CAL bibliographic material linked to a lemma, keyword, scholar or recent listing and recover the original CAL record/URL.

## Minimum usable release

An independently installed MCP server launches over stdio and a researcher/client can complete representative real, bounded CAL requests across the published tool surface with typed results, source links, honest unavailable/uncertain states, clear failures and documented rate/resource limits. Offline contract checks and limited live CAL smoke both matter. Distinguish released v0.1.0 from a source-only v0.2.0 candidate until PyPI/GitHub distribution is actually verified.

## Scope boundary and priority

CAL owns lexicon, text, bibliography and scholarly judgment. This service must not mirror, crawl, scrape in bulk, prefetch entire CAL corpora, persist CAL contents or manufacture linguistic analyses. Use one existing stdio/MCP transport, not separate adapters per CAL page. Keep Agora optional. Priority: finish and verify a truthful v0.2.0 release and first-researcher workflows before adding more specialized tools or generalized middleware.

## Autonomous-development decision rules

- Select work by the researcher journeys above, not issue count or the ease of adding tests. Prefer finishing active PRs and releases over opening new tickets.
- Before introducing a new adapter, workflow, registry, protocol, or validation layer, demonstrate that an existing mechanism cannot meet a concrete acceptance need.
- Preserve source fidelity, access controls, security, and applicable upstream rights. Do not invent inferred text or silently weaken correctness gates.
- Batch repetitive data changes and reuse parameterized tests. Keep independent adversarial review proportional to risk, and validate the actual researcher path.
- If two successive cycles do not advance a journey or remove an observed blocker, reconsider the approach. Stop when the scoped deliverable works instead of generating optional infrastructure work.
