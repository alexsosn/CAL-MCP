# Issue #14 plan — bounded CAL Dictionary Spelling Collation

**Plan date:** 2026-09-05

This ticket follows the repository loop: research → plan → test-only RED → minimal implementation → full GREEN → documentation → independent skeptical review → review-fix RED/GREEN if required → fresh independent re-review → merge.

## Public contract

Expose one caller-controlled operation:

```text
cal_dictionary_collation(source, page)
```

`source` is a readable adapter-owned enum backed by the current CAL dictionary selector mapping documented in `docs/research/issue-14-dictionary-collation.md`.

`page` is a CAL dictionary page-reference string, not an integer. Support the documented forms:

```text
705
1:134
1:134, 2:212
```

One tool call performs exactly one `POST /searchdicts.php`. Returned CAL lemma links are data only; the operation never follows them automatically.

## Public source enum

Define `DictionarySource` with these stable public values:

- `jastrow`
- `lexicon_syriacum`
- `syriac_lexicon`
- `compendious_syriac_dictionary`
- `djba`
- `djpa`
- `levy_targumim`
- `mandaic_dictionary`
- `dnsi`
- `thesaurus_syriacus`
- `samaritan_aramaic`
- `schulthess`
- `dcpa`
- `judean_aramaic`
- `qumran_aramaic`

Keep the one-letter CAL form values internal. Each mapping entry also carries CAL's current rendered source label for result validation and public attribution.

## Page normalization

Accept only the documented decimal grammar:

```text
page-ref := DIGITS [":" DIGITS]
query    := page-ref ("," page-ref)*
```

Implementation rules:

- trim surrounding ASCII spaces;
- allow arbitrary ASCII spaces around commas, then canonicalize separators to `", "`;
- preserve decimal spelling inside each component;
- reject empty values, controls/newlines, bare volume/page separators, ranges, alphabetic page names, or any unrecognized syntax before transport;
- cap the submitted page-reference string at 96 characters and at 16 comma-separated references to prevent pathological request/cache keys.

The result parser should normalize CAL's echoed page reference with the same grammar before service-level equality checking.

## Typed models

Add `dictionary_collation.py` with:

- `DictionarySource` — public readable source enum;
- internal immutable source spec — public enum, current CAL form code, exact current CAL label;
- `DictionaryCollationEntry`:
  - `display_lemma`: exact rendered CAL link label;
  - `target_lemma_key`: exact CAL lemma query value from the entry link;
  - `gloss`: rendered row text after the lemma link, with only the structural leading colon removed;
  - `entry_url`: absolute same-origin CAL entry URL;
- `DictionaryCollationPage` — parsed echoed page, rendered source label, ordered entries, explicit-empty flag;
- `DictionaryCollationProvenance` — CAL source URL, retrieval timestamp, operation, original/submitted page, public source;
- `DictionaryCollationResult` — source enum, CAL source label, canonical submitted page, ordered entries, provenance.

Do not infer dictionary headwords, etymological equivalence, POS subfields, or cross-reference semantics beyond what CAL renders. In particular, when the link label differs from `target_lemma_key`, preserve both values exactly.

## Parser contract

Parse only current collation result semantics.

### Page identity

Require exactly one recognizable page identity of the current form:

```text
CAL: entries for page <page> of <dictionary label>
```

The identity may come from the document title. Normalize `<page>` with the public page grammar. Preserve the dictionary label as rendered.

### Result card

Recognize one `div.summary-card` as the semantic result container.

Within it:

- collect ordered result paragraphs containing exactly one CAL entry link;
- require entry links to resolve to the same CAL origin and target `oneentry.php`;
- require exactly one nonempty `lemma` query value;
- allow only the currently observed optional `cits=no` query control in addition to `lemma`;
- preserve the rendered link label independently of the target lemma key;
- require a nonempty rendered gloss after a structural leading `:`;
- ignore page-level navigation links outside result rows.

### Empty result

Recognize exactly:

```text
No data available for that page.
```

inside the result card as explicit empty success.

Fail closed when:

- the page identity is absent/duplicated;
- the result card is absent/duplicated;
- a row contains missing/multiple/malformed entry links;
- a result link escapes the CAL origin or uses an unexpected target/query shape;
- an entry row has no gloss;
- explicit empty and data rows coexist;
- neither data rows nor explicit empty marker exists.

### Service-level consistency

After parsing, require:

- parsed page == canonical submitted page;
- parsed source label == the source mapping's current CAL label.

A mismatch is parser/upstream drift, not a successful answer for a different dictionary/page.

## Service and request mapping

`DictionaryCollationService.collate(source, page)`:

1. convert/validate `source` as `DictionarySource`;
2. normalize and validate `page` locally;
3. map source to its current CAL code/label;
4. call the shared `CalHttpClient.fetch` with:

