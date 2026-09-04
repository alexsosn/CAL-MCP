# Lexicon lookup

`cal_lexicon_lookup` is the first CAL-backed scholarly tool in CAL-MCP. It resolves a CAL-supported root, headword, alias, or full form to structured lexicon data while preserving CAL's own homograph and sense distinctions.

The tool performs live, bounded requests to CAL. CAL remains the authority for the lexical content; CAL-MCP supplies normalization, typed structure, request policy, and provenance.

## Tool

```text
cal_lexicon_lookup(query, lemma_key=None)
```

### `query`

The lexical form to look up. The shared normalization layer accepts the CAL-supported input representations implemented by CAL-MCP, including CAL/Unicode transliteration, Hebrew square script, and Syriac. See [Input and transliteration](../concepts/input-and-transliteration.md).

Normalization is deterministic. The lookup layer does not infer roots, apply fuzzy spelling correction, rank senses semantically, or choose a homograph by probability.

### `lemma_key`

Optional exact CAL lemma key used only to disambiguate candidates returned for the same query.

Do not invent this value. If a lookup returns `status: "ambiguous"`, select one of the returned `matches[].lemma_key` values and repeat the same query with that key. A key that is not among the current query's matching candidates is rejected.

CAL endpoint names, DOM structure, and PHP form parameters are not part of the MCP contract.

## Lookup behavior

A lookup uses the minimum bounded CAL flow needed by the current public lexicon interface:

1. one lexicon-browser request using at most the first three normalized browser symbols;
2. exact matching against CAL headwords and aliases returned by that bounded browser page;
3. when exactly one candidate is selected, one entry request for that CAL lemma key.

Therefore:

- a not-found lookup uses one CAL request;
- an ambiguous lookup uses one CAL request and does not fetch every candidate entry;
- a successful lookup normally uses two CAL requests;
- the tool does not enumerate neighboring entries or build a local lexicon index.

For CAL multiword browser input, the documented `@`/space convention is preserved when the bounded prefix is constructed. Combining marks do not consume an additional browser-symbol slot.

## Result states

Every normal lookup result has a `status` field.

### `found`

`entry` contains the selected structured lexicon entry. `matches` contains the selected lemma reference, and `provenance.upstream_id` is the CAL lemma key.

The entry preserves, where present:

- CAL lemma key;
- headword variants and pronunciation;
- part of speech and entry gloss;
- numbered and nested sense paths;
- verb stem/sense headings;
- dialect labels;
- citation references, source links, and short citation text exposed by the entry;
- root/grammar information;
- form and usage notes;
- derivatives and their hierarchy depth;
- notes and bibliography text exposed in the parsed entry section.

Optional CAL sections are represented as empty lists when absent. Required entry semantics disappearing from an upstream page is treated as parser drift rather than silently returning a partial entry.

### `ambiguous`

CAL exposes more than one exact matching lemma/homograph. `entry` is `null`; `matches` contains the typed candidates.

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

No exact CAL headword or alias on the bounded browser result matches the normalized query. `entry` is `null` and `matches` is empty.

This is a normal structured result and is distinct from a network failure, CAL maintenance/error content, or parser drift.

## Alias and script examples

The test fixtures include CAL's alias arrow for `bˀyšh`, which resolves to the upstream lemma key `by$h N`. The adapter preserves the CAL key rather than rewriting it to a prettier local identifier.

Hebrew and Syriac inputs are compared deterministically against the same candidate surfaces where the shared normalization/lookup mapping establishes equivalence. This comparison exists to match CAL-supported lexical forms; it is not a general Hebrew↔Syriac transliterator.

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

A citation has `reference`, optional `url`, and `text`. CAL-MCP preserves Unicode citation text instead of transliterating it.

## Provenance

`provenance` is adapter metadata describing the live CAL retrieval:

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

CAL describes its database as a live work in progress, so scholarly use should retain the source URL and retrieval date. Cache hits preserve the timestamp of the actual CAL retrieval rather than fabricating a newer one.

## Failure modes

The tool keeps these cases separate:

- **not found** — normal `not_found` result;
- **ambiguous** — normal `ambiguous` result with explicit CAL candidates;
- **invalid `lemma_key`** — caller error because the key is not one of the current matches;
- **network/timeout/upstream HTTP failure** — typed request-layer failure under the conservative retry policy;
- **CAL maintenance/error page** — content failure before lexicon parsing;
- **parser drift** — CAL returned HTML, but required lexicon semantics can no longer be recognized safely.

See [Configuration](../configuration.md) for request, retry, cache, redirect, and response-size policy.

## Limits and non-capabilities

`cal_lexicon_lookup` does not provide:

- English gloss search across the lexicon;
- concordance/KWIC queries;
- corpus text browsing;
- token-at-coordinate analysis;
- semantic/fuzzy ranking;
- CAL data correction;
- bulk extraction or lexicon crawling;
- a persistent local CAL database.

Those are separate capabilities or deliberate non-goals. Use this tool when the research task starts from a lexical form and needs the corresponding CAL entry or explicit homograph candidates.

## Fixture and reproducibility policy

Normal tests make no CAL requests. Parser tests use deliberately reduced HTML excerpts with source/capture provenance in `tests/fixtures/cal/README.md`; the repository does not archive complete CAL pages. Upstream markup changes should update those fixture contracts only after the new CAL semantics have been checked explicitly.
