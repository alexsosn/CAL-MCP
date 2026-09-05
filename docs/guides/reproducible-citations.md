# Reproducible citations

CAL is a live, continuously maintained scholarly resource. A result retrieved today can differ from the same query after CAL is corrected or extended. CAL-MCP exposes provenance so research notes can record what was actually queried and when.

## Minimum record for a CAL-backed result

Keep these fields with any result used as evidence:

- `source_url` — the CAL page that produced the parsed result;
- `retrieved_at` — the timezone-aware CAL retrieval timestamp;
- the relevant CAL identifier or submitted query;
- any normalized/submitted-query value when CAL-MCP transformed a supported input representation;
- the exact result fields used in the analysis.

CAL's own documentation asks scholarly users to include the date of retrieval. CAL-MCP exposes that date/time but does not prescribe a replacement bibliographic style for citing CAL itself or the source editions represented by CAL.

See [Provenance and citation](../concepts/provenance-and-citation.md).

## Multi-step workflows have multiple retrievals

If a workflow uses several explicit calls, retain each call's provenance separately. For example:

```text
cal_gloss_search(...)
  -> returned lemma_key
cal_lexicon_lookup(...)
  -> lexical entry
cal_kwic_dialect(...)
  -> attestations
```

Those calls may come from different CAL URLs and may be retrieved at different times. Do not overwrite all timestamps with the final step's timestamp.

## Cache semantics

A process-local cache hit keeps the original CAL retrieval timestamp. This is intentional: a result reused from the cache is not a new upstream retrieval.

If a reproducibility experiment needs to force a new CAL retrieval, that is a request-layer configuration concern rather than a tool argument; the current public MCP schemas do not expose cache controls. See [Configuration](../configuration.md).

## Preserve CAL-owned identifiers

Where present, record the identifiers needed to state exactly what was used:

- canonical `lemma_key`;
- CAL file/subtext/page identifiers;
- line/token coordinate and token index;
- source abbreviation for cited-but-not-online material;
- dictionary source/page reference;
- book/chapter/verse for specialist biblical comparison;
- opaque selector IDs returned by CAL for workflows such as Targum Hebrew reflexes.

Do not assign undocumented semantic meaning to opaque IDs. See [CAL identifiers](../concepts/cal-identifiers.md).

## Record CAL content separately from interpretation

CAL-MCP returns CAL content plus adapter provenance. Your own conclusions, translations, statistical transformations, or linguistic interpretations are downstream research output and should not be recorded as though CAL supplied them.

The adapter likewise does not silently correct or enrich CAL data.

## Example research note

A compact research record can capture:

```text
Operation: cal_dictionary_collation
Dictionary source: jastrow
Page: 705
Returned CAL lemma key: lht V
CAL source URL: <source_url from result>
Retrieved: <retrieved_at from result>
Observation: <your own interpretation, clearly separated>
```

The same pattern applies to lexicon, texts, concordance, bibliography, Targum, Syriac, and external-citation workflows.

## Empty results are dated evidence too

When CAL explicitly reports a valid empty/not-found state, retain its provenance if the absence is relevant to the research question. It means “CAL reported this state for this request at this retrieval time,” not a timeless proof that no evidence exists.

A parser/network failure is different and should not be cited as an empty CAL result. See [Errors and upstream drift](../concepts/errors-and-upstream-drift.md).

## Underlying source rights and citation

CAL-MCP provenance identifies the upstream CAL retrieval. It does not replace citation requirements for underlying texts, editions, publications, or third-party dictionaries, and the CAL-MCP MIT license does not grant rights to those materials.

See [Limitations](../limitations.md).