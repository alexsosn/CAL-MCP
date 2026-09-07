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

### Current search UI accepts several representations

CAL's live lexicon browser states that users may enter initial letters in Roman, Hebrew, or Syriac. Its current jump alphabet distinguishes both shin and sin. CAL's advantages page likewise says searching may use Roman transliteration, Unicode, Square/Hebrew script, or Syriac keyboards.

Relevant live pages rechecked 2026-09-07:

- https://cal.huc.edu/browseJLAKEYheaders.php
- https://cal.huc.edu/advantages.htm

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
- bare `ש` must fail as ambiguous rather than guess.

All other Hebrew combining marks (vowels, dagesh, accents, etc.) are outside the v0.1 converter contract. They must fail explicitly rather than be stripped. This leaves existing query normalization untouched, where pointed Hebrew may still pass through to CAL as Unicode.

### 3. Syriac-script consonants → CAL code

For ordinary Syriac consonantal letters, the following is deterministic:

`ܐ ܒ ܓ ܕ ܗ ܘ ܙ ܚ ܛ ܝ ܟ ܠ ܡ ܢ ܣ ܥ ܦ ܨ ܩ ܪ ܫ ܬ`

These map to the same core CAL consonant codes as the Hebrew/transliteration inventory; Syriac `ܫ` maps to `$` (shin).

Syriac vowel points, quššāyā/rukkāḵā marks, syame, feminine dot, punctuation, and other combining/editorial marks are deliberately unsupported in this first conversion contract. CAL has explicit Roman codes for several of them, but a correct comprehensive Unicode→CAL transcription layer requires a separate reviewed mapping rather than silent mark deletion.

### 4. CAL code and shared Roman input

- Explicit/detected simple CAL code is passed through unchanged by the converter.
- Plain shared Roman consonants such as `mlk` are materially unambiguous for conversion because their CAL spelling is identical; they also pass through unchanged.
- The converter should not attempt to canonicalize broad CAL manuscript/editorial syntax. Existing CAL code remains the user's explicit representation and is preserved if valid under the current whitelist.

## Failure policy

Fail closed with `UnsupportedQueryError` or `AmbiguousQueryError` when conversion would require information not present in the input. In particular:

- mixed Hebrew/Syriac input remains ambiguous;
- bare Hebrew `ש` is ambiguous between `$` and `&`;
- Hebrew or Syriac vowel/diacritic/editorial marks are not silently stripped;
- unsupported Unicode transliteration characters are rejected;
- morphology, roots, historical spelling, vowel restoration, and `@` connector inference are never attempted.

## API shape

Add a pure local result type with at least:

- `original`
- `cal_code`
- `representation`
- `strategy`

Suggested strategies:

- `pass_through`
- `unicode_transliteration_to_cal_code`
- `hebrew_to_cal_code`
- `syriac_to_cal_code`

Expose one MCP tool, `cal_convert_to_code`, that performs no CAL request and returns the typed conversion result. An optional explicit representation selector may be accepted for cases where auto-detection is insufficient, but it must reuse the existing `InputRepresentation` vocabulary.

## Compatibility / request-volume decision

Do **not** route existing lookup/search tools through the new converter in issue #52. They already send Unicode representations that CAL accepts. The new capability is additive and local, so existing normalization, cache keys, request counts, and CAL load remain unchanged.

## Testing implications

Test-first coverage should prove:

1. scholarly transliteration special letters map to exact CAL characters;
2. Hebrew medial/final consonants map correctly;
3. `שׁ`/`שׂ` map distinctly and bare `ש` fails;
4. Syriac consonants map correctly;
5. supported simple CAL code/shared Roman input passes through;
6. Hebrew/Syriac vocalization or unsupported marks fail rather than disappear;
7. supported CAL-code → Unicode → CAL-code round trips are exact where the mapping is bijective (excluding semantic `@`/space collapse);
8. the public MCP tool is present, typed, structured, and local-only;
9. existing normalization tests remain unchanged and green.

## Conclusion

A useful v0.1 converter is feasible without linguistic guessing: support the core consonantal inventories and the existing scholarly transliteration alphabet, preserve valid CAL code, distinguish Hebrew shin/sin only when the script encodes the distinction, and reject marks whose CAL coding would require a larger transcription policy. Comprehensive vowel/diacritic/editorial transcription should be a later feature, not an implicit lossy extension of this must-have converter.