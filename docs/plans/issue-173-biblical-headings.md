# Issue #173 plan — book labels in Peshitta and Targum verse headings

Date: 2026-09-29. Research: `docs/research/issue-173-biblical-headings.md`, committed before behavior tests.

1. Reduced current fixtures with provenance comments: Peshitta Ps 23:1 and Targum Ps 23:1 (abbreviated label), and Peshitta Gen 1:1 (CAL's wrong "Kings1" label).
2. RED tests through `SyriacService.peshitta_parallel` and `TargumService.parallel`:
   - Psalms 23:1 returns found on both routes, and Gen 1:1 too;
   - fail closed on: navigation naming another book or chapter; a verse more than one away; no navigation; a heading with another chapter or verse; two headings.
3. A valid RED has the positive tests failing, with lint, format and mypy green.
4. GREEN: a shared verse-navigation check in `biblical.py`; the heading is compared by chapter and verse only.
5. Docs: `docs/tools/syriac.md` and `docs/tools/targum.md` (identity check), `research.md` R-044, fixture README.
6. Verification: the full offline suite; live over MCP for the 11 sampled books on both tools.
7. Independent adversarial review of the exact candidate SHA.
