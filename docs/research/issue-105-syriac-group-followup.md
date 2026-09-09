# Issue #105 research — followable Syriac grouped text categories

**Research date:** 2026-09-09  
**Baseline:** `main` at `4ba30d701750f2d14444812ef977e77c95f10b86`  
**Issue:** #105

## Question

How should CAL-MCP make a `navigation_kind="group"` item returned by `cal_syriac_texts` explicitly followable without guessing a generic text/catalogue route, synthesizing presentation selectors, recursively traversing CAL, or accepting an arbitrary URL?

## Repository contract before this issue

`cal_syriac_texts(category)` already distinguishes three current CAL navigation kinds:

- `text` — `get_a_chapter.php?file=<id>...`;
- `catalogue` — `showsubtexts.php?subtext=<id>...`;
- `group` — `showsubtexts.php?keyword=<id>...`.

`parse_syriac_text_category_page()` validates those routes independently. For `showsubtexts.php` links it treats `keyword` and `subtext` as mutually exclusive semantic selectors; optional `cset` / `script` values are presentation metadata only. A row exposing both semantic selectors is rejected.

The current reduced Metrical Homilies and Hymns fixture, captured/rechecked by the existing Syriac audit, preserves this CAL order:

1. `60420` — Jacob of Serugh, metrical homilies — `GROUP` — `/showsubtexts.php?keyword=60420`;
2. `60424` — Ephrem, Hymns — `TEXT` — `/get_a_chapter.php?file=60424&cset=S`;
3. `63400` — Narsai, metrical homilies — `GROUP` — `/showsubtexts.php?keyword=63400`.

The public service accepts only the top-level descriptive category slugs. Generic `cal_text_catalogue(category_id)` uses the different `subtext=<id>` contract, and `cal_text_page` uses `file=<id>`. There is therefore no MCP-native consumer for a returned `GROUP` item.

The user documentation currently says that navigation kinds describe the next explicit CAL-MCP operation, but the `group` paragraph names no such operation. That is a real reachability/documentation defect rather than merely missing convenience text.

## Bounded current-CAL recheck

Research stayed at route-family scale; it did not enumerate groups or texts.

### Current Syriac module

CAL's current Syriac Studies navigation still exposes the text-category workflow alongside external citations, the missing-from-*A Syriac Lexicon* lists, and MT/Peshitta comparison. The existing dedicated Syriac surface therefore remains the correct module boundary; this issue does not create a duplicate generic Syriac browser.

### `keyword` route

A current web-index lookup for `showsubtexts.php` reached CAL's live page family and returned the generic `Select a Text` surface, but the search/open path did not preserve the requested `keyword=60420` selector. Direct indexed opening of the query-bearing URL was unavailable through the research client. This is insufficient evidence to infer response-body details for a particular group.

Accordingly, this issue must **not** invent a group heading, child list contents, or a `cset` value from that failed recheck. The stable semantic evidence available to the adapter is the exact current parent link already parsed from CAL: `showsubtexts.php?keyword=<positive decimal>`.

### Identifier namespace caution

Current indexed CAL pages also expose `60420` as a Syriac text coordinate (`EphPar`, Ephrem, Hymns on Paradise). The same digits appearing in a `keyword=60420` group link therefore cannot be treated as proof that the group selector is a generic `file_id` or `subtext` identifier. The selector name is part of its semantics.

This makes overloading `cal_text_page(file_id="60420")` or `cal_text_catalogue(category_id="60420")` particularly unsafe: it can resolve a numerically valid but semantically different CAL object.

## `cset` decision

The current parent category fixture emits grouped links as `showsubtexts.php?keyword=60420` and `...?keyword=63400`, with no `cset`. Existing parser policy already treats any `cset` on a returned subtext-navigation link as optional presentation metadata rather than as the group identity.

The bounded live recheck did not establish that the group endpoint requires a charset selector. Therefore the adapter must submit **only** the semantic selector CAL already exposes: `keyword=<group_id>`. It must not synthesize `cset=S`, `cset=Syriac`, or any other unverified value.

If CAL later exposes a group link with an additional presentation selector and preserving it proves semantically necessary, that is a separate researched contract change; the public API should still not make callers supply private CAL presentation fields.

## Public-contract decision

