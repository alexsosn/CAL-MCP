# Lexicon lookup and CAL-code conversion

`cal_convert_to_code` is a local-only conversion helper for supported Aramaic input representations. `cal_lexicon_lookup` resolves a CAL-supported root, headword, alias, or full form to structured lexicon data while preserving CAL's own homograph and sense distinctions. `cal_lexicon_citation_context` explicitly follows one typed citation-context selector returned by lexicon lookup.

The converter performs **zero network requests**. Lexicon lookup and citation-context follow-up perform live, bounded requests to CAL. CAL remains the authority for lexical and citation content; CAL-MCP supplies deterministic conversion/normalization, typed structure, request policy, and provenance.

## Local converter

```text
cal_convert_to_code(value, representation=None)
```

The converter returns ordered CAL-code candidates per explicit space-separated word. A deterministic word has one candidate. A grapheme with a researched finite ambiguity returns every justified candidate rather than choosing one. For example, bare square-script `ש` expands to CAL `$` (shin) and `&` (sin), while `שׁ` and `שׂ` remain deterministic.

The result includes `original`, `representation`, `strategy`, and `words`. Each word records `original`, ordered `candidates`, and `ambiguities`; an ambiguity records its input index, input grapheme, and ordered CAL-code alternatives.

Candidate expansion is bounded. Unsupported or unverified vowels, combining marks, punctuation, editorial notation, mixed scripts, or other characters are rejected rather than silently stripped or linguistically guessed. Ordinary spaces are not converted to CAL `@`, because `@` carries CAL lexical-structure semantics that whitespace alone does not establish.

The current v0.1 conversion contract is intentionally table-driven and grows only after script-specific research and tests. See [Input and transliteration](../concepts/input-and-transliteration.md).

## Lookup tool

```text
cal_lexicon_lookup(query, lemma_key=None)
```

### `query`

The lexical form to look up. The shared normalization layer accepts the CAL-supported input representations implemented by CAL-MCP, including CAL/Unicode transliteration, Hebrew square script, and Syriac. See [Input and transliteration](../concepts/input-and-transliteration.md).

For CAL-native Hebrew/Syriac lookup, verified base letters may retain documented pointing/vocalization and the CAL-native bound-form `_` separator even when the stricter local converter cannot represent the whole query. The lookup keeps those forms unchanged on the bounded native browser path; unverified base letters, unsupported punctuation, and unattached marks still fail locally before CAL I/O.

Normalization is deterministic. The lookup layer does not infer roots, apply fuzzy spelling correction, rank senses semantically, or choose a homograph by probability.

When the input contains a researched finite orthographic ambiguity, lookup generates the corresponding bounded CAL-code candidates and searches every required **unique** CAL browser prefix. Duplicate prefixes are requested once, and multiple encoding paths that resolve to the same CAL lemma are deduplicated by canonical `lemma_key`.

### `lemma_key`

Optional exact CAL lemma key used only to disambiguate candidates returned for the same query.

Do not invent this value. If a lookup returns `status: "ambiguous"`, select one of the returned `matches[].lemma_key` values and repeat the same query with that key. A key that is not among the current query's matching candidates is rejected.

CAL endpoint names, DOM structure, and PHP form parameters are not part of the MCP contract.

## Lookup behavior

For deterministic input a lookup uses the minimum bounded CAL flow needed by the current public lexicon interface:

1. one lexicon-browser request using at most the first three normalized browser symbols;
2. exact matching against CAL headwords and aliases returned by that bounded browser page;
3. when exactly one candidate is selected, one entry request for that CAL lemma key.

Therefore:

- a deterministic not-found lookup uses one CAL request;
- a deterministic ambiguous lookup uses one CAL request and does not fetch every candidate entry;
- a successful lookup normally uses two CAL requests;
- the tool does not enumerate neighboring entries or build a local lexicon index.

For finite encoding ambiguity, all complete CAL-code candidates are derived **before** network access. They are grouped by browser prefix. At most eight unique browser-prefix requests are permitted per public lookup; exceeding that cap raises before the first CAL request. Ambiguity occurring after the three-symbol browser prefix therefore adds no request. After browser aggregation the adapter fetches at most one selected entry, so the absolute ambiguity-aware bound is eight browser requests plus one entry request.

For CAL multiword browser input, the documented `@`/space convention is preserved when the bounded prefix is constructed. Combining marks do not consume an additional browser-symbol slot.

## Result states

Every normal lookup result has a `status` field.

### `found`

`entry` contains the selected structured lexicon entry. `matches` contains the selected lemma reference, and `provenance.upstream_id` is the CAL lemma key.

The entry preserves, where present:

