# Issue #166 plan — file-info coordinate on subdivided text pages

Date: 2026-09-25. Research: `docs/research/issue-166-subtext-file-info.md`, committed before behavior tests.

1. Reduced current fixtures with provenance comments: `text_page_samaritan_56000_112_current.html` (ordinary subtext) and `text_page_ginza_right_001_current.html` (Mandaic private `sub`).
2. RED tests (`tests/test_text_page_subtext_current.py`), driven through `TextService.page` with a recording fake client so that the submitted `sub` is the real one:
   - the Samaritan page returns file `56000`, subtext `112`, its label and 2 lines;
   - the Mandaic page returns file `74410` and 2 lines;
   - fail closed on a `coord` naming another file, another subtext, different padding (`560000112`), or file plus subtext on a request without `sub`.
3. A valid RED has only the positive tests failing, with lint, format and mypy green.
4. GREEN: pass the submitted `sub` into the page parser; accept a bare file id or file id plus that exact value.
5. Keep every existing text-page fixture green (earlier layout).
6. Docs: `docs/tools/texts.md` (pass `subtext_id` exactly as returned), `research.md` R-033, fixture README.
7. Verification: the full offline suite; live over MCP for the five subtexted texts from the end-to-end run.
8. Independent adversarial review of the exact candidate SHA.
