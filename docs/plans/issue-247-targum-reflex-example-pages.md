# Issue #247 implementation plan

Depends on research at
`docs/research/issue-247-targum-reflex-example-pages.md`.
Do not implement the Neofiti parser branch until the bounded current
`getNMT.php` structure check (run 38059821947) finishes.

1. **Model source semantics first.** Decide from observed Onqelos and Neofiti
   pages whether example pairs have explicit trustworthy block boundaries.
   If CAL only provides untyped sequential blocks, represent raw ordered
   text blocks without invented MT↔Aramaic alignment or synthesized verse IDs.
2. **RED:** make reduced semantic HTML fixtures from observed tag/class/head
   structures only (not full upstream captures). Tests must reject wrong
   `targum`/MT ID/CAL lemma, missing or conflicting headings, noncanonical
   lexical links, unexpected navigation, empty/malformed example blocks,
   nested/duplicate untrusted controls, and erroneous deduplication of
   repeated source examples. No normal CI requires CAL access.
3. **RED for public operation:** fake client proves no arbitrary URLs,
   invalid inputs incur zero transport, exactly one GET on valid selected
   selectors, source-aware output and timestamp provenance; preserve
   original parent `cal_targum_hebrew_reflexes` one-POST behavior.
4. **GREEN:** implement minimal new parser and service method, expose a
   typed public `cal_targum_reflex_examples(targum,mt_lemma_id,lemma_key)`
   tool; update public tool manifest, schema/docs, and release verification
   invariants to 35 instead of hardcoded 34, with exact-name assertions.
5. **CI:** Ruff lint/format, mypy and offline pytest in frozen and
   latest-compatible environments. Do not run live acceptance until
   deterministic parser fixtures demonstrate the exact source semantics.
6. **Adversarial independent review** of exact SHA grounded in the recorded
   live CAL shapes and changed source; fix blocking findings with tests.
   Merge only after GREEN CI and review. Publication/trusted publisher
   remain controlled by issue #15.

No bulk CAL requests, auto-followup, arbitrary endpoint execution,
background fetching, or import-time network IO.
