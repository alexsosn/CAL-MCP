# Issue #52 research — Mandaic Unicode → CAL code

Date: 2026-09-07

## Scope

This gate covers the dedicated Unicode **Mandaic** block and, in particular, the Mandaic-specific CAL Roman codes and extra letters required by issue #52. Samaritan and the epigraphic dedicated scripts are already implemented under separate gates. CPA/Syriac evidence remains a separate final script-family slice.

## CAL corpus relevance

CAL has a substantial Mandaic corpus and marks Mandaic as a Babylonian-Aramaic dialect family. Current CAL lexical pages expose Mandaic citations from canonical texts such as the John Book and Ginza.

A citation-sized current fixture is JohnBook 24:3, shown by CAL under the `mdˁ` entry:

`brik šumẖ ḏmanda ḏhiia uhiia zakin`

- https://cal.huc.edu/cal_entry_web.php?lemma=md%28+N
- retrieval date: 2026-09-07

This gives two useful short Mandaic sequences without redistributing corpus text:

- `šumẖ`
- `ḏmanda`

## CAL Mandaic Roman coding is not the generic consonantal table

The live CAL Roman-coding page currently documents the Mandaic-specific extensions:

- `D = ḏ`
- `H = ẖ`
- `S = ṣ`

Source:

- https://cal.huc.edu/prova.html
- retrieval date: 2026-09-07

The CAL Text Entry and Format Manual additionally defines a Mandaic character set derived from the Drower-Macuch transliteration scheme. Its ordered set is:

`a b g d h u z H T i k l m n s ( p S q r [shin] t` and `D` for the Mandaic `ḏ` ligature.

The manual explicitly explains two important departures from a naive historical-consonant mapping:

1. the ordinary Mandaic `h` sign is coded `h`, while the pronominal-suffix / ẖ value is coded `H`;
2. the Mandaic `ḏ` ligature is coded uppercase `D` in Roman/Mandaic input.

It also requires all other ligatures to be resolved into their constituent consonants.

Source:

- https://cal.huc.edu/pdfs/CalManualIntrol.pdf

The extracted older set-IV table renders the shin slot inconsistently as `§`, while an immediately following Mandaic example is `$nat ... lmalka`, and the current live CAL coding page unambiguously defines `$ = shin`. The v0.1 converter therefore uses the **current live `$` code**, not the stale/ambiguous `§` rendering.

## Unicode Mandaic repertoire

Unicode assigns Mandaic letters at U+0840–U+0858:

- U+0840 HALQA
- U+0841 AB
- U+0842 AG
- U+0843 AD
- U+0844 AH
- U+0845 USHENNA
- U+0846 AZ
- U+0847 IT
- U+0848 ATT
- U+0849 AKSA
- U+084A AK
- U+084B AL
- U+084C AM
- U+084D AN
- U+084E AS
- U+084F IN
- U+0850 AP
- U+0851 ASZ
- U+0852 AQ
- U+0853 AR
- U+0854 ASH
- U+0855 AT
- U+0856 DUSHENNA
- U+0857 KAD
- U+0858 AIN

U+0859–U+085B are combining marks for affrication, vocalization, and gemination; U+085E is punctuation.

Authoritative Unicode references:

- https://www.unicode.org/charts/nameslist/n_0840.html
- https://unicode.org/versions/Unicode17.0.0/core-spec/chapter-10/

Unicode describes DUSHENNA as the additional Mandaic letter/ligature representing `ḏ`/`di`, KAD as the `kḏ` digraph that can alternatively be written AK + DUSHENNA, and AIN as a borrowed Arabic ayin. The combining marks alter pronunciation contextually rather than naming independent CAL Roman characters.

## Exact v0.1 mapping

The inherited Mandaic alphabet must follow CAL's Mandaic set rather than the generic Hebrew/Syriac consonant table:

