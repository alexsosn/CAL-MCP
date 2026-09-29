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

## Revision (2026-09-29, after the correction in the research note; superseded by the final plan)

1. RED (new commit): the request sends unpadded chapter and verse; Ps 23:1 is found on both routes. The captured "Kings1" page for a Genesis request must **fail closed**, because it is 1 Kings. An empty label fails closed. The earlier-layout fixtures (label equal to the selector label) stay valid.
2. GREEN: `_format_coordinate_number` is replaced by unpadded decimals in both services. The heading book label is checked against a reviewed `_CAL_HEADING_LABELS` table in `biblical.py`.
3. Verification: live over MCP for all 36 books on both tools (verse 1:1), plus Ps 119:150, Isaiah 40:3 and Gen 50:26.

## Final plan (2026-09-29, after the second correction)

The request format stays CAL's 2-digit format, pinned by tests. GREEN is a reviewed `_CAL_HEADING_LABELS` table in `biblical.py` and a shared `cal_biblical_heading_matches` used by both parsers. Live verification covers all 36 books on both tools.

## Review follow-up (2026-09-29)

- The heading regex accepts multi-word selector labels (`1 Sam`, `Song of Songs`) for the earlier-layout fallback, and only ASCII digits.
- A test pins all 36 (selector, CAL label) pairs, their coverage of the selector list, and their distinctness.
- The 3-digit empty-label fixture is reduced, and the fixture descriptions say they come from 3-digit research requests.
