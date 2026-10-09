# Issue #156 plan — accurate parser-drift classification with the CAL source URL

This change is local only, with no CAL request.

## Findings

- `LexiconCitationContextParseError` subclasses `CalContentError`, not `CalParseError`. Citation
  context drift therefore surfaces as `kind: "content"` with "rejected as unsafe". Every other
  `*ParseError` class is already a `CalParseError`.
- No parse or content error carries the response URL, so `parser_drift` always has
  `source_url: null`, while `upstream_http` and `response_too_large` include it.
- An audit of f-string error messages found one upstream-controlled value:
  `texts.py` "CAL text row has an unexpected <{tag}> element" echoes CAL's raw tag name. All the
  other interpolations are internal constants (query keys, contexts, field names).

## Change

1. `LexiconCitationContextParseError(CalParseError)`.
2. `CalContentError` (and so `CalParseError`) gets an optional `url` attribute.
   `CalHttpClient._fetch_uncached` sets it to the response URL when content validation or the
   parser raises a `CalContentError` without one. Single-flight followers share the same
   exception, so they see the same URL.
3. `classify_public_tool_error` publishes `source_url` for `parser_drift` and `content` errors
   only through the existing `_trusted_cal_url` check (https, `cal.huc.edu`, no controls). An
   untrusted URL is never published. Messages are unchanged.
4. The text-row message no longer quotes CAL's tag name, and the Syriac subtext-navigation
   message no longer lists CAL's unexpected query keys. Both are generic; `source_url` now
   points to the page.
5. Docs: the error-model section, plus a CHANGELOG line.

## Tests

`tests/test_drift_error_source_url.py`:

- every `*ParseError` class is a `CalParseError` and maps to `parser_drift`;
- through MCP, one tool per CAL-backed module returns `parser_drift` with `source_url` equal to
  the fetched CAL URL and `upstream_reached: true`;
- an untrusted URL on a parse error is never published;
- the tag-name guard.

## Review follow-up

The independent review found:

- identity checks that ran after `client.fetch` returned, with no URL: bibliography author and
  result headings, dictionary collation page and source, and the external-citation heading.
  These checks now run inside each `parser=` callback. As a result a mismatched page is never
  cached either;
- a Syriac message built by string concatenation from CAL query keys, which the f-string audit
  missed.

Tests now cover each post-fetch site through MCP, a lookup whose entry stage drifts (the error
names the entry URL, not the browse URL), and the Syriac key leak. `live_smoke` treats any
`CalParseError` as parser drift. `_trusted_cal_url` accepts `None`.
