# Issue #14 research — CAL Dictionary Spelling Collation

**Rechecked:** 2026-09-05

This note records the bounded upstream evidence used before implementing issue #14 plus one source-label correction established during independent review. Normal CI remains offline.

## Research task and CAL semantics

CAL's public `Dictionary Collation` page explains that CAL normalizes lemma spellings across Aramaic dialects, while individual dictionaries often use different spelling systems. The page therefore lets a researcher select one dictionary and enter its page reference to retrieve the CAL lemmas currently associated with that page. CAL also explicitly describes this as useful for cross-dictionary collation.

The public instructions state that multi-volume works without sequential pagination may use volume-qualified page references, with the example:

```text
1:134, 2:212
```

A public CAL-MCP page parameter must therefore remain a page-reference string rather than an integer.

Source: https://cal.huc.edu/searchdicts.html

## Current form contract

A bounded branch-only form probe on 2026-09-05 confirmed one form:

```text
POST /searchdicts.php

dict=<one-letter CAL dictionary selector>
page=<dictionary page reference>
```

The current ordered selector values and labels are:

| CAL value | CAL label |
| --- | --- |
| `J` | Jastrow |
| `L` | Lexicon Syriacum |
| `K` | A Syriac Lexicon |
| `j` | A Compendious Syriac Dictionary |
| `B` | A Dictionary of Jewish Babylonian Aramaic |
| `P` | A Dictionary of Jewish Palestinian Aramaic |
| `V` | Levy, Chaldäisches Wörterbuch ü.die Targumim |
| `M` | A Mandaic Dictionary |
| `W` | Dictionary of the Northwest Semitic Inscriptions |
| `T` | Thesaurus Syriacus |
| `R` | Dictionary of Samaritan Aramaic |
| `S` | Schulthess Lexicon Syropalaestinum |
| `C` | A Dictionary of Christian Palestinian Aramaic |
| `D` | A Dictionary of Judean Aramaic |
| `Q` | Dictionary of Qumran Aramaic |

The selector values are case-sensitive (`J` and `j` are distinct) and are implementation details of the current CAL form. CAL-MCP should not require agents to memorize them. The public adapter contract should use readable stable source names and map them internally to these current form values.

## Representative successful result

One bounded request submitted:

```text
dict=J
page=705
```

CAL returned HTTP 200 from `/searchdicts.php`, approximately 3 KiB. The rendered page begins with the semantic identity:

```text
CAL: entries for page 705 of Jastrow
CAL entries corresponding to page 705 of
Jastrow
Click on a lemma to see an outline entry.
```

The result card then contains ordered paragraph rows. Each current data row has one CAL entry link followed by rendered gloss text. Representative rows include:

```text
l)w N : work, labor
lxt V : to pant → lht V
lxt N : central part of the hand or leg
lxt) N : splint bone → lxt N
...
l(w N : work, toil
```

The entry links target `oneentry.php?lemma=...`, sometimes with optional `cits=no`.

A parser-relevant detail is that the rendered lemma label and the linked canonical CAL lemma key can differ. For example:

```text
rendered label: lxt V
link target:    lemma=lht V
rendered gloss: to pant → lht V
```

and:

```text
rendered label: lxt) N
link target:    lemma=lxt N
rendered gloss: splint bone → lxt N
```

CAL-MCP must preserve both the rendered label and the link target. It must not collapse aliases/redirect-style spellings into the target key or silently rewrite the rendered gloss.

## Explicit empty result

A bounded Jastrow request for page `99999` returned HTTP 200 and the same result-card shell, but no entry rows. CAL rendered one explicit red paragraph:

```text
No data available for that page.
```

That is a successful empty collation result. A successful HTTP page with neither recognizable entry rows nor this explicit marker is parser drift, not an empty result.

## Result-page structure observed

The current successful and empty pages share:

- a page identity containing the submitted page reference and dictionary label;
- one `div.summary-card` containing the result semantics;
- a heading/instruction area;
- zero or more `<p>` result rows, each with one `oneentry.php` lemma link and trailing rendered gloss text;
- for empty results, `<p class="red">No data available for that page.</p>`;
- navigation/footer links outside the result rows.

The parser should use the result card and CAL entry-link semantics rather than collecting arbitrary page links. Same-origin entry-link validation should remain fail-closed.

## Public source identifiers

