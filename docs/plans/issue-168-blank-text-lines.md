# Issue #168 plan — preserve researched blank text lines

Date: 2026-09-26. Research: `docs/research/issue-168-blank-text-lines.md`, committed first.

1. Add a reduced fixture containing the exact captured `60424` blank row.
2. RED tests through `TextService.page`:
   - the blank row is returned with its machine/display coordinates, empty text and no tokens;
   - a current normal row (existing Philemon fixture) remains unchanged;
   - an empty link at `word=1` fails closed;
   - an empty link mixed with a real token fails closed;
   - an altered route/selectors fail closed.
3. Demonstrate RED in PR CI before production code is added.
4. GREEN in the current table-row reader only; do not weaken `_token_from_link` globally.
5. Run focused + full deterministic CI.
6. Update `docs/tools/texts.md`, `research.md`, fixture provenance and CHANGELOG.
7. Independently adversarially review the exact candidate SHA, including mutation-style checks of
   every condition that distinguishes the blank-line sentinel from malformed token rows.
8. Merge only after review approval and green CI.
