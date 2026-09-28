# Issue #185 research — unlemmatized/plain CAL text rows

Date: 2026-09-28. Base: `89b47ccf`.

## Trigger

CAL catalogues expose texts whose current `text-display` rows contain rendered scholarly text but
no `getlex.php` / `bablex.php` token links. The current table parser requires token links and
therefore rejects those rows even though their text is directly present in CAL.

The original issue evidence was Mandaic file `74420`. Issue #170 later found a structurally
different direct CPA page. Because that CPA evidence had already drifted by 2026-09-28, the
layouts were rechecked before choosing a schema.

## Bounded live research

Research used fixed GETs only, with hard response caps and no link traversal. The scope expanded
beyond the issue's initial “about four GETs” because the previously observed CPA page `55002`
changed upstream and because comment links turned out to affect coordinate semantics.

Runs:

- `36476352778`: four-page structural comparison;
- `36476455486`: one fixed follow-up of CPA `55002`;
- `36476596938`: four direct-CPA structural audit;
- `36476799822`: one fixed `55430` row-shape check (its failed assertion exposed exceptional
  comment-linked rows and was research evidence, not a product test);
- `36476900437`: one fixed `55430` exceptional-row classification;
- `36476991388`: two fixed plain-row coordinate-link audits (`74420`, `55430`).

No crawl or pagination sweep was performed and no full scholarly text was retained in the research
record.

## Current Mandaic evidence

Current route:

```text
get_a_chapter.php?cset=M&file=74420&page=0
```

The `text-display` table contains **46 actual text rows** before CAL starts its next navigation
table. Each text row has exactly two `td` cells and no lexical token links.

The first cell is the display coordinate; the second contains rendered text. The original
2026-09-25 capture remains representative:

```html
<tr><td valign="top">par. 104 </td><td>…plain rendered text…</td></tr>
```

The structural research parser initially counted a 47th `td0` row because CAL leaves
`text-display` unclosed; this is navigation after the next `<table>`, not mixed text content.
The production `_TextTableParser` already ends the text table at the next table start.

Three of the 46 current rows make the display coordinate a comment link:

- `par. 129` → `comment.php?coord=744202129`;
- `par. 131` → `comment.php?coord=744202131`;
- `par. 143` → `comment.php?coord=744202143`.

The other rows expose no machine/line coordinate at all.

## Controls and mixed-page question

The same four-page structural comparison checked:

- direct Mandaic `74501`: 24 actual text rows, all lexical/linked;
- Peshitta `62057`: 25 actual text rows, all lexical/linked.

The apparent extra linkless row in each raw structural count was again navigation after CAL's
unclosed text table. No sampled actual text table mixed lexical rows with plain rows.

Therefore there is **no evidence-backed mixed-table semantics**. A table containing both linked
text rows and plain text rows should fail closed until CAL demonstrates such a page.

## Current direct CPA evidence

A complete audit of the four current direct CPA files from #170 found three distinct states:

- `55406`: lemmatized/linked (247 lexical links on the sampled page);
- `55407`: lemmatized/linked (211 lexical links);
- `55430`: current plain/unlemmatized text;
- `55002`: current `text-display` shell contains no non-empty text and no lexical links.

The `55002` state is not a plain row and is now tracked independently by #196. It must not be
turned into a successful empty line under #185.

### CPA 55430

Current route:

```text
get_a_chapter.php?file=55430&cset=C&page=0
```

The page contains **50** actual two-cell text rows and no lexical token links.

- 46 rows have two non-empty unlinked cells;
- 4 rows also have exactly one `comment.php?coord=...` link in the first cell;
- first observed display coordinates include `187:03`, `187:04`, `187:05`, `187:06`,
  `187:07`;
- the four comment-linked coordinates are:
  - `188:07` → `5543018807`;
  - `189:06` → `5543018906`;
  - `190:01` → `5543019001`;
  - `190:08` → `5543019008`.

Thus CPA `55430` and Mandaic `74420` share the same semantic row contract despite different
inner styling: display-coordinate cell + plain rendered-text cell, with an optional comment link
on the coordinate.

