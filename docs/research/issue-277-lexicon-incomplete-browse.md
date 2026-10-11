# Issue #277 — lexicon lookup completeness and multiword CAL-code headwords

Date: 2026-10-11. Grounded in issue #277's bounded, real-CAL 2026-10-10 GET observations and exact main source: `src/cal_mcp/lexicon.py` and `src/cal_mcp/lexicon_browse.py`. No new upstream CAL requests.

Two observed false negatives: `byt@mlkw N` is not on the first of CAL's `byt` browse pages; that first page has **48 rows plus a validated NEXT PAGE**, yet `cal_lexicon_lookup` returns `not_found`. For `xd@(sr b`, machine CAL-code `@` encodes a multiword key; the lookup prefix and matching surfaces should not treat that separator as a third consonant or silently conclude an exhaustive miss. CAL's `first3="xd"` page already includes that key in a bounded first-page result. These are user-facing completeness bugs, not missing corpus contents.

The public `cal_lexicon_browse` implementation already provides a strict `_continuation_from_link` with same-origin `browseSKEYheaders.php`, exact `direction=1&sortkey`, bounded safe printable-ASCII cursor. Lookup's `parse_browse_page` discards NEXT PAGE entirely. Reuse a *single canonical validator* and make the lookup response explicitly surface a bounded prefix/cursor pair. No automatic pagination, new GET, background crawling, or corpus cache/indexing.

Policy: status `truncated` on unmatched first page with NEXT; `not_found` remains reserved for a complete observed page. Add additive `browse_truncated` and `browse_continuations` to response for all statuses, so a matched result can still show incomplete candidate coverage. Each continuation includes the prefix it belongs to. For an ambiguous script with multiple prefixes, keep their exact original order and avoid treating one complete subquery as proof of overall completeness.

Multi-word CAL-symbol correctness should be tested separately from paging. `@` and a literal word separator cannot be consumed as a third prefix consonant; candidate comparison must check exact CAL machine key without requiring its human-readable headwords to spell the same. Preserve POS and homograph selection semantics. Do not invent a CAL lemma that was not present in a returned browse link.

Risk: existing legacy parser tests explicitly assert navigation-agnostic behavior and must be updated *as an intentional contract change* with a real current fixture. All new tests should be offline reduced HTML; no CAL traffic while #262 remains open.
