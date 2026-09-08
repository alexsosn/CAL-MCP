# Issue #110 research — restore current Syriac Peshitta subtext routing

Date: 2026-09-09
Baseline: `main` at `381fb95725322640ed81302f8ca5bfa092920d4d`

## Question

CAL-MCP documents `ot-peshitta` and `nt-peshitta` as supported Syriac text categories, but their existing reduced OT fixture models biblical books as direct `get_a_chapter.php` links. What route does current CAL actually expose, how should that route be represented in the typed Syriac category result, and what existing bounded public operation should perform the next explicit step?

## Current CAL evidence

A bounded current check covered one representative book from each Peshitta category and its immediate destination:

- `https://cal.huc.edu/ot_peshitta.html` currently lists `62001 P Gn` as a link to `showsubtexts.php?cset=Syriac&subtext=62001`.
- `https://cal.huc.edu/nt_peshitta.html` currently lists `62040 P Mt` as a link to `showsubtexts.php?cset=Syriac&subtext=62040`.
- `https://cal.huc.edu/showsubtexts.php?cset=Syriac&subtext=62001` is a shallow `P Gn` chapter selector with chapters 1–50.
- `https://cal.huc.edu/showsubtexts.php?cset=Syriac&subtext=62040` is a shallow `P Mt` chapter selector with chapters 1–30.

The representative destination chapter links use the ordinary text shape:

```text
get_a_chapter.php?cset=S&file=62001&sub=01
get_a_chapter.php?cset=S&file=62040&sub=01
```

The Genesis destination's own rendering controls switch between `showsubtexts.php?script=S&subtext=62001` and `showsubtexts.php?script=R&subtext=62001`. This establishes `subtext=62001` as the semantic book/category selector; `cset=Syriac` / `script=S|R` is presentation/navigation state rather than a new public book identity.

No chapter link was followed beyond the representative destination page, and no book/category enumeration beyond the already-rendered static category pages was performed.

## Comparison with existing CAL-MCP route families

### Generic catalogue `subtext=`

`parse_text_catalogue_page()` already treats a same-origin `showsubtexts.php?subtext=<decimal>` link as `TextCategoryRef(category_id=<decimal>)`. Calling `cal_text_catalogue(category_id="62001")` sends one explicit `showsubtexts.php?subtext=62001` request and parses returned chapter links as ordinary `TextRef` values carrying `file_id=62001` and `subtext_id=01`, `02`, etc.

That is the correct MCP-native follow-up contract for a Peshitta book selector. CAL-MCP does not need a URL executor, recursive book traversal, or a Syriac-only chapter-list tool.

### Syriac grouped `keyword=`

Current dynamic Syriac categories also expose genuine grouped navigation through `showsubtexts.php?keyword=<decimal>`. `parse_syriac_text_category_page()` models those as `SyriacTextNavigationKind.GROUP`.

That route is semantically distinct from Peshitta `subtext=<book>`:

- `keyword=` selects a grouped Syriac collection/listing;
- `subtext=` selects one CAL text/book's shallow subtext/chapter catalogue.

They must remain distinguishable in the typed category result even though both currently use `showsubtexts.php`.

### Direct text links

Other Syriac categories can expose direct `get_a_chapter.php?file=<id>` navigation. Those remain `SyriacTextNavigationKind.TEXT` and are not affected by this ticket.

## Typed navigation decision

Add a third public navigation kind for the already-public `SyriacTextItem.navigation_kind` field:

```text
catalogue
```

Semantics:

- `text` — direct ordinary text page; follow with `cal_text_page` using the returned upstream ID as `file_id` where applicable.
- `group` — Syriac `keyword=` group navigation; its MCP-native follow-up remains issue #105 because the generic catalogue does not model `keyword=`.
- `catalogue` — CAL `showsubtexts.php?subtext=<id>` shallow catalogue; follow with `cal_text_catalogue(category_id=<upstream_id>)`.

The label `catalogue` describes the public follow-up semantics without leaking the private `subtext` form name into the enum.

No new public tool or argument is required.

## Parser validation / fail-closed rules

For a `showsubtexts.php` link in a Syriac category row:

1. parse the query preserving repeated values;
2. accept exactly one semantic selector family:
   - one decimal `keyword` -> `group`;
   - one decimal `subtext` -> `catalogue`;
3. reject a link containing both `keyword` and `subtext` as ambiguous upstream semantics;
4. reject repeated selector values, missing/blank/non-decimal selector values, or an otherwise unrecognized `showsubtexts.php` selector as parser drift;
5. allow known presentation parameters such as current `cset=Syriac` on the Peshitta category link, but do not expose them as public identifiers or use them to decide the book ID;
6. preserve same-origin validation and the row's exact rendered label/order/info-link consistency.

The returned `navigation_url` remains provenance/navigation metadata. CAL-MCP still does not execute arbitrary returned URLs.

## Stale fixture correction

`tests/fixtures/cal/syriac_category_ot_peshitta.html` is stale because it models `62001` / `62002` as direct `get_a_chapter.php?file=...&cset=S` rows. Replace its semantic route with the current `showsubtexts.php?cset=Syriac&subtext=...` shape and add an NT fixture with representative `62040` / `62041` rows.

Reduced fixtures should retain only heading, current book link, label, and file-info relationship necessary for parser behavior; do not archive full category pages.

## Public request bound

The staged workflow stays caller-controlled:

```text
cal_syriac_texts("ot-peshitta")
  -> choose returned catalogue item, e.g. upstream_id="62001"
cal_text_catalogue(category_id="62001")
  -> choose returned chapter TextRef, e.g. file_id="62001", subtext_id="01"
cal_text_page(file_id="62001", subtext_id="01")
```

Each operation performs exactly one CAL request. No book or chapter is prefetched and no runtime route discovery is added.

## Non-goals

- no redesign of Syriac category slugs;
- no change to MT/Peshitta verse comparison;
- no implementation of `keyword=` group follow-up (#105);
- no bulk Bible/chapter traversal;
- no arbitrary CAL URL execution;
- no changes to generic catalogue behavior unless a focused regression proves its existing `subtext=` composition is broken.

## Research load

The current check was limited to the two static Peshitta category pages and one representative immediate destination from each. Rendering-link inspection was limited to the already-open Genesis destination. No chapter content, token analysis, next-page traversal, or additional books were fetched.
