# CAL text discovery, metadata, and page retrieval

CAL-MCP exposes five bounded tools for discovering CAL texts, retrieving CAL's explicit text-information metadata, reading one rendered text page at a time, and explicitly retrieving CAL line comments/translations. These tools adapt CAL's current public text interfaces; they do not create a local corpus, crawl categories, follow pagination automatically, follow metadata links, or call CAL's token-analysis endpoint.

## Which tool to use

| Goal | Tool |
| --- | --- |
| Browse the root CAL text catalogue | `cal_text_catalogue()` |
| Expand one catalogue category returned by CAL | `cal_text_catalogue(category_id=...)` |
| Find CAL texts by the topic/search phrase accepted by CAL | `cal_text_search(query)` |
| Retrieve CAL's detailed source/edition/editorial notes for one text or subtext | `cal_text_information(file_id, subtext_id=None)` |
| Retrieve CAL citations/comments/translations for one returned line coordinate | `cal_text_line_comments(coordinate)` |
| Retrieve one CAL text page | `cal_text_page(file_id, subtext_id=None, page=1)` |

The identifiers returned by these tools are CAL identifiers, not CAL-MCP identifiers. See [`../concepts/cal-identifiers.md`](../concepts/cal-identifiers.md).

## `cal_text_catalogue`

```text
cal_text_catalogue(category_id: string | null = null)
```

With no `category_id`, the tool requests the current root text catalogue. With a CAL category identifier, it requests exactly that one catalogue level.

The result contains three ordered collections, each preserving order within its own route family:

- `categories`: ordinary CAL category references with `category_id` and rendered `label`;
- `texts`: CAL text references with decimal `file_id`, optional `subtext_id` in CAL's current digits-plus-optional-lowercase-suffix grammar, rendered `label`, and optional `description` when that surface provides one;
- `specialized_collections`: CAL-MCP routing references for current CAL branches that cannot be represented truthfully as a decimal generic category. Each item names a `follow_up_tool`, its `selector_name`, and the selectors supported by this CAL-MCP build.

Every catalogue result also includes two traversal facts for machine callers:

- `recursive` is always `false` for the current operation: the result describes only the single CAL catalogue level explicitly requested;
- `has_unexpanded_children` is `true` when the returned level exposes at least one ordinary `category` or `specialized_collection` that can be followed explicitly.

`has_unexpanded_children=false` means only that this returned level exposes no recognized child catalogue/specialized navigation. It does not prove that CAL's corpus has been exhaustively enumerated or that no other CAL route family exists. In particular, callers must not interpret the direct root `texts` array as a corpus-global inventory when child navigation is present.

On a cache miss, an explicit call submits one logical CAL request. A completed cache hit performs zero new upstream I/O. CAL-MCP does not recursively expand returned categories. A caller that wants another level must explicitly call the tool again with the returned `category_id`.

CAL's current root text browser routes the **Targums Onkelos and Jonathan to the Prophets** collection through a dedicated CAL page rather than an ordinary `showsubtexts.php` link. CAL-MCP preserves that branch in root discovery as category `51`. An explicit `cal_text_catalogue(category_id="51")` call targets only that dedicated collection page and returns its ordered children using the normal result shapes: subdivided sources such as `51001 TgO Gn` remain `categories`, while direct sources such as `51400 MegTan (Megillat Taanit)` remain `texts`. The dedicated route stays adapter-private, no child is prefetched, and follow-up retrieval remains a separate caller-controlled action.

CAL's current root text browser likewise routes **Mandaic** through a dedicated collection page rather than the ordinary catalogue hierarchy. CAL-MCP preserves that branch as category `74`. An explicit `cal_text_catalogue(category_id="74")` call targets only that Mandaic catalogue and preserves CAL's two route families: current `showsubtexts.php?subtext=<file>&cset=R` entries are returned as `categories`, while current `get_a_chapter.php?file=<file>&cset=R` entries are returned as direct `texts`. The current catalogue has 12 subdivided categories and 8 direct texts (rechecked 2026-10-01). Following one returned Mandaic category with another explicit `cal_text_catalogue(category_id=<file>)` call returns its ordered children as `texts`, each carrying the parent `file_id` and CAL's exact `subtext_id`. Those selectors are not page numbers: current values include leading-zero forms, sparse numeric forms, one-digit forms, and the literal `col` on file `74421`. The `cset` values remain adapter-private rendering selectors: `R` is Roman CAL code on the current top-level catalogue, `J` is used by the current child catalogue links, and `M` is Standard Transliteration on text-page requests. CAL's group headings and "not currently available" notes are navigation, not texts, and are not returned. Each child row's information link normally names `file_id + subtext_id`; on Ginza Rabba (`74410`, 395 `page N` rows) every row's link names the parent file instead, and CAL-MCP accepts exactly those two forms. Order and duplicate titles are preserved (for example `74423` and `74923`). No returned category or text is fetched automatically: every catalogue expansion and page retrieval is a separate caller-controlled request.

