# Issue #207 research — CAL's "is not a valid search string" citation-search rejection

Date: 2026-09-29. Base: `e97c36b`.

## Trigger

While smoke-testing #178, `cal_citation_text_search("god")` failed with `parser_drift` "CAL citation search page has no recognizable results". CAL had in fact answered with its own explicit rejection.

## Live-current evidence

Bounded POSTs through the production client on 2026-09-29:

| Request | Response |
| --- | --- |
| `searchcits.php`, `English=god` | 1481 bytes; page chrome, then `<span STYLE=font-size:small>"god" is not a valid search string` |
| `searchcits.php`, `English=the` | the same shape: `"the" is not a valid search string` |
| `searchcits.php`, `English=king god` | an ordinary result page, 13 citation rows |
| `newsearchmngs.php`, `English=god` (gloss search) | an ordinary result page |

The page's CSS mentions `.citation-row` and `.citation-results`, but the page has neither container.

## Findings

- CAL rejects some single very common words in citation search with an explicit message that quotes the submitted query. A multi-word query containing such a word is accepted. Gloss search does not reject `god`.
- This is an application-level answer about the caller's input, not parser drift and not a transient failure.

## Consequences

- A citation-search page whose text contains exactly `"<submitted query>" is not a valid search string` raises a new `CalRejectedInputError`. It is classified as `invalid_input` with `upstream_reached: true`, carries CAL's message, and is not retried. `CalOutOfRangeError` (#172/#185 text pages) becomes a subclass of it, so its classification is unchanged.
- A rejection message quoting another string fails closed as `parser_drift`.
- CAL-MCP keeps no local stop-word list; CAL stays the authority.
- Production requests are unchanged.

## Review follow-up (2026-09-30)

The review made two more bounded POSTs. `English=God` is answered with `"god" is not a valid search string`, so CAL echoes the query **lowercased**. `English=a` is also rejected. The echo is therefore compared with the submitted query case-insensitively, after HTML unescaping and up to the literal `" is not a valid search string`, so a quote inside the query cannot cut it short. The error quotes CAL's echo as rendered. A result page that contains citation rows is never treated as a rejection.
