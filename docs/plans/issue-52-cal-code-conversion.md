# Issue #52 plan — deterministic Aramaic/Unicode → CAL code conversion

Date: 2026-09-07

## Goal

Add a local `cal_convert_to_code` capability for the v0.1 contract plus bounded ambiguity-aware lexical search, without changing exact-ID tool semantics.

Research gates:

- `docs/research/issue-52-cal-code-conversion.md`
- `docs/research/issue-52-ambiguity-expansion.md`

Execution addendum:

- `docs/plans/issue-52-ambiguity-expansion.md`

## Gate order

1. Research every corpus-relevant script and ambiguity boundary before implementing it.
2. Commit plan updates before new tests/implementation.
3. Add focused RED tests for converter/public schema/search fan-out.
4. Implement the minimum mapping/candidate/search behavior required by those tests.
5. Add tiny attested CAL corpus fixtures for each supported script family.
6. Run deterministic + latest-compatible full CI.
7. Freeze exact SHA and perform logically independent adversarial review.
8. Any review blocker requires a regression RED, fix, fresh GREEN, and new exact-head review.

## Conversion contract

The converter returns ordered candidate sets **per word**, not a guessed scalar CAL code.

- Deterministic input -> exactly one candidate.
- Researched finite ambiguity -> every justified candidate.
- Unsupported/unverified transcription -> explicit error.
- No silent mark stripping, morphology, spelling reconstruction, or `@` inference.
- Candidate expansion is bounded as specified in the ambiguity addendum.

Scripts to research and either support or explicitly exclude with evidence before v0.1:

- scholarly Unicode transliteration;
- Hebrew/square Aramaic;
- Syriac, including CPA use;
- Imperial Aramaic;
- Palmyrene;
- Nabataean;
- Hatran;
- Samaritan;
- Mandaic;
- any additional dedicated Unicode script shown to correspond to an actual CAL Aramaic corpus family.

## Search contract

`cal_lexicon_lookup` is the v0.1 arbitrary Aramaic lexical-query surface. Where conversion produces multiple CAL candidates, lookup must search all bounded variants.

Implementation must:

- group candidates by unique CAL browse prefix;
- fetch each prefix once;
- reject >8 required prefixes before network I/O;
- aggregate and deduplicate matches by canonical lemma key;
- preserve existing not-found/ambiguous/explicit `lemma_key` selection behavior;
- fetch at most one selected entry;
- preserve legacy request counts for deterministic inputs where conversion fan-out is unnecessary.

Exact-ID tools (`lemma_key`, text IDs, dialect IDs, etc.) do not gain hidden fan-out.

## Corpus fixtures

For each supported script family, use a small fixed set of attested CAL words/very short sequences. Record dialect/corpus, stable locator, retrieval date, CAL Roman form, Unicode-script input, and expected candidate set. Fixtures are citation-sized and offline; no bulk extraction or live CI dependency.

## Public MCP schema

`cal_convert_to_code` remains local-only and structured. It exposes at least:

- original input;
- detected/explicit representation;
- conversion strategy;
- per-word original text;
- ordered CAL-code candidates;
- ambiguity metadata for positions with multiple justified codes.

## Review checklist

Independent review must challenge:

- every mapping against committed evidence;
- omitted corpus-relevant scripts;
- false ambiguity vs unsupported distinctions;
- candidate ordering/deduplication/completeness;
- expansion limits and no silent truncation;
- browse-prefix grouping and 8-request cap before I/O;
- one-entry-fetch invariant;
- deterministic legacy request counts;
- provenance of candidate encodings;
- tiny CAL fixtures and their locators;
- docs claims vs actual supported subset;
- no accidental CAL traffic from the standalone converter.

## Release gate

Issue #52 is a must-have blocker for #15/v0.1.0. Do not tag or publish v0.1.0 until #52 and acknowledged release-blocking maintenance defects (currently #50/#51) are merged and a final release-readiness audit passes.