- CAL lemma key;
- headword variants and pronunciation;
- part of speech and entry gloss, including compound/current CAL abbreviations rather than a small closed local POS vocabulary;
- numbered and recursively nested sense paths;
- verb stem/sense headings;
- dialect labels, including documented CAL dialect subcodes;
- citation references, source links, short citation text, and typed context selectors when CAL exposes the canonical context-link route;
- root/grammar information;
- form and usage notes;
- derivatives and their hierarchy depth;
- notes and bibliography text exposed in the parsed entry section.

Optional CAL sections are represented as empty lists when absent. Required entry semantics disappearing from an upstream page is treated as parser drift rather than silently returning a partial entry.

### `ambiguous`

CAL exposes more than one exact matching lemma/homograph after all bounded encoding candidates are aggregated. `entry` is `null`; `matches` contains the typed candidates.

For example, the deterministic fixture for `br` preserves both CAL keys:

```json
{
  "status": "ambiguous",
  "matches": [
    {"lemma_key": "br N", "headwords": ["br", "brˀ"]},
    {"lemma_key": "br#2 N", "headwords": ["br", "brˀ"]}
  ]
}
```

The actual match objects also include pronunciation, part of speech, gloss, and aliases. CAL-MCP does not guess which homograph the caller intended.

To select the first candidate, call:

```text
cal_lexicon_lookup(query="br", lemma_key="br N")
```

### `not_found`

No exact CAL headword or alias on the bounded browser results matches any justified query candidate. `entry` is `null` and `matches` is empty.

This is a normal structured result and is distinct from a network failure, CAL maintenance/error content, parser drift, or candidate-expansion limit.

## Alias and script examples

The test fixtures include CAL's alias arrow for `bˀyšh`, which resolves to the upstream lemma key `by$h N`. The adapter preserves the CAL key rather than rewriting it to a prettier local identifier.

Hebrew and Syriac inputs are compared deterministically against the same candidate surfaces where the shared normalization/lookup mapping establishes equivalence. The comparison preserves distinctions exposed by CAL's current lexicon-browser character table, including Hebrew shin/sin and Syriac `ܧ`/`ṗ`. This comparison exists to match CAL-supported lexical forms; it is not a general Hebrew↔Syriac transliterator.

## Entry structure

A successful `entry` has these top-level fields:

| Field | Meaning |
| --- | --- |
| `lemma` | CAL lemma reference: key, headwords, pronunciation, part of speech, gloss, aliases |
| `senses` | ordered CAL senses with `label_path`, optional stem heading, definition, dialects, citations |
| `root` | CAL root text when exposed by the entry |
| `grammar` | grammar/stem labels preceding the senses when present |
| `form_usage` | CAL form/usage lines |
| `derivatives` | linked derivatives with CAL key when available and hierarchy `depth` |
| `notes` | CAL notes/bibliography text parsed from the entry section |

A citation has `reference`, `url`, `text`, and nullable `full_coordinate`. For a linked CAL citation, `reference` and `url` preserve the rendered reference and its CAL link. `full_coordinate` is populated only when that resolved link is the canonical current CAL citation-context route with exactly one positive ASCII-decimal selector. A citation URL that is noncanonical, has extra controls, or is not a context link is still preserved as citation metadata but has `full_coordinate: null`; CAL-MCP never turns an arbitrary returned URL into an executable selector.

Current CAL entries can also render citation fragments without a link or a safely separable structured reference; in that case CAL-MCP preserves the whole fragment in `text` and returns `reference: null`, `url: null`, and `full_coordinate: null` rather than inventing those fields. Unicode citation text is preserved without transliteration.

When CAL renders a citation-count marker, the parsed citation count must agree with it. A mismatch is treated as parser drift so silently dropped citation fragments do not produce an apparently complete entry.

## Linked citation full context

```text
cal_lexicon_citation_context(full_coordinate)
```

Use this only with a non-null `Citation.full_coordinate` returned by `cal_lexicon_lookup`. The selector is treated as an opaque CAL coordinate string: CAL-MCP does not split it into locally invented file, chapter, verse, or subtext fields, and the tool does not accept a URL.

A cache-miss call performs exactly one bounded CAL request for that explicit selector. Lexicon lookup never prefetches citation context, and the context operation never follows its returned source-information, token, comment, or navigation links automatically.

A normal result contains:

- `status`: `found` or `not_found`;
- the exact `full_coordinate` submitted by the caller;
- optional CAL-rendered `source_label` and validated `source_info_url`;
- ordered `lines` using the same `TextLine`/`TextToken` structure as bounded text context;
- provenance with the actual CAL context URL, retrieval timestamp, operation name, and selector.

