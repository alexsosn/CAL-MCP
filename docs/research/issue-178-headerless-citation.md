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
