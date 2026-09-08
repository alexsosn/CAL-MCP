# Issue #52 research addendum — ambiguity-preserving CAL code expansion

Date: 2026-09-07

## New requirement

When a Unicode grapheme does not determine exactly one CAL Roman code, CAL-MCP must not either guess or discard the input. It should preserve the ambiguity as the finite set of CAL-code possibilities that are justified by the script itself. When such input is used for lexical search, CAL-MCP should search every bounded candidate rather than force the caller to choose an encoding it cannot know.

This refines the earlier fail-closed rule. **Unsupported** input still fails closed; **finite representational ambiguity** becomes explicit data.

## Ambiguous vs unsupported

Treat a grapheme as ambiguous only when research establishes a small finite set of CAL codes that are all genuinely encoded by that grapheme without additional linguistic inference.

Examples:

- bare Hebrew `ש` -> `$` (shin) or `&` (sin);
- Hatran U+108E3 HATRAN LETTER DALETH-RESH -> `d` or `r`.

These are different from unsupported cases such as vowels/diacritics/editorial marks whose CAL transcription has not been established, malformed mixed-script input, or a character requiring morphological/historical reconstruction. Unsupported cases remain errors.

Pointed Hebrew is deterministic where the dot resolves the distinction:

- `שׁ` -> `$`;
- `שׂ` -> `&`.

## Word-level candidate model

Ambiguity is exposed per lexical word rather than hidden in one guessed string.

Input is segmented only on ordinary ASCII spaces, matching the existing conservative separator policy. The converter does not infer CAL `@` from whitespace and does not perform tokenization beyond that explicit separator.

For each word the result records:

- original word;
- ordered unique CAL-code candidates;
- ambiguous positions and the code alternatives that caused expansion.

Candidate generation is the deterministic Cartesian expansion of only those graphemes with a researched finite alternative set. Candidate order is stable and follows the documented alternative order for each grapheme (e.g. Hebrew shin before sin: `$`, `&`; Hatran daleth before resh: `d`, `r`). Duplicate complete candidates are removed while preserving first occurrence.

The whole conversion result may additionally expose complete-query candidates when their bounded Cartesian product is small, but the per-word candidate list is the primary contract.

## Expansion bounds

Ambiguity must not create unbounded CPU, memory, or CAL traffic.

For v0.1:

- cap generated candidates per word at 32;
- cap complete-query candidates at 64 when materialized;
- fail explicitly with a typed expansion-limit error rather than truncate candidates silently.

These are local conversion limits. Network search has a stricter bound derived from CAL's browse interface below.

## Search integration: lexicon lookup

The current arbitrary Aramaic lexical-query surface is `cal_lexicon_lookup`. Other public operations generally consume English text, opaque IDs, or exact CAL `lemma_key` values returned by prior calls. Therefore v0.1 ambiguity fan-out should integrate with lexicon lookup rather than silently change every exact-ID tool.

Current lexicon lookup performs:

1. normalize query;
2. derive the CAL browse prefix;
3. fetch `browseSKEYheaders.php` for that prefix;
4. locally match candidates;
5. fetch an entry only after one matching lemma is selected.

For ambiguity-preserving search, generate CAL-code candidates first and group them by the browse prefix actually needed upstream. Fetch each **unique prefix once**, then match all candidate spellings against the union of returned browse entries. This is strictly better than one independent lookup per candidate and avoids duplicate CAL requests when ambiguity occurs after the browse prefix.

### Network bound

The production fan-out must have an explicit fixed cap of 8 unique browse-prefix requests per public `cal_lexicon_lookup` call. This matches the worst binary ambiguity across the three-character browse prefix while preventing future script mappings from silently increasing load. If conversion would require more than 8 unique prefixes, fail before making any CAL request.

After browse aggregation:

- zero matching lemmas -> `not_found`;
- one matching lemma -> fetch that entry once;
- multiple matching lemmas -> return the existing explicit ambiguous result and require `lemma_key` selection;
- if `lemma_key` is supplied, it must identify a member of the aggregated matching set, then exactly one entry request is made.

Thus an ambiguity-aware lookup performs at most 8 browse requests plus 1 selected-entry request, never one entry request per encoding candidate.

## Result/provenance requirements

Search results must not erase how they were reached. Provenance should record at least:

- original Unicode query;
- representation/script;
- generated CAL-code candidate words/query candidates used for matching;
- browse prefixes actually requested;
- selected candidate/lemma relationship where a single entry is fetched.

If multiple encodings lead to the same CAL lemma, the lemma is returned once while retaining the candidate provenance.

## TDD implications

Before modifying production search behavior, add RED tests proving:

1. bare Hebrew `ש` returns both `$` and `&` candidates rather than raising;
2. a word with two ambiguous positions expands deterministically and deduplicates;
3. Hatran daleth-resh produces `d` and `r` alternatives once Hatran mapping research is committed;
4. unsupported marks still raise and are never presented as alternatives;
5. candidate-limit overflow fails explicitly rather than truncating;
6. lexicon lookup searches every required unique browse prefix and no duplicate prefix;
7. ambiguity after the browse prefix does not increase CAL request count;
8. >8 required prefixes fails before any network request;
9. aggregated matches preserve existing `not_found` / `ambiguous` / exact `lemma_key` semantics;
10. only one entry request is made after one selected lemma.

## Compatibility decision

The standalone converter becomes ambiguity-preserving. Existing exact CAL-code and deterministic Unicode inputs still produce one candidate and remain behaviorally equivalent.

Lexicon lookup gains bounded ambiguity expansion for representations that require conversion. Existing ordinary Hebrew/Syriac queries that CAL already accepts must be checked carefully: the implementation must not gratuitously replace a one-request Unicode lookup with fan-out unless conversion is needed to represent a script or an unresolved grapheme. Request-count regressions for deterministic inputs remain forbidden.

## Conclusion

Finite orthographic ambiguity is useful information, not an error. CAL-MCP should enumerate all justified CAL-code readings at word level, preserve them in structured output, and make lexical search complete across those readings with prefix deduplication and a hard request bound. Unknown or linguistically underdetermined transcription remains an explicit error.