CAL's root **Syriac** branch is different again: its current target is the dedicated `AvailSyr.html` classification surface and has no researched decimal generic category identifier. CAL-MCP therefore does not fabricate one. Root `cal_text_catalogue()` returns it in `specialized_collections` with `collection_key="syriac"`, CAL's rendered label, `follow_up_tool="cal_syriac_texts"`, `selector_name="category"`, and the ordered public category selectors supported by the same configuration used by `cal_syriac_texts`. Choose one returned selector and make a separate explicit `cal_syriac_texts(category=...)` call. Root discovery does not fetch `AvailSyr.html`, enumerate its children, or add another CAL request; the selector vocabulary is deterministic local adapter metadata.

`category_id` is validated as an opaque decimal CAL identifier. It is preserved as a string rather than converted to an integer so the adapter does not erase potentially meaningful leading zeroes. The one exception is a Christian Palestinian Aramaic catalogue node returned by `cal_text_search`: CAL addresses some of these with a letter-suffixed identifier such as `5500056125a`. Such an identifier is accepted only when it is an observed subdivided CPA file (for example `55000`) followed by a subtext in the ordinary grammar (digits plus an optional single lowercase letter). It is passed to CAL whole and never split into a file and subtext: follow it with `cal_text_catalogue`, which returns the node's text (`55000`/`56125a`) for `cal_text_page`. Any other letter-bearing `category_id` is rejected locally.

CAL's "View in" script control on a catalogue page (for example `Syriac`/`Roman` on Peshitta book `62043`, `Serto`/`CPA` on CPA node `55400122`) re-renders the same node in another script. It is navigation, not a sub-category, so `cal_text_catalogue` never returns it in `categories`. Only a link to the page's own node with a `script` selector is treated this way; a link to any other node is returned as usual. On a letter-suffixed CPA node such as `5500056125a`, CAL's toggle names the suffix-less `5500056125`; that exact form is treated as the page's own toggle too.

## `cal_text_search`

```text
cal_text_search(query: string)
```

This tool submits one query to CAL's current text/topic search surface. It does not expand synonyms, perform semantic search, rerank results, or fetch the returned texts.

The result contains:

- `matches`: ordered CAL search results, each with `file_id`, `subtext_id`, `category_id`, `label`, `description`, and `follow_up_tool` naming the tool that reads it. For `cal_text_page`, pass `file_id` and any `subtext_id`; `category_id` is `null`. For `cal_text_catalogue`, pass `category_id`; `file_id` and `subtext_id` are `null`;
- `provenance.original_query`: exactly what the caller supplied;
- `provenance.submitted_query`: the bounded query sent to CAL after deterministic ASCII-space cleanup;
- CAL source URL and retrieval timestamp.

Current CAL searches may return ordinary text links or `showsubtexts.php` catalogue nodes. A current Mandaic search hit such as Ginza Rabba uses the upstream `cset=M` / `subtext=<file>` collection link; CAL-MCP therefore returns `category_id=<file>` and `follow_up_tool: "cal_text_catalogue"`, not a fabricated direct text. Follow that category explicitly to obtain CAL's real child `subtext_id` values, then pass a returned `file_id` + `subtext_id` to `cal_text_page`. The same composition applies to non-Mandaic catalogue-node results: for example, `cal_text_search("Neofiti")` returns Targum Neofiti `54001`, `"Onkelos"` returns `70703012` (HS 3030), and `"Peshitta"` returns biblical books such as `62001` alongside the directly readable `62018`. Christian Palestinian Aramaic nodes use CAL's CPA script selector (`cset=C`) and may carry a letter-suffixed identifier: `cal_text_search("John")` returns, for example, `5500056125a` ("John 13:15-16:9 Cambridge TS") and `55400122` as `category_id` values. `cset=C` is accepted only on identifiers formed from an observed subdivided CPA file; elsewhere it remains parser drift. A direct `get_a_chapter.php` search result remains `follow_up_tool: "cal_text_page"`.

