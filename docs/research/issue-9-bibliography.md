# Issue #9 research — bounded CAL bibliography search

**Rechecked:** 2026-09-05

This note records the bounded live evidence used before implementing issue #9. Normal CI remains offline.

## Current CAL bibliography entry points

`bibliography/index.html` currently exposes four bibliography surfaces: search by author, search by text/subject, search by lexical item, and a separate recent-bibliography view. Issue #9 covers the three search families named in its acceptance criteria. The recent-five-years view is not a search operation and is left for the issue #12 public-surface audit to account for explicitly.

### 1. Author search is an explicit two-step flow

`namesearch.html` asks for the first one to six letters of a romanized author name. A bounded raw-form probe confirmed:

```text
POST /browsenames.php
first3=<1–6 character prefix>
```

For `Kau`, the response contains an exact-author selector whose values currently include `Kaufhold, H.`, `Kaufman, Stephen A.`, `Kaukhchishvili, S.`, and `Kautzsch, E.`. The selector targets `/getbibauthor.php` and uses the field `myauthor`.

A bounded exact request for `Kaufman, Stephen A.` returned a bibliography headed `CAL Bibliography for Kaufman, Stephen A.` with ordered record cards. An unmatched six-character prefix returns the explicit message `No authors found matching ...` rather than a result selector.

CAL-MCP should therefore expose author discovery and exact-author results as two separate one-request operations. It must not silently choose one author when the prefix is ambiguous.

### 2. Text/subject “keyword” bibliography is an exact CAL tag lookup

`allsigs.html` is CAL's current text/subject bibliography selector. It is not a general full-text keyword box. Category pages lead to exact CAL bibliography tags/sigla, and result links use:

```text
/getbibsigla.php?myauthor=<CAL text/subject tag>
```

Representative bounded pages for `TADA`, `AECT`, `Targum`, and `Loanwords` returned ordered bibliography records. Record cards contain CAL-owned linked tags such as `Collections`, `TADA`, `Vocab`, `Loanwords`, text sigla, and lexical keys.

The issue uses the word “keyword”; the executable contract should make clear that this means one exact CAL bibliography text/subject tag, not substring search, ranking, stemming, or a locally invented query language. Callers can obtain follow-up tags from links preserved on returned records.

### 3. Lexical-item bibliography is an exact CAL lemma-key lookup

`lemmas_list.html` is the current lexical bibliography selector. Lexicon `Full Bibliography` links and the selector lead to:

```text
/getbiblemma.php?myauthor=<CAL lemma key>
```

A bounded `cly V` result returned one bibliography record with linked CAL lemma keys. The adapter should accept a structurally valid CAL lemma key and preserve CAL code spelling rather than normalize it into display Unicode or choose a lexical analysis.

## Shared result shape and links

The three final result endpoints currently render the same semantic shape:

- a heading beginning `CAL Bibliography for ...`;
- zero or more ordered bibliography record cards;
- each record's rendered citation text;
- zero or more linked CAL tags/identifiers associated with that record;
- navigation/footer links outside the record cards.

The linked tags are useful provenance and navigation data. Their labels, absolute URLs, target endpoint family, and `myauthor` query value should be preserved when recognizable. CAL-MCP must not reinterpret a tag as a modern subject ontology or rewrite citation metadata.

Unicode appears in current records, including Hebrew titles and diacritics. Parsing and serialization must preserve Unicode text as returned by CAL.

## Explicit empty states

A bounded nonexistent query against each final result endpoint returned HTTP 200 and the same explicit marker:

```text
NO data FOR <query> ARE CURRENTLY STORED
```

That marker is a successful empty bibliography result. An unrecognized nonempty page without this marker is parser drift, not an empty result.

The intermediate author-prefix endpoint has a different explicit empty state: `No authors found matching ...`. A missing selector on a nonempty response without that marker is parser drift.

## Pagination and boundedness

No next/previous result link, page number, continuation token, or stable result-limit parameter was observed on representative current author, text/subject, or lemma result pages. The current contract therefore has no upstream continuation to expose.

Each public operation should perform exactly one CAL request. Final result responses are complete current CAL pages subject to the shared decoded-response safety limit (2 MiB by default); an oversized response fails with the shared response-size error rather than being truncated. CAL-MCP must not invent page iteration or automatically follow record tags.

The author workflow remains explicitly two-step: prefix discovery is one caller action and exact-author retrieval is another.

## Input implications

- Author prefix: trim surrounding ASCII spaces; require 1–6 characters; reject line breaks/control whitespace locally.
- Exact author: nonempty single-line value selected by the caller; preserve spelling and punctuation.
- Text/subject keyword: nonempty single-line exact CAL tag/value; preserve spelling and punctuation.
- Lemma: structurally valid CAL lemma key; preserve CAL code spelling.
- Bound all public string inputs to conservative lengths before transport.
- No operation performs fallback searching when a value is unknown.

## Sources

- https://cal.huc.edu/bibliography/index.html
- https://cal.huc.edu/namesearch.html
- https://cal.huc.edu/allsigs.html
- https://cal.huc.edu/lemmas_list.html
- https://cal.huc.edu/getbibsigla.php?myauthor=TADA
- https://cal.huc.edu/getbiblemma.php?myauthor=cly+V
- bounded branch-only raw-form/result/empty probes described above

## Research load

Four temporary branch-only research runs used seven bounded CAL requests total: one author-form GET, one author-prefix POST, one exact-author result GET, three final-endpoint empty GETs, and one unmatched author-prefix POST. Web inspection additionally opened a small number of already-public representative pages without traversal. No pagination, category tree, author list, bibliography archive, or corpus was crawled. All temporary probe workflows were removed before implementation planning.
