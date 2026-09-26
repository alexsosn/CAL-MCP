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

The returned text page is live and renders the expected file identity `55000` and CPA text
lines. Its navigation continues through CPA selectors such as `01002a` and keeps `cset=C`.

The corresponding information route works with the composed alphanumeric coordinate:

- `https://cal.huc.edu/get_file_info.php?coord=5500001001a`

Current catalogue evidence and the 2026-09-25 capture show values including
`01001a`, `01001b`, `01001c`, `01002a`, `02003a`, and `03007a`.

## Identifier contract

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

## Live amendment — CPA machine coordinates also carry the subtext suffix

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
current accepted machine-coordinate grammar can be represented narrowly as either all-decimal or
`^[0-9]+[a-z][0-9]+# Issue #170 research — Christian Palestinian Aramaic alphanumeric subtext IDs

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

The returned text page is live and renders the expected file identity `55000` and CPA text
lines. Its navigation continues through CPA selectors such as `01002a` and keeps `cset=C`.

The corresponding information route works with the composed alphanumeric coordinate:

- `https://cal.huc.edu/get_file_info.php?coord=5500001001a`

Current catalogue evidence and the 2026-09-25 capture show values including
`01001a`, `01001b`, `01001c`, `01002a`, `02003a`, and `03007a`.

## Identifier contract

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

 (one embedded lowercase ASCII letter).

This matters for two public surfaces:

1. `cal_text_page` must preserve those current token/line coordinates rather than reject them;
2. `cal_token_analysis` must accept the same coordinate it just returned, otherwise CPA tokens
   cannot be followed up.

`cal_text_line_comments` already accepts bounded ASCII alphanumeric coordinates and therefore
does not need widening for this evidence.

The page parser should still cross-check suffix-bearing coordinates against the exact requested
`file_id + subtext_id` prefix, so an unrelated alphanumeric coordinate on a CPA page fails
closed.

## Current implementation impact

The decimal-only assumption appears in more places than the catalogue parser:

### `src/cal_mcp/texts.py`

- `_text_ref_from_link` parses returned `sub` with `_parse_id`;
- `TextService.page` and `TextService.information` validate caller `subtext_id` with
  `_validate_id`;
- `_page_navigation` parses returned ordinary-route `sub` with `_parse_id`;
- `_page_text_ref` originally parsed the returned file-information `coord` as decimal before
  comparing it with `file_id + submitted_sub`; the current branch now compares against the
  exact accepted file/subtext identity;
- token and line-coordinate parsing still assumes decimal and must be widened only to the newly
  observed machine-coordinate grammar, with an exact CPA prefix check.

For an alphanumeric subtext request, the page request should preserve CAL's current CPA rendering
selector `cset=C`. This is inferred only from the researched alphanumeric CPA selector shape;
ordinary decimal subtexts keep their existing route.

The information request itself needs no extra script selector: current CAL accepts
`get_file_info.php?coord=5500001001a`.

### `src/cal_mcp/token_analysis.py`

- public token-analysis input currently rejects the alphanumeric machine coordinate returned by
  a CPA text page before transport;
- it should accept only the same narrow decimal-or-one-embedded-lowercase-letter machine-coordinate
  grammar.

### `src/cal_mcp/concordance.py`

- `ConcordanceService.kwic_full_context` validates caller `subtext_id` as decimal;
- full-context response URL validation parses returned `sub` as decimal;
- KWIC hit parsing uses the decimal-only optional `sub` query helper.

These should use the same subtext-ID grammar while file IDs and target coordinates stay decimal.

Issue #181 separately covers full-context behavior for subdivided texts; #170 only removes the
incorrect identifier rejection and keeps existing full-context semantics otherwise unchanged.

## Design consequence

Introduce one small shared identifier predicate/validator for the subtext grammar so `texts.py`
and `concordance.py` cannot drift into different accepted languages. Each service keeps its own
typed public/parser error class around that shared predicate.

Do not broaden the generic decimal-ID helpers.

## TDD boundary

RED should prove all of the following before production changes:

1. a reduced current CPA catalogue link with `sub=01001a&cset=C` fails on main;
2. `TextService.page("55000", subtext_id="01001a")` is locally rejected before transport on main;
3. `TextService.information(..., "01001a")` is locally rejected on main;
4. `kwic_full_context(..., subtext_id="01001a")` is locally rejected on main;
5. malformed near-miss subtext IDs remain rejected;
6. decimal subtext behavior remains unchanged;
7. a CPA page fixture carrying the observed alphanumeric token coordinate fails on the current
   decimal-only coordinate parser;
8. token analysis rejects that returned coordinate before transport on the current implementation.

## Request/data impact

No extra hidden requests or traversal. Each operation retains its existing request bound. The CPA
page call adds only the current `cset=C` selector to the same one request when the subtext ID has
the researched lowercase suffix. No CAL corpus data is bundled.