CAL separates a search result's label from its description with a colon followed by whitespace. A colon inside a label, as in a verse range such as `John 13:15-16:9`, is kept as part of the label. A `": "` inside parentheses is also part of the label: `JElet (Jacob of Edessa: Letter to John the Stylite of Litarab)` is returned whole. When a row's parentheses do not balance, CAL-MCP cannot tell where the label ends and splits at the first `": "`. Search submits at most one new logical CAL request and never follows a returned result automatically; each catalogue/page step is caller-controlled and a completed cache hit performs zero new upstream I/O.

CAL echoes the term it actually searched ("CAL search for texts like: …"), and that term can differ from the query: CAL drops characters it does not search on. For example, `Aḥiqar` is searched as `Aiqar` and `Tel-Dan` as `TelDan`, while a query with no searchable characters (`מלכא`, `!!!`) is rejected with `"" is not a valid search string`. CAL-MCP never returns a rewritten term's results under the original query. When CAL's echo differs from `submitted_query`, or CAL rejects the query, the tool returns a typed `invalid_input` error with `upstream_reached: true` naming CAL's term, so the caller can retry explicitly. Use the ASCII titles and sigla CAL uses (for example `Ahiqar`, `Tel Dan`).

CAL currently renders an explicit no-files message when a topic search has no matches. CAL-MCP maps that recognized upstream state to `matches: []`. A successful HTML page that has neither recognizable text results nor CAL's explicit no-files marker is treated as parser drift rather than silently interpreted as an empty result.

Blank queries and unsupported non-ASCII whitespace fail locally before any CAL request is made.

## `cal_text_information`

```text
cal_text_information(
    file_id: string,
    subtext_id: string | null = null,
)
```

CAL text pages expose a dedicated **Text Information** follow-up containing source-corpus, edition, editorial, numbering, manuscript/findspot, bibliography, photo, and quality/caution notes depending on the corpus. The structure is heterogeneous, so CAL-MCP preserves the ordered rendered metadata text instead of inventing fields such as `edition`, `manuscript`, or `bibliography` that CAL does not mark consistently.

Use a `file_id` and optional `subtext_id` already returned by text discovery/page operations. `file_id` remains decimal. Ordinary/CPA `subtext_id` values use decimal digits with an optional single lowercase ASCII letter suffix; CAL currently uses suffix-bearing values such as `01001a` for Christian Palestinian Aramaic. For known subdivided Mandaic files, the exact returned selector is also accepted, including the current literal `col` on `74421`. CAL-MCP keeps the returned string unchanged, including leading zeroes; `col` is not accepted for non-Mandaic files. Internally the private CAL selector is deterministic:

```text
subtext_id is null -> coord=<file_id>
subtext_id present -> coord=<file_id><subtext_id>
```

The private `coord` parameter is not exposed in the MCP schema and arbitrary CAL URLs are not accepted. One explicit tool call submits at most one new logical CAL request to `get_file_info.php`. A completed cache hit performs zero new upstream I/O. Links rendered inside CAL metadata are never followed automatically.

The result contains:

- `status`: `found` or `not_found`;
- the requested `file_id` and optional `subtext_id`;
- `metadata`: ordered CAL-rendered text strings for `found`, otherwise an empty list;
- provenance with the actual CAL source URL, retrieval timestamp, operation name, and requested identifiers.

CAL currently exposes the explicit missing-information state:

```text
Text Information
No information on record for this text.
```

Only that recognized semantic state maps to `status: "not_found"`. An HTTP-success page with the heading but no content, CAL's generic anti-scrape/maintenance output, unrelated HTML, or a page whose missing marker is mixed with ordinary metadata is parser drift rather than a fabricated empty result. HTTP status/body size alone is never used to infer that metadata is missing.

This operation is an explicit scholarly-provenance follow-up. `cal_text_catalogue`, `cal_text_search`, and `cal_text_page` do not prefetch it.

## `cal_text_line_comments`

```text
cal_text_line_comments(coordinate: string)
```

Use the exact `coordinate` returned on a caller-selected `TextLine` from `cal_text_page`. CAL line coordinates are opaque ASCII-alphanumeric identifiers on this route; CAL-MCP accepts 1–64 ASCII letters/digits and does not accept a `comment_url`, arbitrary CAL path, or arbitrary query selectors.

