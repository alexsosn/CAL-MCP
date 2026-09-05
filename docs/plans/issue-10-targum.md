# Issue #10 plan — bounded CAL Targum Studies module

**Plan date:** 2026-09-05

This plan follows the repository loop: research → plan → test-only RED → minimal implementation → GREEN → documentation → independent skeptical review → review-fix RED/GREEN if needed → fresh independent re-review → merge.

## Public contract

Expose four task-level operations:

```text
cal_targum_parallel(book, chapter, verse, include_peshitta=False, include_samaritan=False)
cal_targum_concordance(lemma_key)
cal_targum_hebrew_lemmas(initial, targum)
cal_targum_hebrew_reflexes(targum, mt_lemma_id)
```

Do not add a separate single-Targum browser. Parallel-result source links already target CAL's normal text browser, which is covered by `cal_text_page` and `cal_token_analysis`.

## Input contract and bounds

### Parallel verse

- `book`: one exact current CAL display label from the 36-value selector (`Gen`, `Exod`, …, `2 Chronicles`); map internally to CAL's current two-digit `bookname` value.
- `chapter`: positive integer, maximum 999.
- `verse`: positive integer, maximum 999.
- `include_peshitta`: boolean, default false.
- `include_samaritan`: boolean, default false.
- Submit one POST to `showtargum.php`; only include CAL checkbox fields when requested.

The public result carries the requested CAL book label and current selector ID, chapter/verse, MT rendered text, ordered source readings, optional source chapter URLs, and provenance.

### Targum concordance

- `lemma_key`: reuse the existing CAL lemma-key validator used by concordance/bibliography operations.
- Split the validated key internally into CAL's private `lemma` and POS/stem suffix fields.
- Submit one POST to `showtargumKWIC.php`.

The public result preserves the canonical lemma key, ordered section/source count rows, CAL source/example URLs, total count, and provenance. An all-zero complete table is a valid result.

### Hebrew lemma discovery

- `initial`: one of the current bounded CAL selector slugs: `alef`, `bet`, `gimel`, `dalet`, `heh`, `waw`, `zayin`, `xet`, `tet`, `yod`, `kaf`, `lamed`, `mem`, `nun`, `samekh`, `ayin`, `peh`, `cade`, `qof`, `resh`, `shin`, `sin`, `taw`.
- `targum`: `onqelos` or `neofiti`.
- Map `initial` and `targum` internally to the current chooser path (`Omtlemmas/...MTlemma.html` or `mtlemmas/...MTlemma.html`).
- Submit exactly one GET.

The result preserves ordered MT lemma choices as opaque `mt_lemma_id`, vocalized Hebrew label, displayed POS, selected targum, and provenance. No reflex request is made automatically.

### Hebrew reflexes

- `targum`: `onqelos` or `neofiti`; Pseudo-Jonathan remains unavailable while CAL marks it under development.
- `mt_lemma_id`: positive decimal string, maximum 8 digits, treated as opaque.
- Submit one POST to the current source-specific endpoint.

The result preserves CAL's selected MT Hebrew lemma label plus ordered Targumic CAL lemma correspondences, frequency, absolute CAL example URL, selected targum, opaque MT ID, and provenance.

## Typed models

Add `targum.py` with dedicated parser/service models:

- `TargumSourceReading` — exact CAL label, rendered text, optional same-origin chapter URL;
- `TargumParallelPage` / `TargumParallelResult` — requested reference, MT text, ordered readings;
- `TargumConcordanceRow` — optional section label, exact source label, count, same-origin example URL;
- `TargumConcordancePage` / `TargumConcordanceResult` — lemma key, ordered rows, total;
- `TargumHebrewLemmaCandidate` — opaque MT ID, vocalized Hebrew label, displayed POS;
- `TargumHebrewLemmaOptionsPage` / result — selected initial/targum and ordered choices;
- `TargumReflex` — CAL lemma key/display label, frequency, example URL;
- `TargumReflexPage` / result — selected MT Hebrew lemma plus ordered reflexes;
- `TargumProvenance` — source, source URL, retrieval time, operation, and operation-specific submitted identifiers.

Do not infer linguistic equivalence, harmonize version names, convert CAL source labels into a local ontology, or merge duplicate readings/reflexes.

## Parser contracts

### Parallel page

Recognize the current semantic result heading `MT and targums for <book> <chapter>:<verse>` and require it to match the submitted public reference after CAL's ordinary decimal rendering. If CAL's explicit `error in coordinate` marker is present, return a typed `not_found` status only when no valid comparison readings are present.

Extract MT text separately from source-labelled readings. Preserve source order and source labels. Source chapter links must resolve to the same CAL origin and target the existing text-browser family; malformed/cross-origin source links fail closed.

A successful-looking page with the expected heading but neither comparison data nor the explicit coordinate-error marker is parser drift.

### Concordance page

Require the current heading `CAL: Targum KWIC counts for <lemma key>` to match the submitted canonical key. Parse the ordered source/count table, retaining section headings without flattening them into source names. Parse and validate `total examples: N`; require it to equal the sum of source counts.

