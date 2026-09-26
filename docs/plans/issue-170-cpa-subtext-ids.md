# Issue #170 plan — widen CAL subtext IDs and preserve CPA machine coordinates

Date: 2026-09-26. Research: `docs/research/issue-170-cpa-subtext-ids.md`.

1. Keep one shared subtext-ID predicate: decimal digits plus an optional single lowercase ASCII
   suffix. Generic decimal-ID helpers stay unchanged.
2. Keep reduced/synthetic-provenance fixtures for the current CPA catalogue and page route.
3. Initial RED (already recorded before implementation):
   - catalogue parses `file=55000&sub=01001a&cset=C`;
   - page/information/KWIC full-context accept `01001a`;
   - returned KWIC/full-context sub selectors use the same grammar;
   - malformed near-miss subtext IDs stay invalid.
4. Initial GREEN:
   - `texts.py` uses dedicated subtext validate/parse wrappers;
   - suffix-bearing text-page requests and navigation require current `cset=C`;
   - `concordance.py` uses the same subtext grammar;
   - file/category/target-coordinate decimal contracts are unchanged.
5. Live stdio acceptance then exposed a second issue: CPA token/comment coordinates include the
   lowercase subtext suffix, e.g. `5500001001a019001`.
6. Before changing coordinate handling, add a second RED:
   - revise the structural CPA page fixture to carry the observed machine-coordinate form;
   - page parsing fails on the existing decimal-only coordinate check;
   - token-analysis input rejects that returned coordinate before transport;
   - malformed broader alphanumeric coordinates remain rejected.
7. Second GREEN:
   - add a shared narrow machine-coordinate predicate accepting decimal or one embedded lowercase
     ASCII letter followed by decimal tail;
   - page token/comment parsing uses it;
   - suffix-bearing pages additionally require the exact requested `file_id + subtext_id` prefix;
   - `cal_token_analysis` accepts the same narrow grammar so returned CPA tokens remain usable;
   - do not widen concordance target coordinates without separate live evidence.
8. Update MCP descriptions, user docs, `research.md`, `wiki/decisions.md`, fixture provenance
   and CHANGELOG.
9. Run both complete CI matrices.
10. Installed-stdio live verification: `cal_text_catalogue("55")` succeeds and returned
    `01001a` opens with `cal_text_page`; verify at least one returned token coordinate has the
    researched suffix-bearing form and can be submitted to `cal_token_analysis` without local
    rejection. A downstream token-result `parser_drift` is tracked under #179 and does not turn
    back into an #170 identifier failure. Keep the live calls bounded and remove the temporary
    workflow afterward.
11. Perform a logically independent adversarial review of the exact final SHA. Any finding is
    fixed, retested and re-reviewed before merge.

## Review-finding amendment

The final adversarial review discovered that `has_subtext_letter_suffix()` is not a valid CPA
routing discriminator: current category 55 has 401 decimal-subtext routes with `cset=C` in
addition to 150 suffix-bearing routes.

Before merge:

12. Add RED coverage for a current decimal CPA route (`55001/002`):
    - catalogue parsing preserves it;
    - `cal_text_page("55001", subtext_id="002")` must submit `cset=C`;
    - CPA page navigation for that decimal subtext must require the exact current selector set.
13. GREEN with an evidence-backed current CPA file allowlist; suffix detection remains only an
    identifier/coordinate-shape concern.
14. Re-run both CI matrices and bounded installed-stdio acceptance for both one suffix-bearing and
    one decimal CPA route.
15. Delete temporary workflows, then perform a new logically independent exact-head review.

## Second review-finding amendment

A follow-up route-count reconciliation found four direct CPA text routes
(`55002`, `55406`, `55407`, `55430`) with no `sub`, all requiring `cset=C`.

Before merge:

16. RED:
    - include one current direct CPA route (`55002&cset=C`) in the reduced catalogue fixture;
    - mutated direct CPA catalogue routes with missing/wrong/extra selectors fail closed;
    - `cal_text_page("55002")` submits `cset=C`;
    - direct CPA page navigation, if present, requires exact `file,page,cset=C`.
17. GREEN with distinct current CPA subdivided/direct file sets and their union for private
    `cset=C` routing.
18. Re-run complete CI and installed-stdio acceptance for suffix-bearing subdivided, decimal
    subdivided, and direct CPA examples.
19. Remove temporary workflows and perform a fresh exact-head adversarial review.