One explicit call submits at most one new logical CAL request. A completed cache hit performs zero new upstream I/O. Returned lexicon-entry links are validated and preserved as metadata but are never followed automatically.

The result contains `status: "found" | "no_citations"`, the requested coordinate, ordered `records`, and provenance. Each found record preserves CAL's rendered reference, optional source citation text, optional translation/comment text, the opaque returned `lemma_key`, rendered headword, optional part of speech, optional gloss, and validated same-origin entry URL.

CAL's exact `NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED` state maps to `no_citations` with an empty record list. It does **not** map to `not_found`: current CAL returns the same state for a deliberately invalid coordinate, so this endpoint alone cannot prove whether the line exists.

Malformed response identity, contradictory empty-state/content combinations, structurally incomplete records, foreign or malformed entry links, repeated/empty lemma selectors, and unrecognized successful markup fail closed as parser drift. `cal_text_page` does not prefetch comments for any line.

## `cal_text_page`

```text
cal_text_page(
    file_id: string,
    subtext_id: string | null = null,
    page: integer = 1,
)
```

This tool retrieves exactly one page from CAL's text browser. CAL-MCP keeps CAL's ordinary route and the current mixed direct/subdivided Mandaic collection-74 routes behind the same public operation. Route classification is private adapter metadata derived from current CAL navigation; it is not inferred from the `74` prefix at request time. The `74` prefix identifies only the Mandaic collection boundary; it does not tell CAL-MCP whether a particular file uses the direct or subdivided page route.

### Subtexts

Pass `subtext_id` exactly as CAL returned it from `cal_text_catalogue`, a KWIC hit, or another text result, including leading zeroes. For ordinary and CPA routes, the accepted current grammar is one or more decimal digits plus an optional single lowercase ASCII letter; Christian Palestinian Aramaic currently uses both suffix-bearing selectors such as `01001a` and decimal selectors such as `002`. For Mandaic, known subdivided files use the selectors returned by their child catalogue. These are preserved exactly and may be sparse or differently padded; the current file `74421` additionally exposes the literal selector `col`. That literal is accepted only for evidence-backed Mandaic subdivided files and does not widen ordinary/CPA input grammar. For the current evidence-backed CPA file set, text-page requests and page-navigation links retain CAL's private `cset=C` selector regardless of whether a particular subtext has a suffix; four current CPA files are direct routes with no `subtext_id`. Known direct CPA files reject a supplied `subtext_id`, while known subdivided CPA files require one, so caller input cannot manufacture a route shape absent from the current catalogue. Current paginated direct CPA `55430` additionally returns navigation links with the exact private selectors `sub=&clen=5`; CAL-MCP validates that narrow returned-link variant without adding those selectors to the caller's request or widening subdivided routes. This routing is keyed by observed CPA file identity, not by the `55` prefix or the presence of a letter. Current plain/unlemmatized CPA `55430` rows are preserved as described below. Current direct CPA `55002` is still catalogued, but CAL explicitly reports that no lines are stored; `cal_text_page` therefore returns `not_found` with `page: null`. Other letter placement, multiple-letter suffixes, uppercase suffixes, punctuation, whitespace, and arbitrary strings are rejected locally.

For ordinary decimal subtexts, CAL matches the `sub` selector as a **prefix**, and CAL-MCP cannot tell from the returned page whether that happened. For example, `cal_text_page("56000", subtext_id="11")` returns CAL's page for every Samaritan Targum subtext starting with `11` (Genesis chapters 12–19 as of 2026-09-25), under CAL's label for the first one, "SamTgJ Gen chapter 12". CAL-MCP returns that page as CAL renders it and does not pad or reinterpret the value. Every returned line keeps its own CAL `coordinate`, which embeds the line's real subtext after the file identifier. Some such pages fail closed instead, when their lines do not follow the ordinary coordinate format (for example magic bowls `70700` with `1`).

CAL identifies the text on a subdivided page by a file-information link whose coordinate is the file identifier followed by the submitted `sub` value (for example `56000112` for `56000`/`112`, and `5500001001a` for CPA `55000`/`01001a`; since 2026-09). CAL-MCP accepts that exact composed coordinate, or the bare file identifier used by the earlier layout, and fails closed on any coordinate naming a different file or subtext.

