# Issue #52 research — Samaritan Unicode → CAL code

Date: 2026-09-07

## Scope

This gate covers only the dedicated Unicode **Samaritan** block. Imperial Aramaic, Palmyrene, Nabataean, and Hatran are already implemented under separate gates; Mandaic and CPA/Syriac evidence remain separate slices.

## CAL corpus evidence

CAL exposes the Samaritan Targum alongside the other Pentateuchal targums. The current CAL display for Genesis 37:2 contains the Samaritan phrase `יוסף בר שבעסרי`, giving the clean consonantal fixture `בר` (`br`).

- https://cal.huc.edu/showtargum.php?Peshitta=ON&Sam=ON&bookname=01&chapter=37&verse=2
- retrieval date: 2026-09-07

The dedicated-script test input below is **not** claimed to be CAL's display encoding. CAL currently renders this Samaritan witness in square Hebrew on that page. The test derives the equivalent Samaritan Unicode characters from their explicit letter identities and checks only the deterministic script → CAL-code layer.

## Unicode repertoire and script relevance

Unicode assigns the Samaritan block U+0800–U+083F and documents that the script is used for both Samaritan Hebrew and **Samaritan Aramaic**. It has 22 consonant letters, followed by consonant modifiers, vowel signs, a variant-reading sign, and punctuation.

Authoritative references:

- https://www.unicode.org/charts/nameslist/n_0800.html
- https://unicode.org/versions/Unicode17.0.0/core-spec/chapter-9/

The 22 encoded consonant letters are:

- U+0800 ALAF
- U+0801 BIT
- U+0802 GAMAN
- U+0803 DALAT
- U+0804 IY
- U+0805 BAA
- U+0806 ZEN
- U+0807 IT
- U+0808 TIT
- U+0809 YUT
- U+080A KAAF
- U+080B LABAT
- U+080C MIM
- U+080D NUN
- U+080E SINGAAT
- U+080F IN
- U+0810 FI
- U+0811 TSAADIY
- U+0812 QUF
- U+0813 RISH
- U+0814 SHAN
- U+0815 TAAF

Unicode separately classifies U+0816 onward as consonant modifiers, vowels/modifier letters, a variant-reading sign, and punctuation. Those are outside the v0.1 consonantal conversion contract and must not be silently stripped.

## CAL coding correspondence

CAL's own coding-conventions table defines the consonantal Roman codes used by the converter:

- https://cal.huc.edu/prova.html
- https://cal.huc.edu/searching/fullbrowser.html

The Samaritan consonant identities correspond to the same Northwest Semitic letters represented by CAL's consonantal codes:

| Samaritan Unicode identity | CAL code(s) |
| --- | --- |
| ALAF | `)` |
| BIT | `b` |
| GAMAN | `g` |
| DALAT | `d` |
| IY | `h` |
| BAA | `w` |
| ZEN | `z` |
| IT | `x` |
| TIT | `T` |
| YUT | `y` |
| KAAF | `k` |
| LABAT | `l` |
| MIM | `m` |
| NUN | `n` |
| SINGAAT | `s` |
| IN | `(` |
| FI | `p` |
| TSAADIY | `c` |
| QUF | `q` |
| RISH | `r` |
| SHAN | `$`, `&` |
| TAAF | `t` |

The non-obvious Samaritan names (`IY`, `BAA`, `IT`, etc.) are letter identities within the standard 22-letter Samaritan alphabet, not phonetic instructions. Conversion must preserve orthographic identity rather than modern Samaritan pronunciation.

## SHAN is finite orthographic ambiguity

CAL distinguishes `$ = shin` and `& = sin`; its browser table likewise distinguishes the corresponding scholarly Unicode values `š` and `ś`. Unicode Samaritan, however, encodes only one consonant letter U+0814 `SHAN` in the 22-letter alphabet and provides no separate Samaritan sin character.

Therefore a typed bare Samaritan `ࠔ` does not by itself preserve the CAL shin/sin distinction. The safe deterministic contract is the same finite-ambiguity policy already used for bare square-Hebrew `ש`:

- U+0814 `ࠔ` → ordered candidates `("$", "&")`;
- record `CalCodeAmbiguity` at the character position;
- never choose one variant from lexical context.

For the complete 22-letter sequence, the expected candidates are:

- `)bgdhwzxTyklmns(pcqr$t`
- `)bgdhwzxTyklmns(pcqr&t`

## Attested CAL fixture

Use `br` from the Samaritan Targum at Genesis 37:2 (`יוסף בר שבעסרי`):

- Samaritan Unicode input: `ࠁࠓ` = BIT + RISH
- expected CAL candidate: `br`
- provenance: Samaritan Targum, Gen 37:2, CAL targum display, retrieved 2026-09-07

This is deliberately tiny and citation-sized.

## Bounded ambiguity

The shared converter contract limits expansion to 32 candidates per word. Repeated U+0814 SHAN therefore reuses the existing bound:

- five SHAN characters may produce exactly 32 candidates;
- a sixth would require 64 and must raise `ConversionExpansionError` rather than truncate or guess.

## Failure boundary

Supported:

- U+0800–U+0815 consonant letters;
- ASCII spaces between words;
- U+0814 as explicit finite `$`/`&` ambiguity.

Rejected:

- U+0816–U+0819 consonant modifiers;
- U+081A–U+082D modifier letters, vowels, and variant-reading marks;
- U+0830–U+083E punctuation;
- unassigned Samaritan block code points;
- mixed Samaritan with another detected script;
- ambiguity expansions above 32 candidates.

No mark is stripped or interpreted phonologically in v0.1.

## Implementation implication

Add explicit `samaritan` representation and `samaritan_to_cal_code` strategy. Use a table whose values are ordered tuples of CAL alternatives, with U+0814 mapped to `("$", "&")` and all other researched consonants mapped to one-element tuples. Detection is block-aware; validation accepts only the researched consonant table plus existing separators. Conversion records ambiguity metadata and delegates expansion to the existing bounded `_append_alternatives` helper.