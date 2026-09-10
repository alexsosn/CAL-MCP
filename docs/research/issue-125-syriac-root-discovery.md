# Issue #125 research — discover the specialized Syriac root collection

**Research date:** 2026-09-10  
**Baseline:** `main` at `ee37a443f5d40a688f76ed9943cbf4a9e3f50079`  
**Issue:** #125

## Question

How should root text discovery preserve CAL's current `Syriac -> AvailSyr.html` branch without inventing a decimal CAL category identifier, adding a redundant root-discovery tool, prefetching the Syriac classification page, or duplicating the existing Syriac parsers?

## Current CAL route

Bounded current-page recheck:

- `newtextmenu.html` still renders the root `Syriac` link to `AvailSyr.html`;
- `AvailSyr.html` still renders 20 top-level text classifications;
- representative current classifications include OT Peshitta, Old Syriac Gospels, NT Peshitta, Apocryphal/Pseudepigraphal texts, Commentaries, Metrical Homilies and Hymns, Dispute Poems, Religion, archival/canonical/legal families, Magic, Science/Philosophy, History, Novels/Histories, Martyrologies, Various, and Inscriptions.

Research stopped at this classification surface. It did not enumerate category contents or texts.

## Current CAL-MCP behavior

`parse_text_catalogue_page()` can emit only:

- `TextCategoryRef(category_id=<decimal CAL id>, label=...)`;
- `TextRef(file_id=<decimal CAL id>, ...)`.

The current root parser now explicitly preserves the specialized Onkelos/Jonathan and Mandaic routes because both can be mapped truthfully into the existing decimal catalogue/text contracts. `AvailSyr.html` is still ignored because it has neither a generic `subtext=<id>` category selector nor a direct `file=<id>` selector.

`cal_syriac_texts(category)` already owns the Syriac classification workflow. Its public `category` input is a plain string, and the service validates it against `_TEXT_CATEGORIES`. The currently supported slugs, in the same order as the current classification surface, are:

1. `ot-peshitta`
2. `old-syriac-gospels`
3. `nt-peshitta`
4. `apocryphal-pseudepigraphal`
5. `commentaries`
6. `metrical-homilies-hymns`
7. `dispute-poems`
8. `religion`
9. `archival`
10. `canonical`
11. `documents`
12. `syro-roman-law-book`
13. `canon-law`
14. `magic`
15. `science-philosophy`
16. `history`
17. `novels-histories`
18. `martyrologies`
19. `various`
20. `inscriptions`

Those values are not currently encoded as an MCP enum: the server annotation is `category: str`, and invalid values receive a generic validation error. Therefore a root result that merely says `follow_up_tool="cal_syriac_texts"` would identify the operation but still leave a machine caller without the supported selector vocabulary.

## Rejected designs

### Synthetic decimal `category_id`

Reject. `AvailSyr.html` is not a generic CAL `showsubtexts.php?subtext=<id>` category, and no researched decimal root selector exists. Assigning one would violate the documented meaning of `TextCategoryRef.category_id` and could collide with real CAL identifiers.

### Non-decimal value in `TextCategoryRef.category_id`

Reject. This would silently change an established public field from a CAL decimal identifier into a mixed CAL/CAL-MCP namespace and would require relaxing existing validation.

### New `cal_text_collections()` tool

Reject for this gap. It would duplicate the existing root request, expand the release surface, and still need an operation-aware result model. The existing `cal_text_catalogue()` root response is already the natural discovery surface and can be extended additively.

### Prefetch `AvailSyr.html` during root discovery

Reject. Root discovery must remain one bounded CAL request. Automatically opening the Syriac branch would violate the explicit-follow-up rule and create special hidden I/O.

## Chosen public contract

Add an ordered `specialized_collections` field to `TextCataloguePage` / `TextCatalogueResult`.

Each item is an operation-aware reference rather than a fake CAL category. For the current Syriac branch:

```text
collection_key: "syriac"
label: <CAL rendered root label>
follow_up_tool: "cal_syriac_texts"
selector_name: "category"
supported_selectors: [<the 20 currently supported CAL-MCP category slugs>]
```

