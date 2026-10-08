# Issue #154 research — gloss-field drift is a POS-grammar gap; the "duplicate" row is a CAL redirect

**Date:** 2026-10-08  
**Base:** `main` at `f0e8757` (after #175 and #222)

## Bounded current CAL evidence

Four live requests were made with the production `CalHttpClient`, one per page. No result link,
lemma-entry link, or pagination was followed:

| Label | Request | Status | Bytes |
| --- | --- | --- | --- |
| `field` | `GET newsearchmngs.php?English=(med&secondary=true` (`cal_gloss_field("medicine")`) | 200 | 60116 |
| `camel` | `POST newsearchmngs.php`, `English=camel#` (`cal_gloss_search("camel#")`) | 200 | 5821 |
| `bot` | `GET newsearchmngs.php?English=(bot&secondary=true` (control) | 200 | 223994 |
| `zool` | `GET newsearchmngs.php?English=(zool&secondary=true` (control) | 200 | 110978 |

Captured 2026-10-08 18:48 UTC (CAL footer: `Thu, 08 Oct 2026 14:48:13 -0400`). The captures are not
committed; only reduced fragments are, as fixtures.

## Finding 1 — the field page fails on CAL alternate-gender POS markers

The `field` page uses the same row markup as an ordinary gloss search: one
`<a href="oneentry.php?lemma=…&cits=all">` per row, with `span.lem`, an optional `span.uni`
pronunciation, and a `<pos>` element, followed by `<span class="gloss">`. Nothing about the
result-page layout has drifted.

Running the current `parse_gloss_search_page` on the capture fails with
`CAL gloss search page has no recognizable results`. The cause is
`LexiconParseError("CAL lexicon browse candidate is missing a recognizable lemma header")`, and
re-running `_parse_lemma_header` over every lemma link isolates exactly these rows:

| Page | Lemma key | Rendered `<pos>` |
| --- | --- | --- |
| field | `xyl N` | `n.m.(f.)` |
| field | `$wrnq N` | `n.m.(f.)` |
| field | `qlyd N` | `n.f./(m.)` |
| zool | `gl#3 N` | `n.m.(f.)`, followed by homograph marker `#3` |
| bot | `$yp#2 N` | *(empty `<pos></pos>`)*, followed by `#2` |

Tallying all `<pos>` values across the four captures gives 1,135 `n.m.`, 312 `n.f.`, and a tail of
slash-combined forms (`n.m./f.`, `n.f./m.`, `n.f./m.pl.`, `n./adj.`, `adj./n.m.`). Those
slash-combined forms are already accepted. Only the parenthesized secondary gender, `(f.)` or
`(m.)`, is new to the grammar. CAL renders it inside the `<pos>` element, so it is part of CAL's
displayed POS. It is not gloss text.

The header parser is shared, so the same rows also break `cal_lexicon_browse` and lexicon lookup
on the affected prefixes. #222 (R-061) widened that grammar for one trailing `?` only.

The empty-`<pos>` row on the botany page is a separate shape. It needs a nullable public
`part_of_speech`, which is a contract change, so it is split into follow-up issue #227 rather
than accepted here.

The control pages also show that verb rows render a vowel class after `vb.`, for example `vb. a/u`
and `vb. a(i)/u #2`. The gloss-search path overwrites that remainder with the next-line gloss, so
the vowel class is currently dropped. This was already the case before this issue and does not
fail the page. It is recorded as follow-up issue #228.

## Finding 2 — CAL itself lists `n)qh N` twice; the second row is a `⟹` redirect

The live `camel#` page has six rows. Rows 5 and 6 both link to `oneentry.php?lemma=n%29qh N`
with identical header text and gloss. Row 6, however, starts with
`<span class="uni">nqh N </span>⟹` before the link:

```html
<td class="even"><span class="uni">nqh N </span>⟹<a href="oneentry.php?lemma=n%29qh N&cits=all">…nˀqh, nˀqtˀ…</a>
```

So CAL does repeat the target lemma. The second row records that the alternate CAL key `nqh N`
redirects to `n)qh N`. The current parser ignores everything before the link unless it contains
`→`, the arrow used on lexicon browse pages. It therefore drops `nqh N`, and the two rows become
indistinguishable.

## Implications

1. Accept exactly one parenthesized secondary-gender group, such as `(f.)` or `(m.)`, at the end
   of an otherwise valid POS token, optionally after `/`. Preserve the literal token. Do not
   widen any other punctuation.
2. Keep CAL's repeated rows (no deduplication), but expose the redirect source verbatim on
   gloss-search matches as `cross_reference_from` (`null` for ordinary rows). Text before the
   lemma link that is not exactly one recognized arrow fails closed. The lexicon-lookup browse
   path is not changed.
3. Production request load is unchanged.
