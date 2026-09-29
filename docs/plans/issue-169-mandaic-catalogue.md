# Issue #169 plan — Mandaic catalogue after CAL's script toggle

Date: 2026-09-25. Research: `docs/research/issue-169-mandaic-catalogue.md`, committed before behavior tests.

1. A reduced current fixture with a provenance comment, `text_catalogue_mandaic_current.html`: the toggle, two groups, a subdivided entry, a direct entry, the entry wrapped in `div.direct-link`, an unavailable note, and the amulets note.
2. RED tests (`tests/test_mandaic_catalogue_current.py`) through `TextService.catalogue(category_id="74")`:
   - texts in CAL order, with file ids and labels;
   - fail closed on `cset=J` or an unknown `cset`, an information link naming another file, and an empty title.
3. A valid RED has the positive test failing, with lint, format and mypy green.
4. GREEN: accept `R` or `M`; read current title rows; check the information link.
5. Existing Mandaic tests (earlier layout) stay green.
6. Docs: `docs/tools/texts.md` (Mandaic paragraph), `research.md` R-036, fixture README.
7. Verification: the full offline suite; offline over the full capture; live over MCP for the catalogue, then `cal_text_page` for one subdivided and one direct entry.
8. Independent adversarial review of the exact candidate SHA.
