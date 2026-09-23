# Issue #146 plan — fail closed on altered Targum chooser actions

Date: 2026-09-23. Research is frozen in `docs/research/issue-146-targum-chooser-action.md` and was committed before behavior tests.

1. Add focused RED parser regressions using minimal inline chooser HTML. Cover:
   - a same-origin action under a different directory;
   - a query-bearing root action;
   - a bare query delimiter;
   - a nonempty fragment;
   - a bare fragment delimiter.
2. Add a positive control for a same-origin absolute current root action so hardening does not accidentally require only one textual URL spelling. Existing Onqelos and Neofiti reduced fixtures remain the primary valid-current controls.
3. A valid RED requires Ruff lint/format and strict mypy green; pytest should fail only the new malformed-action cases while the positive control and existing fixtures pass.
4. Implement the smallest shared chooser-action predicate change:
   - reject literal `?` or `#` delimiters in the original action;
   - resolve the action normally;
   - require exact same origin and exact root path `/<expected_action>`.
5. Do not change chooser/reflex public models, MCP schemas, service request construction, cache behavior, or request counts.
6. Run the complete deterministic and latest-compatible CI matrices on the exact candidate head.
7. Perform a logically independent adversarial whole-PR review of the exact candidate SHA. Challenge absolute/root-relative equivalence, dot-segment normalization, query/fragment delimiters, encoded delimiters, Onqelos/Neofiti route separation, valid fixtures, and accidental public/request changes.
8. Any blocker gets a focused review-regression RED/GREEN cycle plus fresh exact-head CI. Merge only with an unchanged reviewed SHA, no unresolved review threads, and SHA-guarded squash merge.

Live CAL load for implementation: zero. Research already consumed one GET in run `35853288206`.
