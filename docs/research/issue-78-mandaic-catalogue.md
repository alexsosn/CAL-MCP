# Issue #78 research — Mandaic catalogue reachability

**Research date:** 2026-09-09  
**Baseline:** `main` at `219d070d997386bef6a0fb9aad66b51545858411`  
**Issue:** #78

## Question

How should `cal_text_catalogue` expose CAL's current Mandaic collection without treating its mixed dedicated route as an ordinary `showsubtexts.php?subtext=...` hierarchy, adding recursive traversal, or exposing CAL-private URL controls?

## Current repository contract

`TextService.catalogue()` currently has three routing cases:

1. root: `GET newtextmenu.html`;
2. category `51`: `GET targum_onkelos_jonathan.html`;
3. every other decimal category: `GET showsubtexts.php?subtext=<category_id>`.

`parse_text_catalogue_page()` recognizes ordinary category links only when their route is `showsubtexts.php`, and recognizes text links only when their route is `get_a_chapter.php`. The root therefore silently drops CAL's dedicated Mandaic branch.

The current text-page implementation already has a separate, researched Mandaic routing table from #97: subdivided collection-74 files and direct collection-74 files use distinct page request shapes. Issue #78 should make those existing file identifiers discoverable; it should not redesign page routing.

## Bounded current-CAL recheck

Research was limited to the Text Browse root and the dedicated Mandaic collection page. No text body, chapter, token, or neighboring result was traversed.

### Root route

Current `newtextmenu.html` still renders a root-level **Mandaic** link whose target is:

```text
show_Mandaic.php?R1=74
```

The stable semantic selector exposed by CAL is therefore collection `74` via `R1=74`, not generic `subtext=74`.

### Dedicated collection shape

Current `show_Mandaic.php?R1=74` renders an ordered list of Mandaic text files. The page contains both already-known route families inside one collection:

- subdivided example `74401` (ATS) -> `showsubtexts.php?cset=M&subtext=74401`;
- direct example `74501` (Haran Gauaita) -> `get_a_chapter.php?cset=M&file=74501`.

The current page also includes Ginza `74410`/`74411` and many direct/other Mandaic files. This research does not enumerate them into adapter configuration; the page itself remains the authoritative bounded catalogue response.

A fetch of the child pages was not needed for #78. The exact child hrefs are enough to classify file-discovery semantics, while #97 already owns and has completed direct-vs-subdivided text-page routing.

## Semantic decision

The Mandaic dedicated page is a **file catalogue**, not another generic category layer.

For this page only:

- `showsubtexts.php?cset=M&subtext=<positive decimal>` means a **subdivided Mandaic text file** and must be returned as `TextRef(file_id=<subtext>, subtext_id=None, ...)`, not `TextCategoryRef`;
- `get_a_chapter.php?cset=M&file=<positive decimal>` means a **direct Mandaic text file** and must be returned as `TextRef(file_id=<file>, subtext_id=None, ...)`;
- both forms must require exactly the expected Mandaic `cset=M` presentation selector for this dedicated collection page;
- the parser must preserve CAL order and rendered file labels;
- returned links are metadata/identifiers only. No child is fetched automatically.

This route-specific interpretation must not weaken the generic catalogue parser. Ordinary `showsubtexts.php?subtext=<id>` links outside the dedicated Mandaic response continue to mean categories.

## Root discovery decision

At the root catalogue, recognize only the exact dedicated Mandaic route family:

```text
show_Mandaic.php?R1=74
```

and expose it as:

```text
TextCategoryRef(category_id="74", label="Mandaic")
```

The exact rendered label should be preserved from CAL. If a Mandaic-labelled root link moves to an unrecognized route/query, fail closed rather than silently dropping it and claiming complete root discovery.

The public selector remains the existing `category_id` string. No new MCP tool is needed.

## Service routing decision

`TextService.catalogue(category_id="74")` should issue exactly one logical request:

```text
GET show_Mandaic.php?R1=74
```

It must not request `showsubtexts.php?subtext=74`, prefetch any returned text, or probe child route shape.

Parsing should be explicitly route-aware. The safest design is a dedicated `parse_mandaic_catalogue_page()` (or equivalent private mode) called only for category `74`, while the root/ordinary/Onkelos parser retains its current semantics.

## Label extraction

On the current Mandaic page, the linked numeric identifier is followed by the human-readable text name on the same rendered semantic row (for example `74401 ATS (The Thousand and Twelve Questions)`). A Mandaic catalogue item should use the rendered human-readable remainder as `TextRef.label`, not expose the numeric anchor as the title.

If a recognized Mandaic navigation link has no nonempty rendered label after removing its linked identifier, parsing must fail closed.

## Validation and drift boundary

For the dedicated Mandaic response:

- require response endpoint `show_Mandaic.php`;
- require exactly one nonempty `R1=74` response selector and reject extra/repeated query controls;
- require child links to remain same-origin CAL routes;
- subdivided child links must expose only one `subtext` semantic identifier plus exact `cset=M`;
- direct child links must expose only one `file` semantic identifier plus exact `cset=M`;
- identifiers must be positive decimal strings;
- duplicate file identifiers fail closed;
- a recognized row with contradictory/ambiguous navigation fails closed;
- a successful-looking dedicated page with no recognized text rows fails closed;
- script-toggle/navigation/reference links that are not text rows are ignored only when they do not mimic a recognized Mandaic text route.

No guessed empty-catalogue success state is introduced because current research did not establish an explicit empty marker.

## Compatibility

Unchanged:

- public `cal_text_catalogue(category_id=None)` schema;
- ordinary category routing and parsing;
- category `51` Onkelos/Jonathan routing;
- `TextRef` / `TextCategoryRef` output schemas;
- Mandaic text-page routing from #97;
- text search, text information, token analysis, concordance, and other services;
- shared cache/single-flight/retry/origin/response-size policy.

The new behavior is only root discovery of category `74` plus one bounded dedicated Mandaic catalogue request.

## Documentation impact

Update text documentation to state that root discovery includes Mandaic category `74`, and that following it performs one dedicated catalogue request returning both direct and subdivided Mandaic files as text references. Explain that the direct/subdivided distinction is handled by the already-researched text-page routing and is not a second discovery request.

Update the specialized-route/reachability audit (#83/#103) after merge or in the same documentation-only scope only where needed to stop describing #78 as unresolved.

## Test implications

A valid RED should prove offline that:

1. root `cal_text_catalogue()` preserves an exact `Mandaic -> show_Mandaic.php?R1=74` branch in CAL order;
2. a Mandaic-labelled root link with changed endpoint/query fails closed;
3. `cal_text_catalogue(category_id="74")` sends exactly `GET show_Mandaic.php?R1=74` and no other request;
4. the dedicated parser returns both representative subdivided and direct links as ordered `TextRef` items, never categories;
5. rendered human-readable labels are preserved;
6. wrong/missing/repeated `R1`, wrong/missing `cset=M`, ambiguous child selectors, duplicate IDs, cross-origin recognized links, and no recognized rows fail closed;
7. ordinary and category-51 catalogue behavior remains unchanged;
8. no child route is fetched automatically;
9. normal CI remains offline.

## CAL load impact

Low. This research used the root Text Browse page and the one dedicated Mandaic collection page, with link targets inspected only far enough to confirm representative direct/subdivided route families. Production remains one logical CAL request per explicit catalogue operation, subject to the shared cache/single-flight/retry policy.