For `found`, the returned lines must contain the requested target coordinate exactly once. For `not_found`, CAL-MCP accepts only CAL's explicit no-citations marker when that marker is consistent with the requested selector and no text rows are present. A successful-looking page with neither recognizable rows nor the exact empty marker is parser drift.

The adapter validates the CAL response origin, route, selector identity, token/comment routes, and source-information link semantics. Current citation-context pages do **not** share the KWIC route's special tolerance for an empty terminal lexical anchor; an empty lexical token label on this route fails closed.

## Provenance

`provenance` is adapter metadata describing the live CAL retrieval and, when conversion-driven search is used, the exact bounded conversion path that led to the result:

| Field | Meaning |
| --- | --- |
| `source` | `CAL` |
| `source_url` | exact CAL URL represented by the parsed result |
| `retrieved_at` | retrieval timestamp in ISO 8601 form |
| `upstream_id` | selected CAL lemma key for `found`; otherwise `null` |
| `original_query` | caller input before normalization |
| `normalized_query` | deterministic normalized query |
| `representation` | detected/selected input representation |
| `normalization_strategy` | normalization strategy used by CAL-MCP |
| `cal_code_word_candidates` | ordered CAL-code candidate list for each input word when lookup uses the converter; empty for the legacy pass-through lookup path |
| `cal_code_query_candidates` | ordered complete CAL-code query candidates used for conversion-driven matching; empty for the legacy pass-through lookup path |
| `browse_prefixes` | exact ordered unique CAL browser prefixes actually requested for this lookup |
| `selected_cal_code_candidates` | conversion candidates that matched the selected lemma when one entry is fetched; empty for `not_found`, unresolved `ambiguous`, and legacy pass-through results |

The four conversion-path keys are always present in serialized provenance, even when their values are empty. This keeps the v0.1 result schema stable across deterministic, ambiguous, found, and not-found results. When multiple encoding candidates resolve to one canonical CAL lemma, the lemma is returned once while `selected_cal_code_candidates` retains every matching encoding path in stable candidate order.

Citation-context results use their own smaller provenance object because `full_coordinate` is already the complete researched selector for that route. CAL describes its database as a live work in progress, so scholarly use should retain the source URL and retrieval date. Cache hits preserve the timestamp of the actual CAL retrieval rather than fabricating a newer one.

## Failure modes

The tools keep these cases separate:

- **not found** — normal lexicon `not_found` result, or a citation-context `not_found` result only when CAL returns the validated explicit no-citations marker;
- **ambiguous lexical match** — normal `ambiguous` result with explicit CAL candidates;
- **finite encoding ambiguity** — explicit candidate sets, automatically searched within fixed bounds;
- **candidate expansion overflow** — typed local failure before unbounded computation or CAL traffic;
- **unsupported conversion input** — typed local failure rather than lossy conversion;
- **invalid `lemma_key`** — caller error because the key is not one of the current matches;
- **invalid `full_coordinate`** — caller error before CAL I/O; it must be a positive ASCII-decimal string;
- **network/timeout/upstream HTTP failure** — typed request-layer failure under the conservative retry policy;
- **CAL maintenance/error page** — content failure before lexicon parsing;
- **parser drift** — CAL returned HTML, but required semantics can no longer be recognized safely, including inconsistent recursive sense numbering, citation-count mismatches, citation-context route/selector contradictions, or malformed context rows.

See [Configuration](../configuration.md) for request, retry, cache, redirect, and response-size policy.

## Limits and non-capabilities

The converter and lexicon operations do not provide:

- morphological analysis, lemmatization, root inference, or historical spelling reconstruction;
- fuzzy or semantic ranking;
- unsupported-diacritic stripping;
- English gloss search across the lexicon;
- concordance/KWIC queries;
- corpus text browsing;
- token-at-coordinate analysis;
- CAL data correction;
- bulk extraction or lexicon crawling;
- automatic citation-context traversal;
- a generic URL-following operation;
- local decoding of opaque `full_coordinate` values;
- a persistent local CAL database.

Those are separate capabilities or deliberate non-goals. Use `cal_convert_to_code` when the task is representation conversion, `cal_lexicon_lookup` when the task needs CAL lexical content, and `cal_lexicon_citation_context` only for an explicit typed context selector returned by lookup.

## Fixture and reproducibility policy

Normal tests make no CAL requests. Parser tests use deliberately reduced HTML excerpts with source/capture provenance in `tests/fixtures/cal/README.md`; the repository does not archive complete CAL pages. Upstream markup changes should update those fixture contracts only after the new CAL semantics have been checked explicitly.
