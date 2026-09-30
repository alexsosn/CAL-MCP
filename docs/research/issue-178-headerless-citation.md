# Issue #178 research — citation search rows and a citation without its own lemma header

Date: 2026-09-29 (captures 2026-09-25 and 2026-09-29). Base: `58d5013`.

## Trigger

In the 2026-09-25 user-level end-to-end run (#15), `cal_citation_text_search("king")` failed with `parser_drift` "CAL citation search result must contain exactly context and citation text". `"camel"` worked.

## Live-current evidence

Two bounded POSTs to `searchcits.php` through the production client on 2026-09-29. The `king` page (570 KB) is byte-identical to the 2026-09-25 capture.

| Query | `citation-row` containers | header + context + citation | other shapes | `<pos>` elements |
| --- | --- | --- | --- | --- |
| `king` | 1068 | 1067 | 1: header + 2 × (context, citation) | 1068 |
| `camel` | 154 | 154 | — | 154 |

Every result is wrapped in `<div class="citation-row even|odd">` inside `<div class="citation-results">`:

```html
<div class="citation-row odd"><a href="oneentry.php?lemma=brt%40ym N&cits=all"><span class="lem"><font color="#0000A0">brt ym</font></span>
	<pos>n.f.</pos>
</a><br>&nbsp;&nbsp;<span class="gloss"> dolphin</span> : (zool.) dolphin<br>
<i>TgEsth<sup>2</sup> 1:2(86)</i> :<span class="heb">…</span>&rlm;
:<span class="rom"> two dolphins sat against the two ears … of King Solomon …</span><br>
 : small wall or glacis<br>
<i>JulSok 257(125):14</i> :<span class="syr">… ܫܘܪܐ …</span>&rlm;
:<span class="rom"> its Lord’s blessings will be a rampart for Edessa and your kingship’s blessing a wall</span><br>
</div>
```

## Findings

1. **One header per sense.** CAL repeats the lemma header for every cited sense. For example, `kl` has five separate rows, each with its own header. So a row normally holds exactly one context and one citation.
2. **A headerless pair.** The one exception is the `brt ym` ("dolphin") row. Its second pair has no gloss span and no header, and plainly belongs to another lemma (Syriac `šwrˀ`, "wall"). Attributing it to `brt ym` would be wrong, and CAL-MCP must not infer the missing lemma.
3. **A second, related defect.** The current line-based parser finds a row's header by a heuristic part-of-speech split of the link text. That fails on 11 header rows in `king`, whose POS forms are `n.(pr.)` (5 rows), `n.m.(f.)` (2), `n.f./m.(?)`, `n.f.(pl.?)`, `n.f.(/m.)` and `n.f./(m.)`. Those rows would be merged into the previous one. CAL marks the POS explicitly with `<pos>…</pos>`, one per row.

## Consequences

- On the current layout, results are parsed per `citation-row` container. The header is the row's single `oneentry.php` link, with the POS taken from CAL's `<pos>` element.
- The row's first (context, citation) pair is attributed to that header. Any further pair in the same row is returned as its own hit with `lemma: null`, keeping CAL's context, reference, source text and translation. The less confusing representation for users is to keep CAL's citation visible but never attribute it to a lemma CAL did not name.
- Any other row shape fails closed: no header, several headers, no `<pos>`, a context without a citation, or a citation without a context.
- Pages without `citation-row` containers keep the earlier line-based parser.
- Production requests are unchanged.

## Findings during GREEN (2026-09-29)

- CAL renders a homograph number after `</pos>` inside the header link (`<pos>n.m.</pos> #3`). It is not part of the headwords. It is accepted only as `#N` matching the key's own homograph suffix; any other text after the POS fails closed.
- Compared on the full `camel` capture, the row parser's output is identical to the earlier parser's for all 154 hits except 18 verb headers. There CAL's `<pos>` includes the vowel class (`vb. a/u`), which the earlier heuristic had split off into `gloss`. The row parser keeps CAL's marked POS and an empty `gloss`.
- On the full `king` capture it returns 1069 hits (1067 rows plus the `brt ym` row's two pairs), one of them with `lemma: null`.

## Review follow-up (2026-09-29)

- Inside CAL's `citation-results` container, any text outside a recognised row (other than the results summary) now fails closed, and so does a row outside that container. A stray close tag or an unrecognised row class can no longer drop a citation silently.
- The header segment's text must be exactly its lemma link's text; text outside the link fails closed.
- Rows are recognised by the `citation-row` class token in any position.
- Other tools keep `part_of_speech` as derived from CAL's rendered header text (`vb.` for verbs); this difference is documented rather than changed here.

## Live smoke finding (2026-09-29): `house`

One further bounded POST (`English=house`, 421 KB, 813 rows) showed two more real shapes:

- **Context-less extra citations.** Two rows add further citations after their (context, citation) pair, separated by an empty `<br>`, with neither a context nor a header. Examples: `ˀlp` "tribal unit" followed by P Lk 5:27 "a tax collector … sitting in the custom house", and `byt šˁˀ` "sundial / zodiacal house" followed by John 2:16 and BT Ber 6b. They plainly belong to other lemmas, so they are returned with `lemma: null` and `lexical_context: null`.
- **Linked references.** A citation reference can be an external link (`<i><a href="http://dukhrana.com/…">BBah 1013:25</a></i>`). Only a lemma-entry (`oneentry.php`) link or a `<pos>` element marks a header; other links in a citation are kept as rendered text.

The row rule is therefore: a header, then a context, then one or more citations, optionally followed by further (context, citation) groups. Only the first citation is attributed to the header; two consecutive contexts, or a context without a following citation, fail closed. On the full captures: `king` gives 1069 hits (1 null lemma), `camel` 154, and `house` 816 (3 null lemmas, all 3 with a null context).