## Representation decision

`TextLine.coordinate` becomes nullable:

```text
coordinate: string | null
```

For a current plain two-cell row:

- `display_coordinate`: required, from the rendered first cell;
- `text`: required, from the rendered second cell;
- `tokens: []`;
- `empty_word_indexes: []`;
- `coordinate`: null when CAL exposes no coordinate;
- when the first cell is exactly one current `comment.php?coord=...` link, validate it and expose
  its coordinate instead of discarding known CAL identity;
- `comment_url`: the validated absolute comment URL when present, otherwise null.

The comment-derived coordinate is a **line/comment coordinate**, not evidence of lexical
tokenization. Because `tokens` is empty, callers have no `word_index` and must not infer a
`cal_token_analysis` request from it. It can, however, be used with `cal_text_line_comments`.

This supersedes the issue's initial blanket hypothesis that every plain row has
`coordinate: null`.

## Plain-row fail-closed contract

A plain row is recognized only inside the already validated current `text-display` table and only
when:

1. the row has exactly two cells;
2. it has **no lexical links**;
3. both cells have non-empty rendered text after whitespace normalization;
4. the text cell has no links;
5. the coordinate cell either:
   - has no links; or
   - has exactly one `comment.php` link with exactly one non-empty decimal `coord` selector;
6. when a comment link exists, its rendered text equals the display coordinate and its coordinate
   belongs to the requested text identity.

Unknown links, empty cells, additional links/selectors, or other row structures remain parser
drift.

At page level:

- all actual text rows must be linked rows or all must be plain rows;
- a linked/plain mixture fails closed;
- an empty `text-display` shell is not plain success (#196).

## TDD boundary

RED should prove:

- reduced current `74420` plain rows parse with null coordinate, display coordinate, text, and no
  tokens;
- a comment-linked plain row preserves comment coordinate and URL;
- a structural CPA-style row with nested `span` text still follows the same two-cell semantics;
- public serialization includes `coordinate: null`;
- mixed linked/plain tables fail closed;
- empty coordinate/text cells, lexical links mixed into a plain row, unexpected links, extra
  comment selectors, and comment/display mismatch fail closed;
- existing linked text fixtures remain unchanged.

## Documentation/API impact

The nullable `coordinate` is additive at the JSON level but changes the Python type annotation
from `str` to `str | None`. Documentation must explain:

- comment and token follow-ups are available only when their required identifiers exist;
- a plain row with null coordinate cannot be passed to `cal_text_line_comments`;
- no plain row can be passed to `cal_token_analysis` because there is no returned token/word
  index.

## Request/data impact

Production remains one upstream page request per explicit `cal_text_page` call. Parsing is local;
no token/comment links are followed automatically.

## Live-acceptance amendment — paginated direct CPA navigation

The first installed-stdio acceptance run (`36478612332`) showed that plain-row parsing itself
succeeds for Mandaic `74420`, then direct CPA `55430` fails earlier in the page assembly on the
exact CPA navigation guard inherited from #170.

A fixed structural GET of `55430` (run `36478762860`) found two duplicate rendered
`next page »` links with the same selector set:

```text
get_a_chapter.php?file=55430&sub=&cset=C&page=1&clen=5
```

Selectors are exactly `file,sub,cset,page,clen`; `sub` is the empty string, `cset=C`, and
`clen=5`.

A three-file direct-CPA audit (run `36478860533`) found no previous/next links on current
`55406` or `55407`, while `55430` repeated the same exact `sub=&clen=5` variant. This is
therefore evidence for a **paginated direct-CPA navigation variant**, not a reason to loosen
subdivided CPA navigation or accept arbitrary extra selectors.

Implementation consequence:

- direct CPA navigation with no public `subtext_id` may use either the earlier exact
  `file,page,cset=C` selector set or the current paginated exact
  `file,page,cset=C,sub=,clen=5` selector set;
- subdivided CPA keeps its existing exact selector contract;
- non-empty `sub`, another `clen`, or any other extra selector still fails closed.

The request route emitted by CAL-MCP remains unchanged; this only validates CAL's returned
navigation links.
