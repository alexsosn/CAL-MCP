# Issue #159 implementation plan — public Syriac missing-word choices

Research: `docs/research/issue-159-syriac-missing-category-enum.md`.

1. Freeze nine authoritative public selectors based on
   `_MISSING_WORD_PATHS`; do not probe CAL.
2. **RED tests first:** in-process MCP tool schema must enumerate exactly
   nine slugs, accept each and reject arbitrary `ot-peshitta` via
   Draft 2020-12 validation; a wrong MCP call must return a structured
   `invalid_input` envelope whose bounded message names the actual values,
   without contacting CAL; a direct bad service selector must likewise list
   valid names without sending HTTP. Assert enumerated set is identical to
   route mapping and docs to prevent divergence.
3. **GREEN:** add a `StrEnum` for nine selectors (mirroring existing
   gloss-field pattern), annotate the tool, preserve existing service
   `str` interface, and enrich *only* this operation's SDK validation
   message and service-invalid error. Keep 500-character bound.
4. Update `docs/tools/syriac.md` to mark the argument as schema-enumerated
   and clarify selection is exact/no upstream request on invalid input.
5. Run deterministic/latest-compatible CI (Ruff, mypy, pytest, no CAL I/O).
6. Perform a logically independent adversarial review of the exact final
   SHA: check enum/mapping exhaustiveness, the existing 34-tool release
   manifest, error sanitation, wrong-type/misspelled input, no extra
   upstream calls, return compatibility. Resolve findings before merge.

**Release policy:** acceptance does not authorize tagging v0.1.0 or
publishing. Issue #15 separately controls trusted-publisher verification.
