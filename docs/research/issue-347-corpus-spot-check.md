# Issue #347: bounded corpus spot-check and evaluation protocol (2026-11-16)

## Research method and boundaries

One *targeted public-web research session* checked selected short phrases from the original 20-token, **unreviewed LLM-authored** [candidate](../../experiments/ci_texts/specimen_unreviewed.json) against CAL's public, indexed text-reader pages. This is **not** a CAL-MCP live smoke: no `cal_mcp` process or MCP tool was invoked. Search-result matches were followed to CAL pages, not to a bulk export. No CAL pages or verses are vendored in this repository; URLs and coordinates below refer to upstream scholarly data with access date **2026-11-16**.

CAL explicitly describes itself as an unfinished, evolving database and requests retrieval-date attribution: https://cal.huc.edu/ .

### Observed narrow parallels

| Draft claim / string | CAL evidence | What is actually supported | Not supported |
| --- | --- | --- | --- |
| `ܥܠ ܠܒܝܬܐ` (enter a house) | [OS LkSin, Luke 14:1](https://cal.huc.edu/get_a_chapter.php?cset=U&file=60042&sub=2), `60042` / `2` / 14:01 | Exact two-token surface sequence is present in **Old Syriac** Luke Sinaitic manuscript presentation. | That the *entire* generated sentence is grammatical Classical Syriac, or that Old Syriac = Peshitta. The witness identity is critical. |
| `ܚܙܐ` (he saw) | [P 1S, 1 Samuel 26:3](https://cal.huc.edu/get_a_chapter.php?cset=U&file=62008&sub=26), `62008` / `26` / 26:03 | The exact surface occurs as part of `ܘܚܙܐ` in the **Peshitta** (prefix `ܘ` attached). | That CAL confirmed every unprefixed use of `ܚܙܐ` or a unique morphological analysis of an arbitrary generated token. |
| `ܐܝܬ ܠܗ` (he has) | [P Gn, Genesis 39:4–6](https://cal.huc.edu/get_a_chapter.php?cset=U&file=62001&sub=39), `62001` / `39` / 39:04–06 | The sequence `ܐܝܬ ܠܗ` occurs in **Peshitta** possessive context. The same source includes `ܒܒܝܬܐ`. | That possession of water in our novel context is idiomatic or that its complete clause has been checked. |
| `ܒܒܝܬܐ` | Same [P Gn 39:5](https://cal.huc.edu/get_a_chapter.php?cset=U&file=62001&sub=39) | Exact bound-preposition form is directly attested in Peshitta. | That its combination with the generated existential clause has been checked. |
| `ܡܝܐ` / `ܒܝܬܐ ܪܒܐ` | No matching context selected in this bounded check | No corpus-based form/phrase approval can be attached from this research step. | Do not infer absence from the corpus or correctness from silence. |

**Important morphology limit:** an exact surface occurrence is evidence of usage, not a CAL lexical identification. The existing code's `draft:...` placeholders are *not CAL lemma keys*. Follow-up with `cal_token_analysis` on a **CAL-owned coordinate**, or `cal_lexicon_lookup` and dialect-scoped KWIC on a selected actual CAL lemma, requires separate explicit calls; arbitrary generated text cannot be fed to `cal_token_analysis`.

## Independent qualitative inspection of the candidate

| Criterion | Observation | Gate |
| --- | --- | --- |
| Orthography/segmentation | Surface tokens are written in Syriac and align with the draft annotations. Existing audit does not prove the morphological segmentation of `ܒܒܝܬܐ` or `ܠܗ`. | PARTIAL |
| Source fidelity | Two word sequences and two additional token forms have narrow, dated CAL evidence. One two-word phrase comes from **Old Syriac**, others from **Peshitta**. | PARTIAL |
| Linguistic validity | Most generated clauses have **not** undergone expert review; attested subphrases cannot certify grammar or idiomaticity of their whole sentences. | UNVERIFIED |
| Grading | Author-declared annotations give 19/20 tokens known = 95%; this is not a validated learner comprehension metric. | NUMERIC ONLY |
| Story/naturalness | The text repeats `ܓܒܪܐ` five times and mostly restates simple observations about a house and water; it has little plot progression. | NOT ACCEPTED |

The experiment currently **fails its target user-facing feature gate**: no independent expert-validated text and no genuine learner study. Code may be valid as a narrow offline accounting probe.

## Bounded next research / test protocol

1. Preserve the original candidate as baseline; do not rewrite it after looking at the parallels, since that would contaminate the comparison.
2. Create **two separately prompted** 50–100 word drafts with the same deliberately small validated vocabulary, one unguided and one restricted to selected dialect-specific CAL-attested lexemes/constructions. These drafts must be labeled unverified until review.
3. Use an identical annotation schema, thresholds and a blinded expert rubric: wrong lemma/sense; unattested form or tense; dialect mixing; unidiomatic syntax; clitic error; bad educational narrative. Record each proposed correction and whether a specific CAL context actually supports it.
4. Track coverage by **running orthographic token** and by **morpheme/lemma**, not as interchangeable denominators. Do not substitute corpus frequency for a real learner's vocabulary.
5. Run a few deliberate, explicitly user-authorized CAL-MCP queries at conservative rate, recording exact CAL `source_url`, `retrieved_at`, coordinate and selected analysis. Never fetch all words automatically; no batch scraping or database copy.
6. Only after separate philological acceptance, test comprehension with actual learners; no claims of efficacy until then.

## Newly observed parser edge case in a real CAL page

CAL Peshitta text pages commonly terminate clauses with the **Syriac sublinear full stop `܂` (U+0702)**, for example on the [P 1S page above](https://cal.huc.edu/get_a_chapter.php?cset=U&file=62008&sub=26). The pilot audit currently strips only `܀` (U+0700) and ASCII punctuation. A copy of a normal CAL word ending in U+0702 therefore fails surface validation. A focused RED test should reproduce this; the minimal fix is to allow only U+0702 / U+0703 **at token ends** (not inside Syriac tokens), with negative tests to guard against unrestricted punctuation acceptance. This fix remains offline and does not alter the CAL-MCP parser.
