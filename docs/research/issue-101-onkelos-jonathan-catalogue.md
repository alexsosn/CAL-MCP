# Issue #101 research — Onkelos/Jonathan catalogue route

**Rechecked:** 2026-09-08
**Baseline:** `main` at `591d80cef54187efdbf74fdb5fbaaa21c8f108e1`

This is a bounded route-family recheck. It does not enumerate corpus contents beyond the one dedicated collection page and representative direct/subdivided children.

## Current failure

CAL's current Text Browse root links `Targums Onkelos and Jonathan to the Prophets` to:

```text
/targum_onkelos_jonathan.html
```

`parse_text_catalogue_page()` currently recognizes only:

- category links ending in `showsubtexts.php`;
- direct text links ending in `get_a_chapter.php`.

The root page still contains many ordinary recognized links, so parsing succeeds while the Onkelos/Jonathan collection is silently omitted.

## Dedicated collection semantics

Current dedicated page:

```text
https://cal.huc.edu/targum_onkelos_jonathan.html
```

It is one shallow catalogue level. Current ordered children include:

- `51001 TgO Gn` -> `showsubtexts.php?cset=H&subtext=51001`;
- ... other Onkelos/Jonathan biblical sources ...;
- `51400 MegTan (Megillat Taanit)` -> `get_a_chapter.php?cset=H&file=51400`.

The existing generic catalogue parser already distinguishes these two child shapes correctly:

- `showsubtexts.php?...&subtext=<id>` -> `TextCategoryRef`;
- `get_a_chapter.php?...&file=<id>` -> `TextRef`.

Therefore the missing behavior is the dedicated parent route, not a new parser for the child list.

## Stable public bridge selector

CAL's current/alternate dialect browser exposes the same source family under:

```text
newshow_browsedialects.php?R1=51
```

and lists the same ordered `51001` ... `51026` plus `51400` family. CAL's dialect-code vocabulary identifies `51` as the Jewish Literary Aramaic collection containing this material.

The narrowest compatible public correction is therefore to expose the dedicated root link as the existing `TextCategoryRef` shape with:

```text
category_id = "51"
label = CAL's rendered root label
```

and privately route `cal_text_catalogue(category_id="51")` to `targum_onkelos_jonathan.html`.

This adds no new MCP tool and no new generic arbitrary-route parameter.

## `cset=H` check

The dedicated page renders `cset=H` in its child links. This selector is not required for the representative follow-up semantics tested here:

- `showsubtexts.php?subtext=51001` and `showsubtexts.php?cset=H&subtext=51001` currently return the same `TgO Gn` chapter catalogue;
- `get_a_chapter.php?file=51400` and `get_a_chapter.php?cset=H&file=51400` currently return the same `MegTan` text page.

`cset=H` also occurs on ordinary current Text Browse links that CAL-MCP already follows without carrying that selector forward.

Issue #101 therefore must not add speculative charset/state propagation. A future semantic difference requires its own failing regression.

## Fail-closed boundary

The dedicated route is a current CAL special case with a stable rendered label and exact path. Root parsing should recognize that exact path as category `51`.

If CAL still renders the Onkelos/Jonathan root label but changes it to an unknown route shape, parsing should fail explicitly rather than return an apparently complete root catalogue missing this collection.

Unrelated navigation/reference links remain ignorable; the parser should not fail merely because every link is not a text route.

## Result/provenance semantics

No new result model is necessary.

Root call:

```text
cal_text_catalogue()
```

returns the Onkelos/Jonathan branch among `categories` as `category_id="51"`.

Follow-up:

```text
cal_text_catalogue(category_id="51")
```

performs exactly one GET to `targum_onkelos_jonathan.html`, returning its ordered child `categories` and direct `texts`. Existing catalogue provenance already records the actual source URL, retrieval time, operation, and requested category ID.

A caller can then explicitly open `51001` as another catalogue level or `51400` as a text page. No child is fetched automatically.

## Documentation implication

The prior Targum research note said single-Targum browsing composes through generic text tools. That remains correct for a source already obtained from another Targum result, but it was incomplete as a discovery statement because this collection vanished from root Text Browse.

After #101, the generic text catalogue has a truthful discovery path for Onkelos/Jonathan; the specialized Targum parallel/concordance/reflex tools remain unchanged.

## Sources

Rechecked 2026-09-08:

- https://cal.huc.edu/newtextmenu.html
- https://cal.huc.edu/targum_onkelos_jonathan.html
- https://cal.huc.edu/newshow_browsedialects.php?R1=51
- https://cal.huc.edu/showsubtexts.php?subtext=51001
- https://cal.huc.edu/showsubtexts.php?cset=H&subtext=51001
- https://cal.huc.edu/get_a_chapter.php?file=51400
- https://cal.huc.edu/get_a_chapter.php?cset=H&file=51400
- `src/cal_mcp/texts.py` at the baseline above

## CAL load

The focused recheck used the dedicated parent page, one alternate selector page, and paired direct/subdivided representative requests with/without the displayed `cset=H`. No child corpus traversal, chapter enumeration, or text crawling was performed by the development workflow. Normal CI remains offline.
