# Issue #196 plan — recognize current explicit no-lines text pages

Date: 2026-09-29. Research: `docs/research/issue-196-empty-cpa-55002.md`.

1. Add a reduced current CPA `55002` fixture containing:
   - current file-information identity;
   - exact manuscript-variant toggle route/label;
   - exact rendered `NO LINES FOR 55002 ARE CURRENTLY STORED` marker;
   - an empty `text-display` shell.
2. RED before production changes:
   - direct parser maps the current CPA fixture to `None`;
   - service/public serialization maps it to `status=not_found, page=null`;
   - the existing Tel Dan `13250 999` no-lines fixture remains accepted;
   - wrong file id, unlinked arbitrary prefix text, malformed marker and repeated marker fail closed;
   - one normal found page remains unchanged.
3. GREEN:
   - replace whole-page loose regex search with a dedicated semantic-line detector;
   - remove rendered link text exactly once from each candidate line and normalize whitespace;
   - require the remaining line to full-match the evidence-backed no-lines grammar:
     `NO LINES FOR <decimal file> [<decimal selector>] ARE CURRENTLY STORED`;
   - require the marker file id to equal `requested_file_id`;
   - when both a requested/submitted decimal subtext and marker selector exist, require equality;
   - reject multiple exact no-lines markers or a marker-like line whose identity disagrees;
   - do not reinterpret arbitrary non-link prefix text.
4. Keep all found-page parsing, page routing and request count unchanged.
5. Update fixture provenance, `research.md`, text-tool docs/CHANGELOG only where they improve the
   explicit `not_found` contract; no new public schema is introduced.
6. Run focused tests plus both complete CI matrices.
7. Installed-wheel/stdio live acceptance:
   `cal_text_page(file_id="55002", page=1)` returns `status=not_found`, `page=null`.
8. Remove temporary workflow, run workflow-free CI on the exact head, then perform a logically
   independent adversarial review. Fix/retest/re-review every finding before merge.
