# Research-plan-TDD-test gates — CAL KWIC unrendered entries (#266)

1. Research before tests: docs/research/issue-266-kwic-unrendered-hits.md.
2. RED source-shaped reduced fixture for mlk N dialect 71: one legitimate BR-line linked hit, one literal error: line not found for 71600222x004133, one following form summary reporting TWO examples. Assert upstream total 2, rendered hits 1, unrendered hits 1 with exact message/coordinate/owning form, and typed additive MCP result serialization without invented full-context URL.
3. GREEN: recognize the exact diagnostic marker, preserve source-line ordering, and count both rendered/unrendered entries per following validated form summary. Reuse old KWIC target structures and never forge a target hit.
4. Adversarial negatives: malformed coordinate, contradictory/count-mismatched summaries, out-of-form errors, unknown found-for text, and unchanged legacy dialect/text KWIC fixtures. Do not infer source identity.
5. Update docs/tools/concordance.md, research.md and public result shape while retaining all 36 tools. Run Ruff/mypy and full pytest in pinned/latest-compatible CI. Perform genuinely independent skeptical exact-head review against actual issue source evidence and negative fixtures. Squash merge only after both matrices and review; do not use live CAL while issue #262 is rate-limited.
6. A text-scoped diagnostic route requires a separate source-backed research follow-up, not permissive fallback.
