# Issue #330 implementation plan — installed-wheel smoke for evolving tool surface

**Plan date:** 2026-11-07. Research committed first at `f7e8e2f6653463ec74097fc8d93d34e7d5839c67`.

## Acceptance boundary

When the next tagged `0.2.x` release is attempted, the existing release workflow must run the **current 13-case smoke** on the exact installed distribution. A successful report requires 12 CAL-backed cases, including `cal_bibliography_recent`, at least 12 measured transport starts, a structured nonempty recent-bibliography response with valid citations and provenance, and every reviewed historical case. The source package can continue to advertise 37 tools. Never claim new package publication, never run the full CAL suite during PR CI or research, and leave the immutable v0.1.0 tag/manifest intact.

## RED — offline deterministic tests first

1. Update the tests that explicitly assert *current* `DEFAULT_SMOKE_CASES` to demand the exact 13 identities, including `recent_bibliography:cal_bibliography_recent` as the last case, and a 12-attempt floor rather than 11. Preserve a separate explicit immutable 12-item `_REVIEWED_V01_SMOKE_IDENTITIES` expectation.
2. Add a malformed/empty recent result content test using synthetic structured `records` with blank/missing citations, and a positive array of records. Validate that `evaluate_tool_result` treats `recent_bibliography` as a nonempty scholarly row family rather than accepting an empty response.
3. Test anti-vacuity: 12-case original matrix cannot pass the current release gate even when all 12 synthetic outcomes are reported `ok`; 13 correct cases with only 11 actual starts also cannot pass.
4. Execute CI on the **test-only** branch: Ruff/mypy clean; pytest must fail because the new case/content gate is absent. Record the RED evidence before production updates.

## GREEN

1. Append one `SmokeCase("recent_bibliography", "cal_bibliography_recent", {})` to `DEFAULT_SMOKE_CASES`, without touching prior case order or selectors. This is one explicit GET, with the same source-owned window as #39.
2. Add `recent_bibliography: ("records","citation",1)` to the minimal scholarly-content checks. The existing generic JSON-schema/provenance validation and 429/transport failure handling remain active.
3. Preserve `_REVIEWED_V01_SMOKE_IDENTITIES` untouched; define `_REVIEWED_CURRENT_SMOKE_IDENTITIES` as reviewed v0.1 tuple plus one exact recent identity. The current completion gate must compare against the latter, require at least 13 cases and 12 CAL-backed, and count at least 12 actual starts, still no more than 25. Keep the first-failure stop, pacing and timeout unchanged.

## Review and documentation gates

- Fix only current-version test references to 12/11; leave historical v0.1 assertions where they specifically describe the published release. Include altered smoke-data fixtures and negative tests as warranted.
- Update `wiki/testing.md` and/or `docs/installation.md` to distinguish historical 12-case v0.1 release from future 13-case current source. Add `CHANGELOG.md` unreleased note and dated research cross-link; an architecture decision only if a durable boundary changes.
- Rerun complete pinned and latest-compatible CI, Ruff and strict mypy. Normal CI must perform **zero CAL HTTP**.
- Independently review the exact final SHA, especially that a future current release cannot pass with a truncated matrix or insufficient counted I/O, that invalid recent bibliography structured data fails, that original fixed cases and historical manifest are not weakened, and that no unexpected CAL traffic is introduced.
- PR merge and close #330 only after exact-head CI green and review accepted. This episode's previous issue #39 installed-wheel one-call live smoke already provides bounded user-facing acceptance; an actual new package tag later requires the complete current 13-case live release gate under its established controls.
