# Issue #172 research — `cal_syriac_group` and CAL's current card layout

Date: 2026-09-30. Base: `61e69ad`.

## Trigger

The 2026-09-25 user-level end-to-end run (#15) found that `cal_syriac_group` fails for every group tried with `parser_drift` "CAL Syriac category row has ambiguous navigation semantics". Groups `60420` (EphPar, from `metrical-homilies-hymns`) and `61000` (Old Syriac inscriptions, from `inscriptions`) were tried.

## Live-current evidence

Two bounded GETs of the tool's own request, `showsubtexts.php?keyword=<group>`, through the production client on 2026-09-30:

| Group | Cards | Child link | Card info link |
| --- | --- | --- | --- |
| `60420` | 15 | `get_a_chapter.php?file=60420&sub=01&cset=S` "hymn 1" | `coord=60420` (the group) |
| `61000` | 80 | `get_a_chapter.php?file=61000&sub=001&cset=S` "Drijvers.1=OS.As55= Birecik" | `coord=61000001` (file + sub) |

Both pages have the same structure:

```html
<div class="script-toggle"> … <a class="script-toggle-opt active" data-cset="S" href="/showsubtexts.php?subtext=60420&script=S">Syriac</a>
  <a class="script-toggle-opt" data-cset="R" href="/showsubtexts.php?subtext=60420&script=R">Roman</a></div>
<details class="dialect-group">
  <summary><span>EphPar</span> <a class="info-link" href="/get_file_info.php?coord=60420&return=…">&#9432;</a></summary>
  <ul>
    <li><a class="book-link" href="/get_a_chapter.php?file=60420&sub=01&cset=S">hymn 1</a>
        <a class="info-link" href="/get_file_info.php?coord=60420&return=…">&#9432;</a></li>
    …
```

Each page has one `details.dialect-group`, no `single-entry-row` (a class CAL's CSS defines), and page chrome links (`cal-nav-link`, logo). The script toggle's `showsubtexts.php?subtext=…&script=…` links are presentation controls, not children. The `keyword` request still returns the group.

## Findings

- A group's children are subtexts of one file. The old line parser saw all cards as a single ambiguous row, and its item model had no subtext, so children sharing a file id would also collide.
- The card info link's coordinate is either the file id or the file id plus the submitted sub, as on text pages (R-039).

## Consequences

- Group pages in the card layout are parsed by a dedicated structural parser:
  - The script toggle is ignored, but its links must name the group, with a script `S` or `R`.
  - The summary's info link must name the group.
  - Each `li` must hold exactly one `book-link` (`get_a_chapter.php` with `file`, a decimal `sub` and `cset`) and at most one `info-link`, whose coordinate is the file or file + sub.
  - Any other link or class inside the group, a repeated (file, sub), or a page with no cards fails closed.
- Items gain `subtext_id`, which is `null` for items without one (the catalogue path is unchanged). A card child is `navigation_kind: "text"` with `upstream_id` = the file and `subtext_id` = CAL's `sub`, followed with `cal_text_page(file_id, subtext_id=…)`.
- Production requests are unchanged.

## Review follow-up (2026-09-30)

The review made two more bounded GETs of groups taken from `cal_syriac_texts` results: `63400` (JS, 15 cards) and `61200` (Syriac coins, 4 cards). Both have the same card structure. On all four observed pages every card's file is the group id, and no card carries text outside its links. The parser now accounts for every link and every piece of text by its place: banner navigation (`javascript:history.back()`, `/newtextmenu.html`, `/`), the page title, the toggle label, the summary label, and the cards. Everything else fails closed, so content is never dropped silently: text in a card outside its links, a link or text elsewhere, a second group, an empty summary label, a card for another file, or a card script other than `S`/`R`. The document head is ignored. The group marker is recognised whatever the `details` element's other attributes or classes.

## Final installed-stdio acceptance

Run `36832851364` rebuilt and installed the candidate and exercised the public MCP server over
stdio with four bounded live CAL requests:

- `cal_syriac_group("60420")` → 15 ordered children; first child `subtext_id="01"`;
- `cal_syriac_group("61000")` → 80 ordered children; first child `subtext_id="001"`;
- `cal_text_page("60420", subtext_id="01", page=1)` → `status=found` with lines;
- `cal_text_page("61000", subtext_id="001", page=1)` → `status=found` with lines.

The run followed no other group children and performed no recursive enumeration.

