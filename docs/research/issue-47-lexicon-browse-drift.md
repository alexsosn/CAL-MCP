# Issue #47 research — current CAL lexicon browse anchor drift

**Rechecked:** 2026-09-06

## Release-blocking observation

The v0.1 candidate smoke run `34050614210` stopped after its first CAL request:

```text
GET https://cal.huc.edu/browseSKEYheaders.php?first3=%22br%22
HTTP 200
```

`parse_browse_page` then raised `LexiconParseError: CAL lexicon browse page contains neither entries nor explicit no-match`. The smoke used concurrency 1, retries 0, cache disabled, and a hard nine-request ceiling. No entry fetch or later smoke operation occurred.

## Bounded current-shape probe

Branch-only run `34050940101` made exactly one fixed GET to the same browse URL with the project User-Agent and existing response-size/time limits. It returned:

- HTTP 200;
- `Content-Type: text/html; charset=UTF-8`;
- 20,108 bytes;
- 127 semantic lines;
- 48 raw `oneentry.php` anchors;
- no `cal_entry_web.php` anchors;
- the same `browseSKEYheaders.php?first3=...` browse contract.

No prefix enumeration, entry fetch, pagination walk, retry, or neighboring-query probe occurred. The temporary workflow and probe helper deleted themselves after the run.

## Current semantic result structure

The current page still renders the expected lexicon candidate information. Representative raw rows are structurally equivalent to:

```html
<td>
  <a href="oneentry.php?lemma=br N&cits=all">
    <span class="lem">br, brˀ</span>
    (<span class="uni">bar (ber), brā</span>)
    <pos>n.m.</pos>
  </a><br>
  <span class="gloss">son</span>
</td>
```

The 48 candidate anchors preserve canonical CAL lemma keys in the `lemma` query parameter. Glosses remain adjacent rendered text after the anchor. The request contract and lexicon candidate semantics therefore have not moved to a new endpoint or model.

## Actual drift source: malformed jump-menu anchors

Before the candidate table, CAL's current jump menu contains malformed anchors such as:

```html
<td><a href=/browseSKEYheaders.php?first3="b"> b </td>
<td><a href=/browseSKEYheaders.php?first3="g"> g </td>
```

The closing `</a>` tags are absent. Python's `html.parser.HTMLParser` is a token parser and does not perform browser-style HTML tree repair. CAL-MCP's `_SemanticHTMLParser` currently treats a new `<a>` encountered while an anchor is already open as a nested anchor by incrementing `_OpenLink.depth`.

HTML does not permit nested anchors. Because each malformed jump-menu `<a>` increases that synthetic depth, later valid lexicon candidate anchors are never finalized as independent `_Link` values. The probe therefore showed candidate text lines such as `br, brˀ ... n.m.` with `LINKS=[]` even while the raw page contained 48 valid `oneentry.php` hrefs.

This is a shared semantic-extractor recovery defect exposed by current CAL markup, not a lexicon-domain semantic change.

## Required parser behavior

When a new `<a>` start tag is encountered while another `<a>` is still open, the extractor should recover the same way a browser's HTML parser does conceptually: terminate the impossible prior anchor and start the new anchor. It must not model nested anchors.

The recovery must:

- preserve already collected visible text;
- finalize the prior anchor with its own href/text when it has text;
- allow the new anchor to become a separate `_Link`;
- preserve valid ordinary anchors unchanged;
- leave the existing `span.cit-ref-plain` synthetic-link handling unchanged;
- not convert malformed pages into empty results silently;
- retain existing explicit no-match recognition.

## Reduced regression shape

The deterministic fixture should include only the semantic defect needed to reproduce the live page:

1. at least two jump-menu `<a>` elements missing `</a>` before their `</td>` boundaries;
2. a later valid `oneentry.php?lemma=br N&cits=all` candidate anchor;
3. an adjacent gloss line;
4. a second valid candidate anchor to prove later anchors remain independent and ordered.

The fixture is a reduced structural regression, not an archived CAL page.

## Scope implications

No public MCP contract changes are required. `LexiconLookupService.lookup` should keep:

- the same `GET browseSKEYheaders.php?first3="..."` request;
- exact candidate filtering and ambiguity behavior;
- at most one selected `cal_entry_web.php` entry fetch after browse discovery;
- CAL order and canonical lemma keys;
- current provenance semantics.

Normal CI remains offline. After offline GREEN, one tiny fixed live confirmation against the reproduced browse request is sufficient before independent review.

## Sources

- `https://cal.huc.edu/browseSKEYheaders.php?first3=%22br%22`
- issue #47
- release candidate smoke run `34050614210`
- one-request research run `34050940101`
