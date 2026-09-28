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
     requested text identity, or rendered-link/display mismatch.
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