Add one dedicated bounded operation:

```text
cal_syriac_group(group_id)
```

`group_id` is a positive decimal selector returned by a `SyriacTextItem` whose `navigation_kind` is `group`. It is not documented as a text ID or generic catalogue ID.

The operation performs one logical GET request:

```text
showsubtexts.php?keyword=<group_id>
```

It accepts no arbitrary URL and no public `cset`, `script`, `file`, or `subtext` parameter.

A completed shared-client cache hit can perform zero new upstream I/O; single-flight and bounded retry behavior remain the shared request-layer policy. There is no automatic group recursion or child text fetch.

## Result/model decision

Reuse `SyriacTextItem` for ordered child navigation because it already faithfully distinguishes direct text, nested group, and shallow catalogue routes and validates same-origin navigation targets.

Add a focused group result containing:

- requested `group_id`;
- ordered child `items`;
- normal Syriac provenance including a dedicated `group_id` field and operation `syriac_group`.

Do **not** require or fabricate a page/group label in the public result because the current live research did not establish a stable group-heading contract. The parser should consume only recognized navigation rows and fail closed if none survive.

## Parser boundary

Refactor the existing category row extraction into a private shared navigation-item parser rather than creating a second looser HTML parser. Category pages retain their current exact-heading and category-URL validation unchanged.

The group parser must:

1. require response endpoint `showsubtexts.php`;
2. require exactly one nonempty `keyword` query value equal to the requested `group_id`;
3. reject unexpected response query fields instead of silently accepting a different route contract;
4. reuse the existing same-origin child-route rules for `get_a_chapter.php` and `showsubtexts.php`;
5. preserve CAL order, labels, identifiers, navigation kinds, and optional file-info links;
6. reject duplicate identifiers, ambiguous semantic selectors, detached/contradictory info links, malformed identifiers, cross-origin child links, and a successful-looking page with no recognized navigation rows.

The requested response URL itself should be exact `keyword=<group_id>` for this contract. This deliberately does not infer presentation controls that were not established by research.

## Validation / failure semantics

- `group_id` must be a string containing a positive decimal identifier; invalid input fails locally before transport.
- A response for another `keyword`, another endpoint family, repeated `keyword`, or extra response selector is parser drift.
- An HTTP/network/content failure stays a shared typed request-layer failure.
- A successful HTML page with no recognized child rows is parser drift for this operation; research did not establish a stable explicit empty-group marker, so returning a guessed empty success would be unsafe.

## Compatibility

Unchanged:

- `cal_syriac_texts(category)` inputs and result schema;
- `SyriacTextItem` and its three navigation kinds;
- direct text follow-up via `cal_text_page`;
- `catalogue` follow-up via `cal_text_catalogue`;
- missing-word and MT/Peshitta operations;
- generic text catalogue/page routing;
- parent calls never prefetch child groups.

The only new public surface is the explicit consumer for already-returned GROUP identifiers.

## Documentation impact

Update `docs/tools/syriac.md` to:

- list four specialist Syriac operations;
- map `group` items to `cal_syriac_group(group_id)`;
- distinguish `keyword` group selectors from generic `subtext` / `file` identifiers;
- document one logical request, cache/single-flight/retry semantics, and non-recursive behavior;
- stop claiming that every navigation kind has a follow-up while leaving GROUP unnamed.

Update executable tool description/instructions only as needed for discoverability. No capability should suggest arbitrary URL following.

## Test implications

The RED suite should establish, offline:

- a GROUP identifier returned by the existing parent model is consumable by the new operation;
- exact GET request shape is `showsubtexts.php` + one `keyword` pair and **no synthesized `cset`**;
- child order/kind/labels are preserved via the same navigation parser rules;
- nested group/catalogue/text links remain metadata and are not followed;
- invalid group IDs fail before transport;
- response keyword/route contradictions fail closed;
- existing direct/category behavior remains unchanged;
- MCP schema exposes only `group_id` plus context plumbing, not private CAL fields;
- normal CI remains offline.

## CAL load impact

Low. This research used only current navigation/index evidence and a single route-family lookup; it did not enumerate any Syriac group. Production adds one bounded request per explicit caller-selected group, subject to the existing process-local cache/single-flight/retry policy.