# Issue #208 plan — make KWIC full-context rows fail closed like text rows

Date: 2026-10-01. Research: `docs/research/issue-208-full-context-row-strictness.md`.

1. Extend the internal full-context table representation so a cell retains:
   - rendered linked text;
   - rendered loose text outside links;
   - whether unsupported elements occurred in the cell.
   Do not change public result models.
2. RED before production changes:
   - insert loose text between two current lexical anchors and require `ConcordanceParseError`;
   - insert an unknown tag such as `<wmr>` inside a token anchor and require failure;
   - rewrite a current `bablex.php` link to same-origin `/evil/bablex.php` and require failure;
   - add a fragment to a current lexical link and require failure;
   - repeat the nested-path guard for a current `getlex.php` fixture.
3. GREEN:
   - allow only the observed full-context cell markup needed by current captures:
     links, spans and `cal-variant` within table rows;
   - reject loose non-whitespace text in a linked scholarly-text cell;
   - require full-context lexical/comment paths to be exactly the CAL-root endpoint and reject
     fragments before URL preservation;
   - preserve current same-origin and exact-selector checks.
4. Keep Hebrew terminal-empty-anchor semantics unchanged.
5. Add positive coverage across Samaritan R, BA Ezra H, Syriac U, BT H and Tel Dan controls.
6. Update `docs/tools/search.md` / full-context documentation, `research.md`, fixture provenance
   only as needed; record the durable fail-closed alignment in `wiki/decisions.md` only if the
   project decision changes rather than merely applying the existing parser policy.
7. Run focused tests, formatter/lint/type checks and both full CI matrices.
8. After offline CI, run a bounded installed-wheel/stdio live smoke for one already-known full-
   context hit in each supported returned script family: Roman (`R`), Hebrew (`H`) and
   Unicode Syriac (`U`). Do not discover or crawl additional hits.
9. Perform a logically independent adversarial review of the exact final SHA. Any finding gets a
   new plan amendment and RED → GREEN cycle before merge.
