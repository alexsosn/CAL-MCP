# Issue #166 research — file-info coordinate on subdivided text pages

Date: 2026-09-25. Base: `0338642`.

## Trigger

The 2026-09-25 user-level MCP end-to-end run (#15) found that `cal_text_page` fails with `parser_drift` "CAL text page file identifier differs from the requested file" for every text tried that has subtexts: Biblical Aramaic `30000/1`, Samaritan Targum `56000/112`, magic bowls `70700/001`, Palmyrene `41201/001`, and the Mandaic Ginza `74410` (whose `sub` is the private page selector). Texts without subtexts (`13250`, `51018`, `62057`) still work.

## Live-current evidence

Eight bounded GETs through the production `CalHttpClient` (project User-Agent, sequential): five from the end-to-end capture, and three more for this research (`70700/001`, `70700/1`, `41201/001`).

| Request | File-info link |
| --- | --- |
| `get_a_chapter.php?file=30000&sub=1&page=0` | `get_file_info.php?coord=300001` — `30000: BiblicalAramaic in Hebrew verses` |
| `get_a_chapter.php?file=56000&sub=112&page=0` | `coord=56000112` — `56000: SamTgJ Gen chapter 12` |
| `get_a_chapter.php?file=70700&sub=001&page=0` | `coord=70700001` — `70700: JBA magic bowls` |
| `get_a_chapter.php?file=70700&sub=1&page=0` | `coord=707001` — `70700: JBA magic bowls` |
| `get_a_chapter.php?file=41201&sub=001&page=0` | `coord=41201001` — `41201: C3901 (PAT 0246)` |
| `get_a_chapter.php?cset=M&file=74410&sub=001` | `coord=74410001` — `74410: Ginza Rabba (Great Treasury) Right Side` |

On subdivided pages, the `coord` of the file-info link is now **the file identifier followed by the submitted `sub` value exactly as sent**, including zero padding (`001`, and `1` when `1` is sent). The label prefix is still the bare file identifier. The 2026-09-10 Ginza capture (`text_page_ginza_right_001.html`) had `coord=74410` for the same request, so this is upstream drift.

Pages requested without `sub` keep `coord=<file_id>`.

### The `sub` value is matched as a prefix

`sub=1` for the magic bowls returns 281 KB, against 12 KB for `sub=001`. Its rows are bowls `100`–`125` (display coordinates such as `125_1:07`, `100_1:01`). CAL treats an unpadded `sub` as a prefix. `cal_text_page` still fails closed on that page, because its bowl-line coordinates are not decimal (`CAL returned a non-decimal coordinate`), so no mixed page is returned as one subtext. Callers must pass `subtext_id` exactly as CAL returned it from the catalogue or a KWIC hit, which the documentation now says explicitly.

## Consequences

- The file-info `coord` is accepted when it equals the bare requested file identifier (earlier layout) or the requested file identifier followed by the exact submitted `sub` value (current layout). Any other value, such as a different file, a different subtext or different padding, still fails closed.
- The returned `TextRef.file_id` stays the requested file identifier, and the label-prefix check is unchanged.
- For Mandaic subdivided pages, the expected suffix is the private `sub` page selector the adapter submitted. This is not a public subtext.
- The public schema, request counts and routing are unchanged. The `cset=M` Mandaic route is researched separately in #169.

## Offline verification

With the rule applied, all six captured pages parse: `30000/1` has 1 line (Gen 31:47), `56000/112` has 20, `74410` has 24, `70700/001` has 15 and `41201/001` has 1. The prefix-matched `70700/1` page still fails closed.

## Review amendment (2026-09-25)

An independent adversarial review of `07fc5c4` found that the claim "no mixed page is returned as one subtext" was wrong. A live `get_a_chapter.php?file=56000&sub=11&page=0` (202 KB) has file-info `coord=5600011` and the label `56000: SamTgJ Gen chapter 12`, and 197 rows from subtexts 112–119 (Gen 12–19). It parses as one page for subtext `11`. The `70700`/`1` page fails closed only because its bowl-line coordinates are not ordinary decimal coordinates.

The page itself has nothing that separates the subtexts: one file-info link, no separators, and a label for the first match only. Subtext widths differ by corpus (`1` for `30000`, `112` for `56000`, `001` for `70700`), so CAL-MCP cannot detect a prefix match from the page. Validating `subtext_id` against CAL's subtext list would add a request to every text page, and that is not justified here. The page is CAL's own answer to that request, and every returned line keeps its real CAL coordinate. The documentation and tool description now state the prefix behaviour plainly, and `text_page_samaritan_56000_prefix_11_current.html` pins it.

The review also found two separate problems, filed as their own issues:
- the same file-info drift in `cal_kwic_full_context` for subtexts;
- on current table-layout pages, `display_coordinate` and `comment_url` are silently lost for every row.

It also asked for a direct test of `parse_text_page` with a subtext and a comment on the earlier-layout fallback, which are now in place. The Ginza fixture now keeps CAL's `next page` link, which the first reduction dropped.
