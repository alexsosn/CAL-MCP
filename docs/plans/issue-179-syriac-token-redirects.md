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

## Live compatibility amendment

The first live acceptance caught that current Targum `5101801011/0` also uses the strict
one-row `lexlink` result table but has no `-->` redirect.

Before changing production again:

11. Add a reduced current Targum `lexlink` fixture and RED test proving the current implementation
    rejects it.
12. Generalize only the researched current-table parser:
    - strict table/link/selectors stay identical;
    - explicit redirect -> validate and expose `analyzed_lemma_key`;
    - no redirect -> `analyzed_lemma_key=None`, with no inferred source key.
13. Re-run full CI and the three-call installed-stdio acceptance.

## Adversarial-review amendment — final installed-stdio controls

Exact-head review of `f94ad277` found that the first installed-stdio acceptance run caught the
Targum regression, but the temporary workflow was removed before the Targum GREEN. The final
branch therefore lacks a successful user-level acceptance after all parser changes.

Before merge:

1. Add a bounded temporary installed-wheel/stdio workflow with exactly three token-analysis calls:
   - Peshitta `620570101`, word 1: preserve analysed `)syr N` and linked target `)syr A`;
   - Targum `5101801011`, word 0: succeed and keep `analyzed_lemma_key=null`;
   - Tel Dan `1325000000002`, word 0: confirm the pre-existing linked control still succeeds.
2. If Tel Dan exposes a newly drifted shape, research and record it before changing production.
3. Remove the temporary workflow after the acceptance result.
4. Run both full CI matrices on the workflow-free exact head.
5. Perform a new logically independent exact-head adversarial review.

