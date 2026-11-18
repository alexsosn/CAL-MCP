# #347 — feasibility research: CAL-assisted comprehensible input (2026-11-15)

## Research question
Can a learner-facing LLM create *Classical Syriac* graded microstories with a defensible lexical budget, while CAL-MCP provides cited lexical and corpus evidence? This is a feasibility experiment, **not** a CAL-MCP feature or an instruction to automatically crawl CAL.

## Evidence
1. [CAL introduction](https://cal.huc.edu/info.html) describes a live, incomplete scholarly lexicon spanning Aramaic varieties. Its [new-user guide](https://cal.huc.edu/cal_new_user_guide.html) documents headword lookup, English gloss search and texts. CAL citations need an access date.
2. [CAL-MCP text/token documentation](../../docs/tools/token-analysis.md) shows that `cal_token_analysis(coordinate, word_index)` only accepts coordinates from CAL's own online texts. It **cannot morphologically validate arbitrary generated Syriac text**. [Lexical guide](../../docs/guides/lexical-research.md) confirms that gloss search, lookup, and KWIC follow-ups are explicit steps and that CAL may preserve multiple analyses.
3. Second-language reading research often discusses **95–98% known running-word coverage** ([replication/review](https://www.cambridge.org/core/journals/language-teaching/article/how-much-vocabulary-is-needed-to-use-english-replication-of-van-zeeland-schmitt-2012-nation-2006-and-cobb-2007/1D217A56A2E0056E67802A6A8360FDDE); [2024 processing discussion](https://academic.oup.com/applij/article/45/6/953/7841943)). These studies are not trials with beginner Classical Syriac learners: treat 0.95 as a **configurable exploratory threshold**, not a validated learning outcome.
4. [Beginner Syriac teaching example](https://ceulearning.ceu.edu/course/info.php?id=18907) uses basic texts alongside a communicative teaching approach. [Thirty Syriac reading selections](https://api.pageplace.de/preview/DT0400.9781463244903_A46859807/preview-9781463244903_A46859807.pdf) illustrate a different, authentic-text graded approach. Neither establishes that LLM-authored Classical Syriac stories are accurate.
5. CAL-MCP [request policy](../../docs/limitations.md) intentionally forbids corpus mirroring, hidden traversal and enrichment presented as CAL. The experimental verifier must make **zero HTTP requests** and store no CAL-derived text.

## Working hypothesis
- **Feasible to measure:** proportion of running whitespace tokens *annotated* solely with the learner's known lemma identifiers, uniqueness of new lemma IDs, and consistency between the Syriac draft and explicit token annotation.
- **Not proved by that measurement:** correctness of lemmas, dialect, surface inflection, clitic segmentation, idiom, readability or actual comprehension. All tags are author-supplied. High coverage can be gamed with repeated trivial vocabulary.
- **Necessary additional gates:** manual expert review of each story and of CAL cross-checks, sampled with explicit URLs/dates. Genuine learner testing would require participants, a comprehension task and repeated sessions.

## Minimal pilot protocol
1. Author one short **original, unreviewed** Syriac candidate, not a CAL excerpt. Explicitly label all observations as provisional.
2. Manually annotate each whitespace-delimited surface token with one or more candidate lemma IDs (including clitics) and build a learner-known set.
3. Run the offline audit at 0.95 and a maximum of one novel lemma; test that malformed/missing annotations fail closed. Output numeric coverage and all novel lemma keys. Never call this a morphology check.
4. Conduct a separate skeptical review of sample orthography, alignment, source identity claims, and statistical interpretation.
5. Hold off on generation APIs, CAL web calls, batch lexicon verification, integration into the public MCP server or release work until a real linguist can check the pilot and the existing user-facing features are secure.

## Evaluation / failure criteria
- A draft that scores above the lexical threshold but uses ungrammatical forms is a **failure of linguistic validation** regardless of the numeric score.
- Repeated 20-token texts with one unknown token can technically pass 95% while being stilted. Record repetition and pedagogical naturalness separately.
- An unannotated/misaligned token, non-Syriac text, invalid annotation or unavailable source evidence must not be quietly promoted to a valid CAL citation.
- CAL provenance must only be recorded when actually fetched; **none is fetched in this first offline proof of concept**.

## Research-to-implementation plan and TDD gates
- **RED:** commit deterministic tests for token alignment, clitic multi-lemma treatment, repeated unknowns, zero-token rejection, Unicode punctuation, and budget violations. Confirm tests fail because the experimental audit module is absent.
- **GREEN:** implement an isolated stdlib-only `experiments/ci_texts/audit.py` with no imports from runtime CAL-MCP, no HTTP, and no packaging entry point.
- **Measure:** run the specimen and a deliberate high-unknown variant; record actual numeric results and limitations in the experiment README.
- **Review:** independent adversarial pass against the issue's acceptance criteria and evidence provenance; keep the PR draft pending expert linguistic review.

**Scope:** issue [#347](https://github.com/alexsosn/CAL-MCP/issues/347). No alteration to `src/cal_mcp`, release docs or MCP tool schema.

## Follow-up 2026-11-16: public-web source sampling

The initial no-CAL-data stage is complete. A subsequent manually selected **public CAL web** spot-check recorded several exact form/phrase parallels and their witness identities; see [source-by-source findings](issue-347-corpus-spot-check.md). This is not a CAL-MCP invocation and does not upgrade any `draft:...` key to a genuine CAL lemma. The revised immediate plan allows **bounded, explicit human-directed upstream lookups** while still forbidding automatic traversal, harvesting, background requests or presenting a sample attestation as validation of a whole generated sentence. The final linguistic-review and real learner-comprehension gates remain open.

## 2026-11-18 review follow-up: distinguish lexical budget from surface repetition

**Research finding:** The current unreviewed 20-token candidate has only **10 distinct terminal-punctuation-stripped surface forms**, including five occurrences of `ܓܒܪܐ`, even though its *author-labeled* known-token fraction is 19/20 = 95%. A hypothetical 5-token passage consisting only of `ܓܒܪܐ` would be scored 100% known by the numeric budget if `draft:man` is declared known. Neither outcome establishes a readable story.

**Plan / test-first gate:** Add two *descriptive-only*, zero-network counters to `audit_draft`: `unique_surface_forms` (distinct Unicode-exact Syriac token surfaces **after existing terminal-punctuation trimming**) and `surface_type_token_ratio` (unique forms / running whitespace tokens). They are separate from CAL lemma identities, do not change `passes_lexical_budget`, do not use new normalizations, and have **no acceptance threshold**. First commit tests showing 1/5 repetition and the actual specimen's 10/20 = 0.5 ratio; confirm RED in both CI lanes with lint/format green. Then implement the smallest change using the already-validated `surfaces` list; record GREEN CI, falsify independent tests/review and update the experiment README. Keep source corpora, runtime MCP code, release metadata, public API and CAL HTTP untouched.

**Interpretation:** Type-token ratio depends heavily on text length, orthography, clitic segmentation and inflection, so it is only a within-document repetition warning. It is not learner vocabulary knowledge, lexical richness independent of text length, Syriac morphology, CAL attestations, narrative progression or expert approval. The CAL-MCP v0.2.0 publication gate #353 is independent of this draft experiment.
