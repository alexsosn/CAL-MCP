# CAL concordance and KWIC

CAL-MCP exposes five bounded concordance/KWIC operations over CAL's current public research interfaces. Each valid explicit operation submits at most one new logical CAL request to the shared client. Moving from a concordance row or dialect selector to KWIC, or from one returned KWIC hit to full context, is always a separate explicit caller action; CAL-MCP does not crawl texts, expand dialects, or prefetch full-context pages.

## Which tool to use

| Goal | Tool |
| --- | --- |
| List the ordered lemma-frequency index for one CAL text | `cal_text_concordance(text_id, script="semitic")` |
| Find one CAL lemma in 1–8 explicit CAL texts | `cal_kwic_texts(lemma_key, text_ids, script="roman")` |
| Discover CAL's current dialect choices for one lemma | `cal_kwic_dialects(lemma_key)` |
| Find one CAL lemma in one explicit CAL dialect | `cal_kwic_dialect(lemma_key, dialect_id)` |
| Read CAL's target-centered full text context for one returned KWIC hit | `cal_kwic_full_context(file_id, target_coordinate, charset, subtext_id=None)` |

CAL text/dialect identifiers and lemma keys are upstream CAL identifiers. CAL-MCP preserves them for explicit follow-up calls rather than replacing them with adapter-owned IDs.

## `cal_text_concordance`

```text
cal_text_concordance(
    text_id: string,
    script: string = "semitic",
)
```

This is CAL's **one-text lemma-frequency index**. It is not itself a KWIC hit list.

The result preserves CAL's ordered rows with:

- `frequency`;
- canonical `lemma_key`;
- rendered `gloss`;
- the CAL `kwic_url` exposed by that row.

`script` accepts:

- `semitic` — CAL's Semitic-script rendering (default);
- `transliteration` — CAL transliteration.

`text_id` must be an explicit decimal CAL text identifier. Each valid explicit operation submits at most one new logical CAL request to the shared client. To inspect a lemma in context, pass the row's `lemma_key` and explicit text IDs to `cal_kwic_texts` in another call.

## `cal_kwic_texts`

```text
cal_kwic_texts(
    lemma_key: string,
    text_ids: array[string],
    script: string = "roman",
)
```

This operation asks CAL for one exact lemma key in **1–8 explicit text IDs**. The text list is never expanded automatically.

Caller-supplied text IDs must be decimal CAL identifiers and must not repeat. More than eight IDs, an empty list, duplicate IDs, invalid lemma keys, or unsupported rendering choices fail locally before transport.

`script` accepts:

- `roman` — CAL Roman/transliteration rendering (default);
- `hebrew` — Hebrew-script rendering;
- `syriac` — Syriac-script rendering.

The result preserves:

- CAL's upstream `total` hit count;
- ordered `hits`;
- legitimate duplicate hits, including repeated target coordinates when CAL renders them as separate examples;
- `file_id` and optional `subtext_id`;
- `target_coordinate`;
- rendered `context`;
- returned CAL `charset`;
- absolute `full_context_url`;
- `empty_scope_ids` for requested texts CAL explicitly reports as having no examples.

CAL-MCP does **not** deduplicate, rerank, or statistically summarize hits. It also does not follow `full_context_url` automatically. To inspect one selected hit, pass that hit's typed `file_id`, `target_coordinate`, `charset`, and optional `subtext_id` to `cal_kwic_full_context`. Arbitrary caller-supplied URLs are not accepted by that follow-up.

For a successful response with a positive total, CAL-MCP requires the rendered upstream total to equal the number of safely parsed target hits. It also requires the requested text scopes to be accounted for by hits or CAL's explicit no-example markers. Contradictory totals, malformed target links, missing context, foreign text IDs, or incomplete scope coverage fail closed as `ConcordanceParseError` rather than returning a plausible partial result.

## `cal_kwic_dialects`

```text
cal_kwic_dialects(lemma_key: string)
```

This operation reads the **current** ordered CAL dialect selector for one exact lemma key. It returns CAL-owned `dialect_id` / `label` pairs.

The dialect map is not hard-coded in CAL-MCP. A caller that wants KWIC examples for one returned dialect must explicitly call `cal_kwic_dialect` with that `dialect_id`.

## `cal_kwic_dialect`

```text
cal_kwic_dialect(
    lemma_key: string,
    dialect_id: string,
)
```

This operation requests one exact CAL lemma key in one explicit decimal dialect ID. It submits at most one new logical CAL request to the shared client and never expands to neighboring/all dialects.

The returned hit model is the same scholarly KWIC model used by text-scoped search: ordered hits, duplicates preserved, CAL file/subtext IDs, target coordinates, rendered context, per-hit charset, full-context URL, and upstream total. Full context for one selected hit remains a separate explicit `cal_kwic_full_context` call.

## `cal_kwic_full_context`

```text
cal_kwic_full_context(
    file_id: string,
    target_coordinate: string,
    charset: string,
    subtext_id: string | null = null,
)
```

This operation consumes the typed selectors already returned on a `KwicHit`. It does not accept `full_context_url` or any other arbitrary URL. `file_id`, `target_coordinate`, and a non-null `subtext_id` must be decimal CAL identifiers. `charset` is the exact CAL hit charset and must be one of `R`, `H`, or `S`.

A cache miss submits exactly one logical request to CAL's target-centered context route. Returned navigation or lexical links are validated as metadata but are not followed. The response has:

- `status: "found"` with ordered full-context `lines`; or
- `status: "not_found"` and an empty `lines` array when CAL explicitly reports the requested target coordinate as absent;
- the requested `file_id`, optional `subtext_id`, `target_coordinate`, and `charset`;
- per line: machine `coordinate`, rendered `display_coordinate`, rendered text, ordered lexical `tokens`, and optional CAL `comment_url`;
- per token: coordinate, zero-based word index as CAL returned it, rendered token text, and validated CAL lexical URL;
- CAL provenance and retrieval time.

For `found`, the requested target coordinate must appear in exactly one parsed line. The parser also verifies that the response route and selectors match the request, that the page identifies the requested CAL file, and that lexical/comment links remain on the expected CAL routes with consistent coordinates. A mismatched or contradictory page fails closed as `ConcordanceParseError`.

Current Hebrew (`charset="H"`) full-context pages append one empty lexical anchor after the last visible token of each text row. Bounded research on 2026-09-10 confirmed this as a stable presentation artifact for the tested route. CAL-MCP accepts it only in this full-context parser, only for `H`, only as the single terminal empty lexical anchor, and only when its word index is the successor of the preceding visible token. The artifact is omitted from returned tokens. Ordinary `cal_text_page` parsing is unchanged and remains strict about empty lexical anchors.

`not_found` is not parser drift: it is accepted only when CAL returns the explicit `Target coordinate <id> not found.` marker for the requested target and no text rows contradict it. An unrelated marker, repeated marker, or marker mixed with parsed text rows fails closed.

## CAL lemma keys and homographs

The KWIC tools consume **canonical CAL lemma keys**, not free-form transliteration queries. A key consists of CAL's lemma identity plus its key/POS suffix, for example:

```text
mlk N
)ryk#2 A
```

A terminal `#<positive decimal>` homograph marker is part of CAL's upstream lemma identity and is preserved. CAL-MCP validates the CAL-code base separately rather than treating `#2` as ordinary user transliteration. In practice, callers should reuse canonical lemma keys returned by CAL-MCP lexicon, search, concordance, or token-analysis results instead of constructing them heuristically.

## No `lth` / context-window parameter

CAL's historical/current concordance help still describes an `lth` / “number of words” context-width field with a maximum of 20. During bounded live research on **2026-09-05**, however:

- the current advanced-search form did not render that control; and
- otherwise identical one-hit requests with `lth=1` and `lth=20` produced byte-for-byte identical result output.

CAL-MCP therefore does **not** expose a context-window option that the current service appears to ignore. If CAL restores a meaningful supported control later, it should be researched and added through a new tested public contract rather than silently forwarded now.

## Request and result bounds

Each valid explicit operation submits at most one new logical CAL request to the shared client:

- one text concordance request;
- one text-scoped KWIC request over at most eight explicit text IDs;
- one dialect-selector request;
- one one-dialect KWIC request;
- one full-context request for one explicit returned-hit selector set.

There is no automatic pagination, continuation, all-text/all-dialect expansion, full-context prefetch, background indexing, or corpus mirror. No current KWIC result pagination/continuation was observed during the 2026-09-05 CAL audit, so CAL-MCP does not invent a continuation token.

The shared HTTP client still enforces its origin, redirect, timeout, concurrency, retry, cache/single-flight, and maximum-response-size policy. The default decoded response-body ceiling is 2 MiB, with a hard configurable ceiling of 16 MiB. An oversized result raises the shared response-size error before endpoint parsing and is not cached or retried as a transient failure.

### Shared cache, single-flight, and retry semantics

Each valid explicit operation in this family submits at most one new logical CAL request to the shared client. A completed cache hit performs zero new upstream I/O, and an identical simultaneous call can be a single-flight follower without duplicating the active request. Retryable failures may consume bounded retry transport attempts under the shared policy. These mechanisms do not create hidden traversal, prefetch, or background work.

## Empty results, upstream failures, and parser drift

These states remain distinct:

- a CAL result with an explicit zero total/no-examples marker is a valid empty KWIC result;
- an exact full-context target-not-found marker for the requested coordinate is a valid typed `not_found` result;
- caller validation errors fail before transport;
- network, timeout, HTTP, maintenance/content, redirect, and oversized-response failures remain typed request-layer failures;
- a successful-looking CAL page whose totals, target links, scope IDs, selector fields, route identity, target identity, lexical/comment links, or required semantic markers disagree raises `ConcordanceParseError`.

CAL-MCP does not convert parser drift into an empty result.

## Provenance

Results include adapter provenance with:

- `source: "CAL"`;
- the actual CAL `source_url`;
- timezone-aware `retrieved_at`;
- the operation name;
- relevant canonical `lemma_key`, `text_id`, or `scope_ids`;
- the requested public rendering choice where applicable.

Duplicate-request cache hits preserve the original CAL retrieval timestamp and source URL, following the shared request-layer provenance contract.

## Fixture-backed examples

Normal tests use deliberately reduced semantic excerpts captured/rechecked on **2026-09-05** and **2026-09-10**. Representative contracts include:

- one-text concordance rows for CAL text `13250`;
- multi-text KWIC with one explicitly empty text scope;
- two legitimate hits sharing target coordinate `1325006` but carrying different context;
- a current CAL dialect selector;
- one Biblical Aramaic dialect hit with Hebrew rendering and a subtext ID;
- explicit zero-hit output;
- target-centered Tel Dan full-context rows in Roman and Hebrew rendering;
- CAL's explicit full-context target-not-found marker;
- total-count mismatch, malformed/contextless target links, malformed full-context selectors, and Hebrew empty-anchor drift cases.

The fixtures are parser contracts, not archived CAL pages. Normal CI performs zero CAL requests.