`collection_key` and `follow_up_tool` are explicitly CAL-MCP metadata. They are not presented as upstream CAL identifiers. `label` remains CAL-rendered data from the one root response.

`supported_selectors` must be derived from the same `_TEXT_CATEGORIES` configuration used by `SyriacService.texts()` rather than copied into `texts.py`. Add a small read-only helper in `syriac.py` that returns the configured keys in insertion order. This avoids configuration drift and does not add a network operation.

The selector list describes **what this CAL-MCP build supports**, not a freshly enumerated copy of `AvailSyr.html`. The bounded live recheck establishes that the current upstream classification surface still corresponds to that support set. If CAL adds/removes/relabels classifications later, the existing Syriac drift/update process remains responsible for changing `_TEXT_CATEGORIES`.

## Root parser boundary

Recognize the specialized branch only when the root link is:

- relative to CAL;
- exact path `AvailSyr.html` (bare or root-relative);
- no query or fragment semantics are required;
- nonempty rendered label.

If CAL still renders the exact label `Syriac` but changes the route to another path, nested suffix lookalike, query-bearing variant, or foreign origin, fail closed instead of silently returning a root result that appears exhaustive.

A changed nonempty label on the exact researched route is preserved rather than hard-coded.

No non-root Syriac page is parsed by the generic text parser. Existing `cal_syriac_texts` remains the only consumer of the classification pages.

## Result compatibility

Additive output change only:

- existing `categories`, `texts`, and `provenance` retain their semantics;
- non-root catalogue results normally return `specialized_collections: []`;
- root results can contain the Syriac specialized reference in that field;
- Onkelos/Jonathan remains category `51`;
- Mandaic remains category `74`;
- no public input signature changes;
- no tool-count/release-surface change.

Because categories/texts are already separate ordered collections, the result does not claim one global interleaving across heterogeneous kinds. `specialized_collections` preserves CAL order among specialized references; currently Syriac is the only root branch that requires this representation.

## Provenance / request bound

`cal_text_catalogue()` continues to perform exactly one logical `GET newtextmenu.html` request on a cache miss and zero new upstream I/O on a completed cache hit. The specialized reference is parsed from that response and enriched only with deterministic local configuration.

No `AvailSyr.html`, category page, group, catalogue child, or text is fetched automatically. Root provenance remains the actual `newtextmenu.html` source URL and retrieval timestamp.

## Failure semantics

Fail closed for:

- exact `Syriac` label on a changed/foreign/nested/query-bearing specialized route;
- exact `AvailSyr.html` route with an empty rendered label;
- duplicate specialized collection keys in one parsed page;
- successful-looking root content that otherwise keeps existing parser semantics.

Do not turn unrelated links into specialized collections merely because their labels contain `Syriac`.

## Test implications

Offline RED should prove:

- ordinary + category-51 + Syriac specialized + category-74 root branches are all preserved without changing existing category identifiers;
- the Syriac specialized item exposes `cal_syriac_texts`, selector name `category`, and exactly the current configured selector keys;
- exact route accepts a changed nonempty label;
- wrong path, query, nested suffix lookalike, foreign absolute lookalike, and empty label fail closed;
- duplicate Syriac specialized links fail;
- non-root catalogue output contains an empty specialized list;
- one root service call performs one request and does not fetch `AvailSyr.html`;
- current Onkelos/Jonathan and Mandaic dispatch behavior remains unchanged;
- normal CI opens no CAL socket.

## Documentation impact

Update text discovery docs and the capability matrix to state that root catalogue discovery distinguishes ordinary CAL categories from specialized collection references. Update Syriac docs to show the machine-actionable transition from the root specialized reference to `cal_syriac_texts(category=<returned supported selector>)`.

After merge, update #83/#103. If no other specialized root branch remains unrepresented, #83 can move from implementation umbrella to completed route-family audit status after its matrix/documentation acceptance criteria are checked.

## CAL load impact

Research used only the already-known root and Syriac classification pages. Production adds no request: root discovery stays one CAL request and all selector enrichment is deterministic local metadata.
