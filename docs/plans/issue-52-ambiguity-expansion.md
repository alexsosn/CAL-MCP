# Issue #52 plan addendum — ambiguity-preserving conversion and search

Date: 2026-09-07

Research gate: `docs/research/issue-52-ambiguity-expansion.md`.

## Gate 1 — revise RED tests before production changes

Add/replace focused tests so the new contract is test-first:

### Converter

- bare Hebrew `ש` yields ordered candidates `("$", "&")` instead of raising;
- pointed `שׁ` and `שׂ` remain deterministic;
- multiple ambiguous graphemes expand all combinations in stable order;
- duplicate candidates are deduplicated;
- unsupported marks still raise;
- expansion over 32 candidates for one word raises a typed limit error, never truncates;
- result exposes per-word candidates and ambiguity metadata;
- deterministic inputs still expose exactly one candidate and preserve the existing code value.

### Lexicon search

Use fake transport only. Require:

- candidate CAL spellings are grouped by unique CAL browse prefix;
- every required unique prefix is requested exactly once;
- ambiguity outside the browse prefix adds zero requests;
- multiple encoding candidates leading to the same lemma are deduplicated;
- existing not-found/ambiguous/`lemma_key` selection semantics remain intact;
- after selection, exactly one entry request is performed;
- more than 8 unique prefixes raises before transport is called;
- deterministic legacy inputs retain existing request counts.

Commit tests and run full CI. Valid RED must be attributable to the old fail-closed/single-query implementation, with Ruff/format/mypy green.

## Gate 2 — minimal converter implementation

Refactor the in-progress #52 converter only as required by RED:

- represent conversion as ordered candidate sets per word;
- introduce typed ambiguity metadata;
- introduce a typed expansion-limit error;
- replace bare-Hebrew-shin failure with `$`/`&` alternatives;
- later script-specific ambiguous characters (e.g. Hatran daleth-resh) use the same table-driven alternative mechanism;
- retain explicit failure for genuinely unsupported marks.

Do not silently discard characters, infer morphology, infer `@`, or broaden the mapping beyond researched tables.

## Gate 3 — bounded lexicon fan-out

Integrate conversion only where needed by `LexiconLookupService`:

1. derive candidate CAL spellings;
2. derive browse prefix for each candidate;
3. stable-deduplicate prefixes;
4. reject >8 unique prefixes before any network call;
5. fetch each prefix once;
6. match the union of browse entries against all candidate spellings;
7. deduplicate matching lemmas by canonical `lemma_key` while retaining candidate provenance;
8. preserve existing ambiguity handling;
9. fetch at most one selected entry.

Do not integrate fan-out into exact-ID tools in this ticket.

## Gate 4 — corpus/script expansion

Continue the already-required script inventory (Imperial Aramaic, Palmyrene, Nabataean, Hatran, Samaritan, Mandaic, CPA/Syriac, Hebrew). For each script:

- commit research evidence first;
- add attested tiny CAL fixture(s);
- add RED for deterministic and ambiguous characters;
- implement only the documented table;
- keep unsupported marks explicit.

## Gate 5 — docs and public schema

Document that `cal_convert_to_code` returns candidate sets, not a guessed single code, and that `cal_lexicon_lookup` automatically searches all bounded representational variants when required.

Public structured output must make ambiguity inspectable. No hidden variant selection.

## Gate 6 — GREEN and independent review

Require deterministic + latest-compatible CI green. Freeze exact head and perform logically independent adversarial review focused on:

- completeness of candidate expansion;
- ordering/deduplication;
- no silent truncation;
- unsupported-vs-ambiguous boundary;
- prefix deduplication;
- hard 8-prefix network cap before I/O;
- one-entry-fetch invariant;
- legacy deterministic request counts;
- provenance of candidate encodings;
- corpus-script mappings and fixtures;
- no unreviewed combinatorial expansion.

Any blocker requires regression RED, fix, fresh GREEN, and new exact-head review before merge.
