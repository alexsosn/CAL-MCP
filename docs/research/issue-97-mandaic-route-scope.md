# Issue #97 research — scope Mandaic direct and subdivided text-page routes

Date: 2026-09-08
Baseline: `main` at `88892f4054d470f2d7fa7e72b647ada13befbd11`

## Question

The fix merged in #95 routes every `file_id` beginning with `74` and lacking a public `subtext_id` through CAL's Mandaic page-selector request `cset=M&file=<id>&sub=<page>`. Does current CAL actually use that route uniformly across collection 74, and what is the narrowest deterministic correction that preserves the one-request public `cal_text_page` contract?

## Current production behavior

`TextService.page()` currently computes:

```python
mandaic_page_route = normalized_subtext is None and normalized_file.startswith("74")
```

and, when true, sends:

```text
GET get_a_chapter.php?cset=M&file=<file_id>&sub=<one-based page padded to >=3 digits>
```

This behavior was introduced to restore Ginza Rabba retrieval. It is too broad if a `74...` file is linked by CAL as a direct text instead of through a subdivision/page selector.

## Current CAL menu evidence

A fresh independent review after #95 found heterogeneous routing on the current Mandaic menu:

- subdivided examples: `74410` (Ginza Rabba Right Side) and `74401` (ATS) link through `showsubtexts.php?...&subtext=<file>`;
- direct examples: `74501` (Haran Gauaita), `74716`, and `74717` link directly to `get_a_chapter.php?...&file=<file>` with no `sub` page selector.

The browser-visible current menu is:

- https://cal.huc.edu/show_Mandaic.php?R1=74

A branch-only raw-menu probe then made one bounded GET per inspected rendering, with a 15-second timeout and 512 KiB response cap. No text/subtext links were followed. The temporary workflow was deleted before planning.

The live CAL response for the Roman menu and CAL's alternate `cset=J` rendering exposed the same route classification for the 20 entries returned to the probe:

### Subdivided/menu-to-`showsubtexts.php`

```text
74401
74402
74410
74411
74421
74422
74423
74428
74430
74432
74701
74923
```

### Direct/menu-to-`get_a_chapter.php`

```text
74420
74424
74425
74426
74427
74429
74431
74501
```

The indexed/browser view used by the bug report exposes additional collection-74 entries not present in that live runner's 20-entry response. In that evidence, `74716` / `74717` are direct, while `74700` is linked through `showsubtexts.php`. This reinforces the central result: neither the `74` prefix nor a narrower `744`/`747` prefix predicts route kind.

The live raw menu also uses `cset=R` or `cset=J` in its own navigation even when the probe requested `cset=M`; #95's already-researched `cset=M` text-page request remains outside this ticket. Issue #97 changes only *which files receive the `sub=NNN` page-selector form*, not the established Mandaic text rendering selector. If that selector itself later proves incompatible, it should be a separate focused regression.

## Post-review direct-page evidence

The first adversarial review correctly noted that menu routing alone did not prove the response shape of a direct Mandaic text. A bounded follow-up probe therefore requested exactly one current direct page:

- `https://cal.huc.edu/get_a_chapter.php?cset=M&file=74717`
- HTTP 200, `text/html; charset=UTF-8`, 58,154 bytes, no redirect;
- rendered file heading `74717: Qmaha Dbr ˁngaria`;
- first rendered line coordinate `001`, machine coordinate `74717001`;
- first lexical token `bšumaihun`, linked as `getlex.php?coord=74717001&word=0&hasvariant=0`;
- no `Previous Page` or `Next Page` navigation links were rendered.

The probe was fixed to that one URL, used a 15-second timeout and 512 KiB cap, and did not follow any returned text/token/comment links. Its temporary read-only workflow was subsequently removed. The reduced regression fixture `tests/fixtures/cal/text_page_mandaic_direct_74717.html` retains only the semantic fragment needed to prove the direct page is compatible with the ordinary/unpaginated parser mode.

This evidence closes the review gap: direct Mandaic page 1 is not merely a menu-route assumption; the current destination has the same file-heading/line/token semantics needed by the existing ordinary page parser, without Mandaic `sub=NNN` page navigation.

## Classification decision

There is no defensible arithmetic/prefix rule for current CAL Mandaic routing. Runtime discovery would require an extra CAL request and violate the existing one-request operation contract.

Therefore the narrowest deterministic policy is:

