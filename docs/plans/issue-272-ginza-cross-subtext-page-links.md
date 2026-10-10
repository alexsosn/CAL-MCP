# Issue #272 — research-plan-TDD-test and independent source review

Research: `docs/research/issue-272-ginza-cross-subtext-page-links.md`.

1. **RED**, tests from current captured CAL fixture: `TextService.page("74410",subtext_id="001")` makes one already-known `cset=M,file=74410,sub=001` GET and returns a valid page with `next_page=null`, `next_subtext_id="002"`, unchanged source lines/coordinates/provenance; no additional GET or auto-crawl. Direct parser with the actual response should have the same next-subtext identity.
2. **RED**, strict negative source mutations: a jump to `003`, foreign `file`, changed `cset`, nonzero private `page`, forbidden selector, repeated link and wrongly labelled `previous page` must all remain parser drift. Existing `74401/12` same-subtext pagination tests must remain untouched and green.
3. **GREEN**, one narrow `74410` branch in `_page_navigation`, bounded exact selector/adjacency tests, two additive `TextPage` properties and response serialization; `previous_page`/`next_page` semantics unchanged. No schema/tool-count or request-volume change.
4. Verify Ruff, mypy and full pytest in pinned and latest-compatible CI. Require independent skeptical source-grounded review of exact final SHA and a new test-first sub-loop for any discovered gaps. No merge without all gates.
5. No CAL live requests, release tag, PyPI publication, or Agora integration. Update text-page docs and dated research when source semantics are implemented.
