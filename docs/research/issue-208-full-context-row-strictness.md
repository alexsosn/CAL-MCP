# Issue #208 research — strict KWIC full-context text rows

Date: 2026-10-01. Base: `9d087a9e`.

## Trigger

`cal_kwic_full_context` and `cal_text_page` both return `TextLine`, but their row parsers
currently enforce different structural guarantees. Issue #208 records three offline mutations of
the current full-context captures that the full-context parser accepts although the text-page
parser rejects them.

No live request is required for this repair: all positive evidence is already retained in current
reduced fixtures.

## Current fixture surface

The repository has current/recent full-context captures covering both lexical-link families and
multiple CAL script selectors:

- Samaritan `56000/112` — Roman (`R`), `getlex.php`;
- Biblical Aramaic Ezra `31000/4` — Hebrew (`H`), `getlex.php`;
- Syriac Roman-law text `60301/53` — Unicode Syriac (`U`), `getlex.php`;
- Babylonian Talmud `71002/01051` — Hebrew (`H`), `bablex.php`;
- Tel Dan controls — Roman and Hebrew.

The repair must keep all current captures green.

## Gap 1 — loose text between lexical anchors is flattened into the row

The shared concordance `_TableHTMLParser` stores one flattened `_TableCell.text` plus its links.
`handle_data` appends every text node in a cell to `_cell_parts`, whether the text is inside a
lexical anchor or loose between anchors.

`_parse_full_context_row` validates the link set, then returns that flattened cell text as
`TextLine.text`. Consequently inserting unlinked `LOOSE` text between two lexical token anchors
changes the returned scholarly text without a parser error.

The text-page parser keeps loose parts separate from links and fails closed on loose text in a
linked row. Full-context should use the same semantic boundary.

## Gap 2 — unknown elements inside text cells disappear structurally

`_TableHTMLParser` has no tag allow-list. Apart from `tr`, `td`/`th`, and `a`, start/end
tags are ignored while their text children continue into the flattened cell. A tag-shaped
editorial string such as `<wmr>` can therefore be interpreted as markup and vanish from the
returned text.

The current text-page parser explicitly permits only CAL's observed row markup
(`a`, `span`, `cal-variant`, and row/table structure) and rejects unknown elements so that
unescaped scholarly angle brackets cannot be silently lost. Full-context rows need the same
fail-closed rule.

## Gap 3 — route validation is basename-only

Concordance `_is_path(href, filename)` compares only the last URL path segment.
`_cal_navigation_url` verifies same origin and then calls that helper. Thus a same-origin path
such as `/evil/bablex.php?...` passes as a `bablex.php` lexical link.

The helper also does not reject a fragment, so a link such as
`bablex.php?coord=...&word=0#unexpected` is preserved in `lexical_url` even though the
evidence-backed CAL endpoint has no fragment.

For full-context lexical and comment links, the accepted paths should be exact CAL-root paths
(`getlex.php`, `bablex.php`, `comment.php`) with no fragment. Existing exact selector-set,
coordinate, word-index and origin validation remains unchanged.

## Implementation boundary

This issue should not globally tighten every use of concordance `_is_path`; that helper is used
by unrelated historical/current parsers whose route evidence was reviewed separately.

The narrow repair is:

1. retain enough cell structure for full-context rows to distinguish linked token text from loose
   text and to detect unexpected tags;
2. apply the row checks only at the full-context text-row boundary;
3. require exact root paths and no fragments when turning full-context lexical/comment links into
   URLs;
4. preserve current Hebrew terminal-empty-anchor handling and current `cal-variant` text;
5. keep result schemas and request count unchanged.

## TDD boundary

RED must independently prove rejection of:

- loose text between lexical links;
- an unknown element inside a lexical token;
- a same-origin nested lexical path such as `/evil/bablex.php`;
- a lexical URL fragment;
- the equivalent malformed `getlex.php` path, so the fix is not BT-specific.

Positive controls must cover every retained full-context fixture family.

## Request/data impact

No production request changes and no new live research. One explicit full-context call remains one
bounded CAL request; no links are followed automatically.
