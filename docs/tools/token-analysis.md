# CAL token-at-coordinate lexical analysis

`cal_token_analysis` exposes CAL's existing text-browser lexical-analysis operation for one explicit token already identified by a CAL machine coordinate and zero-based token index.

```text
cal_token_analysis(
    coordinate: string,
    word_index: integer,
)
```

Use `cal_text_page` to obtain the `coordinate` and `word_index` for a rendered CAL token. CAL-MCP does not guess a coordinate from pasted text and does not tokenize arbitrary input for this operation.

## Result semantics

A successful result preserves:

- `coordinate`: the exact CAL machine coordinate supplied by the caller;
- `word_index`: CAL's zero-based token index;
- `status`: `found` or `not_found`;
- `candidates`: CAL's ordered lexical analyses for that token;
- `provenance`: CAL source URL and timezone-aware retrieval timestamp plus the requested coordinate and token index.

Each candidate contains:

- `analysis_label`: CAL's compact analysis label exactly as rendered for that candidate, for example `xd n02`, `w_ c`, or the current Syriac redirect label `)syr noun sg. emphatic= )syr N --> )syr A`;
- `analyzed_lemma_key`: the source/analysed CAL lemma key when CAL explicitly renders a linked redirect; otherwise `null`;
- `lemma`: the same typed `LemmaRef` structure used by CAL-MCP lexicon lookup. Its `lemma_key` is the **linked target entry**, with rendered headword(s), pronunciation, part of speech, gloss, and aliases where the linked header supplies them.

For example, current Peshitta Philemon 1:1 word 1 is analysed as `)syr N` but redirects to linked entry `)syr A`. CAL-MCP returns `analyzed_lemma_key: ")syr N"` and `lemma.lemma_key: ")syr A"`; it does not collapse the two identities.

CAL-MCP deliberately does **not** interpret the rest of the compact analysis label into a new morphology schema. It also does not choose a preferred analysis.

## Ambiguity

CAL can return more than one lexical analysis for the same token. Those candidates remain multiple and remain in CAL order.

A fixture-backed current example is CAL machine coordinate `7102601002203`, `word_index=0`, where the upstream page exposes two ordered candidates:

```text
w_ c -> lemma key w_ c
my c -> lemma key my c
```

CAL-MCP returns both. It does not rank, merge, or silently choose between them.

## Coordinates and token indexes

`coordinate` is an opaque CAL identifier. Most observed values are decimal; current Christian Palestinian Aramaic text pages return coordinates such as `5500001001a019001`, embedding one lowercase subtext suffix between decimal segments. CAL-MCP therefore accepts only a decimal string or the researched decimal + one lowercase ASCII letter + non-empty decimal-tail form and preserves it verbatim. It does not decode semantic fields from the coordinate or claim that CAL identifiers are permanently stable.

`word_index` is zero-based because that is the index CAL exposes in text-browser token links. It must be an integer greater than or equal to zero. Boolean, negative, and non-integer values are rejected locally.

These conventions match the token metadata returned by `cal_text_page`; see [`../concepts/cal-identifiers.md`](../concepts/cal-identifiers.md).

## Not found, invalid input, and parser drift

The states are intentionally distinct:

- **invalid caller input** — a coordinate outside the researched decimal-or-single-embedded-lowercase-letter grammar, or an invalid `word_index`, raises local validation failure before any CAL request;
- **not found** — CAL returned one of the adapter's explicitly recognized no-candidate states. These currently include the legacy `there is no data for this word ...` page and a normal token-analysis result marker followed by CAL's exact `unrecognizable query or no such lemma found` message with no lemma-entry link. Both map to `status: "not_found"` and an empty candidate list;
- **upstream/transport failure** — HTTP/content/request failures remain shared CAL client errors;
- **parser drift** — a successful CAL page that has neither a complete recognized analysis nor one of the explicitly recognized no-candidate states fails closed as `TokenAnalysisParseError`.

`status: "not_found"` deliberately does not claim a finer cause than CAL exposes. The legacy no-data page is currently used for cases such as a nonexistent coordinate or out-of-range word index, while the current no-lemma sentence itself conflates an unrecognizable query with an absent lemma. CAL-MCP therefore reports only the observable upstream no-candidate state rather than inventing a scholarly distinction.

The current no-lemma sentence is accepted only together with exactly one normal token-analysis result marker and no lemma-entry link. If CAL mixes that sentence with lemma markup, omits the result marker, or returns some other unexplained successful shape, the parser fails closed instead of silently treating drift as an empty result.

Current linked Syriac redirect pages use a one-row result table with an `a.lexlink` header whose HTML is slightly mis-nested and is followed by a full lexicon sense outline. CAL-MCP treats the table close as the candidate boundary, validates the explicit `SOURCE --> TARGET` redirect against the linked `lemma` selector, and does not reinterpret the following sense lines as additional token analyses.

CAL also currently returns **linkless** successful token-analysis summaries for some Peshitta and CPA proper-name/other tokens. Their candidate grammar is not yet sufficiently established to construct a truthful `LemmaRef`, so they remain parser drift under release blocker #193 rather than being guessed into this result model or mislabeled `not_found`.

## Request bound

Each valid explicit operation submits at most one new logical CAL request to the shared client.

It does not:

- fetch the complete linked lexicon entry;
- analyze neighboring tokens;
- retrieve the containing passage;
- try fallback coordinates or token positions;
- batch-analyze a text;
- prefetch or rank alternative analyses;
- build a local token-analysis index.

The returned `LemmaRef` is sufficient for an explicit follow-up `cal_lexicon_lookup` when a caller wants a full lexicon entry. That follow-up is a separate user-initiated tool call.

The shared CAL HTTP policy still applies its origin, redirect, timeout, concurrency, retry, cache, and maximum-response-byte limits.

### Shared cache, single-flight, and retry semantics

Each valid explicit operation in this family submits at most one new logical CAL request to the shared client. A completed cache hit performs zero new upstream I/O, and an identical simultaneous call can be a single-flight follower without duplicating the active request. Retryable failures may consume bounded retry transport attempts under the shared policy. These mechanisms do not create hidden traversal, prefetch, or background work.

## Fixture-backed examples

Offline tests use reduced semantic excerpts rechecked against current CAL behavior through 2026-09-08. They cover:

- one lexical analysis;
- a real two-candidate ambiguous token;
- Hebrew and Syriac rendered headwords;
- CAL's legacy explicit no-data result;
- CAL's current result-marker plus `unrecognizable query or no such lemma found` empty-analysis state;
- contradictory current empty-state markup with a lemma link;
- current empty-state text without the required result marker;
- incomplete/missing lemma-link markup;
- unknown successful markup;
- local coordinate/token-index validation, including current CPA suffix-bearing coordinates and malformed near-misses;
- single-fetch request construction and provenance;
- MCP schema exposure without private upstream `coord` / `word` parameter names.

The fixtures are parser contracts, not archived CAL pages. Normal CI makes zero CAL requests.
