# Issue #52 research — deterministic Aramaic/Unicode → CAL code conversion

Date: 2026-09-07

## Question

What is the smallest release-safe local conversion contract that lets CAL-MCP users turn ordinary Aramaic input into CAL Roman code without guessing linguistic information or silently losing marks?

## Current adapter behavior

`src/cal_mcp/normalization.py` already recognizes five input representations:

- `cal_code`
- `unicode_transliteration`
- `hebrew`
- `syriac`
- `roman_shared`

The existing normalization path is intentionally query-oriented, not a general converter. It converts only the simple consonantal CAL-code subset **from CAL code to Unicode transliteration** and otherwise passes supported Hebrew/Syriac/Unicode input through. Changing those semantics would alter existing request contracts, so issue #52 should add a separate pure conversion primitive and MCP tool rather than rewrite `normalize_query()`.

## Authoritative CAL evidence

### Current Roman coding table

CAL's live `prova.html` page was rechecked 2026-09-07:

https://cal.huc.edu/prova.html

It gives the core Roman code table:

| CAL code | consonant |
| --- | --- |
| `)` | aleph |
| `b` | beth |
| `g` | gimel |
| `d` | daleth |
| `h` | he |
| `w` | waw |
| `z` | zayin |
| `x` | heth |
| `T` | teth |
| `y` | yodh |
| `k` | kaph |
| `l` | lamedh |
| `m` | mem |
| `n` | nun |
| `s` | samekh |
| `(` | ayin |
| `p` | pe |
| `c` | tzade |
| `q` | qoph |
| `r` | resh |
| `$` | shin |
| `&` | sin |
| `t` | taw |
| `P` | emphatic p |

The same page separately documents Jewish-Aramaic vowels, Syriac diacritics/final punctuation, Mandaic extensions, `@` as a lexical-compound/multiword connector, and manuscript/editorial syntax. Those conventions are not one-to-one consequences of ordinary consonantal Unicode input and must not be synthesized by this converter.

### Unicode is a first-class modern CAL input representation

The CAL Text Entry and Format Manual note currently hosted at:

https://cal.huc.edu/pdfs/CalManualIntrol.pdf

states that texts may now be submitted in standard browser-recognizable fonts, explicitly including Unicode Hebrew and Syriac. It also says modern-font diacritics may be submitted directly and gives `tF` vs Syriac feminine-dot Unicode as an example. Therefore CAL's Unicode display/input conventions and its historical Roman storage/coding conventions must not be treated as globally lossless equivalents.

### CAL corpus inventory is broader than Hebrew/Syriac

The current CAL dialect/text inventory is materially broader than the first draft of this issue assumed.

CAL's current dialect taxonomy includes:

- Old Aramaic;
- Imperial Aramaic;
- Biblical Aramaic;
- Middle Aramaic, including Palmyrene, Nabataean, Hatran, and Qumran;
- Palestinian Aramaic, including CPA and Samaritan;
- Syriac;
- Babylonian Aramaic, including Mandaic;
- Late Jewish Literary Aramaic.

Current sources rechecked 2026-09-07:

- https://cal.huc.edu/pdfs/CalManualIntrol.pdf
- https://cal.huc.edu/Cal_dialect_codes.html
- https://cal.huc.edu/searching/basic_concordance.html

The live Middle Aramaic catalogue currently exposes substantial Palmyrene, Nabataean, Hatran, and Qumran corpora:

- https://cal.huc.edu/newshow_browsedialects.php?R1=4

The live Mandaic surface exposes canonical texts, prayers, ritual texts, and magic material:

- https://cal.huc.edu/show_Mandaic.php?R1=74

CAL also explicitly says active work continues on less-studied dialects including Mandaic, Samaritan, and Nabataean:

- https://cal.huc.edu/advantages.htm

### Dedicated Unicode scripts exist for several CAL corpus families

The current Unicode script inventory includes dedicated encodings for at least:

- Imperial Aramaic;
- Palmyrene;
- Nabataean;
- Hatran;
- Mandaic;
- Samaritan;
- Syriac and Hebrew.

Unicode also separately encodes other Aramaic-derived scripts (for example Elymaic and Manichaean). Their existence does **not** by itself put them into the v0.1 contract; CAL corpus evidence must decide relevance.

Authoritative Unicode sources:

- https://www.unicode.org/Public/draft/charts/
- https://unicode.org/versions/Unicode17.0.0/core-spec/chapter-10/

