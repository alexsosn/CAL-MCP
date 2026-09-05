# Provenance and citation

CAL is a live scholarly database. CAL-MCP therefore treats provenance as part of the result contract rather than as incidental logging.

## Common guarantees

Successful CAL-backed result families preserve at least:

- `source` identifying CAL;
- `source_url` — the actual upstream CAL result URL associated with the parsed response;
- `retrieved_at` — a timezone-aware timestamp for the actual CAL retrieval.

Task-specific provenance also preserves useful submitted/original identifiers where that information exists, for example:

- original and normalized/submitted query text;
- selected CAL text/file/subtext/page identifiers;
- canonical lemma key;
- selected bibliography mode/tag/author;
- dictionary source/page;
- biblical book/chapter/verse;
- Targum/Syriac selector values or source abbreviations.

The auxiliary fields are intentionally not forced into one universal shape when CAL surfaces do not share the same semantics.

## Retrieval time versus cache reuse

CAL-MCP's completed-result cache is process-local and exists only to suppress duplicate live requests during one running server session.

A cache hit keeps the `retrieved_at` value from the original CAL response. It does **not** rewrite that timestamp to the later time when the cached result was reused. This prevents a cached answer from looking like a fresh CAL retrieval.

The same principle applies to duplicate in-flight requests: waiting callers receive the result of the single active CAL request rather than a fabricated second retrieval.

See [Configuration](../configuration.md) for cache/single-flight policy.

## CAL identifiers versus adapter metadata

Fields such as lemma keys, text/file IDs, coordinates, source abbreviations, and rendered labels originate in CAL. CAL-MCP preserves them so a caller can make an explicit follow-up request, but it does not promise that undocumented CAL identifiers are permanent across all future upstream revisions.

Fields such as an operation name, submitted query normalization strategy, cache metadata, or the public adapter source enum are CAL-MCP metadata.

See [CAL identifiers](cal-identifiers.md) for identifier stability boundaries.

## Reproducible scholarly use

When retaining a CAL-MCP result for analysis or publication, keep together:

1. the relevant CAL content/result fields;
2. `source_url`;
3. `retrieved_at`;
4. the CAL identifier/query that identifies the requested object;
5. any normalization/submitted-query metadata needed to reproduce the request.

CAL's own project documentation describes the lexicon/database as a work in progress and asks scholarly users to cite the date of retrieval. CAL-MCP exposes the retrieval timestamp to make that practical; it does not define a replacement citation style for CAL or underlying editions.

For a workflow-oriented checklist, see [Reproducible citations](../guides/reproducible-citations.md).

## Links returned by CAL

Some results contain same-origin CAL URLs to a lexicon entry, text chapter, KWIC examples, or other follow-up view. Such links are provenance/navigation metadata unless the current tool explicitly models that target.

CAL-MCP does not automatically follow those links. Following one is another explicit caller operation. This keeps both request load and scholarly scope visible.

## Empty and not-found results

An explicit empty/not-found result may still carry provenance because CAL was successfully contacted and reported that semantic state. That is different from a network/upstream/parser failure where no trustworthy CAL result was produced.

See [Errors and upstream drift](errors-and-upstream-drift.md) for the distinction.

## Data-rights boundary

The MIT license covers CAL-MCP software and repository documentation. It does not grant rights to CAL data, CAL website content, underlying text editions, or third-party dictionaries. Provenance fields help identify the upstream source but do not change those rights.