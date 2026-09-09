# Issue #97 adversarial-review addendum — current 747xx Mandaic routes

**Rechecked:** 2026-09-09.

## Why this addendum exists

The first issue-97 implementation review used a partial live menu observation plus a few browser/index examples to build `_MANDAIC_SUBDIVIDED_FILE_IDS`. An independent exact-head review of PR #99 found that this set was still incomplete for the current CAL menu.

The authoritative current menu is:

- https://cal.huc.edu/show_Mandaic.php?R1=74

The review re-opened that menu and inspected the destination hrefs for the additional `747xx` rows that had not been classified by the earlier 20-row branch probe. The review did not recursively traverse their contents; route classification comes from the menu's own links.

## Current 747xx route classification

Current menu rows `74700` through `74723` are mixed.

### Subdivided — `showsubtexts.php?cset=M&subtext=<file>`

```text
74700
74701
74702
74711
74714
```

### Direct — `get_a_chapter.php?cset=M&file=<file>`

```text
74703
74704
74705
74706
74707
74708
74709
74710
74712
74713
74715
74716
74717
74718
74719
74720
74721
74722
74723
```

The existing focused research had already classified `74700`/`74701` as subdivided and `74716`/`74717` as direct. The newly material review findings are therefore the missing subdivided IDs:

```text
74702
74711
74714
```

Representative current link evidence observed from the menu:

- `74702 MandAmulets` -> `showsubtexts.php?cset=M&subtext=74702`
- `74711 Mandaic Magic Bowls (Moriggi)` -> `showsubtexts.php?cset=M&subtext=74711`
- `74714 Phylacteries (zaraziata)` -> `showsubtexts.php?cset=M&subtext=74714`
- neighboring direct rows such as `74703`, `74710`, `74713`, `74716`, `74718`, and `74723` -> `get_a_chapter.php?cset=M&file=<file>`

## Consequence

The PR head reviewed at `20617ad6606d4b6aa55b1a4436dba3f89ee8cb53` omitted `74702`, `74711`, and `74714` from `_MANDAIC_SUBDIVIDED_FILE_IDS`. Those files therefore took the direct route and were misrouted relative to current CAL navigation.

The correction remains the same architectural policy already chosen by issue #97: maintain a private current subdivided-file allowlist because no arithmetic/prefix rule predicts route kind, and default other `74...` files to the direct page-1 route. The review does **not** justify a `747xx` prefix rule.

## Review-regression requirement

Before production changes:

1. extend the deterministic route-scope regression so `74702`, `74711`, and `74714` must emit the specialized `sub=001` request;
2. demonstrate RED with static/type gates green and pytest failing only on these missing current routes;
3. add only those three IDs to the private allowlist;
4. rerun both CI dependency matrices;
5. perform a fresh exact-head adversarial review.

## CAL load impact

This review was bounded to the already identified current Mandaic menu route family. It inspected the menu and its link destinations to classify the previously unaccounted `747xx` rows; it did not enumerate text content, chapters, tokens, comments, or lexical links and introduced no runtime probing or fallback behavior.
