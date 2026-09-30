# Issue #171 research — non-Mandaic `showsubtexts.php` links in text search results

Date: 2026-09-30. Base: `a57d1d5`.

## Trigger

The 2026-09-25 user-level end-to-end run (#15) found that `cal_text_search("Neofiti")` fails with `parser_drift` "CAL Mandaic text search result has an invalid cset". The parser treats every `showsubtexts.php` result link as the specialised Mandaic route (`cset=M`).

## Live-current evidence

Bounded requests on 2026-09-30:

| Request | Result link |
| --- | --- |
| `POST newsearchtxts.php`, `search=Neofiti` | `<a href="/showsubtexts.php?subtext=54001&cset=H"><b>54001 </a></b>: TN (Targum Neofiti): book 1 chapter 2 verse 2 …` |
| `POST newsearchtxts.php`, `search=Onkelos` | `<a href="/showsubtexts.php?subtext=70703012&cset=H"><b>70703012 </a></b>: HS 3030: Hilprecht 3030 …` |
| `cal_text_catalogue(category_id="54001")` over MCP | 0 categories and the Neofiti chapters as texts (`54001`/`101` "TN Gen chapter 01", …) |
| `cal_text_catalogue(category_id="70703012")` over MCP | one text, `70703`/`012` "HS 3030" |

## Findings

- A `showsubtexts.php` result with a non-Mandaic script names a CAL catalogue node (a subdivided source, or a node listing one subtext), not a readable page. `cal_text_page("54001")` without a subtext is not the right follow-up. `cal_text_catalogue(category_id=<the linked id>)` works for both observed results.
- The Mandaic route (`cset=M`, #169/#185) remains a text that `cal_text_page` reads directly.

## Consequences (first design, superseded by the review follow-up below)

- Each text-search match gains `follow_with`: `cal_text_page` for `get_a_chapter.php` links and Mandaic `cset=M` links, and `cal_text_catalogue` for `showsubtexts.php` links with one of CAL's script codes `R`, `H`, `S` or `U`. For a catalogue node, `file_id` is the linked `subtext` value, which is exactly what `cal_text_catalogue(category_id=…)` takes, and `subtext_id` is `null`.
- A `showsubtexts.php` link with any other or missing `cset`, or a non-decimal `subtext`, still fails closed.
- Production requests are unchanged.

## Review follow-up (2026-09-30)

- **Peshitta.** The review made one bounded search for `Peshitta`. It returned 60 results: one `get_a_chapter.php?file=62018&cset=U` and 59 `showsubtexts.php?…&cset=U` catalogue nodes, including a 7-digit `6203504`. That page also failed before this change. `cset=U` is therefore observed; `R` and `S` are CAL's other script codes and are accepted by analogy.
- **Routing follows the collection, not the script.** CAL uses `cset` to choose a script; CAL's Mandaic catalogue itself links `subtext=74410&cset=R`. So a Mandaic collection (`74…`) link with `cset` `M` or `R` is read by `cal_text_page`. Any other identifier with `cset` `H`, `U`, `R` or `S` is a catalogue node. Every other combination fails closed, including `cset=M` outside the Mandaic collection.
- **Result shape.** The field is `follow_up_tool`, the vocabulary already used by `specialized_collections`. A catalogue node's identifier is reported as `category_id`, with `file_id: null`, because `70703012` is not a file id: it lists file `70703`, subtext `012`. Every catalogue-routed row failed before this change, so no existing caller depends on the earlier draft shape.
