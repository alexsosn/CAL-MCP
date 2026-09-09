# CAL text discovery, metadata, and page retrieval

CAL-MCP exposes four bounded tools for discovering CAL texts, retrieving CAL's explicit text-information metadata, and reading one rendered text page at a time. These tools adapt CAL's current public text interfaces; they do not create a local corpus, crawl categories, follow pagination automatically, follow metadata links, or call CAL's token-analysis endpoint.

## Which tool to use

| Goal | Tool |
| --- | --- |
| Browse the root CAL text catalogue | `cal_text_catalogue()` |
| Expand one catalogue category returned by CAL | `cal_text_catalogue(category_id=...)` |
| Find CAL texts by the topic/search phrase accepted by CAL | `cal_text_search(query)` |
| Retrieve CAL's detailed source/edition/editorial notes for one text or subtext | `cal_text_information(file_id, subtext_id=None)` |
| Retrieve one CAL text page | `cal_text_page(file_id, subtext_id=None, page=1)` |

The identifiers returned by these tools are CAL identifiers, not CAL-MCP identifiers. See [`../concepts/cal-identifiers.md`](../concepts/cal-identifiers.md).

## `cal_text_catalogue`

```text
cal_text_catalogue(category_id: string | null = null)
```

With no `category_id`, the tool requests the current root text catalogue. With a CAL category identifier, it requests exactly that one catalogue level.

The result contains two ordered collections:

- `categories`: CAL category references with `category_id` and rendered `label`;
- `texts`: CAL text references with `file_id`, optional `subtext_id`, rendered `label`, and optional `description` when that surface provides one.

On a cache miss, an explicit call submits one logical CAL request. A completed cache hit performs zero new upstream I/O. CAL-MCP does not recursively expand returned categories. A caller that wants another level must explicitly call the tool again with the returned `category_id`.

CAL's current root text browser routes the **Targums Onkelos and Jonathan to the Prophets** collection through a dedicated CAL page rather than an ordinary `showsubtexts.php` link. CAL-MCP preserves that branch in root discovery as category `51`. An explicit `cal_text_catalogue(category_id="51")` call targets only that dedicated collection page and returns its ordered children using the normal result shapes: subdivided sources such as `51001 TgO Gn` remain `categories`, while direct sources such as `51400 MegTan (Megillat Taanit)` remain `texts`. The dedicated route stays adapter-private, no child is prefetched, and follow-up retrieval remains a separate caller-controlled action.

`category_id` is validated as an opaque decimal CAL identifier. It is preserved as a string rather than converted to an integer so the adapter does not erase potentially meaningful leading zeroes.

## `cal_text_search`

```text
cal_text_search(query: string)
```

This tool submits one query to CAL's current text/topic search surface. It does not expand synonyms, perform semantic search, rerank results, or fetch the returned texts.

The result contains:

- `matches`: ordered CAL text references;
- `provenance.original_query`: exactly what the caller supplied;
- `provenance.submitted_query`: the bounded query sent to CAL after deterministic ASCII-space cleanup;
- CAL source URL and retrieval timestamp.

Current CAL searches may return ordinary text links or specialized Mandaic collection links. CAL-MCP maps both to the same `TextRef` result shape. For current Mandaic hits such as Ginza Rabba, the specialized upstream `cset=M` / `subtext=<file>` link stays adapter-private: the result exposes the CAL file identifier as `file_id`, keeps `subtext_id` as `null`, and preserves CAL's rendered label and description. That `file_id` can be passed directly to `cal_text_page(file_id, page=...)`, which applies the current Mandaic route classification internally. Search still submits at most one new logical CAL request and never follows a returned result link automatically; a completed cache hit performs zero new upstream I/O.

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

Use a `file_id` and optional `subtext_id` already returned by text discovery/page operations. CAL-MCP validates both as decimal identifiers and keeps the exact strings, including leading zeroes. Internally the private CAL selector is deterministic:

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

## `cal_text_page`

```text
cal_text_page(
    file_id: string,
    subtext_id: string | null = null,
    page: integer = 1,
)
```

This tool retrieves exactly one page from CAL's text browser. CAL-MCP keeps CAL's ordinary route and the current mixed direct/subdivided Mandaic collection-74 routes behind the same public operation. Route classification is private adapter metadata derived from current CAL navigation; it is not inferred from the `74` prefix at request time. The `74` prefix identifies only the Mandaic collection boundary; it does not tell CAL-MCP whether a particular file uses the direct or subdivided page route.

### Page numbering

The MCP parameter is deliberately **one-based**: `page=1` means the first displayed CAL page. For ordinary text pages, CAL's current internal `page` parameter is zero-based. Current CAL Mandaic navigation is heterogeneous: known subdivided files such as Ginza Rabba Right/Left (`74410`/`74411`) use the specialized `cset=M` route with a one-based `sub` selector such as `001`, `002`, or `1000`, while direct files such as `74501` and `74717` use a direct page-1 request with no `sub` or ordinary `page` field. A direct Mandaic request for `page>1` is rejected locally until CAL exposes a researched pagination contract for that route. These upstream forms remain adapter-private, and each supported public call submits at most one new logical CAL request; a completed cache hit performs zero new upstream I/O.

For a paginated text, the result may contain:

- `page`: displayed one-based page number;
- `page_count`: total number of rendered CAL pages when CAL reports one;
- `total_lines`: total line count CAL reports;
- `previous_page` and `next_page`: explicit one-based navigation targets when CAL renders them.

