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
