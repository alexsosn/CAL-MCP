# Issue #328 research — bibliography typed-link query and path identity

**Rechecked:** 2026-11-07 against current committed minimal CAL bibliography fixtures and shared adapter, without additional CAL network traffic.

## Observed supported navigation

The existing reduced fixtures `bibliography_author_kaufman.html`, `bibliography_author_sokoloff_current.html`, `bibliography_keyword_tada.html`, `bibliography_lemma_br_n_current.html`, and `bibliography_lemma_cly_v.html` represent bounded CAL observations from 2026-09-05 and 2026-09-24. In these files, *all non-placeholder record-local bibliography navigation links* have the root-level shape:

- `/getbibsigla.php?myauthor=TADA` and other text/subject tags;
- `/getbiblemma.php?myauthor=br%20N`, `/getbiblemma.php?myauthor=%29wwr+N` and other exact lemma keys;
- author selector form `getbibauthor.php` with one `myauthor` value (source: `docs/research/issue-9-bibliography.md`).

These examples use exactly one `myauthor` parameter, with no additional query fields, fragments, path aliases or navigation traversal. A few actual CAL bibliography result cards contain **empty placeholder links** (`myauthor=` or a lone newline), already handled separately in `_is_empty_placeholder_link`; that rule must remain intact. Existing non-bibliography CAL record links may be preserved as generic same-origin links and must not be conflated with recognized typed bibliography follow-ups.

## Reproduced parser acceptance gap (code inspection)

`src/cal_mcp/bibliography.py::_parse_bibliography_link` resolves `href` with `urljoin`, identifies target **only** by final filename, and checks `parse_qs(target.query).get("myauthor")`. Hence it currently presents `/getbibsigla.php?myauthor=TADA&mode=changed` as an exact `keyword=TADA` follow-up while omitting the extra mode that CAL might interpret differently. A same-origin `/archive/getbibsigla.php?myauthor=TADA` similarly gets recognized by filename, and `/./getbibsigla.php?... ` is silently normalized before classification. Fragments and malformed percent sequences can also be advertised as canonical links. The tool must not imply a canonical adapter operation is identical to unvalidated CAL URLs.

## Narrow supported contract and unknowns

For an identified bibliography endpoint, only its *canonical root-level path* (either a bare script relative to CAL root or one literal leading slash, or a same-origin absolute URL with that path) and exactly one nonempty UTF-8 `myauthor` query field are evidence-backed. Query values may use `+`, `%20`, encoded punctuation and non-ASCII text; preserve the actual exact decoded string. Reject fragments, duplicate/unknown fields, malformed percent encoding and dot-segment/path aliases as `BibliographyParseError` rather than producing a misleading typed `query_kind`. For an otherwise legitimate same-origin **different** endpoint, continue to preserve its URL with `query_kind=null`.

Only links in current user-requested bibliography pages are parsed. No extra request, canonical redirect probe, archive crawl, or link follow-up is needed or permitted. The release v0.1.0 schema and the post-v0.1 recent-bibliography tool contracts remain unchanged. The fix is a local fail-closed correctness hardening.

## Sources

- `tests/fixtures/cal/bibliography_author_kaufman.html`
- `tests/fixtures/cal/bibliography_author_sokoloff_current.html`
- `tests/fixtures/cal/bibliography_keyword_tada.html`
- `tests/fixtures/cal/bibliography_lemma_br_n_current.html`
- `tests/fixtures/cal/bibliography_lemma_cly_v.html`
- `docs/research/issue-9-bibliography.md`
- `docs/research/issue-39-recent-bibliography.md`
- https://cal.huc.edu/getrecentbib.php (previous bounded live acceptance for #39; no new raw fetch for this ticket)

## Review-regression verification

Independent parser review identified a further ambiguity in `urllib.parse.urljoin/urlsplit`: it can normalize away raw leading space or embedded newline from an `href`, while existing bibliography value handling trims a raw trailing space. These make a raw noncanonical link appear to match a canonical typed follow-up. Synthetic review-regression RED was added in commit `66f56b7544a6bb6993cf0af00c1a93d2875a9c58`; its [GitHub Actions run 42311304811](https://github.com/alexsosn/CAL-MCP/actions/runs/42311304811) reached pytest and produced six expected `DID NOT RAISE BibliographyParseError` failures (the three input variants in both targeted and recent bibliography pages), with 2,362 other tests passing. The subsequent guard rejects raw surrounding whitespace and C0/DEL controls **before** interpreting a link as a typed CAL follow-up. This remains offline; no extra CAL request was made.
