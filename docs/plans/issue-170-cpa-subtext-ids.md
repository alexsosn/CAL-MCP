# Issue #170 plan — widen only CAL subtext IDs

Date: 2026-09-26. Research: `docs/research/issue-170-cpa-subtext-ids.md`.

1. Add one tiny shared identifier module whose only new contract is `^[0-9]+[a-z]?$` for CAL subtext IDs. Keep every existing decimal-ID helper intact.
2. Add reduced/synthetic-provenance fixtures for:
   - current CPA catalogue link `file=55000&sub=01001a&cset=C`;
   - one current-shape CPA text row whose file-info identity is `5500001001a`.
3. RED tests before implementation:
   - catalogue returns `TextRef(file_id="55000", subtext_id="01001a", ...)`;
   - page accepts `01001a`, submits exactly one request including `cset=C`, and preserves the public subtext ID;
   - information accepts `01001a` and requests `coord=5500001001a`;
   - KWIC full-context accepts `01001a` and sends it unchanged;
   - returned KWIC/full-context sub selectors can use the same grammar;
   - malformed near-misses are rejected both as caller input and returned CAL data.
4. GREEN:
   - `texts.py`: dedicated subtext validate/parse wrappers; catalogue, page, information, navigation and composed file-info identity use them;
   - for a suffix-bearing subtext only, page routing adds `cset=C`, matching current CPA links;
   - `concordance.py`: dedicated subtext validate/parse wrappers and optional-query helper;
   - no widening of file IDs, category IDs, target coordinates or generic decimal helpers.
5. Update user docs, `research.md`, `wiki/decisions.md`, fixture provenance and CHANGELOG.
6. Run focused tests and both full deterministic CI matrices.
7. User-level live verification from an installed candidate over stdio: `cal_text_catalogue("55")` succeeds and one returned `01001a` entry opens via `cal_text_page`; keep the probe bounded and delete any temporary workflow afterward.
8. Perform a logically independent adversarial review of the exact final SHA. Fix/retest/re-review any finding before merge.