CAL also lists some Syriac texts under a six-digit id that is itself a file plus a trailing decimal subtext (one digit in both known cases): `634081` (Tamar and Judah) is CAL file `63408`, sub `1`, and `634082` (The Sleepers of Ephesus) is sub `2` (CAL evidence 2026-09-25 and 2026-09-29). `cal_syriac_texts` returns them as `text` items, and `cal_text_page("634081")` reads them under that id: `text.file_id` stays `634081`, and line coordinates start with `634081`. On those pages CAL's file-information label shows only the file (`63408: Tamar and Judah`) and CAL's own links use `file=63408&sub=1`. CAL-MCP accepts that label only when the page's own text links name exactly that file and sub, and every line coordinate must then start with the requested id; any other label prefix fails closed. Previous/next navigation is checked against CAL's file and sub.

### Page numbering

The MCP parameter is deliberately **one-based**: `page=1` means the first displayed CAL page. For ordinary text pages, CAL's current internal `page` parameter is zero-based. Current Mandaic uses the same distinction between **subtext identity** and **pagination**. Known subdivided files require the exact `subtext_id` returned by their child catalogue; public `page` then selects a rendered page within that same subtext and maps to CAL's private zero-based `page` selector. Among current direct Mandaic files, only `74501` has independently observed pagination and therefore accepts public `page>1` without a public subtext. The other current direct files (`74420`, `74424`, `74425`, `74426`, `74427`, `74429`, `74431`) and legacy direct `74717` remain page-1-only until CAL supplies researched pagination semantics for those exact files. These private route differences do not add discovery requests: each explicit page call submits at most one new logical CAL request; a completed cache hit performs zero new upstream I/O.

For a paginated text, the result may contain:

- `page`: displayed one-based page number;
- `page_count`: total number of rendered CAL pages when CAL reports one;
- `total_lines`: total line count CAL reports (`null` if no pagination marker on the page shows it);
- `previous_page` and `next_page`: explicit one-based navigation targets when CAL renders them.

Some short CAL texts are not rendered with a page-count marker. Ordinary unpaginated pages are returned as page 1 with `page_count`, `total_lines`, `previous_page`, and `next_page` set to `null`.

