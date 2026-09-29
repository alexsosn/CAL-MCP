# Issue #173 research — book labels in Peshitta and Targum verse headings

Date: 2026-09-29 (captures 2026-09-25). Base: `3c788e0`.

## Trigger

The 2026-09-25 user-level MCP end-to-end run (#15) found that `cal_syriac_peshitta_parallel(book="Psalms", chapter=23, verse=1)` fails with `parser_drift` "CAL Peshitta heading does not match the requested verse". Genesis 1:1 worked in the first run, on 2026-09-24.

## Live-current evidence

Twenty-two bounded POSTs through the production `CalHttpClient` (project User-Agent, sequential), one verse each on `showpesh.php` and `showtargum.php`, for 11 books: Gen, 1 Sam, Hab., Psalms, Job, Song of Songs, Qoheleth, Lamentations, Proverbs, 1 Chronicles and Esther.

| Book (selector label, id) | Peshitta heading | Targum heading |
| --- | --- | --- |
| Gen (01) | `MT and Peshitta for Kings1 1:1` | `MT and targums for Kings1 1:1` |
| 1 Sam (08) | `MT and Peshitta for  1:1` (empty label) | `MT and targums for  1:1` |
| Hab. (22) | `… Hab 1:1` | `… Hab 1:1` |
| Psalms (27) | `… Ps 23:1` | `… Ps 23:1` |
| Job (28) | `… Job 1:1` | `… Job 1:1` |
| Song of Songs (29) | `… Song 1:1` | `… Song 1:1` |
| Qoheleth (31) | `… Qoheleth 1:1` | `… Qoheleth 1:1` |
| Lamentations (32) | `… Lam 1:1` | `… Lam 1:1` |
| Proverbs (33) | `… Prov 1:1` | `… Prov 1:1` |
| 1 Chronicles (34) | `… Chron1 1:1` | `… Chron1 1:1` |
| Esther (36) | `… Esther 1:1` | `… Esther 1:1` |

The book label in CAL's heading is CAL's own abbreviation. It is sometimes **wrong or empty**: Genesis is headed "Kings1", and 1 Samuel has no label. The verses themselves are right: the Genesis page shows בְּרֵאשִׁית and 1 Sam 1:1 its own text. A selector-label comparison therefore cannot work, and a table of CAL's heading labels would encode CAL's mistakes.

Each page carries verse navigation with CAL's numeric book id:

```html
<a href="showpesh.php?bookname=27&chapter=023&verse=0">display previous verse</a>
<a href="showpesh.php?bookname=27&chapter=023&verse=2">display next verse</a>
<a href="showtargum.php?bookname=27&chapter=023&verse=0&Peshitta=1&Sam=1">display previous verse</a>
<a href="babshowtargum.php?bookname=27&chapter=023&verse=001&Peshitta=1&Sam=1">display JLA in Babylonian pointing</a>
```

- Every captured page has at least one such link.
- Each link names the requested book id (unpadded on Peshitta pages, padded on Targum pages) and the requested chapter, with a verse within one of the requested verse.
- The first verse links to a previous verse `0`.

## Consequences

- The heading must still be the page's only verse heading, with the requested `chapter:verse`. Its book label is not compared.
- The requested book is instead verified by CAL's verse navigation. There must be at least one `showpesh.php` / `showtargum.php` / `babshowtargum.php` link with `bookname`, `chapter` and `verse`. Every such link must name the requested numeric book id and chapter, with a verse within one of the request. Anything else fails closed.
- The result keeps reporting the requested selector label as `book`, with CAL's book id.
- The public schema and request counts are unchanged. The verse-label leak into `mt_text` is #155.
