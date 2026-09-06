# Issue #47 research — current CAL lexicon browse drift

**Rechecked:** 2026-09-06  
**Issue:** #47  
**Surface:** `GET https://cal.huc.edu/browseSKEYheaders.php?first3=%22br%22`

## Trigger

The v0.1 release candidate live smoke run `34050614210` made one CAL request to the exact `br` browse URL, received HTTP 200, and then raised:

`LexiconParseError: CAL lexicon browse page contains neither entries nor explicit no-match`

The run consumed one request before stopping. It did not retry or traverse another CAL surface.

## Bounded current-source probes

Two branch-only one-request probes were used to isolate the structural cause. Each used a direct HTTPS GET, a 10-second timeout, no retry or redirect traversal, an honest CAL-MCP issue-specific User-Agent, and a 128 KiB response cap. Both returned HTTP 200, `text/html; charset=UTF-8`, and 20,108 bytes.

- Run `34054219555`: structural counts and short semantic summaries only.
- Run `34054342949`: a single raw-markup window around the first `br` candidate only.

The temporary workflow was deleted immediately after the probes. Normal CI remains offline.

## Current request and navigation contract

The request contract observed by the failed release smoke remains valid:

- method: `GET`;
- path: `/browseSKEYheaders.php`;
- query parameter: `first3="br"` (URL encoded as `%22br%22`);
- no redirect was returned.

The current response contained:

- 48 `oneentry.php` lemma links and zero `cal_entry_web.php` links;
- 52 anchors total including browser/navigation anchors;
- one `NEXT PAGE` control;
- a previous-range navigation anchor rendered as `⬅︎br, brˀ`;
- no explicit no-match marker for this successful query.

The adapter must therefore continue treating pagination as upstream navigation, not as permission for hidden automatic traversal. One lookup performs the requested browse step and, only when the caller selects an exact candidate, at most one explicit selected-entry fetch under the existing service contract.

## Current candidate semantics

The first current candidate is structurally:

```html
<td>
  <a href="oneentry.php?lemma=br N&cits=all" target="_self">
    <span class="lem"><font>br, brˀ</font></span>
    (<span class="uni">bar (ber), brā</span>)
    <pos>n.m.</pos>
  </a>
  <br>
  <span class="gloss">son</span>
</td>
```

The next current rows use the same semantics: the canonical CAL lemma key is carried by the `lemma` query parameter, the linked rendered text carries headword/pronunciation/POS, and the gloss follows the link after `<br>` in the same table cell. Examples observed in CAL order included `br N`, `br@)n$ N`, `br@gnwn N`, `br#2 N`, and later candidates. The current first probe also showed the rendered candidate block as header plus gloss, e.g. `br, brˀ (bar (ber), brā) n.m. son`.

No alias-arrow prefix occurred in the logged first candidate window. Existing dated browse evidence/fixtures retain CAL's separate alias-prefix form (`aliases → canonical link`), and nothing in the current `br` evidence contradicts that representation. The parser must preserve that compatibility rather than infer aliases from headword spelling.

## Reproduced parser failure mechanism

The candidate table itself is parseable. The failure originates earlier in the same current page, in CAL's jump table. Current jump cells contain anchor starts without explicit anchor end tags, for example the observed tail of the jump table is equivalent to:

```html
<td><a href=/browseSKEYheaders.php?first3="t"> &nbsp;t &nbsp;</td>
```

Browsers repair the malformed HTML by implicitly closing the anchor at the table-cell boundary. Python's `html.parser.HTMLParser` reports the tags literally and does not synthesize that `</a>`.

CAL-MCP's `_SemanticHTMLParser` currently keeps `_open_link` alive until it sees a literal matching `</a>`. Subsequent `<a>` starts therefore increase the open-link nesting depth instead of beginning independent links. By the time the valid candidate table starts, the real `oneentry.php` anchors are swallowed into the unterminated jump anchor and `parse_browse_page()` sees no lemma links. Because the page is successful rather than an explicit empty result, it correctly fails closed with `LexiconParseError`.

This explains why reduced browse fixtures containing well-formed anchors pass while the current full response fails.

## Required parser boundary

The smallest faithful correction is in semantic HTML extraction, not the public lexicon model or request contract:

- a table-cell/row/block boundary that necessarily ends the rendered link must close or discard an unterminated open anchor before the next semantic cell/row is parsed;
- the malformed jump/navigation anchor must not become a lemma candidate;
- valid candidate anchors inside their cells must still be emitted with exact href/text;
- candidate order, canonical `lemma` keys, headwords, pronunciation, POS, glosses, and existing alias handling remain unchanged;
- old well-formed browse fixtures must remain valid;
- a current-looking page with malformed candidate semantics must still fail closed;
- explicit no-match remains distinct from malformed/drift pages.

The correction must be narrowly scoped so that forgiving CAL's malformed navigation markup does not silently forgive malformed lexical candidate links or full-entry citation structure.

## Fixture reduction for TDD

The regression fixture only needs:

1. one or two malformed jump-table cells with unclosed `<a>` tags;
2. one well-formed candidate cell using the current nested `span`/`font`/`pos` link and `<br>` gloss shape;
3. optionally a second candidate to prove ordering and a navigation link to prove it is ignored.

It must not retain the full 20 KiB page or unrelated CAL lexical content.

## Architecture impact

No public MCP schema, request-volume policy, provenance contract, normalization rule, or durable architecture decision changes. This is an upstream-markup compatibility correction inside the existing lexicon anti-corruption boundary described by D-004 and D-007.
