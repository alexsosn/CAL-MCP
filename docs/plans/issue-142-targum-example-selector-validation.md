# Issue #142 plan — fail closed on malformed Targum example selectors

Date: 2026-09-17. Research is frozen in `docs/research/issue-142-targum-example-selector-validation.md` and was committed first.

1. Add focused parser-level RED regressions before production changes. Start from otherwise-valid reduced concordance/reflex HTML and vary only the example href. Cover concordance unexpected selector, missing/wrong charset, non-decimal text ID, duplicate text ID, non-ASCII-whitespace text list, reflex unexpected selector, and fragment-bearing concordance/reflex URLs. Existing repeated/missing required-selector tests remain authoritative where already present.
2. A valid RED requires dependency/install validation, Ruff lint/format, and mypy GREEN. Pytest should fail only the new malformed-link cases while existing valid Targum fixtures continue to pass.
3. Implement the minimum parser-only validation: exact query-key sets for each example family, `charset=H` for the current concordance contract, one-or-more unique ASCII-decimal concordance text IDs separated only by single ASCII spaces, and no fragments in validated same-origin navigation URLs.
4. Preserve current `example_url` serialization and all public dataclasses/tools. Do not introduce typed follow-up selectors here, change request methods/paths, add CAL requests, or modify #109 semantics.
5. Run the complete deterministic and latest-compatible CI matrices on the exact candidate head.
6. Perform a logically independent adversarial whole-PR review. Challenge over-validation of legitimate encoded lemma keys, query decoding behavior (`+` as space), duplicate/repeated selectors, fragments, encoded/non-ASCII whitespace, route/origin assumptions, valid Onqelos/Neofiti fixtures, and accidental public-schema/request changes.
7. Any blocker gets a focused review-regression RED/GREEN cycle and fresh full CI. Merge only if exact reviewed SHA is unchanged, no unresolved threads remain, and the PR is mergeable against current `main`; use SHA-guarded squash merge.

CAL load impact: zero.