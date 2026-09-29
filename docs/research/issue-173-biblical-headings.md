# Issue #173 research — book labels in Peshitta and Targum verse headings

Date: 2026-09-29 (captures 2026-09-25). Base: `3c788e0`.

## Final finding (read this first)

- CAL's verse headings use CAL's own book labels (`Ps`, `Kings1`, `Chron2`, …), not the selector labels. That is the whole defect behind the `parser_drift` error. The fix checks the label against a reviewed table of all 36 labels.
- The tool's own requests use CAL's 2-digit coordinate format and always returned the right verse.
- The "Live-current evidence" and "Correction" sections below come from **3-digit research requests**, not the tool's format. Their claims that CAL's label is "sometimes wrong or empty", that "the verses themselves are right", that "CAL's handling changed around 2026-09-25", and that the adapter "silently returns the wrong verse" are **retracted**; see "Second correction". The 3-digit pages also carry CAL's own `pesh coord error` marker, which `_COORDINATE_ERROR_RE` does not match, so they would fail as incomplete pages in any case.

## Trigger

The 2026-09-25 user-level MCP end-to-end run (#15) found that `cal_syriac_peshitta_parallel(book="Psalms", chapter=23, verse=1)` fails with `parser_drift` "CAL Peshitta heading does not match the requested verse". Genesis 1:1 worked in the first run, on 2026-09-24.

## Live-current evidence (superseded: 3-digit research requests)

Twenty-two bounded POSTs through the production `CalHttpClient` (project User-Agent, sequential), one verse each on `showpesh.php` and `showtargum.php`, for 11 books: Gen, 1 Sam, Hab., Psalms, Job, Song of Songs, Qoheleth, Lamentations, Proverbs, 1 Chronicles and Esther.

| Book (selector label, id) | Peshitta heading (3-digit research request) | Targum heading (3-digit research request) |
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

## Correction (2026-09-29, superseded by the second correction): zero-padded chapters make CAL return the wrong verse

The first reading above was wrong. The "Kings1" page captured for a Genesis 1:1 request is **1 Kings 1:1**: its MT is וְהַמֶּלֶךְ דָּוִד זָקֵן. So CAL's heading was correct, and the navigation link only echoes the submitted book id. Trusting that echo would have silently served 1 Kings as Genesis.

Thirteen more bounded POSTs, run 2026-09-29, isolated the cause: CAL-MCP's zero-padded coordinate fields.

| POST (`bookname`, `chapter`, `verse`) | Heading | MT text |
| --- | --- | --- |
| `01`, `001`, `001` (the adapter's current form) | `Kings1 1:1` | 1 Kings 1:1 — **wrong** |
| `1`, `001`, `001` | `Kings1 1:1` | 1 Kings 1:1 — **wrong** |
| `08`, `001`, `001` | ` 1:1` (empty label) | Genesis 1:1 — **wrong** |
| `1`, `1`, `1` | `Gen 1:1` | Genesis 1:1 |
| `2`, `1`, `1` and `02`, `1`, `1` | `Exod 1:1` | Exodus 1:1 |
| `8`, `1`, `1` | `Sam1 1:1` | 1 Samuel 1:1 |
| `27`, `23`, `1` and `27`, `023`, `001` | `Ps 23:1` | Psalms 23:1 |
| `27`, `119`, `150` | `Ps 119:150` | Psalms 119:150 |
| `12`, `40`, `3` (Targum) | `Isaiah 40:3` | Isaiah 40:3 |
| `1`, `50`, `26` (Targum) | `Gen 50:26` | Genesis 50:26 |

The book id's padding does not matter. A 3-digit **chapter** does, except in Psalms, the only book with a 3-digit chapter width in CAL's own links (`chapter=023`; other books link `chapter=01`). CAL apparently builds a fixed-width coordinate, so a wrongly padded chapter shifts it into another book. The 2026-09-24 end-to-end run read Genesis 1:1 correctly with the same padded request, so CAL's handling changed around 2026-09-25. The adapter's `_format_coordinate_number` (3 digits) now makes `cal_targum_parallel` and `cal_syriac_peshitta_parallel` **silently return the wrong verse** for affected books.

A further 36 POSTs, run 2026-09-29 with unpadded values (`chapter=1`, `verse=1`, one per book), return the right verse for every book, with these heading labels:

```text
Gen Exod Lev Num Deut Joshua Judges Sam1 Sam2 Kings1 Kings2 Isaiah Jer Ezek Hosea Joel
Amos Obad Jonah Micah Nahum Hab Zeph Haggai Zech Mal Ps Job Song Ruth Qoheleth Lam Prov
Chron1 Chron2 Esther
```

All 36 labels are distinct. The Targum route used the same labels in all 11 sampled books.

### Revised consequences

- Chapter and verse are submitted as CAL's unpadded decimal numbers, which is what CAL's own form users type. That makes every tested book and verse, including Psalms 119:150, return the right text.
- The heading is the page's identity. It must name the requested `chapter:verse`, and its book label must be CAL's heading label for the requested book (a reviewed static table) or the exact selector label (the earlier layout). Any other label, including an empty one, fails closed, so a shifted coordinate can never be served as the requested verse.
- The verse-navigation links are only an echo of the request. They are not used as identity evidence.
- The public schema, request counts and routes are unchanged.

## Second correction (2026-09-29): the tool's own requests were never affected

The "Correction" above tested 3-digit chapters (`chapter=001`), which was the format of the research requests. The adapter itself sends CAL's **2-digit** format (`f"{value:02d}"` below 100, for example `bookname=01`, `chapter=01`, `verse=01`), and that matches CAL's own navigation links (`chapter=01`, `verse=01`). Four more bounded POSTs in exactly the tool's format return the right verse:

| POST (tool format) | Heading | MT |
| --- | --- | --- |
| `01`, `01`, `01` (Peshitta and Targum) | `Gen 1:1` | Genesis 1:1 |
| `08`, `01`, `01` | `Sam1 1:1` | 1 Samuel 1:1 |
| `27`, `23`, `01` | `Ps 23:1` | Psalms 23:1 |

So `cal_targum_parallel` and `cal_syriac_peshitta_parallel` never returned the wrong verse. The only defect is the one reported: CAL's heading uses its own book labels. The 3-digit behaviour is recorded as a CAL property: a 3-digit chapter shifts CAL's coordinate into another book. The request format therefore must not change, and a test pins it.

### Final consequences

- Request coordinates are unchanged: CAL's 2-digit format, pinned by tests.
- The heading must be the page's only verse heading. It must name the requested `chapter:verse` with CAL's heading label for the requested book (from the reviewed table of all 36 labels above), or with the exact selector label (the earlier layout). Any other label, including an empty one, fails closed, so a page for another book is never returned as the requested verse. The fixtures from the 3-digit requests (1 Kings for Genesis; an empty label) pin exactly that.
- The navigation links are not used as identity evidence, because they echo the request.