Recognized source/example links must stay on the CAL origin and target the current KWIC family. A complete all-zero table and total zero is valid. Missing heading/table/total, nonnumeric counts, total mismatches, or malformed/cross-origin source links are parser drift.

### Hebrew lemma chooser

Parse only the expected source-specific form/action and `R1` radio candidates. Each candidate must have one positive decimal opaque ID and a nonempty rendered Hebrew/POS label. Preserve order and reject duplicate IDs. Use the current page title/heading to ensure the expected MT lemma chooser family was returned.

### Hebrew reflex page

Require the source-specific heading (`Onkelos correspondences to ...` or `Neofiti correspondences to ...`) with a nonempty selected Hebrew lemma. This explicitly rejects CAL's broad response to an invalid opaque ID, whose heading currently ends after `to`.

Parse ordered CAL lemma/frequency rows. Recognized example links must stay on the CAL origin, target the expected source-specific example endpoint, contain exactly the submitted MT ID, and expose one CAL lemma value matching the rendered row. Preserve CAL Unicode/display spelling and canonical query value separately where available.

A valid selected MT lemma with zero reflexes may be represented as an empty ordered result only if CAL exposes explicit result semantics for that state in fixtures/research; otherwise an unrecognized no-row page fails closed.

## Test-first sequence

### RED — reduced fixtures/parser/service/MCP contract

Before production code, add reduced semantic fixtures/tests covering at minimum:

1. Gen 1:1 parallel page with MT plus several ordered CAL source labels and Unicode Hebrew/Aramaic/Syriac text;
2. optional Peshitta present and Samaritan absent without fabrication;
3. source chapter links preserved as absolute same-origin URLs;
4. invalid parallel coordinate with explicit `error in coordinate` → typed not-found;
5. parallel heading/request contradiction → parser drift;
6. `klb N` Targum concordance with section headings, ordered source counts, links, and total 59;
7. complete zero-count concordance → valid total 0 result;
8. count/total mismatch and malformed/cross-origin example link → parser drift;
9. Hebrew lemma chooser with multiple ordered vocalized candidates and opaque IDs;
10. duplicate/malformed chooser IDs and wrong source form/action → parser drift;
11. valid Onqelos reflex page for MT ID `1751` preserving Hebrew label, `tyq#2 N`, frequency 2, and example URL;
12. valid Neofiti reflex page with two ordered correspondences;
13. invalid-ID broad CAL page with empty `correspondences to` heading → parser drift;
14. reflex link MT-ID/query contradiction or cross-origin target → parser drift;
15. invalid book, chapter/verse bounds, initial, targum, lemma key, and MT ID fail locally before transport;
16. exact one-request mappings for all four public operations;
17. provenance preserves operation, source URL, retrieval time, requested public values, and submitted CAL identifiers where relevant;
18. MCP introspection exposes only task-level parameters and no private CAL names such as `bookname`, `Peshitta`, `Sam`, `R1`, `lemma`, `pos`, `texts`, or `charset`.

A valid primary RED requires install, Ruff lint/format, and strict mypy to pass, with pytest failing only because the new `cal_mcp.targum` module/tools do not yet exist.

### GREEN — minimal implementation

Implement only the models, bounded mappings/validators, small HTML parsers, service methods, and MCP registration needed by the RED suite. Reuse `CalHttpClient` and existing CAL lemma-key validation. Do not add a second HTTP stack, hidden source/chapter/KWIC traversal, automatic example fetching, version harmonization, or a local biblical/Targum corpus.

## Documentation gate

Before review:

- add `docs/tools/targum.md`;
- update README's implemented surface;
- document exact CAL book labels, optional Peshitta/Samaritan behavior, not-found coordinate semantics, zero-count concordance semantics, Hebrew-reflex two-step workflow, Onqelos/Neofiti limitation, Pseudo-Jonathan under-development status, and composition with `cal_text_page` / existing KWIC tools;
- record reduced fixture provenance and state that normal tests are offline.

## Independent review gate

Review the exact final SHA skeptically for:

- leaking CAL form names or raw private endpoint mechanics into public schemas;
- adding a redundant single-Targum browser instead of composing existing text tools;
- changing/normalizing CAL version labels or order;
- silently fabricating missing Samaritan/Peshitta readings;
- accepting `error in coordinate` as successful empty data;
- rejecting valid all-zero concordance or accepting incomplete zero-like pages;
- failure to reconcile concordance row sums with CAL's total;
- accepting wrong-query headings/results and provenance contradictions;
- trusting arbitrary/cross-origin source/example links;
- accepting CAL's broad invalid-MT-ID fallback as a valid reflex result;
- exposing Pseudo-Jonathan Hebrew reflexes despite CAL marking the path under development;
- more than one CAL request per public tool call or hidden follow-up traversal.

Any blocker gets a test-only review-regression RED before its fix, followed by a fresh exact-SHA re-review.

## CAL load bound

Production: exactly one CAL request per public operation. Hebrew lemma discovery → reflex lookup, parallel source → chapter browsing, and concordance source → detailed KWIC remain separate caller-controlled calls. No automatic verse walking, source expansion, biblical-book traversal, all-version crawl, concordance example fetch, Hebrew-lemma alphabet crawl, or corpus mirror.

Tests: offline reduced fixtures only.