# Issue #85 research — Mandaic text-page routing and token links

Date: 2026-09-08
Baseline: `main` at `d704ee5c2b542e22c22a3929771fa466dea0a0f6`

## Question

Why does `cal_text_page(file_id="74410", page=1)` fail for Ginza Rabba Right Side even though CAL serves the bounded page, and what is the smallest compatible fix that preserves the existing public tool and one-request policy?

## Current adapter behavior

`TextService.page()` currently assumes CAL's ordinary text-browser route for every file:

- `GET get_a_chapter.php`;
- `file=<CAL file id>`;
- optional caller `sub=<subtext_id>`;
- `page=<public page - 1>`.

`parse_text_page()` recognizes lexical token links only when their path ends in `bablex.php`. Navigation is likewise modeled around ordinary `get_a_chapter.php?...&page=<zero-based>` links.

That contract works for existing ordinary fixtures such as BT AZ and the unpaginated Tel Dan page, but it does not match CAL's current Mandaic browser.

## Current CAL Mandaic route evidence

The current specialized Mandaic menu is `show_Mandaic.php?R1=74`. It lists Ginza Rabba Right Side as file `74410`, Ginza Rabba Left Side as `74411`, and the other currently exposed Mandaic files under the same `74...` namespace.

The rendered file links use the specialized route, for example:

- `showsubtexts.php?cset=M&subtext=74410`;
- `showsubtexts.php?cset=M&subtext=74411`.

The current chapter list for Ginza Rabba Left Side labels page 1, page 2, and later pages explicitly. Those page links resolve as:

- page 1 -> `get_a_chapter.php?cset=M&file=74411&sub=001`;
- page 2 -> `get_a_chapter.php?cset=M&file=74411&sub=002`.

The issue #85 source check establishes the same route for Ginza Rabba Right Side page 1:

- `get_a_chapter.php?cset=M&file=74410&sub=001`.

Search-indexed current CAL output also exposes Right Side page 290 at `get_a_chapter.php?cset=M&file=74410&sub=290`, confirming that Mandaic `sub=NNN` is the displayed page selector rather than the ordinary text-browser `page=` parameter.

Therefore for current CAL Mandaic text identifiers in collection `74`, the existing MCP one-based page parameter can map directly to a zero-padded upstream `sub` selector while adding `cset=M`.

## Current CAL Mandaic lexical-link evidence

A current indexed Mandaic page (`74713: Qmaha D-Shiul`) is rendered by `get_a_chapter.php?cset=M&file=74713`. Its words are linked for lexical analysis, but the token links use:

- `getlex.php?coord=<coordinate>&word=<zero-based-index>`

not `bablex.php`.

For example, the rendered word `marai` on line 01 links to `getlex.php?coord=7471301&word=0`.

The current text parser accepts only `bablex.php`, so even a correctly routed Mandaic page can be reduced to zero recognizable token rows and fail with `TextParseError("CAL text page contains no recognizable coordinate/token rows")`.

## Public-contract constraint

Issue #85 does not require a new tool or a new public argument. `cal_text_page(file_id, subtext_id=None, page=1)` should continue to perform exactly one CAL request.

The smallest compatible internal distinction is a Mandaic page route selected from CAL's current collection namespace:

- ordinary route: existing `file` / optional `sub` / zero-based `page` behavior;
- Mandaic collection-74 route when `file_id` starts with `74` and no explicit public `subtext_id` is supplied: `cset=M`, `file=<id>`, `sub=<page as at least three digits>`.

This uses the current CAL collection identifier hierarchy rather than a per-title exception. It does not enumerate the Mandaic catalogue and adds no discovery request.

If a caller explicitly supplies `subtext_id`, keep the existing ordinary route in this ticket rather than guessing whether that caller intends CAL's specialized page selector. Specialized collection discovery/typed route metadata belongs to the separate catalogue/discovery backlog (#78/#83).

## Parser boundary

For Mandaic-routed pages:

- `getlex.php` must be recognized as a lexical-token endpoint alongside the existing `bablex.php` endpoint;
- its `coord` and `word` query values use the same typed token model and validation;
- the absolute lexical URL must preserve the actual upstream endpoint;
- if the page has no ordinary `Page N of M` marker, the adapter may use the explicit caller page as the observed page only because the request itself uses the researched one-to-one `sub=NNN` page selector;
- any specialized previous/next links using `sub=NNN` may be interpreted only as adjacent page navigation for the same `cset=M` and file; do not invent a total page count if CAL does not render one.

Ordinary-route navigation validation must remain unchanged.

## TDD target

A reduced Mandaic fixture should model only the semantics needed by the parser:

- file-info link for `74410`;
- one or two `001:NN` lines;
- `getlex.php` token links with decimal coordinates and zero-based word indices;
- an optional same-file `cset=M` next-page link using `sub=002` if needed to freeze specialized navigation behavior.

The initial service regression must prove current production sends the wrong request for `file_id="74410", page=1`. Static/type gates must pass and pytest failures must be confined to the new Mandaic route/token expectations before production changes.

## Non-goals

- No recursive Mandaic catalogue enumeration.
- No second CAL request to discover the route.
- No new public tool or collection parameter.
- No Mandaic-script rendering endpoint (`manget_a_chapter.php`) in this ticket.
- No automatic token analysis; token URLs remain metadata for explicit follow-up.
- No changes to ordinary text-page request shape unless a regression proves they are required.
- No attempt to solve the separate Ginza text-search/catalogue-discovery tickets (#78/#80/#83).

## Load policy

Normal tests remain offline. Research used only current indexed CAL pages/menu evidence plus the exact page already identified in issue #85; no crawl or page enumeration was performed. A direct container probe was attempted once but failed before DNS resolution and therefore generated no CAL request.

## Conclusion

Issue #85 is a route-family plus token-link compatibility bug, not evidence that Ginza is absent. The Mandaic collection uses `cset=M` with one-based `sub=NNN` page selectors and `getlex.php` lexical links, while CAL-MCP currently assumes ordinary zero-based `page=` routing and `bablex.php` tokens. The fix can remain internal, bounded to one request, and preserve the existing public `cal_text_page` contract.