Some short CAL texts are not rendered with a page-count marker. Ordinary unpaginated pages are returned as page 1 with `page_count`, `total_lines`, `previous_page`, and `next_page` set to `null`.

Subdivided Mandaic pages can also omit a page-count marker while still rendering an adjacent previous/next link. For that private specialized route, CAL-MCP preserves the caller's explicit one-based page number and validates any rendered `cset=M` navigation as an adjacent page of the same file. Direct Mandaic page-1 responses use the ordinary/unpaginated parser semantics instead; they do not receive synthetic page numbering or relaxed specialized navigation. CAL-MCP does not invent `page_count` or `total_lines` when CAL does not provide them.

For a successful requested-page operation, the page CAL renders or explicitly selects must remain consistent with the caller's one-based `page`. If CAL supplies contradictory page metadata or non-adjacent navigation, CAL-MCP fails closed as parser drift rather than returning contradictory page/provenance metadata.

For ordinary pagination, previous/next links must address the same `file_id` and `subtext_id` as the requested page and point to the adjacent in-range page implied by CAL's pagination marker. For the subdivided Mandaic route, navigation must retain `cset=M`, target the same file, and select the adjacent decimal `sub` page. Direct Mandaic page-1 responses do not opt into that specialized navigation contract. Foreign files/subtexts, foreign Mandaic collection selectors, malformed selectors, and non-adjacent targets are parser drift. Missing previous/next links are not invented.

CAL's current browser also exposes a `show all` navigation path. CAL-MCP **does not expose it** because it defeats the bounded-request contract. Moving to another page requires another explicit `cal_text_page` call.

### Text and line fields

A found page has a `text` reference plus ordered `lines`. Each line preserves the CAL relationships that are explicit in the current page:

- `coordinate`: CAL's machine coordinate used by linked operations;
- `display_coordinate`: the rendered scholarly line/page locator when CAL supplies one;
- `text`: the rendered text of that line;
- `tokens`: ordered linked tokens, each with the CAL machine coordinate, zero-based CAL `word_index`, rendered token text, and absolute `lexical_url`;
- `comment_url`: CAL's line-comment URL when CAL renders one.

CAL currently exposes lexical token links through more than one endpoint family, including `bablex.php` and `getlex.php`. CAL-MCP preserves whichever lexical URL the page supplies and applies the same coordinate/word-index validation to both. It does not infer a missing coordinate, reconstruct a display locator, or call a token link automatically. The `lexical_url` is provenance/navigation information; use `cal_token_analysis` in a separate explicit caller-controlled step.

### Missing text and parser drift

The current CAL text browser sometimes reports a missing file/subtext selection as an HTTP-success page containing CAL's explicit `NO LINES FOR ... ARE CURRENTLY STORED` message. CAL-MCP represents that as:

```text
status: "not_found"
page: null
```

A recognized page with text returns `status: "found"`. Transport/content failures remain request errors, while an unrecognized successful page raises parser-drift failure. Malformed identifiers found in CAL's returned links are also parser drift (`TextParseError`); invalid caller-supplied identifiers remain local request-validation errors before transport. These states are intentionally distinct.

## Request bounds

Every explicit public text operation submits at most one new logical CAL request to the shared client. A completed cache hit performs zero new upstream I/O, and an identical simultaneous call can be a single-flight follower without duplicating the active request. Retryable failures may consume bounded retry transport attempts under the shared retry policy. These mechanisms do not create hidden background work.

The operation-level bounds remain:

- no recursive catalogue expansion;
- no automatic traversal to previous/next pages;
- no automatic text-information lookup from discovery/page results;
- no metadata-link traversal;
- no route-discovery request before Mandaic page retrieval;
- no `show all` request;
- no prefetch of text-search matches;
- no token lexical-analysis requests;
- no background indexing or corpus mirror.

The shared HTTP client still applies its timeout, origin, redirect, concurrency, retry, cache, and maximum-response-byte policies.

## Provenance

Text results include adapter provenance with the CAL source URL and timezone-aware retrieval timestamp. Depending on the operation, provenance also records the requested `file_id`, `subtext_id`, `category_id`, one-based page, or original/submitted search query.

Returned CAL identifiers and coordinates should be stored together with that provenance. CAL-MCP preserves them for faithful follow-up calls but does not promise that CAL will keep an identifier stable forever.

## Fixture-backed examples

Offline tests use deliberately reduced semantic excerpts captured/rechecked on 2026-09-04 and 2026-09-08, plus the 2026-09-09 text-information contract. Representative cases include:

- root discovery of the dedicated Onkelos/Jonathan collection as category `51`, followed by one explicit catalogue call that keeps subdivided `51001` and direct `51400` child shapes distinct;
- a topic search for `Tel Dan` returning CAL file `13250`;
- a topic search for `Ginza` returning the current specialized Mandaic file references `74410` and `74411` without following those links;
- a text-information lookup preserving Ephrem source/edition/editorial/quality notes in CAL order, plus CAL's explicit `No information on record for this text.` missing state;
- a paginated `BT AZ` page exposing page and machine-coordinate metadata;
- the short Tel Dan text, which has valid `getlex.php` token links but no page-count marker;
- a Ginza Rabba Right Side page using the current Mandaic `cset=M` / `sub=NNN` route and adjacent navigation without a rendered total page count;
- a direct Mandaic page such as `74717`, which uses page 1 without an invented `sub=NNN` selector;
- CAL's explicit no-lines page for a nonexistent subtext.

The fixtures are parser contracts, not archived CAL pages. Normal CI performs zero CAL requests.