1. preserve a private allowlist of collection-74 file IDs that current CAL explicitly exposes through `showsubtexts.php`;
2. treat all other `74...` files without a public `subtext_id` as **direct Mandaic** text routes;
3. keep explicit public `subtext_id` behavior on the pre-existing ordinary route, unchanged;
4. keep all non-`74...` files on the ordinary route, unchanged.

The first implementation used the 12-file live-runner set above plus indexed/browser evidence for `74700`. A later exact-head adversarial review re-read the same current menu more completely and found three additional subdivided `747xx` rows omitted by that partial observation: `74702`, `74711`, and `74714`. The complete current `747xx` route classification observed in that review is recorded in `docs/research/issue-97-review-747xx-route-addendum.md`.

The current private subdivided set therefore includes:

```text
74401 74402 74410 74411 74421 74422 74423
74428 74430 74432 74700 74701 74702 74711 74714 74923
```

The allowlist is adapter routing metadata, not a new public identifier taxonomy. Current neighboring `74703`–`74710`, `74712`–`74713`, and `74715`–`74723` are direct menu links, so the review strengthens rather than weakens the conclusion that a `747` prefix rule would be wrong.

This policy intentionally prefers a direct request for an unknown/new `74...` file over inventing a `sub=NNN` selector. If CAL later adds a new subdivided Mandaic file, the adapter may fail to retrieve it until the menu evidence is researched and the private allowlist is updated; that is safer than silently sending an ungrounded specialized request.

## Direct Mandaic page behavior

For a direct collection-74 file with no public `subtext_id`:

- `page=1` maps to one request using the researched direct shape: `get_a_chapter.php` with `cset=M` and `file=<id>`, **without** `sub` or invented `page` query fields;
- page numbers greater than 1 are not currently grounded by the direct menu route and should fail locally before transport rather than being converted to `sub=NNN`;
- parsing uses the existing unpaginated/ordinary page semantics; there is no synthetic page-count or specialized-navigation mode.

This preserves exactly one CAL request for supported direct page-1 retrieval.

## Subdivided Mandaic behavior

For an allowlisted subdivided file with no public `subtext_id`, preserve #95's researched behavior:

- `page=1` -> `cset=M&file=<id>&sub=001`;
- `page=2` -> `...&sub=002`;
- larger positive pages are not truncated;
- parser may use the requested public page when CAL omits ordinary `Page N of M` metadata;
- specialized previous/next links remain same-file / `cset=M` / adjacent-`sub` validated;
- no total page count is invented.

Ginza Rabba Right (`74410`) and Left (`74411`) remain explicitly covered. The review-regression suite also pins the current subdivided `74702`, `74711`, and `74714` routes so a partial menu observation cannot silently regress them again.

## Public contract and non-goals

No public MCP schema change is needed. `cal_text_page(file_id, subtext_id=None, page=1)` remains the only operation.

Out of scope:

- Mandaic collection discovery (#78/#83);
- token-analysis failures (#81);
- public structured error redesign (#84);
- route-probing requests at runtime;
- recursive catalogue/text traversal;
- redesign of CAL rendering-selector semantics.

## TDD target

The initial test-only RED proved at least:

1. `TextService.page("74501", page=1)` sends exactly one direct Mandaic request containing `cset=M` + `file=74501` and **no** `sub` or ordinary `page` parameter;
2. another representative direct `74...` ID not on the allowlist (`74717`) follows the same direct classification;
3. direct Mandaic `page=2` fails before transport;
4. `74410` and `74411` still use `sub=001` / specialized routing;
5. a non-Ginza subdivided allowlist member (`74401` / `74701`) also remains specialized, preventing a title-specific hack;
6. explicit public `subtext_id` and ordinary non-Mandaic request shapes remain unchanged.

The exact-head review then added a second test-only RED for the three omitted current subdivided routes `74702`, `74711`, and `74714`. Both dependency matrices passed installation/environment checks, Ruff lint, Ruff format, and strict mypy; pytest failed only those three routing expectations (latest-compatible: 712 passed / exactly 3 failed).

Normal CI remains offline.

## Research load

The implementation research used five fixed branch-only CAL GETs total: four menu/rendering requests while resolving route classification and one post-review direct-page request for `74717`. Each had a 15-second timeout and 512 KiB cap. No token, comment, next-page, catalogue-child, or other returned navigation link was followed.

The later exact-head review classified the previously omitted `747xx` rows from the same current menu's destination hrefs without traversing their text contents. Detailed review evidence is in `docs/research/issue-97-review-747xx-route-addendum.md`. Temporary research/helper workflows were removed after use.