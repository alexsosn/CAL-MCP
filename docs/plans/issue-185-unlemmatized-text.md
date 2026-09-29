# Issue #185 plan — preserve unlemmatized two-cell text rows

Date: 2026-09-28. Research: `docs/research/issue-185-unlemmatized-text.md`.

1. Widen only `TextLine.coordinate` from `str` to `str | None`.
   Keep `TextToken.coordinate` and all token-analysis identifiers unchanged.
2. Add reduced structural fixtures:
   - Mandaic `74420`: plain two-cell rows, including one row with no coordinate link and one
     exact-shape `comment.php?coord=...` coordinate link;
   - CPA `55430`: two-cell plain row whose text cell contains current-style `span` markup.
   Scholarly row text may be replaced with explicit fixture text; route/display/comment semantics
   must come from observed CAL evidence.
3. RED through public page parsing/service serialization:
   - unlinked row → `coordinate=None`, display coordinate, rendered text, empty tokens/slots,
     no comment URL;
   - comment-linked plain row → validated coordinate + comment URL, empty tokens;
   - nested span text remains rendered text;
   - serialized JSON emits `coordinate: null` where absent;
   - linked existing fixture remains byte-for-semantics unchanged.
4. RED fail-closed cases:
   - one actual text table mixing linked and plain rows;
   - plain row with fewer/more than two cells;
   - empty display coordinate or empty text;
   - any link in the text cell;
   - unknown/multiple links in coordinate cell;
   - comment link with extra/missing selectors, non-decimal coordinate, coordinate outside the
     requested text identity, or loose display text beside the comment link.
5. GREEN page classification:
   - classify a non-empty `text-display` table as linked when every row contains a lexical link;
   - classify it as plain when no row contains a lexical link;
   - reject a linked/plain mixture before per-row conversion;
   - keep an empty table as parser drift (#196), not successful empty content.
6. GREEN plain-row conversion:
   - require exactly two non-empty cells;
   - render first cell as `display_coordinate`, second as `text`;
   - accept no links or exactly one strict relative `comment.php?coord=...` in the first cell;
   - validate a comment-derived coordinate against the requested file/subtext identity;
   - emit `tokens=()`, `empty_word_indexes=()`;
   - never tokenize or invent a coordinate.
7. Update `docs/tools/texts.md`, MCP tool description, `research.md`, `wiki/decisions.md`,
   fixture provenance and CHANGELOG. Guidance must distinguish line/comment coordinates from token
   coordinates: plain rows have no returned token/word-index pair.
8. Run focused tests and both full CI matrices.
9. Installed-wheel/stdio live acceptance:
   - Mandaic `74420` returns plain lines with display coordinates and text;
   - CPA `55430` returns plain lines;
   - linked Peshitta `62057` remains linked/tokenized;
   - assert at least one nullable-coordinate plain row and one comment-coordinate plain row across
     the two positive pages, without printing scholarly text.
10. Remove temporary workflow, re-run workflow-free CI on the exact head, then perform a logically
    independent adversarial review. Fix/retest/re-review every finding before merge.

## Live-acceptance amendment — direct CPA pagination selectors

The initial live gate found that current paginated direct CPA `55430` returns navigation links
with exact extra selectors `sub=&clen=5`, while preserving `cset=C`. Bounded follow-up found no
navigation on current direct controls `55406`/`55407`.

Before repeating live acceptance:

11. RED the navigation parser with a direct CPA link
    `file=55430&sub=&cset=C&page=1&clen=5`, plus near-miss guards for non-empty `sub`,
    `clen!=5`, and unknown extras.
12. GREEN only the exact direct-CPA variant above (plus the already supported earlier exact core
    selector set). Do not widen subdivided CPA navigation.
13. Re-run full CI before the final installed-stdio acceptance.

## Adversarial-review amendment — scope paginated private selectors per file

Exact-head review of `943452ed` found that production accepts the observed private
`sub=&clen=5` navigation variant for every direct CPA file, while the live evidence and D-016
name only current paginated direct file `55430`.

Before merge:

14. RED: a known other direct CPA file (use `55406`) with
    `file=55406&sub=&cset=C&page=1&clen=5` must fail closed.
15. GREEN: keep the ordinary exact direct route available to the direct-file family, but allow the
    private empty-`sub` / `clen=5` variant only for an explicit evidence-backed paginated-direct
    file set, currently `{"55430"}`.
16. Run both full CI matrices and perform a fresh exact-head adversarial review.