| Unicode | CAL code |
| --- | --- |
| HALQA | `a` |
| AB | `b` |
| AG | `g` |
| AD | `d` |
| AH | `h` |
| USHENNA | `u` |
| AZ | `z` |
| IT | `H` |
| ATT | `T` |
| AKSA | `i` |
| AK | `k` |
| AL | `l` |
| AM | `m` |
| AN | `n` |
| AS | `s` |
| IN | `(` |
| AP | `p` |
| ASZ | `S` |
| AQ | `q` |
| AR | `r` |
| ASH | `$` |
| AT | `t` |
| DUSHENNA | `D` |

The expected U+0840–U+0856 sequence is therefore:

`abgdhuzHTiklmns(pSqr$tD`

This explicitly exercises CAL's Mandaic `D`, `H`, and `S` codes.

### KAD

U+0857 KAD is deterministic but expands one Unicode character to two CAL characters:

`KAD → kD`

Rationale:

- Unicode defines it as the `kḏ` digraph and allows AK + DUSHENNA as an equivalent spelling;
- CAL says that, except for the special DUSHENNA ligature itself, Mandaic ligatures are resolved into their constituents;
- AK maps to `k`, DUSHENNA to `D`.

This is a deterministic string expansion, not an ambiguity and therefore produces no `CalCodeAmbiguity` item.

### AIN

U+0858 AIN is **explicitly unsupported in v0.1**.

Unicode identifies it as a borrowed Arabic ayin, not part of the ordinary inherited Mandaic alphabet. The older CAL manual says Arabic ayin may be indicated by a special `ˑ` sign, but the current live CAL Roman-coding page does not document that character as a current Mandaic code, and the current CAL-MCP CAL-code whitelist does not include it. That is insufficient evidence to add a new public CAL code safely.

Accordingly `ࡘ` must raise `UnsupportedQueryError` until current CAL behavior for that borrowed letter is independently verified. This satisfies the issue requirement to handle Mandaic-specific extras explicitly without inventing a mapping.

## Combining marks and punctuation

U+0859 AFFRICATION MARK, U+085A VOCALIZATION MARK, and U+085B GEMINATION MARK remain unsupported. Unicode documents them as context-sensitive pronunciation/orthographic marks. The CAL manual has historical notation for some Arabic/Persian diacritics, but no current exact one-to-one mapping from these Unicode marks to the current CAL Roman contract has been established.

They must therefore fail closed rather than disappear or trigger phonological inference. U+085E punctuation and unassigned block characters are likewise unsupported.

## Attested CAL fixtures

Use JohnBook 24:3 from the current CAL `mdˁ` entry:

1. `šumẖ`
   - Unicode Mandaic input: `ࡔࡅࡌࡇ` = ASH + USHENNA + AM + IT
   - expected CAL code: `$umH`

2. `ḏmanda`
   - Unicode Mandaic input: `ࡖࡌࡀࡍࡃࡀ` = DUSHENNA + AM + HALQA + AN + AD + HALQA
   - expected CAL code: `Dmanda`

These fixtures verify the unusual Mandaic vowel-letter and `D/H` behavior against an attested CAL citation while remaining tiny and offline.

## Failure boundary

Supported:

- U+0840–U+0856 with the exact CAL Mandaic set mapping above;
- U+0857 KAD as deterministic `kD` expansion;
- ASCII spaces between words.

Rejected:

- U+0858 borrowed AIN pending a current CAL-code verification;
- U+0859–U+085B combining marks;
- U+085E punctuation and unassigned Mandaic-block code points;
- mixed Mandaic with another detected script.

No Mandaic character in the supported set creates finite candidate ambiguity, so the existing candidate-expansion ceiling is not exercised by this script slice.

## Implementation implication

Add explicit `mandaic` representation and `mandaic_to_cal_code` strategy. Use a strict mapping table whose values are output strings, including `kD` for U+0857. Detection is block-aware; validation accepts only U+0840–U+0857 plus existing separators. U+0858 and all marks/punctuation fail explicitly. The converter remains pure/local and must not add CAL requests.