# Issue #328 plan — fail closed on ambiguous CAL bibliography navigation links

**Plan date:** 2026-11-07; research committed first at `4319cf353b2744584666e2b3e3bb479b065094e9`.

## Scope and public contract

Preserve `BibliographyLink` `{label,url,query_kind,query_value}` exactly as released. Harden only `_parse_bibliography_link` against identifying a navigation URL as a canonical typed follow-up when its raw path/query is not the studied CAL contract. No new public tools, argument changes, transport requests, normalization of CAL query values, or data mirror.

Supported typed links: same CAL origin, root-level `/getbibauthor.php`, `/getbibsigla.php`, or `/getbiblemma.php` (also bare filename relative to CAL root); *exactly one* `myauthor` query field with a nonempty single-line value; no fragment; valid percent escapes and strict UTF-8 for escaped values. Preserve `+` spaces, `%20` spaces, encoded punctuation, case and original URL spelling in `url`. Unknown same-origin **other endpoint** links are still generic; do not invent a typed result for those. Existing explicit empty label/value placeholders remain omitted by their separate existing parser rule.

## RED tests first

Add `tests/test_bibliography_link_identity.py` with minimal synthetic record cards (no CAL data), using `parse_bibliography_page` and `parse_recent_bibliography_page` where applicable:

1. reject unexpected additional query field, even if empty; reject duplicate `myauthor`;
2. reject root-path aliases under a directory, dot-segment normalization, repeated leading slash and `?myauthor=...` that normalizes onto a canonical endpoint;
3. reject fragments, malformed percent escapes (`%ZZ`) and invalid escaped UTF-8 (`%FF`);
4. retain precisely decoded exact canonical examples for author/keyword/lemma, absolute and relative same-origin routes, percent-escaped punctuation, and an accented or other Unicode token;
5. preserve generic nonbibliography same-origin record URL as `query_kind=null` and existing empty placeholder semantics;
6. do not reclassify a bad link as a silent empty result or strip an invalid field; no extra request is made.

Prove the new tests fail against the old adapter for the specific newly researched ambiguity. Use no upstream network, and ensure new tests pass Ruff format/lint.

## GREEN

Implement the smallest canonical path and strict-query guard in `_parse_bibliography_link`, with explicit `BibliographyParseError` for invalid same-origin typed-link semantics. Keep the author-prefix form parser and `_is_empty_placeholder_link` unchanged unless a failing regression reveals a direct related issue. Avoid global URL handling policy changes or new helper infrastructure unless actually needed.

## Validation, docs, independent review

- Run focused RED/GREEN and **full** deterministic + latest-compatible pytest, Ruff and strict mypy via CI.
- Update `docs/tools/bibliography.md` for typed-link canonicality/fail-closed behavior and index the evidence in `research.md`. Architecture decisions are unchanged.
- Open one focused PR referencing #328. Have a logically independent review on the **exact final SHA**, grounded in the fixtures, current parser and exercised error paths; specifically challenge false positives, double decode, Unicode, placeholder swallowing, cross-origin and path normalization.
- No new live CAL smoke needed: the public schema and upstream request pattern do not change. A user-facing release E2E episode was completed for the new recent bibliography operation in #39; do not multiply upstream requests for a locally testable path validator. No release or Agora package changes in this issue.

Merge and close #328 only with green exact-head CI, review and acceptance evidence.
