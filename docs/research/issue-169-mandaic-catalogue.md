# Issue #169 research — Mandaic catalogue after CAL's script toggle

Date: 2026-09-25. Base: `941261f`.

## Trigger

The 2026-09-25 user-level MCP end-to-end run (#15) found that `cal_text_catalogue(category_id="74")` fails with `parser_drift` "CAL Mandaic catalogue child cset changed unexpectedly".

## Live-current evidence

Seven bounded GETs through the production `CalHttpClient` (project User-Agent, sequential): `show_Mandaic.php?R1=74` (the adapter's request, captured in the end-to-end run), `show_Mandaic.php?cset=J`, `showsubtexts.php?subtext=74410&cset=R`, `showsubtexts.php?subtext=74701&cset=R`, `get_a_chapter.php?file=74410&sub=001&cset=R`, and `get_a_chapter.php?file=74501` with `cset=R` and with `cset=M`.

### The catalogue

`show_Mandaic.php?R1=74` now renders a script toggle and an accordion of groups. Each text is one list item with a route link, whose text is the title, followed by an information link:

```html
<span class="cset-choice"><a href="show_Mandaic.php?cset=R" style="font-weight:bold">Roman</a> <a href="show_Mandaic.php?cset=J">Mandaic script</a></span>
<h1 class="page-title">CAL Mandaic Texts</h1>
<details><summary>Canonical texts</summary><ul>
  <li><a href="/showsubtexts.php?subtext=74410&cset=R">Ginza Rabba (Great Treasury) Right Side</a> <a href="/get_file_info.php?coord=74410" target="_info"><img … alt="info"></a></li>
…
<li><a href="/get_a_chapter.php?file=74501&cset=R">Haran Gauaita</a> <a href="/get_file_info.php?coord=74501" …></a></li>
…
<details><summary>Magic and astrology</summary>
<div class="direct-link">Sfar Malwashi (Book of the Zodiac) (not currently available)</div>
<div class="direct-link"><li><a href="/showsubtexts.php?subtext=74701&cset=R">Mandaic Magic Bowls</a> <a href="/get_file_info.php?coord=74701" …></a></li></div>
```

The page lists 20 texts in 5 groups: 12 via `showsubtexts.php?subtext=<file>&cset=R` and 8 via `get_a_chapter.php?file=<file>&cset=R`. Each has an information link with the same file id. Two texts share the label `Diwan Malkuta ˁlaita` (`74423`, `74923`). Some entries are plain text marked "(not currently available)".

Two things changed from the earlier layout, which rendered the file identifier as the link text and the title after it:
- the child `cset` is now `R`, where it was `M`;
- the link text is now the title.

### What `cset` means

On `showsubtexts.php?subtext=74410` CAL labels the toggles: `script=J` is "Mandaic" and `script=M` is "Standard Transliteration". `R` is CAL's Roman code. The same Ginza line is `m$aba` with `cset=R` and `mšaba` with `cset=M`. `get_a_chapter.php?file=74501` returns the same file (`coord=74501`, the same token coordinates) with `cset=R` and with `cset=M`. So `cset` selects only the rendering script. The `cset=M` page route used by `cal_text_page` still works (live over MCP for `74410` pages 1 and 2 in #166), and nothing in the page route has to change.

The 12 subdivided and 8 direct files in the current catalogue agree with the adapter's private `_MANDAIC_SUBDIVIDED_FILE_IDS` table. Every subdivided file is in it and no direct file is.

## Consequences

- Mandaic catalogue child links accept `cset=R` (current) or `cset=M` (earlier layout). Any other value, including `J`, still fails closed: CAL-MCP never requests the Mandaic-script catalogue.
- Current rows are read as "route link text = title". The file identifier comes from the route query and must match the row's information link when one is present. The earlier "link text = file id, title after it" rows are still read.
- The script-toggle links, group headings and "not currently available" notes are CAL navigation, not texts, and are not returned. Texts are returned in CAL's order.
- The public schema, request counts and page routing are unchanged.
