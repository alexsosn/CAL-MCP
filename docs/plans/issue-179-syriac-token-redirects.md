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
   - Tel Dan current linked control `1325001`, word 4 (selected from the 2026-09-27 live text page): confirm the pre-existing multi-candidate linked parser still succeeds.
2. Tel Dan's old fixture coordinate proved stale; the bounded live research amendment records the current coordinate before final acceptance. Do not change production for identifier churn alone.
3. Remove the temporary workflow after the acceptance result.
4. Run both full CI matrices on the workflow-free exact head.
5. Perform a new logically independent exact-head adversarial review.

## Final adversarial-review amendment — fail closed on malformed current labels

Exact-head review of `445c7224` found two missing guards in the new current `lexlink` parser:

- a valid result table can currently succeed with an empty rendered analysis label;
- an analysis label containing `-->` but not matching the researched `SOURCE --> TARGET` suffix
  can currently fall through as a non-redirect candidate with `analyzed_lemma_key=null`.

Before merge:

6. RED:
   - remove the rendered pre-table analysis label from the current Syriac fixture and require
     `TokenAnalysisParseError`;
   - mutate the explicit redirect to a malformed target such as `)syr N --> )syrA` and require
     `TokenAnalysisParseError`.
7. GREEN:
   - require a non-empty analysis label for the current `lexlink` shape;
   - if `-->` occurs, require the researched redirect regex to match before returning success.
8. Run both full CI matrices and perform a fresh exact-head adversarial review.

## Final redirect-cardinality amendment

Re-review of `f3dfb627` found that a label with multiple `-->` operators can still match the
last researched-looking suffix and silently discard an earlier source key.

Before merge:

9. RED: mutate the current redirect into a two-arrow chain and require parser drift.
10. GREEN: whenever redirect notation is present, require exactly one `-->` and a valid
    researched suffix whose target equals the linked lemma key.
11. Re-run both full CI matrices and perform the final exact-head adversarial review.

