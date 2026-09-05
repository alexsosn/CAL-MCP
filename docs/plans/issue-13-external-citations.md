
Research for this issue used seven fixed bounded branch-only requests across three runs; temporary workflows were removed before this plan was frozen. Normal tests are offline fixtures only.

## Execution record

- Primary test-only RED: `8d9e3978f351eb9c3dc913e540ace5c909f50112`.
- First documented GREEN: `b94dc404e9ed94877735ae3fd9449d9168c2cdad`, with 327 tests passing.
- First skeptical review found source-abbreviation format-control validation and missing concrete documentation-example gaps. The review-regression RED had 327 passing / 2 failing tests; minimal fixes reached 329 passing tests.
- Fresh whole-PR review then found a composability gap for CAL-returned source abbreviations containing Unicode format controls. A dedicated review-regression RED had 329 passing / 1 failing test; the parser now rejects those returned identifiers before exposing them.
- A subsequent fresh review found the same staged-composability issue for CAL-returned source abbreviations longer than the public 128-code-point follow-up limit. The dedicated RED kept install/Ruff/format/mypy green and produced exactly 330 passing / 1 failing test.
- The minimal length fix uses one shared 128-code-point bound for caller input and returned source abbreviations. This helper-free checkpoint triggers authoritative full CI before the final exact-SHA whole-PR review.
