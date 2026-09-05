# External citations

CAL includes lexical citations from some source texts that are cited in the database but are not available as full online CAL texts. CAL-MCP exposes that workflow separately from both online text browsing and English citation-text search.

## Tools

### `cal_external_citation_dialects()`

Returns CAL's current ordered dialect choices for the cited-but-not-online source workflow. Each item contains CAL's opaque `dialect_id` and rendered dialect label.

The dialect list is read live from CAL. CAL-MCP does not hard-code the current selector and does not enumerate sources automatically.

### `cal_external_citation_sources(dialect_id)`

Returns the ordered source abbreviations and descriptions that CAL currently lists for one explicit dialect returned by `cal_external_citation_dialects()`.

A source result is metadata for a text with citations in CAL; it is **not** an online CAL `file_id` or passage. Descriptions are preserved as rendered by CAL rather than decomposed into inferred bibliographic fields.

CAL may explicitly report that a dialect currently has no extra citations. That is returned as an empty successful result. A successful-looking page with neither recognized source rows nor CAL's explicit empty state is parser drift.

### `cal_external_citations(source_abbrev)`

Returns CAL's ordered lexical citations for one exact source abbreviation returned by `cal_external_citation_sources()`.

Each citation preserves:

- the canonical CAL lemma key and rendered lemma label;
- the same-origin CAL lexical-entry URL as metadata;
- CAL's rendered external-source reference;
- optional part of speech, gloss, source text, and translation when CAL supplies them.

Optional fields remain null when CAL omits them. CAL-MCP does not fabricate missing citation content.

The external-source reference is not represented as an online CAL coordinate. Lexical-entry links are never followed automatically.

CAL may explicitly report that no citations are stored for a source abbreviation. That is returned as an empty successful result. Count mismatches, contradictory empty markers, wrong-source headings, malformed lemma links, and unrecognized success pages fail closed as parser drift.

## Explicit workflow

The three stages are caller-controlled:

```text
cal_external_citation_dialects()
  -> choose one returned dialect_id
cal_external_citation_sources(dialect_id)
  -> choose one returned source abbreviation
cal_external_citations(source_abbrev)
```

Each tool call performs exactly one bounded CAL request. There is no hidden dialect traversal, source traversal, pagination, source-text reconstruction, online-text lookup, or lexical-entry expansion.

### Concrete example

Current CAL discovery includes the dialect choice `{"dialect_id": "6", "label": "Syriac"}`. Calling `cal_external_citation_sources("6")` returns, among many current Syriac choices, the source abbreviation `1CorH` for the Harklean version of 1 Corinthians. A separate `cal_external_citations("1CorH")` call returns ordered lexical citations including a record whose rendered `reference` is `1CorH 12:28`.

`1CorH 12:28` is CAL's external-source reference, **not an online CAL passage coordinate**. It must not be treated as a `file_id`/subtext/page location or passed to `cal_text_page`. Following the citation's returned CAL lemma with `cal_lexicon_lookup` is another explicit caller action.

## Relationship to other citation/text tools

`cal_citation_text_search(query)` searches one to three English words inside CAL lexicon citations. It does not discover cited-but-not-online source texts.

`cal_text_catalogue`, `cal_text_search`, and `cal_text_page` operate on CAL's online text corpus. External citation source abbreviations returned here must not be passed off as online text identifiers.

Following a returned CAL lemma into `cal_lexicon_lookup` is a separate explicit caller action.

## Failure semantics

Caller input is validated before transport. Invalid dialect identifiers or source abbreviations therefore do not consume a CAL request.

CAL's explicit no-sources and no-citations messages are valid empty results. Upstream HTTP failures remain request-layer failures. A successful response whose semantic structure no longer matches the documented CAL shapes raises a content/parser error instead of returning a guessed partial result.

Cross-origin or wrong-endpoint source/lemma links, duplicate ambiguous query parameters, malformed returned lemma keys, contradictory empty markers, and reported-count mismatches are treated as parser drift. CAL-MCP exposes no `page`, `offset`, or `limit` parameter for this workflow because current CAL surfaces do not provide a faithful bounded pagination contract here.

## Validation and provenance

`dialect_id` is an opaque decimal CAL identifier returned by dialect discovery. `source_abbrev` is an exact CAL abbreviation returned by source discovery; punctuation and case are preserved. Non-space whitespace and Unicode control/format characters are rejected before transport.

Results include the CAL source URL, retrieval time, operation name, and the submitted dialect/source identifier where applicable. CAL-private form names and endpoint parameters are adapter internals and are not exposed in the MCP schema.

Normal automated tests use reduced offline fixtures derived from the bounded research probes; they do not contact CAL.
