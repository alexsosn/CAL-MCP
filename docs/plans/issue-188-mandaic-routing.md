# Issue #188 plan — restore Mandaic catalogue → subtext → page composition

Date: 2026-10-01. Research: `docs/research/issue-188-mandaic-routing.md`.

1. Preserve the current private Mandaic direct/subdivided file classification as routing metadata,
   including still-reachable legacy hidden subdivided IDs.
2. RED — top-level discovery:
   - current `cal_text_catalogue("74")` fixture must return the 12
     `showsubtexts.php` entries as categories and the 8 direct entries as texts;
   - route-link accounting must still fail closed if any current route vanishes from the parsed
     result.
3. RED — search composition:
   - a Mandaic text-search result whose route is `showsubtexts.php?subtext=<id>&cset=M/R`
     must return `category_id=<id>` and `follow_up_tool="cal_text_catalogue"`;
   - direct Mandaic `get_a_chapter.php` search results remain text-page follow-ups.
4. Add reduced current child-catalogue fixtures from the research evidence:
   - `74401`: sparse selectors `11,12,23...`;
   - `74421`: numeric selectors plus exact `col`;
   - `74430`: unpadded `1..5`.
5. RED — child catalogue parsing:
   - preserve exact `file_id`, `subtext_id`, rendered label and order;
   - validate child file/info identity and the evidence-backed Mandaic script selector;
   - accept `col` only on the Mandaic subtext path;
   - global/CPA subtext grammar still rejects `col`.
6. RED — subdivided page requests:
   - known subdivided Mandaic files require an explicit `subtext_id` before transport;
   - `74401/12` page 1 sends exact `sub=12` and no fabricated `sub=012`;
   - `74430/1` sends exact unpadded `sub=1`;
   - `74421/col` is accepted only because the requested file is Mandaic subdivided;
   - page 2 retains the exact subtext and adds private zero-based `page=1`.
7. RED — subdivided response/navigation:
   - freeze the current `74401/sub=12/page=1` Page-2 shape;
   - require page markers to drive public page/page_count;
   - previous/next links preserve the exact file, exact subtext and `cset=M`;
   - accept only the researched private pagination selectors (`page`, optional `clen=5`);
   - never derive a public page number from `sub`.
8. RED — direct current Mandaic pagination:
   - page 1 of a current direct file keeps `cset=M&file=<id>` with no invented subtext;
   - page 2 of current direct `74501` sends zero-based `page=1`;
   - freeze current Page-2 marker/navigation with empty `sub` and optional `clen=5`;
   - direct page numbers beyond the current marker range use the existing out-of-range semantics.
9. Backward compatibility:
   - `74700`, `74702`, `74714` remain subdivided;
   - `74711` remains classified as subdivided even though its current child catalogue is empty;
   - legacy direct `74717` remains page-1-only until evidence supports pagination;
   - ordinary non-Mandaic and CPA routing/tests remain unchanged.
10. GREEN with the narrowest internal changes:
    - top-level Mandaic parser returns categories vs direct texts according to the exact route;
    - Mandaic child links use a Mandaic-specific subtext parser;
    - service routing uses explicit Mandaic `subtext_id` plus ordinary private `page`, instead of
      synthesizing `sub` from public page;
    - direct current Mandaic files use an explicit evidence-backed paginated-direct set.
11. Update `docs/tools/texts.md`, `research.md`, `CHANGELOG.md`, and a durable decision note.
    Mark the #85/#97 page→sub assumption as superseded rather than silently rewriting history.
12. Run both CI matrices.
13. Installed-wheel/stdio live acceptance, bounded and sequential:
    - top-level `cal_text_catalogue("74")` reports 12 categories + 8 direct texts;
    - all 8 current direct texts open page 1;
    - `74501` opens page 2;
    - representative category round-trips cover sparse `74401/12`, offset `74422/106`,
      unpadded `74430/1`, and non-decimal `74421/col`;
    - no child catalogue or page is recursively prefetched.
14. Remove temporary workflows, run workflow-free CI on the exact final SHA, and perform a
    logically independent adversarial review. Every finding gets a plan amendment and
    RED → GREEN cycle before merge.

## Documentation-review follow-up — `74421/col` information identity

While updating the user workflow, discovery exposed one additional compositional invariant:
a child returned by `cal_text_catalogue("74421")` with `subtext_id="col"` must remain
followable by `cal_text_information`, not only by `cal_text_page`.

- RED `4178af08`: `cal_text_information("74421", subtext_id="col")` was rejected before
  transport, while a non-Mandaic `col` control remained invalid.
- GREEN `0f68d9dc`: known subdivided Mandaic files use the same evidence-backed selector
  validator for text information; ordinary and CPA grammar is unchanged.
- Final installed-stdio acceptance includes one `74421/col` information call. With the
  original catalogue/page matrix this raises the explicit acceptance budget from 18 to
  **19 sequential logical CAL requests**, with no recursion or page enumeration.

## Post-#218 integrated acceptance — returned Mandaic token coordinates

Issue #218 was discovered by the first #188 live acceptance when current direct file `74425`
returned evidence-backed alphanumeric token coordinates. PR #219 researched, tested, reviewed,
and merged the exact file-scoped `74425` / `74429` coordinate handling into this branch.

The final #188 installed-stdio acceptance therefore keeps the existing 19-call catalogue/page/
information matrix and adds **one** explicit `cal_token_analysis` follow-up using an alphanumeric
coordinate already returned by the `74425` page-1 call. It does not add another page request.

Final hard cap: **20 sequential logical CAL requests**:
- 1 category-74 catalogue;
- 8 current direct page-1 reads;
- 1 direct `74501` page-2 read;
- 4 child-catalogue + selected-page round-trips = 8 requests;
- 1 `74421/col` text-information follow-up;
- 1 token-analysis follow-up from the already-returned `74425` token.

The acceptance must also assert that `74429` page 1 contains its researched uppercase-`A`
coordinate family and that the selected `74425` alphanumeric coordinate is preserved unchanged
through `cal_token_analysis`.

## Adversarial-review amendment — direct pagination must be file-evidenced

Exact-head review found that the first GREEN allowed `page>1` for all eight current direct
Mandaic files even though research had demonstrated current pagination only for `74501`.

Installed-stdio audit run `37066672702` made exactly eight page-2 calls and showed:

- `74501`: genuine Page 2 of 11, total 246 lines, previous 1, next 3;
- `74420`, `74425`, `74426`, `74429`, `74431`: adapter returned `page=2` while CAL
  supplied no page count, line total, previous, or next navigation;
- `74424`, `74427`: page-2 requests reached CAL but failed parser validation.

The successful no-metadata cases are unsafe: `_parse_text_page` was assigning the requested page
number whenever a Mandaic response lacked page-count markup, so an upstream page that ignored the
private `page` selector could be mislabeled as a real page 2.

Review RED → GREEN:

15. RED: for current direct files `74420`, `74424`, `74425`, `74426`, `74427`,
    `74429`, and `74431`, public `page=2` must fail locally before transport.
16. Preserve the positive control: `74501` page 2 still sends private zero-based `page=1`.
17. GREEN: scope the evidence-backed paginated-direct set to exactly `{"74501"}`.
    All other current direct Mandaic files remain readable on page 1.
18. Update R-056/D-019 and user documentation so they do not imply that catalogue membership
    proves pagination.
19. Rerun both CI matrices and repeat the same bounded 20-call final acceptance; no extra live
    pagination requests are needed because the negative page-2 behavior is a local validation
    invariant covered by RED.
20. Remove all temporary workflows and perform a fresh exact-head adversarial review before merge.

