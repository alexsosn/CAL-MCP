# Issue #179 plan — parse current linked Syriac token-analysis redirects

Date: 2026-09-27. Research: `docs/research/issue-179-syriac-token-redirects.md`.

1. Add a minimal reduced fixture for current
   `getlex.php?coord=620570101&word=1` preserving only:
   - the unique result marker;
   - CAL's rendered redirect label;
   - the one malformed-nesting `a.lexlink` lemma header;
   - a tiny sense-outline sentinel after the table to prove the boundary.
2. RED before production code:
   - current Syriac fixture returns one candidate;
   - `analysis_label` preserves the complete rendered analysis label;
   - additive `analyzed_lemma_key == ")syr N"`;
   - linked target remains `lemma.lemma_key == ")syr A"`;
   - serialized result exposes both;
   - current sense-outline content does not become another candidate;
   - existing single/multiple linked fixtures return `analyzed_lemma_key=None`.
3. RED fail-closed mutations:
   - remove the `lexlink`;
   - add a second `lexlink`;
   - change the rendered redirect target but not the linked target;
   - change the linked target but not the rendered redirect;
   - add/remove/repeat unexpected query selectors;
   - damage the candidate table/anchor boundary.
4. GREEN:
   - extend `TokenAnalysisCandidate` with nullable `analyzed_lemma_key`;
   - add a small HTML parser dedicated to the researched current `lexlink` candidate table;
   - parse the analysis-label region independently of the malformed linked header;
   - reuse existing lemma-key/header helpers for the target `LemmaRef`;
   - validate redirect source/target notation and target/link identity;
   - if a page contains current `lexlink` markup, never fall back to the legacy parser on a
     malformed current structure;
   - otherwise retain legacy/reduced parsing unchanged.
5. Keep linkless marker-success pages as parser drift under #179; #193 owns their semantics.
6. Update `docs/tools/token-analysis.md`, `research.md`, fixture provenance, server description
   if needed, and CHANGELOG.
7. Run focused tests, then both complete deterministic CI matrices.
8. Installed-stdio live acceptance with three bounded calls:
   - Peshitta `620570101`, word 1 succeeds and exposes source `)syr N` + target `)syr A`;
   - one existing known-working Targum or Tel Dan token still succeeds;
   - one linkless Peshitta/CPA token still fails closed at the #193 boundary, proving #179 did not
     misclassify it as success/not-found.
9. Delete any temporary live workflow.
10. Perform a fresh logically independent adversarial review of the exact final SHA. Fix, retest,
    and re-review every finding before merge.