CPA does not require a distinct Unicode block for the ordinary CAL use case: its manuscript tradition is represented through Syriac-script characters, so CPA belongs under the Syriac-script conversion path unless corpus research demonstrates a distinct encoded requirement.

### CAL display script is not necessarily source palaeographic script

Do not infer source-script coverage from CAL HTML rendering alone. CAL often renders one attested Aramaic citation in Roman transliteration plus normalized Hebrew and Syriac forms even when the dialect is Palmyrene or another epigraphic variety. For example current Palmyrene entries display normalized transliteration/Hebrew/Syriac rather than requiring Palmyrene Unicode.

Therefore the converter's dedicated-script support must be based on Unicode character identity + historically corresponding consonantal value, while corpus-derived fixtures supply **attested lexical sequences**, not a claim that CAL itself stores those lines in the palaeographic Unicode block.

## Corpus-derived round-trip fixture policy

Synthetic alphabet tests remain necessary, but they are not enough. Add a small, fixed, reviewable set of attested CAL words/sequences from representative corpus families and use them as regression fixtures.

Fixture rules:

1. Use only a handful of short words or very short sequences per script family — ordinary scholarly quotation, not corpus replication.
2. Record CAL source/dialect + stable locator (text ID/coordinate/entry URL where available) and retrieval date.
3. Store only the minimal text required to exercise conversion; do not copy pages or bulk text.
4. Preserve the CAL Roman/transliteration form as the expected canonical code basis.
5. Independently encode the same consonantal sequence in the relevant Unicode script for the test input.
6. Test `Unicode-script → CAL code` and, where the supported mapping is bijective, the local reverse round trip.
7. Do not create a live test dependency on CAL: corpus samples become tiny offline fixtures after research verification.

This is deliberately a citation-sized fixture policy. It does not require or justify bulk extraction, corpus redistribution, or a derived local CAL corpus. The tests should contain only the minimum attested forms needed to establish mapping correctness.

Candidate corpus families for fixtures, subject to exact mapping verification:

- Imperial Aramaic / Official Aramaic;
- Palmyrene;
- Nabataean;
- Hatran;
- Samaritan Aramaic;
- Mandaic;
- CPA/Syriac;
- Jewish Aramaic/Hebrew script.

If a corpus family uses characters outside a clean one-to-one consonantal map, document the finite ambiguity when it can be enumerated exactly; otherwise reject the case rather than inventing a lossy transliteration policy.

## Safe v0.1 conversion contract

### 1. Unicode scholarly transliteration → CAL code

The inverse of the existing simple CAL consonant table is deterministic:

- `ˀ → )`
- `ˁ → (`
- `ḥ → x`
- `ṭ → T`
- `ṗ → P`
- `ṣ → c`
- `š → $`
- `ś → &`
- shared Roman consonants `b g d h w z y k l m n s p q r t` remain identical.

ASCII spaces remain spaces. The converter must not infer CAL `@`, because CAL documents `@` as a semantic connector for lexical compounds or words written as more than one unit; whitespace alone does not establish that condition.

### 2. Hebrew-script consonants → CAL code

The ordinary consonantal mapping is deterministic for:

`אבגדהוזחטיכךלמםנןסעפףצץקרת`

with final letters mapping to the same CAL code as their medial counterparts.

Hebrew `ש` is a special case because CAL distinguishes `$` (shin) from `&` (sin), while unpointed square-script `ש` does not encode which value is intended. Therefore:

- `שׁ` (shin dot) → `$`
- `שׂ` (sin dot) → `&`
- bare `ש` is a finite representational ambiguity and yields both `$` and `&` candidates; see `docs/research/issue-52-ambiguity-expansion.md`.

All other Hebrew combining marks (vowels, dagesh, accents, etc.) are outside the v0.1 converter contract unless separately researched. They must not be silently stripped. This leaves existing query normalization untouched, where pointed Hebrew may still pass through to CAL as Unicode.

### 3. Syriac-script consonants → CAL code

For ordinary Syriac consonantal letters, the following is deterministic:

`ܐ ܒ ܓ ܕ ܗ ܘ ܙ ܚ ܛ ܝ ܟ ܠ ܡ ܢ ܣ ܥ ܦ ܨ ܩ ܪ ܫ ܬ`

These map to the same core CAL consonant codes as the Hebrew/transliteration inventory; Syriac `ܫ` maps to `$` (shin).

