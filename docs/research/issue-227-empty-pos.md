# Issue #227 research — CAL renders an explicitly empty POS for `$yp#2 N`

**Date:** 2026-10-08  
**Base:** branch `claude/issue-228-verb-vowel-class` at `a38ca63`. #227 builds on #228's per-link
`<pos>` capture.

## Bounded current CAL evidence

Two live GETs were made with the production client. No links were followed.

| Label | Request | Status | Bytes |
| --- | --- | --- | --- |
| `browse` | `GET browseSKEYheaders.php?first3="$yp"` | 200 | 10019 |
| `entry` | `GET cal_entry_web.php?lemma=$yp#2 N` | 200 | 26338 |

The R-062 botany gloss-field capture (2026-10-08) was re-read offline.

## Findings

**Result rows.** The browse row and the botany gloss row for `$yp#2 N` carry an empty `<pos>`
element, followed by the homograph marker:

```html
<a href="oneentry.php?lemma=%24yp%232 N&cits=all" target="_self"><span class="lem"><font color="#0000A0">šyp, šypˀ</font></span>
	<pos></pos>
 #2</a><br>&nbsp;&nbsp;<span class="gloss"> a type of marsh reed</span>
```

The shared header grammar needs a POS token, so `cal_gloss_field("botany")`,
`cal_lexicon_browse("$yp")` and lookup's browse step for that prefix all fail closed on the
entire page.

**Exact entry.** The current header has no POS span at all:

```html
<div class="lemma-header"><span class="lemma-formal"><b>šyp, šypˀ</b></span> <span class="lemma-gloss"><b>a type of marsh reed</b></span></div>
```

`parse_lexicon_entry` therefore skips the real header and accepts a later line as the header:
`headwords=('Page',)`, `part_of_speech='refs.'`, gloss `in other dictionaries: DJBA: 1138b`. This
is the silent corruption described in #224. Today lookup never reaches this entry, because its
browse step fails first. Once browse accepts the row, a lookup of `šyp` would select `$yp#2 N` and
return the corrupted header.

## Implications

1. On result rows, an empty `<pos>` element is CAL's explicit "no POS". Return
   `part_of_speech: null` only when CAL marks exactly one empty `<pos>` and the rendered header
   has no POS-looking token. Otherwise fail closed. A row with no `<pos>` at all still uses the
   existing grammar.
2. `LemmaRef.part_of_speech` becomes nullable. The derivative and text-token models are already
   nullable.
3. To keep lookup from exposing #224's corruption, add a narrow structural guard: when the entry
   page has CAL's current `div.lemma-header`, only that block may be the header, and failing to
   parse it is `parser_drift`. A lookup of `$yp#2 N` then fails closed, as it effectively does
   today. Full structural parsing of entry headers, including a null POS on exact entries, stays
   in #224.