Ordinary paginated Mandaic navigation must preserve `cset=M`, the same file, and the same selected subtext (or CAL's empty private `sub` value for a direct text); only CAL's private zero-based `page` changes to the adjacent page. Returned `clen=5` is accepted only on an observed navigation shape.

**Ginza Rabba file `74410` is a narrowly evidenced exception.** CAL's Petermann **page** is represented as one subtext, so the captured `74410/001` page presents a `next page` link to **subtext `002`** with private `page=0`. CAL-MCP returns `next_subtext_id: "002"` and `next_page: null`: this is **cross-subtext navigation**, not page 2 of `001`. The additive `previous_subtext_id` and `next_subtext_id` fields are null unless CAL explicitly provides an adjacent, same-file, Mandaic `page=0` link. A caller may choose to fetch the new subtext by a **separate** explicit `cal_text_page(file_id="74410", subtext_id="002")` request. The adapter never follows it automatically or infers the next ID from arithmetic alone. Other Mandaic files' cross-subtext links still fail closed. Short or legacy direct pages may still have no page-count marker; CAL-MCP does not invent `page_count` or `total_lines` when CAL does not provide them.

CAL renders the pagination marker (`Page N of M (T lines total)`) alongside its previous/next, `show all` and manuscript-variants links, and repeats it without the line total below the text. CAL-MCP reads every copy, requires them to agree, and fails closed on a marker it cannot read exactly. `show all` and the variants toggle are not exposed.

A `page` beyond the last page is an `invalid_input` error whose message names the last page. CAL itself silently shows its last page for such a request: the final `Page N of N` of a paginated text, or the only page of a short text that has no pagination marker and no navigation. Any other page mismatch is `parser_drift`.

For a successful requested-page operation, the page CAL renders or explicitly selects must remain consistent with the caller's one-based `page`. If CAL supplies contradictory page metadata or non-adjacent navigation, CAL-MCP fails closed as parser drift rather than returning contradictory page/provenance metadata.

For ordinary pagination, previous/next links must address the same `file_id` and `subtext_id` as the requested page and point to the adjacent in-range page implied by CAL's pagination marker. Mandaic previous/next links are held to the same scholarly identity rule while also retaining the exact current private `cset=M` route. Foreign files/subtexts, changed script selectors, malformed selectors, and non-adjacent page targets are parser drift. Missing previous/next links are not invented.

CAL's current browser also exposes a `show all` navigation path. CAL-MCP **does not expose it** because it defeats the bounded-request contract. Moving to another page requires another explicit `cal_text_page` call.

### Text and line fields

A found page has a `text` reference plus ordered `lines`. Each line preserves the CAL relationships that are explicit in the current page:

- `coordinate`: CAL's machine/line coordinate when CAL exposes one, otherwise `null` on current plain/unlemmatized rows; linked token rows use the token coordinate, while some plain rows expose only a comment/line coordinate;
- `display_coordinate`: the rendered scholarly line/page locator when CAL supplies one;
- `text`: the rendered text of that line;
- `tokens`: ordered rendered linked tokens, each with the CAL machine coordinate, zero-based CAL `word_index`, rendered token text, and absolute `lexical_url`;
- `empty_word_indexes`: ordered CAL word indexes for explicit empty `getlex.php` lexical slots on current fragmentary rows; normally empty;
- `comment_url`: CAL's line-comment URL when CAL renders one; when that line also has a non-null `coordinate`, it can be passed to `cal_text_line_comments` in a separate explicit call.

Current lemmatized pages render each line as a two-cell table row with a display-coordinate cell and lexical token links. The coordinate cell is either CAL's line-comment link, whose text is the display coordinate (for example `Gen12:01)0(`), or plain text (for example `001:01`, `ms01 pg002 sd1 ln15`), sometimes followed by CAL's "[ai]" Ask-AI link, which CAL-MCP does not expose. `comment_url` is set exactly when CAL renders a comment link for the line. CAL-MCP fails closed on malformed row shapes, foreign links, a comment/Ask-AI link naming another line, loose text between tokens, or token links outside the text rows. Token text is kept as CAL renders it, including editorial angle brackets that CAL sometimes leaves unescaped in its HTML, such as `<w)th`. A bracket that happens to look like an HTML tag, such as a bare `<wmr>`, cannot be told apart from markup. CAL-MCP then fails closed instead of dropping it: any element in a text row other than CAL's links, spans and `<cal-variant>` is rejected.

Current CAL also has **plain/unlemmatized two-cell rows** (rechecked on Mandaic `74420` and direct CPA `55430`). The first cell is the rendered display coordinate and the second is rendered scholarly text, but there are no lexical token links. CAL-MCP returns these with `tokens: []` and `empty_word_indexes: []`. If CAL supplies no line link, `coordinate` is `null`; if the first cell is exactly a validated `comment.php?coord=...` link, its line/comment coordinate and `comment_url` are preserved. That coordinate does not create a token-analysis handle: use `cal_token_analysis` only with a returned token's own `coordinate` + `word_index`. A plain row with `coordinate: null` cannot be followed with `cal_text_line_comments`. Sampled current text tables are homogeneous; CAL-MCP fails closed if one table mixes linked and plain rows. An empty `text-display` shell is never treated as a successful plain line. Current direct CPA `55002` accompanies that shell with CAL's explicit no-lines marker and therefore maps to the documented `not_found` state below.

CAL also renders explicit empty lexical slots on some fragmentary Syriac rows. Current CAL uses empty relative `getlex.php` anchors with the same machine coordinate as the rendered tokens, a non-negative `word` index, and `hasvariant=0`. CAL-MCP keeps rendered links in `tokens` and preserves the empty slots separately in `empty_word_indexes`. Thus an all-empty row can have `text: ""`, `tokens: []`, and `empty_word_indexes: [0]`; a mixed row keeps its rendered text/tokens and records the empty indexes alongside them. The adapter does not invent token text. Altered routes/selectors, coordinate disagreement, duplicate empty indexes, or an empty index colliding with a rendered token fail closed.

CAL currently exposes lexical token links through more than one endpoint family, including `bablex.php` and `getlex.php`. CAL-MCP preserves whichever lexical URL the page supplies and applies coordinate/word-index validation to both. On suffix-bearing CPA pages, each returned machine coordinate must begin with the exact requested `file_id + subtext_id` and continue with a decimal tail; a coordinate for another subtext fails closed. Current Mandaic uses a few additional opaque, narrowly scoped token-coordinate forms: direct `74425` accepts forms including `7442500a` and `74425231aa`, direct `74429` accepts forms including `74429A01`, and the exact subdivided text `74421/col` returns coordinates such as `74421col13614`. Those researched families are accepted only under their matching file or file/subtext identity; numeric `74421` subtexts stay on the ordinary decimal path. CAL-MCP does not infer a missing coordinate, normalize the returned handle, reconstruct a display locator, or call a token link automatically. The `lexical_url` is provenance/navigation information; use the returned token's exact `coordinate` + `word_index` with `cal_token_analysis` in a separate explicit caller-controlled step.

### Missing text and parser drift

The current CAL text browser sometimes reports a missing file/subtext selection—or a catalogued text for which CAL currently stores no lines, such as direct CPA `55002`—as an HTTP-success page containing CAL's explicit `NO LINES FOR ... ARE CURRENTLY STORED` message. The marker may share one semantic line with CAL's manuscript-variants toggle; CAL-MCP removes only the validated rendered toggle label and then requires the remaining no-lines marker to match the requested file identity exactly. CAL-MCP represents that state as:

```text
status: "not_found"
page: null
```

A recognized page with text returns `status: "found"`. Transport/content failures remain request errors, while an unrecognized successful page raises parser-drift failure. Malformed identifiers found in CAL's returned links are also parser drift (`TextParseError`); invalid caller-supplied identifiers remain local request-validation errors before transport. These states are intentionally distinct.

## Request bounds

Every explicit public text operation submits at most one new logical CAL request to the shared client. A completed cache hit performs zero new upstream I/O, and an identical simultaneous call can be a single-flight follower without duplicating the active request. Retryable failures may consume bounded retry transport attempts under the shared retry policy. These mechanisms do not create hidden background work.

The operation-level bounds remain:

- no recursive catalogue expansion or specialized-collection prefetch;
- no automatic traversal to previous/next pages;
- no automatic text-information lookup from discovery/page results;
- no automatic line-comment lookup from page results;
- no metadata-link traversal;
- no route-discovery request before Mandaic page retrieval;
- no `show all` request;
- no prefetch of text-search matches;
- no token lexical-analysis requests;
- no background indexing or corpus mirror.

The shared HTTP client still applies its timeout, origin, redirect, concurrency, retry, cache, and maximum-response-byte policies.

## Provenance

Text results include adapter provenance with the CAL source URL and timezone-aware retrieval timestamp. Depending on the operation, provenance also records the requested `file_id`, `subtext_id`, `category_id`, one-based page, line coordinate, or original/submitted search query.

Returned CAL identifiers and coordinates should be stored together with that provenance. CAL-MCP preserves them for faithful follow-up calls but does not promise that CAL will keep an identifier stable forever.

## Fixture-backed examples

Offline tests use deliberately reduced semantic excerpts captured/rechecked on 2026-09-04 and 2026-09-08, plus the 2026-09-09 text-information contract and the 2026-09-10 line-comments contract. Representative cases include:

- root discovery of the dedicated Onkelos/Jonathan collection as category `51`, followed by one explicit catalogue call that keeps subdivided `51001` and direct `51400` child shapes distinct;
- root discovery of Mandaic as category `74`, followed by one explicit dedicated-catalogue call that returns subdivided `74401` as a category and direct `74501` as a text without fetching either child;
- root discovery of Syriac as an operation-aware `specialized_collections` item whose supported selectors compose explicitly with `cal_syriac_texts`, without fetching `AvailSyr.html`;
- a topic search for `Tel Dan` returning CAL file `13250`;
- a topic search for `Ginza` returning current Mandaic catalogue nodes `74410` and `74411` without following either child catalogue;
- a text-information lookup preserving Ephrem source/edition/editorial/quality notes in CAL order, plus CAL's explicit `No information on record for this text.` missing state;
- a paginated `BT AZ` page exposing page and machine-coordinate metadata;
- the short Tel Dan text, which has valid `getlex.php` token links but no page-count marker;
- a current subdivided Mandaic `74401/12` page using `cset=M`, preserving exact `sub=12`, and paginating independently through CAL's private zero-based `page` selector;
- a direct Mandaic page such as `74717`, which uses page 1 without an invented `sub=NNN` selector;
- CAL's explicit no-lines page for a nonexistent subtext.

The fixtures are parser contracts, not archived CAL pages. Normal CI performs zero CAL requests.
