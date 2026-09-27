# Issue #170 research — Christian Palestinian Aramaic alphanumeric subtext IDs

Date: 2026-09-26. Base: `5a354678`.

## Trigger

The 2026-09-25 installed-stdio end-to-end run found that
`cal_text_catalogue(category_id="55")` fails closed because CAL's Christian Palestinian
Aramaic catalogue returns alphanumeric `sub` selectors while CAL-MCP currently requires every
identifier to be decimal.

## Current CAL evidence

Rechecked live on 2026-09-26.

The current catalogue is:

- `https://cal.huc.edu/showsubtexts.php?subtext=55`

Its first text route is currently:

- `https://cal.huc.edu/get_a_chapter.php?file=55000&sub=01001a&cset=C`
  — “Gen 19 Damascus frag V”.

The returned text page is live and renders the expected file identity `55000`. Its navigation
continues through CPA selectors such as `01002a` and keeps `cset=C`.

The corresponding information route works with the composed alphanumeric coordinate:

- `https://cal.huc.edu/get_file_info.php?coord=5500001001a`

Current catalogue evidence and the 2026-09-25 capture show values including
`01001a`, `01001b`, `01001c`, `01002a`, `02003a`, and `03007a`.

## Subtext identifier contract

Only **subtext IDs** widen. The researched public/upstream shape is:

```text
decimal digits + optional single lowercase ASCII letter suffix
```

Equivalent regex:

```text
^[0-9]+[a-z]?$
```

Examples accepted as subtext IDs: `112`, `001`, `01001a`.

Examples still rejected: `a01001`, `01001ab`, `01001A`, `01-001a`, whitespace,
empty strings, and arbitrary URLs/strings.

File IDs, category IDs, text IDs and page numbers remain decimal-only unless separate researched
CAL evidence proves otherwise.

## Live amendment — CPA machine coordinates carry the subtext suffix

The first installed-stdio acceptance run on 2026-09-26 successfully parsed the CPA catalogue and
made the requested page GET, but `cal_text_page("55000", subtext_id="01001a")` still failed with
`CAL returned a non-decimal coordinate`.

A bounded follow-up structural probe made one GET to the same current CPA page and retained only
link-route coordinate metadata, not scholarly text. Current CAL exposes:

- `get_file_info.php`: `coord=5500001001a`;
- `getlex.php`: coordinates such as `5500001001a019001`,
  `5500001001a019002`, ...;
- `comment.php`: coordinates such as `5500001001a019002`.

The observed token/comment machine-coordinate shape is therefore the requested composed
`file_id + subtext_id` prefix followed by a non-empty decimal line tail. In generic form the
currently observed machine-coordinate grammar is either all-decimal or
`^[0-9]+[a-z][0-9]+$` (one embedded lowercase ASCII letter).

This matters for two public surfaces:

1. `cal_text_page` must preserve those current token/line coordinates rather than reject them;
2. `cal_token_analysis` must accept the same coordinate it just returned, otherwise CPA tokens
   cannot be followed up.

`cal_text_line_comments` already accepts bounded ASCII alphanumeric coordinates and therefore
does not need widening for this evidence.

The final installed-stdio acceptance call then submitted the first returned CPA token
(`5500001001a019001`, word 0) to `cal_token_analysis`. The input was accepted, CAL was reached,
and CAL answered HTTP 200. Parsing then failed closed with
`CAL token-analysis result marker is not followed by a candidate`. That is a separate
token-analysis result-shape problem, not an identifier/routing failure; the evidence has been added
to existing release blocker #179 for bounded investigation there.

For a suffix-bearing text page, CAL-MCP should additionally require every token/line machine
coordinate to start with the exact requested `file_id + subtext_id` prefix. That keeps the new
acceptance narrow: an unrelated alphanumeric coordinate on a CPA page remains parser drift.

## Current implementation impact

### `src/cal_mcp/texts.py`

- `_text_ref_from_link` originally parsed returned `sub` with the decimal helper;
- `TextService.page` and `TextService.information` originally validated caller `subtext_id`
  as decimal;
- `_page_navigation` originally parsed returned ordinary-route `sub` as decimal;
- `_page_text_ref` originally parsed the returned file-information `coord` as decimal before
  comparing it with `file_id + submitted_sub`; the current branch already compares against the
  exact accepted file/subtext identity;
- token and line-coordinate parsing still assumes decimal and must be widened only to the newly
  observed machine-coordinate grammar, with an exact CPA prefix check.

This paragraph's initial routing hypothesis was superseded by the two adversarial-review
amendments below. Current CPA routing is file-identity based: all observed CPA text routes retain
`cset=C`, including suffix-bearing subdivided, decimal subdivided, and direct texts.

The information request itself needs no extra script selector: current CAL accepts
`get_file_info.php?coord=5500001001a`.

### `src/cal_mcp/token_analysis.py`

Public token-analysis input currently rejects the alphanumeric machine coordinate returned by a
CPA text page before transport. It should accept only the same narrow decimal-or-one-embedded-
lowercase-letter machine-coordinate grammar.

### `src/cal_mcp/concordance.py`

