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

- `coordinate`: the exact decimal CAL machine coordinate supplied by the caller;
- `word_index`: CAL's zero-based token index;
- `status`: `found` or `not_found`;
- `candidates`: CAL's ordered lexical analyses for that token;
- `provenance`: CAL source URL and timezone-aware retrieval timestamp plus the requested coordinate and token index.

Each candidate contains:

- `analysis_label`: CAL's compact analysis label exactly as rendered for that candidate, for example `xd n02` or `w_ c`;
- `lemma`: the same typed `LemmaRef` structure used by CAL-MCP lexicon lookup, preserving CAL's lemma key, rendered headword(s), pronunciation, part of speech, gloss, and aliases where the linked header supplies them.

CAL-MCP deliberately does **not** interpret the compact analysis label into a new morphology schema. It also does not choose a preferred analysis.

## Ambiguity

CAL can return more than one lexical analysis for the same token. Those candidates remain multiple and remain in CAL order.

A fixture-backed current example is CAL machine coordinate `7102601002203`, `word_index=0`, where the upstream page exposes two ordered candidates:

```text
w_ c -> lemma key w_ c
my c -> lemma key my c
```

CAL-MCP returns both. It does not rank, merge, or silently choose between them.

## Coordinates and token indexes

`coordinate` is an opaque CAL identifier. CAL-MCP validates only that it is a non-empty decimal string and otherwise preserves it verbatim; it does not decode semantic fields from its digits or claim that CAL identifiers are permanently stable.

`word_index` is zero-based because that is the index CAL exposes in text-browser token links. It must be an integer greater than or equal to zero. Boolean, negative, and non-integer values are rejected locally.

These conventions match the token metadata returned by `cal_text_page`; see [`../concepts/cal-identifiers.md`](../concepts/cal-identifiers.md).

## Not found, invalid input, and parser drift

The states are intentionally distinct:

- **invalid caller input** — a non-decimal coordinate or invalid `word_index` raises local validation failure before any CAL request;
- **not found** — CAL's current explicit HTTP-success no-data message (`there is no data for this word ...`) maps to `status: "not_found"` and an empty candidate list;
- **upstream/transport failure** — HTTP/content/request failures remain shared CAL client errors;
- **parser drift** — a successful CAL page that lacks both a complete recognized analysis and CAL's explicit no-data marker fails closed as `TokenAnalysisParseError`.

This distinction matters because CAL currently returns the same explicit no-data message for at least two cases: a nonexistent decimal coordinate and an out-of-range word index. CAL-MCP reports only the upstream state it can observe and does not invent a more specific scholarly explanation.

## Request bound

Every `cal_token_analysis` call performs exactly **one** user-initiated CAL request.

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

## Fixture-backed examples

Offline tests use reduced semantic excerpts rechecked against current CAL behavior on 2026-09-04. They cover:

- one lexical analysis;
- a real two-candidate ambiguous token;
- Hebrew and Syriac rendered headwords;
- CAL's explicit no-data result;
- incomplete/missing lemma-link markup;
- unknown successful markup;
- local coordinate/token-index validation;
- exact one-request service behavior and provenance;
- MCP schema exposure without private upstream `coord` / `word` parameter names.

The fixtures are parser contracts, not archived CAL pages. Normal CI makes zero CAL requests.