```text
CalRequest(
    method="POST",
    path="searchdicts.php",
    data=(("dict", code), ("page", canonical_page)),
)
```

5. parse one response;
6. enforce page/source consistency;
7. return typed result with CAL provenance.

Use a dedicated versioned cache namespace. Do not fetch `searchdicts.html` at runtime, retry with alternate source codes, follow lemma entries, or make hidden second requests.

## TDD RED gate

Before any production code, add offline reduced fixtures/tests covering:

1. Jastrow page 705 success with ordered entries;
2. direct row where `display_lemma == target_lemma_key`;
3. redirect-style row where `display_lemma != target_lemma_key` (`lxt V` → `lht V`);
4. punctuation-bearing target lemma keys (`#`, `+`, `$`, parentheses) decoded exactly from query parameters;
5. Jastrow page 99999 explicit empty result;
6. page identity/source label preserved;
7. missing/duplicate summary card → parser drift;
8. missing page identity → parser drift;
9. explicit-empty-plus-entry contradiction → parser drift;
10. row missing gloss → parser drift;
11. cross-origin entry link → parser drift;
12. malformed/multiple lemma query values or unexpected entry target/query controls → parser drift;
13. source mapping emits the exact current CAL form code for at least multiple case-sensitive values (`J` vs `j`);
14. all public source enum values map uniquely to one internal code and one nonempty CAL label;
15. page normalization for `705`, `1:134`, and `1:134, 2:212`;
16. page validation rejects empty, controls, malformed colon/comma syntax, alphabetic/range syntax, overlength, and more than 16 page refs before transport;
17. service performs exactly one POST with exact ordered form fields and returns provenance;
18. service rejects parsed source/page mismatch;
19. MCP schema exposes one `cal_dictionary_collation` tool with enum source values and string page input, without CAL endpoint/form names or pagination parameters.

A valid RED requires install, Ruff lint/format, and strict mypy green while pytest fails specifically because the new module/server tool does not yet exist or because its required behavior is unimplemented. Test fixtures must be reduced semantic reproductions, not archived full CAL pages.

## Minimal GREEN implementation

Implement only:

- the source enum/spec mapping;
- page-reference validation/normalization;
- typed models and serialization;
- dedicated small HTML result parser;
- one service method using the shared HTTP client;
- one MCP tool registration.

Do not modify shared HTTP policy, lexicon parsing, normalization rules, caching architecture, or unrelated public schemas unless a new failing regression proves a necessary cross-cutting correction.

## Documentation gate

Before review:

- add `docs/tools/dictionary-collation.md`;
- update the README implemented-tool list/instructions where current tool surfaces are enumerated;
- document all supported public source values and exact CAL labels;
- explain page-reference syntax including multi-volume input;
- state that results reflect correspondences currently stored by CAL and coverage varies by dictionary;
- explain `display_lemma` versus `target_lemma_key`;
- document explicit empty results, one-request-per-call behavior, no hidden lemma expansion, shared response-size failure, and CAL provenance;
- record reduced fixture source/date.

## Independent skeptical review gate

Freeze an exact final SHA and review the entire issue boundary, specifically challenging:

- whether source-code case sensitivity is preserved (`J` vs `j`);
- whether every public source maps uniquely and accurately to the researched current form;
- whether page grammar unnecessarily excludes a documented form or admits undocumented arbitrary syntax;
- whether page/source echoes are checked strongly enough to prevent answering for the wrong dictionary/page;
- whether alias/redirect rows lose the difference between rendered label and linked target lemma key;
- whether punctuation/URL decoding corrupts CAL lemma keys;
- whether navigation/cross-origin links can be mistaken for result entries;
- whether explicit empty state can mask parser drift;
- whether malformed markup can silently return a partial result;
- whether the service ever performs more than one CAL request;
- whether MCP schema leaks endpoint/form controls or forces callers to know one-letter codes;
- whether documentation overstates dictionary coverage or inferred equivalence.

Any blocker enters a fresh review-regression RED → minimal fix → full GREEN → fresh exact-SHA independent re-review loop.

## Merge gate

Only after:

1. valid RED evidence;
2. minimal implementation;
3. full deterministic GREEN;
4. documentation complete;
5. exact-SHA independent review clean;
6. no unresolved review threads;
7. final head CI green.

Then mark ready and guarded-squash merge with the expected reviewed head SHA, and verify issue #14 closes.

## CAL access/load impact

Production: exactly one user-initiated CAL POST per tool call. No source-form prefetch, dictionary traversal, lemma follow-up, corpus crawl, background refresh, or pagination loop.

Tests and review: offline fixtures only. Live research for this issue ended before the TDD stage after four total bounded CAL requests.