The CAL one-letter radio values are compact form controls rather than meaningful stable research identifiers. The public contract should expose adapter-owned readable source values while also returning CAL's exact rendered dictionary label in every result.

Proposed public values:

| Public source | Current CAL value | CAL label |
| --- | --- | --- |
| `jastrow` | `J` | Jastrow |
| `lexicon_syriacum` | `L` | Lexicon Syriacum |
| `syriac_lexicon` | `K` | A Syriac Lexicon |
| `compendious_syriac_dictionary` | `j` | A Compendious Syriac Dictionary |
| `djba` | `B` | A Dictionary of Jewish Babylonian Aramaic |
| `djpa` | `P` | A Dictionary of Jewish Palestinian Aramaic |
| `levy_targumim` | `V` | Levy, Chaldäisches Wörterbuch ü.die Targumim |
| `mandaic_dictionary` | `M` | A Mandaic Dictionary |
| `dnsi` | `W` | Dictionary of the Northwest Semitic Inscriptions |
| `thesaurus_syriacus` | `T` | Thesaurus Syriacus |
| `samaritan_aramaic` | `R` | Dictionary of Samaritan Aramaic |
| `schulthess` | `S` | Schulthess Lexicon Syropalaestinum |
| `dcpa` | `C` | A Dictionary of Christian Palestinian Aramaic |
| `judean_aramaic` | `D` | A Dictionary of Judean Aramaic |
| `qumran_aramaic` | `Q` | Dictionary of Qumran Aramaic |

The internal mapping is dated upstream knowledge. A later CAL selector change should be reviewed as upstream drift rather than changing public names opportunistically.

## Page-reference validation boundary

The public documentation only demonstrates decimal page numbers and comma-separated volume-qualified decimal references. The smallest grounded grammar is therefore:

```text
page-ref := integer [":" integer]
query    := page-ref ("," page-ref)*
```

Surrounding ASCII spaces and spaces around commas may be normalized deterministically. Empty values, line breaks/control characters, bare colons, ranges, alphabetic page names, and other undocumented syntaxes should fail locally rather than be guessed.

This keeps a single caller action to one CAL request while supporting the documented multi-volume syntax.

## Boundedness and pagination

No continuation control, page-number navigation for the result list, or recursive dictionary traversal was observed. One collation call should submit exactly one bounded CAL POST and return exactly that result page. CAL-MCP must not follow returned lemma links automatically.

The shared HTTP client already provides the required response-size limit, bounded concurrency, duplicate suppression, cache policy, timeout handling, transient-only retry behavior, and redirect boundary. Issue #14 needs no HTTP-stack changes.

## Documentation and attribution

CAL's public page notes that the database is a work in progress and that coverage varies by reference work. CAL-MCP documentation should therefore describe results as the CAL correspondences currently stored for that dictionary/page, not as an exhaustive equivalence table between dictionaries.

## Review-time source-label correction

The first form extraction accidentally concatenated the generic `Page` field label after the final dictionary selector, producing `Dictionary of Qumran Aramaic Page`. During independent review, the current public form was re-read directly and clearly rendered the final selector as `Dictionary of Qumran Aramaic`, followed separately by `Page` and its input. The source mapping, tests, and user documentation were corrected to the exact selector label while preserving private selector code `Q`.

One bounded review request attempted to verify the Qumran result title directly with `dict=Q&page=99999`. CAL returned HTTP 405 to that probe client, so no result-page identity was obtained; the request was not retried. The temporary workflow self-deleted. This failed request is recorded as evidence, not treated as evidence for a different method, because the earlier bounded form/result research had already confirmed successful POST behavior for the implemented endpoint.

## Sources and research load

Sources:

- https://cal.huc.edu/searchdicts.html
- `POST https://cal.huc.edu/searchdicts.php`, `dict=J&page=705`, bounded probe on 2026-09-05
- `POST https://cal.huc.edu/searchdicts.php`, `dict=J&page=99999`, bounded probe on 2026-09-05
- `POST https://cal.huc.edu/searchdicts.php`, `dict=Q&page=99999`, one review-time attempt on 2026-09-05 that returned HTTP 405 and was not retried

Two temporary branch-only research workflows used four CAL requests total: one form GET plus one representative result in the first run, followed by one repeated representative result and one explicit empty result in the second run. Independent review added one bounded Qumran POST attempt. All temporary workflows were deleted. No dictionary pages, lemma entries, result links, or source lists were traversed automatically.