- `ConcordanceService.kwic_full_context` originally validated caller `subtext_id` as decimal;
- full-context response URL validation originally parsed returned `sub` as decimal;
- KWIC hit parsing used the decimal-only optional `sub` query helper.

These use the same subtext-ID grammar while file IDs and target coordinates remain decimal in #170.
Issue #181 separately covers full-context behavior for subdivided texts.

## Design consequence

Keep two distinct shared predicates:

- subtext ID: `^[0-9]+[a-z]?$`;
- machine coordinate: decimal, or one embedded lowercase ASCII letter followed by a non-empty
  decimal tail.

Text and token-analysis services wrap the machine-coordinate predicate in their own typed
public/parser errors. Generic decimal-ID helpers remain unchanged.

## TDD boundary

The initial RED, committed before the first implementation, proved:

1. a current CPA catalogue link with `sub=01001a&cset=C` fails on main;
2. `TextService.page("55000", subtext_id="01001a")` is locally rejected before transport;
3. `TextService.information(..., "01001a")` is locally rejected;
4. `kwic_full_context(..., subtext_id="01001a")` is locally rejected;
5. malformed near-miss subtext IDs remain rejected;
6. decimal subtext behavior remains unchanged.

After live acceptance exposed machine-coordinate drift, a second RED must be recorded before the
coordinate implementation:

7. the CPA page fixture uses the observed `5500001001a019001` token coordinate and fails on the
   current decimal-only page parser;
8. token analysis rejects that returned coordinate before transport;
9. malformed broader alphanumeric coordinate shapes remain rejected.

## Request/data impact

No extra hidden requests or traversal. Each operation retains its existing request bound. A page
call for an evidence-backed current CPA file adds only the private `cset=C` selector to the same
one request; no discovery request is performed at runtime. No CAL corpus data is bundled.

## Adversarial review amendment — CPA decimal subtexts also require `cset=C`

A fresh one-request structural review of the complete current category-55 catalogue on 2026-09-27
checked only `get_a_chapter.php` selectors, without retaining scholarly text. It found **551**
direct text routes:

- **150** suffix-bearing subtexts, all `file=55000`, all with exact selector set
  `file,sub,cset` and `cset=C`;
- **401** decimal subtexts, also all with exact selector set `file,sub,cset` and `cset=C`,
  across current files
  `55001`, `55003`, `55006`, `55007`,
  `55400`–`55405`, and `55420`–`55423`.

Example current decimal CPA route: `file=55001&sub=002&cset=C` (CPA Psalms chapter 2).

This disproves the intermediate implementation assumption that a lowercase suffix itself is the
private routing discriminator. The suffix determines the widened public identifier grammar and the
machine-coordinate prefix behavior, but **CPA page routing must be selected by the current CPA file
identity**, including decimal subtexts.

Implementation consequence:

- keep the shared subtext grammar unchanged;
- introduce a current evidence-backed CPA file allowlist for text-page routing, analogous to the
  existing evidence-backed Mandaic per-file routing table;
- for any allowlisted CPA file with a public subtext, submit `cset=C`;
- validate current CPA catalogue/page-navigation links with exact `cset=C` selector semantics
  regardless of whether that particular subtext has a suffix;
- do not infer CPA routing from the generic `55` prefix or from “has a suffix” alone.

The review probe made exactly one CAL GET to the category-55 catalogue.

## Second adversarial review amendment — CPA also has four direct `cset=C` texts

The category-55 live MCP acceptance returned 555 text references, while the complete subtext-route
audit accounted for 551. A second one-request structural review resolved the four remaining
`get_a_chapter.php` routes. They are direct CPA texts with no `sub` selector:

- `file=55002&cset=C`;
- `file=55406&cset=C`;
- `file=55407&cset=C`;
- `file=55430&cset=C`.

All four use the exact selector set `file,cset` and `cset=C`.

This changes the routing model again: the current CPA catalogue has **551 subdivided routes**
(`file,sub,cset=C`) and **4 direct routes** (`file,cset=C`). The adapter therefore needs
separate evidence-backed CPA subdivided/direct file sets (or equivalent exact semantics), with
`cset=C` on both route families. A direct CPA follow-up must not be sent as the generic
`file,page` route without the CPA rendering selector.

The review probe made exactly one CAL GET and retained only route selectors.

## Direct-route parser boundary

Installed-stdio verification of representative direct CPA file `55002` submitted the corrected
route `get_a_chapter.php?file=55002&cset=C&page=0` and received HTTP 200. Parsing then failed
closed with `CAL text page contains no recognizable coordinate/token rows`.

A bounded structural follow-up showed that the current page does contain a `text-display` table,
but its relevant structure has one `tr`, two `bdo` elements and one `span.psyr`, with no
`td` elements and no `getlex.php`/`bablex.php` links. This is a linkless/unlemmatized text
layout and belongs to release blocker #185, whose scope already covers CAL pages with scholarly
text but no machine token links.

Therefore #170 owns discovery, identifier preservation, and exact private CPA routing. For direct
CPA routes, live acceptance proves that the correct `cset=C` request reaches CAL; reading the
linkless returned content is deliberately deferred to #185's independent research/TDD/review loop.
Suffix-bearing `55000/01001a` and decimal-subtext `55001/002` both parse successfully today.
