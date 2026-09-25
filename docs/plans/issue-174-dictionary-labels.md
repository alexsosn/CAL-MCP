# Issue #174 plan — dictionary-collation result labels

Date: 2026-09-25. Research: `docs/research/issue-174-dictionary-labels.md`, committed before behavior tests.

1. Reduced current fixtures with provenance comments: DJBA page 100 (2 entries) and Schulthess page 100 (2 of 9 entries).
2. RED tests (`tests/test_dictionary_collation_current_labels.py`) through `DictionaryCollationService`:
   - DJBA returns `source_label` "Dictionary of Jewish Babylonian Aramaic";
   - Schulthess returns "Schulthess";
   - a table test checks that every source's accepted labels include its form label;
   - fail closed on a heading naming another dictionary (DJPA's label on a DJBA request).
3. A valid RED has the positive tests failing, with lint, format and mypy green.
4. GREEN: per-source accepted labels, form label plus current heading label.
5. Docs: `docs/tools/dictionary-collation.md` (heading labels), `research.md` R-037, fixture README.
6. Verification: the full offline suite; live over MCP for all 15 sources, page 100.
7. Independent adversarial review of the exact candidate SHA.
