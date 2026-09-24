# Issue #150 research — bibliography result-page drift

Date: 2026-09-24. Base: `2a9a2c5e00c18e441b2fb79ec666dad2aba72bd7`.

## Trigger

The 2026-09-24 user-level MCP end-to-end run (#15) found:

- `cal_bibliography_lemma("br N")` **succeeds but returns one record** whose 1071-character `citation` starts with `CAL BIBLIOGRAPHY SEARCH` and runs every work on the page together, with 70+ links attached. This is silent wrong data;
- `cal_bibliography_author("Sokoloff, Michael")` and `cal_bibliography_keyword("Vocab")` fail with `parser_drift` "CAL bibliography record link has no label".

The `bibliography` `live_smoke` case (`cly V`) passes only because it checks that `records` is non-empty.

## Live-current evidence

Four bounded GETs were made through the production `CalHttpClient` (project User-Agent, sequential):

| Request | Status | Bytes | `<p>` records |
| --- | --- | --- | --- |
| `getbiblemma.php?myauthor=br+N` | 200 | 8,744 | 6 |
| `getbibauthor.php?myauthor=Sokoloff%2C+Michael` | 200 | 23,506 | 49 |
| `getbibsigla.php?myauthor=Vocab` | 200 | 88,817 | 216 |
| `getbiblemma.php?myauthor=qqqqzz+N` (no data) | 200 | 2,697 | 0 |

### 1. All records now sit in one card, one `<p>` per record

The page keeps the `<h1>CAL Bibliography for <query></h1>` heading, then a modern wrapper with **one** `<div class="card">`. Inside the card CAL embeds its whole legacy result document:

```html
<div class="card"><div class="uni">
<html><TITLE>CAL BIBLIOGRAPHY SEARCH</TITLE><BODY …><font …>
<p>Jansma, T., "<TITLE_ANALYTIC>…</TITLE_ANALYTIC>." <i>Parole de l'Orient</i> 5 (1974): 21–48.
   <a href="/getbiblemma.php?myauthor=br%20N">br N</a> <a …>qym N</a> …</p>
<p>Avishur, Y., …</p>
…
</font><hr></BODY></html>
</div></div>
```

Each bibliographic record is exactly one `<p>` element (opening and closing counts are equal on all three pages). Every `<p>` carries at least one link. Apart from the `<TITLE>` text and whitespace, no text sits inside the card outside the `<p>` records. The earlier layout used one `div.card` per record. The current parser still treats each card as one record, so it merges all records and takes the legacy `<TITLE>` text into the citation.

The outer page also has its own `<head><title>`. Title content is document metadata, never record content.

Record markup includes custom tags (`TITLE_ANALYTIC`, `TITLE_MONOGRAPHIC`), `<i>`, `<sup>` and `<u>`, and CAL's own text, including one C1 control character (`\x9a`) in a Keyword/Vocab citation. That text passes through unchanged, because CAL is the authority for its content.

### 2. Empty link placeholders

The author and keyword pages contain `<a href="/getbiblemma.php?myauthor="></a>`, and the same shape for `getbibsigla.php`, with an **empty label and an empty `myauthor` value**. These appear at most once per record, after the record's real tag links (12 of 49 Sokoloff records, and more on Vocab), for example:

```html
… <a href="/getbibsigla.php?myauthor=Samar">Samar</a> <a href="/getbiblemma.php?myauthor="></a></p>
```

A link with no target value and no text carries no CAL data; it is how CAL renders an empty lemma/keyword list entry. The parser rejects any link without a label, so the whole page fails.

### 3. The no-data marker now sits inside the card

```html
<h1>CAL Bibliography for qqqqzz N</h1>
<main><div class="card"><div class="uni">
NO data FOR qqqqzz N ARE CURRENTLY STORED<br></div></div>
```

Under the one-card-per-record rule this card becomes a "record" whose text is the no-data marker, and the page then fails with "contradicts its no-data marker". **Empty bibliography results are broken too.**

## Consequences

- Records are the `<p>` elements inside result cards. A card that contains `<p>` elements yields one record per `<p>`. Any non-whitespace text in such a card outside `<p>` (other than title metadata) fails closed, so content is never silently dropped or merged. Nested or unclosed `<p>` fails closed.
- A card without `<p>` keeps the earlier one-record-per-card meaning as a strict compatibility fallback, except that a card whose entire text is the explicit no-data marker, with no links, is the marker container rather than a record.
- `<title>` content is ignored wherever it appears.
- A record link whose label **and** `myauthor` value are both empty is CAL's empty placeholder and is omitted. Any other unlabelled link, or a link without a target, still fails closed.
- The heading, query-kind, origin/endpoint validation, and the no-data/record contradiction checks are unchanged.
- The public schema, request counts and bounds are unchanged.
- `live_smoke`'s bibliography case also asserts that no citation contains CAL's page-title text, so a record-boundary regression cannot pass as "non-empty".
