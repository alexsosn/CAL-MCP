# Issue #186 research — Syriac text ids whose file-info label shows 5 digits

Date: 2026-09-29 (captures 2026-09-25 and 2026-09-29). Base: `2f5b014`.

## Trigger

In the 2026-09-25 user-level end-to-end run (#15), `cal_syriac_texts("metrical-homilies-hymns")` lists `text` items `634081` (Tamar and Judah) and `634082` (The Sleepers of Ephesus), with navigation `get_a_chapter.php?file=634081&cset=S`. `cal_text_page("634081")` then fails with `parser_drift` "CAL text page file-info label is malformed".

## Live-current evidence

One capture from the #168 research, plus four bounded GETs through the production client on 2026-09-29:

| Request | File-info link | CAL's own page links |
| --- | --- | --- |
| `get_a_chapter.php?file=634081&page=0` (tool format, 2026-09-25) | `coord=634081`, text `63408: Tamar and Judah` | `file=63408&sub=1&…&page=1`, `file=63408&sub=&…&variants=0` |
| `get_a_chapter.php?file=634081&page=1` (tool format, page 2) | same | previous `file=63408&sub=1&…&page=0`, next `…&page=2` |
| `get_a_chapter.php?file=634082&page=0` | `coord=634082`, `63408: The Sleepers of Ephesus` | `file=63408&sub=2&…&page=1` |
| `get_a_chapter.php?file=63408&sub=1&page=0` | `coord=634081`, `63408: Tamar and Judah` | `file=63408&sub=1&…&page=1` |
| `showsubtexts.php?keyword=63408` (group JS vol. VI) | group `coord=63408`; subtexts `coord=634081`, `coord=634082` | `get_a_chapter.php?file=63408&sub=1&cset=S`, `…&sub=2&cset=S` |

Row coordinates on the 634081 page are `634081001`, `634081002`, … (file `63408`, sub `1`, line).

## Findings

- `634081` is CAL's file `63408` plus subtext `1`, and `634082` is sub `2`. This is the same convention as #166: the file-info `coord` is the file id followed by the sub. The label prefix is the file (`63408`). The label is not truncated.
- CAL serves the 6-digit id directly as `file=634081` (no `sub`), including page 2, and returns the same text as `file=63408&sub=1`.
- The two known 6-digit ids in the Syriac catalogue are `634081` and `634082`; no other appeared in the end-to-end run's category listings.

## Consequences

- For a request without `sub`, a file-info label whose prefix `P` is a proper prefix of the requested id `F` (with `F = P + S`, and `S` digits) is accepted only when the page's own `get_a_chapter.php` links name `file=P&sub=S`. The page then corroborates CAL's split, so no split is guessed.
- The returned `text.file_id` stays the requested `634081`; CAL-MCP does not renumber.
- Any other label prefix still fails closed as `parser_drift`, and so does a matching prefix without corroborating links.
- Production requests are unchanged.

## Review follow-up (2026-09-29)

- Every row coordinate on such a page must start with the requested id (`634081…`), because identity is accepted from indirect evidence.
- A `get_a_chapter.php` link with repeated `file` or `sub` values disqualifies the split.
- Known limit: the corroboration relies on CAL's previous/next/"show all" links, which carry the non-empty `sub`. A split id whose text has a single page and so has no such links would fail closed as `parser_drift`. Both known ids have several pages (9 and 4).
