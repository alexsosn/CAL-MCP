# Issue #193 plan — preserve linkless token-analysis summaries

Date: 2026-09-27. Research: `docs/research/issue-193-linkless-token-analysis.md`.

1. Add reduced current fixtures for:
   - Peshitta simple one-line summary (`620570101`, word 0);
   - Peshitta two-line summary (`620570101`, word 2);
   - CPA simple one-line summary (`5500001001a019001`, word 0).
   Retain only the unique result marker, exact parser-relevant rendered summary lines, and the
   return-to-text-browser boundary.
2. RED before production changes:
   - parse each linkless fixture as found with `candidates == ()`;
   - preserve ordered `unlinked_summaries`;
   - service/public serialization exposes the new list and reports `status=found`;
   - explicit no-data/no-lemma pages remain `not_found` with both collections empty;
   - marker-only, unexpected summary link, mixed linked+linkless, and table-like malformed shapes
     fail closed;
   - existing #179 current linked redirect/non-redirect fixtures remain unchanged.
3. GREEN data model:
   - add `unlinked_summaries: tuple[str, ...] = ()` to `TokenAnalysisPage` and
     `TokenAnalysisResult`;
   - do not change `TokenAnalysisCandidate` or make its `lemma` optional;
   - serialize `unlinked_summaries` as an ordered list.
4. GREEN parser:
   - preserve current no-data/no-lemma handling first;
   - preserve strict #179 current-table handling next;
   - add a narrow linkless-success parser only for one unique marker, no lemma-entry links, no
     post-marker table, one-or-more non-empty unlinked semantic lines before return navigation;
   - reject links or other candidate/table structures in that region;
   - preserve whitespace-normalized rendered text without decoding `=` or `-->`.
5. GREEN service semantics:
   - `FOUND` iff linked candidates or unlinked summaries are non-empty;
   - `NOT_FOUND` only for the existing explicit empty states.
6. Update `docs/tools/token-analysis.md`, MCP tool description, `research.md`,
   `wiki/decisions.md`, fixture provenance, and CHANGELOG.
7. Run focused tests and both complete CI matrices.
8. Installed-wheel/stdio live acceptance with exactly the three researched examples:
   - Peshitta word 0 → one summary;
   - Peshitta word 2 → the two ordered summaries;
   - CPA word 0 → one summary;
   plus no automatic entry traversal.
9. Remove any temporary workflow, re-run workflow-free CI on the exact final head, and perform a
   logically independent adversarial review. Fix/retest/re-review every finding before merge.
