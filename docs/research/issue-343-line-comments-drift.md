# Issue #343 — live CAL line-comments parser drift research

**Date:** 2026-11-15 UTC. Main source baseline `55a9d26942467431e809c567f31f81068f41ce46`.

## Exact observed failure

[Installed-wheel dependent smoke run #43735329113](https://github.com/alexsosn/CAL-MCP/actions/runs/43735329113), source SHA `5c5033ce0229044423ea053ba71b8f55eadfd104`, tried 21 reviewed MCP steps with hard 25 CAL starts/60-second spacing/no retries. It stopped after five measured CAL transport starts:
1. `cal_lexicon_lookup(query="br",lemma_key="br N")` — PASS.
2. `cal_lexicon_citation_context(full_coordinate=<coordinate from live lexicon>)` — PASS.
3. `cal_text_page(file_id="13250",page=1)` — PASS.
4. `cal_text_line_comments(coordinate=<a live returned TextLine.coordinate, comment_url preferred>)` — **`parser_drift`**.

The report does not disclose which exact CAL line coordinate was used or the source HTML, so a parser change is **not yet justified**. No 429, network, or SDK failure occurred.

## Evidence from checked-in code

- `src/cal_mcp/texts.py:parse_text_line_comments_page` verifies `comment.php?coord=<requested_coordinate>`, exact unique `CAL: citations and comments for <coordinate>` title, exactly one summary card, and either exactly one `NO CITATIONS FOR THIS LINE ARE CURRENTLY BEING USED` marker or structured records with unique reference/expected spans/link ordering. Unexpected markup is intentionally `TextParseError`.
- The source validator checks the full CAL link route and selectors; the previous `cal_text_page` result's `comment_url` is metadata, not an arbitrary URL input accepted by the tool. The failing smoke currently chooses a returned line with comment_url when present, otherwise falls back to the first line; a selector failure in that fallback needs separation from actual CAL markup drift.
- `tests/fixtures/cal/text_page_tel_dan_getlex.html` includes historical Tel Dan `comment.php?coord=1325002`; an older fixture uses `1325000000002`. Real CAL could be using yet another form. No current CAL line-comments response is archived for this exact chosen live line.
- `tests/fixtures/cal/text_line_comments_pj_gen8_21.html` validates a **PJ Gen 8:21** comment page and `text_line_comments_none.html` a synthetic explicit empty marker. They do not justify assuming all CAL text families are structurally identical.

## Safe next research

Run **one explicit diagnostic** only after #340's currently running remainder smoke completes. Use an installed wheel and existing bounded `CalHttpClient` (max concurrency 1, retries 0, cache off, <=2 actual transport starts, 60 seconds after parent completion). Select the exact line from the current one-page `cal_text_page` result **only if a canonical CAL comment_url is present**. Fetch one `comment.php?coord=...` page in memory; output only the selected coordinate, HTTP status, expected-title boolean, summary-card count, comment-record-builder count, empty-marker boolean, and a preapproved parser exception category; never print/archive CAL lexical text or raw HTML.

If CAL HTTP 429, halt with an unavailable classification, no further queries. A trustworthy structural observation and minimal sanitized fixture must precede any parser change (RED) and new narrow live check. Until then #343 and #340 block all-37 release acceptance.


## First structural diagnostic, 2026-11-15 — reproducible CAL mismatch, not yet a parser fix

[GitHub Actions run 43740174887](https://github.com/alexsosn/CAL-MCP/actions/runs/43740174887), source SHA `24e029eb83eca70c9de3e99fc3e80ad1cf6c94e5`, installed fresh `cal-mcp 0.2.0.dev0` wheel; **exactly 2 actual CAL starts**, one current `cal_text_page(file_id=13250)` then one canonical returned comment selector, spaced by at least 60 seconds, no retries or other CAL requests. Sanitized structural report:

```json
{"coordinate":"1325002","http_status":200,"content_type_is_html":true,
 "response_size_bytes":2383,"title_count":1,"title_matches":true,
 "summary_cards":1,"record_count":0,"empty_marker_count":0,
 "event_signatures":[],"parse_status":"drift",
 "parser_reason":"unrecognized_structure","structure_error":"unrecognized_markup"}
```

The selector is **not fabricated**: a current Tel Dan page returned the matching canonical `comment.php?coord=1325002` link. CAL responded 200 with exact correct title and a unique summary card. No recognized paragraph records or exact explicit-empty marker were obtained before the parser failed. Because the diagnostic's allowlist did **not** include every `_LineCommentsHTMLParser` low-level exception, `unrecognized_markup` alone is insufficient to identify the change; preserve strict parse rejection. No raw CAL HTML or lexical content was logged. An ordinary web retrieval of this same URL could not access its contents, so do not treat a third-party cached page as current evidence.

**Next narrow diagnostic:** first expand the parser-reason allowlist from the actual eight source `TextParseError` branches and record sanitized markup hierarchy (`tag`, allowlisted `class` flags, attribute names) of the summary region, without content. RED tests and bounded exact-candidate live rerun are required before changing the parser. Avoid any parallel CAL job.


## Second diagnostic: exact nested-span parser failure (2026-11-15)

[Run #43741590108](https://github.com/alexsosn/CAL-MCP/actions/runs/43741590108), installed-wheel source SHA `6a6dd39e78196a9f2170e1b28db43949a939d6e1`, **2/2 CAL starts**, 60-second gap, HTTP 200, valid exact title and unique summary-card, coordinate `1325002`, 2383 bytes. The expanded error allowlist identified **`nested_span`** for both first-pass HTML parsing and the strict public parser. The tag-only summary prefix (text omitted) was `["p","i","span","span","span","br","a","i","b","other"]`. This is concrete evidence for a nested `<span>` inside a CAL citation paragraph, but **not evidence that arbitrary nested spans are safe**, nor which span class is an allowed script wrapper.

Before fixing, run one more tiny structural diagnostic after a RED offline test: capture at most six **CSS-class tokens** of the first summary-card paragraph spans (ASCII identifier-class names only, 32 characters max per token, otherwise `other`), and for each record one nontext nesting depth and parent span class. This can reveal whether the new nested span is a known harmless `syr` or `heb` wrapper. No literal CAL texts/HTML or link URLs may appear. The targeted fixture must model only the observed approved structure; any unrecognized nesting still raises `TextParseError`. The third diagnostic must remain <=2 sequential CAL starts and not overlap a live job.


## Third diagnostic: exact safe CSS nesting (2026-11-15)

[One-off run #43742235591](https://github.com/alexsosn/CAL-MCP/actions/runs/43742235591), installed-wheel source SHA `05fb8d2e212377fa0907090095564e71f08ce8d4`; CAL 2/2 actual transport starts and at least 60 seconds between them, HTTP 200, canonical `comment.php?coord=1325002`, title and single summary valid. The first record's **span-only** structure, with no text content or URLs, was:

```json
[{"css_class":"rom","depth":0,"parent_span":null},
 {"css_class":"uncertain","depth":1,"parent_span":"rom"},
 {"css_class":"rom","depth":0,"parent_span":null}]
```

The current parser accepts two top-level citation spans `heb` + `rom` and rejects any nested span. A current **romanized source span** contains an `uncertain` inline wrapper and is followed by a second `rom` span (translation). This is sufficient evidence for a narrowly guarded addition; no other script or class nesting has been demonstrated.

**Exact TDD acceptance contract:** a citation record may have the historical `heb,rom` span pair, *or* `rom,rom` **only if the first top-level `rom` span contains exactly one immediate child `span.uncertain`**. Flatten the child's text into the source span in display order without introducing a third semantic citation span. Preserve all existing validation of unique reference, break, CAL lexical link and entry phrase, status, source URL, and provenance. Reject wrappers with any other class, wrappers under `heb` or the second `rom` span, duplicated or nested wrappers, or unclosed markup. Use one minimal synthetic structural fixture, add failing parser and adversarial tests first (RED), then minimal implementation. Run both CI matrices and one **bounded** installed-wheel `cal_text_line_comments` live retest selected from a current one-page Tel Dan response, with 60-second gap and no retries. Independent skeptical review is mandatory before merging. Do not generalize to arbitrary nested spans.


## Installed-wheel parser-fix acceptance, 2026-11-15

[Nonpublishing run #43743133034](https://github.com/alexsosn/CAL-MCP/actions/runs/43743133034), source SHA `a6379d95695d79e8ae97df23ebf945037a05d69a`, built exactly one wheel, installed into a clean venv outside the checkout. The hard two-request diagnostic (one current `cal_text_page`, then its typed canonical `comment.php?coord=1325002` link after >=60 sec) logged **2/2 actual CAL transport starts**, HTTP 200, unique correct title and summary. The enhanced real parser returned **`parse_status: "found"`**, `record_count: 1`, `parser_reason: null`, `structure_error: null`. Accepted top-level event signature `["reference","span:rom","span:rom","br","anchor","gloss"]`. The exact class nesting remained `rom > uncertain`, then sibling `rom`; no lexical text, translation or raw CAL HTML was logged.

**Result:** the bounded direct parser/service route is successfully repaired on current CAL. This does not yet prove the entire MCP tool against the *final* exact release candidate SHA; the issue remains open until exact-candidate installed-wheel MCP acceptance and review. Test corpus includes the reduced synthetic `text_line_comments_roman_uncertain.html`, historical `PJ Gen8:21` behavior, and deliberately malformed wrappers. The new typed `has_uncertain_reading` flag preserves that a romanized reading was marked uncertain; the text itself remains flattened and no offsets are claimed.
