# Issue #182 research — display coordinate and comment link on CAL's table-layout text pages

Date: 2026-09-25. Base: `941261f`.

## Trigger

The independent review of #166 found that `cal_text_page` returns `display_coordinate: null` and `comment_url: null` for every line of CAL's current text pages, even where CAL renders a coordinate and a comment link. The fields are dropped silently.

## Live-current evidence

Seventeen full text-page captures from 2026-09-25 were surveyed, fetched through the production `CalHttpClient` (project User-Agent, sequential). They cover:
- the end-to-end run;
- the #166, #167 and #168 research;
- two further GETs for this issue: Tel Dan `13250` and Peshitta Philemon `62057`.

The collections are Biblical Aramaic, Samaritan Targum, Talmud, Mandaic, magic bowls, Palmyrene, Syriac (Roman and `cset=S`), Old Aramaic and Peshitta.

Every page renders its lines in `<table class="text-display">`, one `<tr>` per line, with exactly two cells:

```html
<tr><td valign="top"><a href="comment.php?coord=56000112010" STYLE="color:red" target="_com">Gen12:01)0(  </a></td><td><a href="getlex.php?coord=56000112010&word=0&hasvariant=0">w)mr</a> …</td></tr>
<tr><td valign="top">001:01  </td><td><a href="getlex.php?coord=7441000101&word=0&hasvariant=0">mšaba</a> …</td></tr>
<tr><td valign="top">001_1:01 </td><td><a href="bablex.php?coord=70700001101&word=0" target="info">hdyN</a> …</td></tr>
<tr><td valign="top">01 <a href="/ask_ai_prompt.php?coord=620570101&cset=R&return=…" title="Ask AI to translate this line">[ai]</a></td><td><a href="getlex.php?coord=620570101&word=0&hasvariant=0">p.awlAws</a> …</td></tr>
<tr><td valign="top"><span class="mono" dir="ltr" style="display:inline-block;">1.005:07 </span> </td><td>…</td></tr>   (cset=S)
```

The survey of every `valign="top"` row in the 17 pages found:

- every row has exactly 2 cells;
- the second cell holds only lexical token links (8,202 `getlex.php` and 5,047 `bablex.php`), with no loose text;
- the first cell is either a `comment.php` link whose text is the display coordinate (336 rows), or plain text, optionally followed by an `ask_ai_prompt.php` "[ai]" link (25 rows). In `cset=S` the plain text sits inside a `mono` span.

The text-page line splitter (`lexicon._parse_lines`) breaks at every `<td>`. The coordinate cell becomes a separate token-less line, which `_parse_text_line` discards, and the token cell becomes a line whose "display coordinate" is the empty text before its first token. The `<div>`-row fixtures captured before 2026-09 kept both parts in one block, which hid this.

The same splitter drops a cell whose text is empty together with its links. That is how #168's rows of empty word slots disappear.

## Consequences

- When a page has CAL's `text-display` table, lines are read per `<tr>`, pairing the coordinate cell with the token cell:
  - `display_coordinate` is the coordinate cell's own text, excluding the "[ai]" link text, or the comment link's text when there is one;
  - `comment_url` is the comment link, whose `coord` must equal the row's token coordinate;
  - `text` is the token cell text.
- Fail closed on:
  - a text row that does not have exactly two cells;
  - lexical links in the coordinate cell;
  - any link in the coordinate cell other than `comment.php` or `ask_ai_prompt.php`;
  - a comment or Ask-AI link naming another coordinate;
  - lexical links outside text rows;
  - loose text in the token cell (not observed; it would otherwise be silently merged).
- Pages without the table keep the existing line mode, as a strict fallback for the earlier layout.
- The public schema is unchanged: both fields already exist and were documented. Request counts are unchanged.
