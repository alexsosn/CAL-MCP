# Experimental Classical Syriac CI text audit — issue #347

**Status:** research prototype; **not** a shipped CAL-MCP feature. The candidate text is original LLM-authored draft material, **not** taken from CAL and **not linguistically reviewed**. No CAL-MCP query was run. A subsequent **targeted CAL website** spot-check found a few short attested parallels but did not confirm the candidate's morphological annotations or the correctness of the full text.

See [research, assumptions and TDD plan](../../docs/research/issue-347-comprehensible-input.md).

## Run

In the repository root with Python 3.11+:

```bash
python -m pytest tests/test_ci_texts_experiment.py -q
python -c 'import json; from experiments.ci_texts.audit import audit_draft; p="experiments/ci_texts/specimen_unreviewed.json"; print(audit_draft(json.load(open(p, encoding="utf-8"))))'
```

The JSON specimen is a short 20-token draft. Its `draft:...` lemma identifiers are **local placeholder concepts**, **not** CAL keys, attestations, morphology analyses or a dialect-certified lexicon. To use genuine CAL lemma keys later, a person must explicitly map, source-check and review each identifier and corresponding surface form.

The verifier compares supplied whitespace-token surface strings to the draft; strips only a narrow set of terminal punctuation; counts a running token as known only when **all** of its annotated lemma identifiers belong to the supplied learner-known set (including clitic components); and counts distinct unknown lemma identifiers separately. It rejects missing/misaligned annotations and standalone Syriac combining marks, and rejects any claim of CAL or human linguistic verification. It **does not resolve ambiguous analyses**; a manually selected lemma annotation is treated as an unverified input. It cannot validate the annotations themselves.

## Measured pilot — 2026-11-15, offline Python 3.13

| Scenario | Running tokens | Known tokens | Unknown tokens | New lemma IDs | Coverage | Lexical gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Unreviewed specimen, as annotated | 20 | 19 | 1 | 1 | 95% | PASS (threshold 95%, max 1 new) |
| Same text, learner **does not** know `draft:water` | 20 | 16 | 4 | 2 | 80% | FAIL |

Original focused tests: **19 passed**, including a Unicode combining-mark regression and a pinned audit of the committed specimen. Additional tests exercise ordinary CAL Syriac token-final `܂` and `܃` while rejecting both internally. This verifies elementary accounting and fail-closed structure validation for the offline experiment. It does **not** establish that the Syriac passage is grammatical, that learners know the declared vocabulary, that any draft identifier is a CAL lemma, or that 95% produces comprehension. The candidate is highly repetitive and is not yet a pedagogically acceptable graded reader.

## Targeted CAL corpus spot-check — 2026-11-16

A manually selected set of short form/construction observations is recorded in [the dated research note](../../docs/research/issue-347-corpus-spot-check.md), with public CAL URLs and verse/line coordinates. In particular, `ܥܠ ܠܒܝܬܐ` is observed in **Old Syriac Luke Sinaitic**, while `ܚܙܐ` (with conjunctive prefix) and `ܐܝܬ ܠܗ` have separate **Peshitta** evidence. These witnesses are not treated as interchangeable. No generic automatic morphology checker is implied, and the placeholders remain unverified.

This spot-check also exposed a real orthographic edge case: common CAL Syriac corpus text uses terminal `܂` and `܃`; the separate test-first fix adds support for them in the offline auditor without accepting punctuation inside a token.

## Honest next study gates

1. A Syriac specialist independently corrects/approves forms, clitic analyses, idiom, dialect and story naturalness. Particular constructions such as `ܥܠ` and `ܐܝܬ ܠܗ` require explicit checking.
2. For an *explicit small selection* of lexemes, use `cal_gloss_search`, `cal_lexicon_lookup`, `cal_kwic_dialect` and source contexts as needed; record real CAL source URLs, retrieval timestamps and chosen analyses. Do not pretend `cal_token_analysis` works on arbitrary drafts.
3. Compare an unconstrained LLM candidate to a constrained candidate under blind expert error annotation; measure how many human interventions are required.
4. Only after expert acceptance, test with real learners using comprehension questions and reading time, not a numeric coverage threshold alone.

**CAL access:** zero CAL-MCP requests and zero new requests in experimental code. A few CAL public-text pages were inspected manually through a web browser for the spot-check; no hidden traversal, local corpus, included CAL text or added MCP API. The specimen belongs to the experiment only and must not be promoted to official CAL data.
