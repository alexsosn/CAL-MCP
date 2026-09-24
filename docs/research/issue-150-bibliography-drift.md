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

A second shape, `<a href="/getbibsigla.php?myauthor=%0A">\n</a>` (a URL-encoded newline value with a newline label), appears once on the Sokoloff page and twice on Vocab. A link whose value and label are empty or whitespace-only carries no CAL data; it is how CAL renders an empty lemma/keyword list entry. The parser rejects any link without a label, so the whole page fails.

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
- A record link whose label **and** `myauthor` value are both empty or whitespace-only (and whose target is a same-origin bibliography result endpoint with only that parameter) is CAL's empty placeholder and is omitted. Any other unlabelled link, or a link without a target, still fails closed.
- The heading, query-kind, origin/endpoint validation, and the no-data/record contradiction checks are unchanged.
- The public schema, request counts and bounds are unchanged.
- `live_smoke`'s bibliography case also checks record structure (a non-empty citation, a links list, no page-title text, and a citation length bound), so gross record merging cannot pass as "non-empty". See the review amendment below.

## Implementation verification (2026-09-24)

Offline, the full raw captures parse to exactly one record per `<p>`: `br N` 6 records / 73 links, Sokoloff 49 / 96, Vocab 216 / 695, and the no-data page 0. No citation contains CAL's page title. A first mutation pass covered the nested, unbalanced and unclosed record checks, content outside records, title skipping and the marker-card rule. The independent review found six untested guards; see the review amendment.

## Live verification (2026-09-24)

A wheel built from this branch, driven over stdio through MCP against live CAL (4 requests, sequential):

- `cal_bibliography_lemma("br N")`: 6 records;
- `cal_bibliography_author("Sokoloff, Michael")`: 49 records;
- `cal_bibliography_keyword("Vocab")`: 216 records;
- `cal_bibliography_lemma("qqqqzz N")`: a valid empty result.

No citation contains CAL's page title. `python -m cal_mcp.live_smoke` then completed all eight cases on 9/9 CAL requests, with the strengthened bibliography assertion.

## Review amendment (2026-09-24)

An independent adversarial review of `2ceaad7` confirmed exact record segmentation on all 271 real records (citations and link labels matched an independent extraction, with 0 mismatches). It requested changes, now made:

1. **Lost `<p>` boundaries silently merged records again.** A card with no `<p>` fell back to the one-card-per-record rule even when it held CAL's embedded legacy document, and title skipping hid the telltale text. A card containing legacy-document markup (`html`, `body`, `title`, `font`, `hr`) now requires `<p>` records and otherwise fails closed ("legacy result document has no record boundaries"). A marker-only card is still the no-data result.
2. **The `live_smoke` check could not see that regression.** It now checks each record's structure: a non-empty citation of at most 700 characters, a links list, and no page-title text. Observed citations are at most 374 characters; the merged `br N` record was over 1,000.
3. **Record text inside `<title>` was silently dropped.** A `<title>` inside a record now fails closed. The docs sentence that claimed title leakage was "rejected" has been corrected.
4. **Six guards had no tests.** The placeholder origin/fragment check, endpoint check, only-`myauthor` check, single-value check, a link outside records in a record card, and an open card link when a record opens now each have a negative test. A second mutation pass (13 guards, plus the smoke length bound) fails the tests every time.
5. The Sokoloff fixture now keeps CAL's record order.
6. The limitation that a single dropped `</p><p>` boundary is indistinguishable from one long record is documented.
7. The test helpers are typed, so `mypy` is clean over the new test file.

A re-review of `4ea89c9` approved it. Its one low-severity finding (the title-text smoke test was rejected by the links check before reaching the title check) is fixed: each `live_smoke` structure check (non-string or empty citation, length bound, title text, links list) now has its own test, and disabling any one fails the tests.
