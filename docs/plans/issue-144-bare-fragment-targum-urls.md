# Issue #144 plan — reject bare-fragment Targum navigation URLs

Date: 2026-09-23. Research is frozen in `docs/research/issue-144-bare-fragment-targum-urls.md` and was committed first.

1. Add focused parser-level RED regressions before production changes. Start from otherwise-valid reduced Targum concordance/reflex HTML and append a bare trailing `#` to the example `href`.
2. Keep an explicit positive reflex control containing encoded `%23` in the `cal` selector so the regression cannot be “fixed” by rejecting encoded number signs.
3. A valid RED must leave Ruff lint/format and mypy green while pytest fails only the new malformed-link cases.
4. Implement the minimum shared-validator change: reject a literal `#` in the original `href` before `urljoin()`; retain the existing parsed-fragment check.
5. Do not change public dataclasses, serialized fields, tool schemas, endpoint/request construction, cache behavior, request counts, or #109 follow-up semantics.
6. Run the complete deterministic and latest-compatible CI matrices on the exact candidate head.
7. Perform a logically independent adversarial whole-PR review of the exact candidate SHA. Challenge encoded `%23`, relative/absolute href handling, nonempty fragments, valid chapter URLs, false positives, and accidental public/request changes.
8. Any blocker gets a focused review-regression RED/GREEN cycle and fresh full CI. Merge only if the exact reviewed SHA is unchanged, no unresolved threads remain, and the PR is mergeable against current `main`; use SHA-guarded squash merge.

CAL load impact: zero.
