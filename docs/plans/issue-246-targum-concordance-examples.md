# Issue #246 test-first implementation plan

Research: `docs/research/issue-246-targum-concordance-examples.md`.

1. **RED** reduced, synthetic BR-line CAL Targum example fixture based on the two 2026-10-10 live source-shape audits (no full copyrighted verse transcription). Test exact source URL, group heading, ordered linked coordinates/contexts/target highlight, Targum-specific total; reject wrong group, unexpected origin, repeated selectors, invalid/missing totals and wrong linked target paths. Verify 1 GET / zero transport on invalid selectors, and parent returns derived `text_ids`. Test public schema tool identity.
2. **GREEN** implement bounded `TargumConcordanceExamplesService`, source-specific heading/summary checks, reuse existing internal KWIC hit/coordinate parsing after validating compatibility on reduced fixture. New MCP tool and parent row `text_ids` as additive field.
3. Batch release manifest and documentation updates from 35 to 36 tools (maintaining exact tool-name equality), preserve existing operation schemas. Avoid a separate CI run per documentation file.
4. Require Ruff, mypy and pytest in deterministic and latest-compatible CI, plus a new genuinely independent adversarial review of exact SHA. Only after passing offline gates make a separate bounded decision whether one installed-wheel live acceptance of one returned group is justified, with fixed attempt cap 25, zero retries.
5. Only merge after code/data review and final CI; separate issue #15 keeps release/PyPI blocked.

Do not invent verse identities, infer alignment, crawl linked chapters, deduplicate targets, or re-request parent rows automatically.
