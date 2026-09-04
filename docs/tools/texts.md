# CAL text discovery and page retrieval

CAL-MCP exposes three bounded tools for discovering CAL texts and retrieving one rendered text page at a time. These tools adapt CAL's current public text interfaces; they do not create a local corpus, crawl categories, follow pagination automatically, or call CAL's token-analysis endpoint.

## Which tool to use

| Goal | Tool |
| --- | --- |
| Browse the root CAL text catalogue | `cal_text_catalogue()` |
| Expand one catalogue category returned by CAL | `cal_text_catalogue(category_id=...)` |
| Find CAL texts by the topic/search phrase accepted by CAL | `cal_text_search(query)` |
| Retrieve one normal CAL text page | `cal_text_page(file_id, subtext_id=None, page=1)` |

The identifiers returned by these tools are CAL identifiers, not CAL-MCP identifiers. See [`../concepts/cal-identifiers.md`](../concepts/cal-identifiers.md).

## `cal_text_catalogue`

```text
cal_text_catalogue(category_id: string | null = null)
```

With no `category_id`, the tool requests the current root text catalogue. With a CAL category identifier, it requests exactly that one catalogue level.

The result contains two ordered collections:

- `categories`: CAL category references with `category_id` and rendered `label`;
- `texts`: CAL text references with `file_id`, optional `subtext_id`, rendered `label`, and optional `description` when that surface provides one.

A call performs **one CAL request**. CAL-MCP does not recursively expand returned categories. A caller that wants another level must explicitly call the tool again with the returned `category_id`.

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

CAL currently renders an explicit no-files message when a topic search has no matches. CAL-MCP maps that recognized upstream state to `matches: []`. A successful HTML page that has neither recognizable text results nor CAL's explicit no-files marker is treated as parser drift rather than silently interpreted as an empty result.

Blank queries and unsupported non-ASCII whitespace fail locally before any CAL request is made.

## `cal_text_page`

```text
cal_text_page(
    file_id: string,
    subtext_id: string | null = null,
    page: integer = 1,
)
```

This tool retrieves exactly one normal page from CAL's text browser.

### Page numbering

The MCP parameter is deliberately **one-based**: `page=1` means the first displayed CAL page. CAL's current internal page parameter is zero-based; that detail remains adapter-private.

For a paginated text, the result may contain:

- `page`: displayed one-based page number;
- `page_count`: total number of rendered CAL pages;
- `total_lines`: total line count CAL reports;
- `previous_page` and `next_page`: explicit one-based navigation targets when CAL renders them.

Some short CAL texts are not rendered with a page-count marker. In that case CAL-MCP does not invent pagination metadata: the observed page is returned as page 1 and `page_count`, `total_lines`, `previous_page`, and `next_page` are `null`.

For a successful requested-page operation, the page CAL renders must match the caller's one-based `page`. If CAL returns a different displayed page, or returns an unpaginated page-1 shape for a request after page 1, CAL-MCP fails closed as parser drift rather than returning contradictory page/provenance metadata.

When CAL renders a previous/next link, CAL-MCP also requires that link to address the same `file_id` and `subtext_id` as the requested page and to point to the adjacent in-range page implied by CAL's pagination marker. Navigation without a pagination marker, foreign text/subtext targets, or non-adjacent/out-of-range targets are parser drift. Missing previous/next links are not invented.

CAL's current browser also exposes a `show all` navigation path. CAL-MCP **does not expose it** because it defeats the bounded-request contract. Moving to another page requires another explicit `cal_text_page` call.

### Text and line fields

A found page has a `text` reference plus ordered `lines`. Each line preserves the CAL relationships that are explicit in the current page:

- `coordinate`: CAL's machine coordinate used by linked operations;
- `display_coordinate`: the rendered scholarly line/page locator when CAL supplies one;
- `text`: the rendered text of that line;
- `tokens`: ordered linked tokens, each with the CAL machine coordinate, zero-based CAL `word_index`, rendered token text, and absolute `lexical_url`;
- `comment_url`: CAL's line-comment URL when CAL renders one.

CAL-MCP does not infer a missing coordinate, reconstruct a display locator, or call a token link automatically. The `lexical_url` is provenance/navigation information; public token-at-coordinate analysis is a separate capability tracked by issue #8.

### Missing text and parser drift

The current CAL text browser sometimes reports a missing file/subtext selection as an HTTP-success page containing CAL's explicit `NO LINES FOR ... ARE CURRENTLY STORED` message. CAL-MCP represents that as:

```text
status: "not_found"
page: null
```

A recognized page with text returns `status: "found"`. Transport/content failures remain request errors, while an unrecognized successful page raises parser-drift failure. Malformed identifiers found in CAL's returned links are also parser drift (`TextParseError`); invalid caller-supplied identifiers remain local request-validation errors before transport. These states are intentionally distinct.

## Request bounds

Every public text tool performs exactly one user-initiated CAL request:

- no recursive catalogue expansion;
- no automatic traversal to previous/next pages;
- no `show all` request;
- no prefetch of text-search matches;
- no token lexical-analysis requests;
- no background indexing or corpus mirror.

The shared HTTP client still applies its timeout, origin, redirect, concurrency, retry, cache, and maximum-response-byte policies.

## Provenance

Text results include adapter provenance with the CAL source URL and timezone-aware retrieval timestamp. Depending on the operation, provenance also records the requested `file_id`, `subtext_id`, `category_id`, one-based page, or original/submitted search query.

Returned CAL identifiers and coordinates should be stored together with that provenance. CAL-MCP preserves them for faithful follow-up calls but does not promise that CAL will keep an identifier stable forever.

## Fixture-backed examples

Offline tests use deliberately reduced semantic excerpts captured/rechecked on 2026-09-04. Representative cases include:

- a topic search for `Tel Dan` returning CAL file `13250`;
- a paginated `BT AZ` page exposing page and machine-coordinate metadata;
- the short Tel Dan text, which has valid text lines but no page-count marker;
- CAL's explicit no-lines page for a nonexistent subtext.

The fixtures are parser contracts, not archived CAL pages. Normal CI performs zero CAL requests.