Syriac vowel points, quššāyā/rukkāḵā marks, syame, feminine dot, punctuation, and other combining/editorial marks are deliberately unsupported until an exact CAL mapping is independently verified. CPA ordinary consonantal input follows this Syriac-script path.

### 4. Other dedicated Aramaic Unicode scripts

For Imperial Aramaic, Palmyrene, Nabataean, Hatran, Samaritan, and Mandaic, do not assume a mapping merely from alphabet order. Before implementation for each script:

- verify the Unicode character inventory and character names;
- verify the CAL Roman correspondence against an attested corpus sample;
- identify extra letters/orthographic distinctions (especially Mandaic) and their CAL codes;
- identify finite ambiguous graphemes (for example Hatran daleth-resh) and enumerate exact alternatives rather than guessing;
- identify punctuation/combining marks and reject them unless CAL's mapping is exact and documented;
- add a table-driven script map only after the above evidence is committed.

The release target is **coverage of every dedicated Unicode script that is both relevant to an actual CAL Aramaic corpus family and safely convertible under a deterministic or finitely ambiguous code table**. A script may be explicitly unsupported in v0.1 only if research records why conversion is not representable without linguistic inference or CAL does not actually expose a corresponding corpus/use case.

### 5. CAL code and shared Roman input

- Explicit/detected simple CAL code is passed through unchanged by the converter.
- Plain shared Roman consonants such as `mlk` are materially unambiguous for conversion because their CAL spelling is identical; they also pass through unchanged.
- The converter should not attempt to canonicalize broad CAL manuscript/editorial syntax. Existing CAL code remains the user's explicit representation and is preserved if valid under the current whitelist.

## Failure and ambiguity policy

Finite orthographic ambiguity is explicit output, not an error. Unknown/unverified transcription remains fail-closed.

In particular:

- researched ambiguous graphemes yield all justified CAL-code candidates;
- mixed scripts remain unsupported/ambiguous unless a specific mixed-script contract is researched;
- vowel/diacritic/editorial marks are not silently stripped;
- unsupported Unicode transliteration characters are rejected;
- morphology, roots, historical spelling, vowel restoration, and `@` connector inference are never attempted.

Detailed candidate expansion and bounded search semantics are defined in `docs/research/issue-52-ambiguity-expansion.md`.

## API shape

The pure local result must expose ambiguity rather than a guessed scalar. At minimum it should retain:

- `original`
- `representation`
- `strategy`
- per-word ordered CAL-code `candidates`
- ambiguity metadata where a grapheme has multiple CAL values.

A deterministic one-word input therefore has a one-element candidate list. The representation vocabulary must grow to explicit script identifiers for every supported dedicated Unicode script. Strategy values remain transformation-oriented (`*_to_cal_code`) rather than dialect claims.

Expose one MCP tool, `cal_convert_to_code`, that performs no CAL request and returns the typed conversion result.

## Compatibility / request-volume decision

Do not silently fan out exact-ID tools. The arbitrary Aramaic lexical query surface is `cal_lexicon_lookup`; ambiguity-aware search integration is specified in `docs/research/issue-52-ambiguity-expansion.md` and must use hard request bounds and prefix deduplication.

Existing deterministic Unicode query paths must retain their prior request behavior unless conversion is actually required.

## Testing implications

Test-first coverage must prove:

1. scholarly transliteration special letters map to exact CAL characters;
2. Hebrew medial/final consonants map correctly;
3. `שׁ`/`שׂ` map distinctly and bare `ש` yields both candidates;
4. Syriac consonants map correctly;
5. each researched additional Unicode script has alphabet-edge tests and at least one corpus-derived attested fixture;
6. supported simple CAL code/shared Roman input passes through;
7. unsupported marks fail rather than disappear;
8. finite ambiguous script characters enumerate all researched candidates;
9. supported CAL-code → Unicode/script → CAL-code round trips are exact where the mapping is bijective;
10. the public MCP tool is present, typed, structured, and local-only;
11. ambiguity-aware lexicon fan-out remains bounded and deduplicated;
12. existing deterministic normalization/request-count tests remain green.

## Conclusion

The initial Hebrew/Syriac-only scope is too narrow for a release-blocking CAL converter. CAL's own corpus taxonomy spans several Aramaic traditions with dedicated Unicode scripts. Before v0.1, issue #52 must inventory those scripts, support every safely deterministic or finitely ambiguous corpus-relevant mapping, and prove them with a small offline set of attested CAL examples. The converter must remain conservative: enumerate real representational ambiguity, but never silently drop marks or invent linguistic resolutions.