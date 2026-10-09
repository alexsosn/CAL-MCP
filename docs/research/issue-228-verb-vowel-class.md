# Issue #228 research — CAL marks a verb's vowel class inside `<pos>` on result rows

**Date:** 2026-10-08  
**Base:** `main` at `c8585b7` (after #154 and #180)

## Bounded current CAL evidence

Two live GETs were made with the production client. No links were followed.

| Label | Request | Status | Bytes |
| --- | --- | --- | --- |
| `browse` | `GET browseSKEYheaders.php?first3="(hr"` (`cal_lexicon_browse("(hr")`) | 200 | 8557 |
| `entry` | `GET cal_entry_web.php?lemma=(hr V` (exact entry behind `cal_lexicon_lookup`) | 200 | 36371 |

The #154 captures from 2026-10-08 (gloss fields medicine, botany and zoology; R-062) were re-read
offline for gloss-search rows.

## Findings

**Browse and gloss-search rows.** CAL renders the verb's vowel class inside the `<pos>` element
of the lemma link:

```html
<a href="oneentry.php?lemma=%28hr V&cits=all" target="_self"><span class="biglem"><font color="#0000A0">ˁHR, ˀHR</font></style></span>
		<pos>vb. a/u</pos>
</a><br>&nbsp;&nbsp;<span class="gloss"> to be sexually aroused</span>
```

The gloss-field pages carry `vb. a/u`, `vb. a/a`, `vb. a(i)/u` (then `#2`), `vb. a/i(u?)` and
`vb. a/u, e/a` in the same position.

**Exact entry.** The vowel class is not in the POS here. CAL renders it as the vocalized form:
`<span class="lemma-vocalized">(a/u)</span> <span class="lemma-pos">vb.</span>`.

**Current CAL-MCP output for `(hr V`:**

| Path | `part_of_speech` | `pronunciation` |
| --- | --- | --- |
| `cal_lexicon_lookup` (exact entry) | `vb.` | `a/u` |
| `cal_lexicon_browse` and lookup's browse step | `vb.` | `null` (`a/u` dropped) |
| `cal_gloss_search` / `cal_gloss_field` | `vb.` | `null` (`a/u` dropped) |
| `cal_citation_text_search` (#178, reads `<pos>`) | `vb. a/u` | — |

The flattened link text is parsed with a POS-token grammar that stops at `vb.`. The remainder,
`a/u`, lands in the header's gloss slot, and the row parsers then overwrite that with the
next-line gloss. So the value is silently lost.

## Implication

When a result row marks its POS with a `<pos>` element, use that element's text as
`part_of_speech`, as citation search already does. It must agree with the rendered header: the
grammar's POS token is a prefix of it, and nothing but a CAL homograph marker (`#N`) may follow
it inside the link. Any disagreement, or more than one `<pos>` in a link, fails closed. Rows
without `<pos>` markup keep the existing grammar.

The exact-entry header is unchanged: CAL itself presents the vowel class there as the vocalized
form, and CAL-MCP keeps it as `pronunciation`. An empty `<pos>` (#227) is out of scope here and
still fails closed.
