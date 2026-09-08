# Issue #106 research — CAL text-information metadata

**Research date:** 2026-09-09
**Baseline:** branch created from pre-#104 `main`; synchronize with current `main` before TDD.

## Research question

What stable public selector and result shape can expose CAL's current `get_file_info.php` text-information pages without accepting arbitrary URLs, inventing bibliographic structure, or automatically following their links?

## Current CAL workflow

CAL exposes text-information pages through links of the form:

```text
get_file_info.php?coord=<decimal text selector>
```

Current indexed examples include:

- `6042013` — Ephrem, Hymns on Paradise;
- `43200017` — Hatran H 17;
- `43200244` — Hatran H 244;
- `43200336` — Hatran H 336;
- `300001` — Biblical Aramaic in Hebrew verses.

These pages have the semantic heading `Text Information` and preserve research-relevant source, edition, editorial, numbering, manuscript/findspot, bibliography, photo, and cautionary notes.

## Selector semantics are not simply "base file ID"

CAL navigation demonstrates that the `coord` can identify a finer text/subtext selection by concatenating the base text identifier and its CAL subtext selector.

Representative current evidence:

```text
newshow_browsedialects.php?R1=56
  56000       SamTg J
  56000128    SamTgJ Gen chapter 28

get_a_chapter.php?clen=5&cset=R&file=56000&sub=128
  renders 56000: SamTgJ Gen chapter 28
```

Hatran metadata shows the same pattern: `43200336` identifies H 336 within base text `43200`.

The public API therefore should reuse existing text identifiers instead of exposing CAL's private `coord` directly:

```text
cal_text_information(file_id, subtext_id=None)
```

Private request selector:

- when `subtext_id is None`: `coord = file_id`;
- when `subtext_id` is present: `coord = file_id + subtext_id` exactly as validated decimal strings.

This preserves existing `TextRef` composition and avoids an arbitrary-coordinate/URL execution surface. TDD must pin representative direct and subdivided selectors before production code is changed.

## Result shape: preserve CAL text, do not normalize bibliography

The page family is semantically stable at the heading/result level but its metadata body is heterogeneous.

Examples:

- Ephrem Hymns on Paradise is chiefly a prose corpus/edition note plus a substantial quality warning;
- Hatran pages contain corpus-level notes, item/findspot descriptions, reading authorities, bibliography rows, and `.photo` rows;
- Biblical Aramaic metadata contains compact `SUB` numbering conventions.

A fixed schema such as `edition`, `manuscript`, `bibliography`, or `findspot` would be lossy and would manufacture distinctions CAL does not consistently encode.

The faithful initial model should therefore preserve CAL's ordered rendered metadata as normalized nonempty text lines/paragraphs, together with the requested identifiers and provenance. Links may be preserved as rendered text/navigation metadata only if parser evidence makes that lossless; they must never be followed automatically.

Proposed typed result core:

```text
TextInformationResult
  file_id
  subtext_id
  metadata: ordered strings
  provenance:
    source = "CAL"
    source_url
    retrieved_at
    operation = "text_information"
    upstream selector / requested identifiers
```

Do not invent a title separate from the metadata unless the reduced fixtures demonstrate a stable semantic title field independent of the `Text Information` page heading.

## Empty, missing, anti-scrape, and drift semantics

A bounded direct HTTP research probe made four fixed GETs (three known selectors plus one intentionally nonexistent selector):

```text
6042013
43200336
56000128
99999999
```

All four returned HTTP 200 with the same 8659-byte anti-scraping page containing CAL's request not to scrape and no text-information semantics. This means raw HTTP status/body size cannot distinguish a missing selector from a valid metadata page under that access mode.

Accordingly:

- the adapter must recognize a genuine `Text Information` semantic page, not merely HTTP 200;
- CAL's anti-scrape/maintenance/generic response must remain a shared content/upstream failure or parser drift, not a successful empty result;
- no `not_found` state should be invented unless a focused fixture/current CAL surface exposes an explicit missing-text-information marker;
- a well-formed but nonexistent decimal selector may therefore fail closed rather than return fabricated `not_found` in the initial contract.

Normal CI remains offline; the anti-scrape research probe has been removed from the branch.

## Existing parser interaction

`_page_text_ref()` currently uses text-page `get_file_info.php?coord=...` links to validate page identity. Its present comparison treats returned `coord` as if it must equal `requested_file_id` exactly. Current composite selector evidence suggests subdivided pages may use a composite info selector.

This is potentially an independent text-page parser bug, but the current browser/index extracts do not expose the raw info-link href strongly enough to change that behavior inside #106. Do not broaden #106 opportunistically. If a reduced/live fixture confirms a composite `get_file_info.php` link on a page requested as `file_id + subtext_id`, file a focused regression issue before altering `_page_text_ref()`.

## Boundedness

One explicit metadata lookup should perform exactly one CAL request:

```text
GET get_file_info.php?coord=<private composed selector>
```

No text page, bibliography item, image/photo source, archive link, or other metadata link is followed automatically. No catalogue enumeration, prefetch, background indexing, or local mirror is introduced.

## Sources rechecked

Current CAL/browser-index evidence rechecked 2026-09-09:

- `https://cal.huc.edu/get_file_info.php?coord=6042013`
- `https://cal.huc.edu/get_file_info.php?coord=43200017`
- `https://cal.huc.edu/get_file_info.php?coord=43200244`
- `https://cal.huc.edu/get_file_info.php?coord=43200336`
- `https://cal.huc.edu/get_file_info.php?coord=300001`
- `https://cal.huc.edu/newshow_browsedialects.php?R1=56`
- `https://cal.huc.edu/get_a_chapter.php?clen=5&cset=R&file=56000&sub=128`
- repository `src/cal_mcp/texts.py` current page-reference parsing.

## CAL load

Four fixed GETs total were made by the dedicated research probe, each capped at 15 seconds and 512 KiB. No returned links were followed and no corpus/category enumeration was performed. The probe is not part of normal CI or the planned production path.
