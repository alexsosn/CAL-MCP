# Issue #177 plan — text-concordance rows CAL marks "no data found"

Date: 2026-09-29. Research: `docs/research/issue-177-concordance-no-data-rows.md`, committed before behavior tests.

1. A reduced current fixture with a provenance comment: `text_concordance_41201_no_data_current.html`, containing the `+snqlyTws+N` row, `qrb ` and `z(yd N` (no-data rows) and two normal rows.
2. RED tests (`tests/test_text_concordance_no_data_rows_current.py`):
   - the page parses;
   - the invalid-key no-data rows have `lemma_key: null` and keep label, gloss, frequency and URL;
   - the valid-key no-data row keeps its key;
   - normal rows are unchanged;
   - an invalid key on a normal row (no marker) still fails closed.
3. GREEN: in the concordance row parser, recognize the explicit marker; `lemma_key` becomes `str | None`.
4. Docs: `docs/tools/concordance.md`, `research.md` R-045, fixture README, CHANGELOG.
5. Verification: the full suite; offline on the full capture (985 rows); live over MCP for 41201 and 13250.
6. Independent adversarial review of the exact candidate SHA.

## Revision (2026-09-29, during GREEN)

- Rows get an explicit `cal_reports_no_data` boolean from CAL's marker. The marker must equal `no data found for <row label>` after whitespace collapsing; a marker naming another label fails closed.
- Parsing the full capture found capital-letter keys on normal rows (`bwlbrK PN`). They are accepted verbatim in concordance rows and rejected as KWIC input with guidance; see the research note's "Second finding".
